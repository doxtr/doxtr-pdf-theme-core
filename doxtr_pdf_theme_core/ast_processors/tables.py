"""AST processor for table positioning and styling.

This module handles:
- Vertical mode fix for block elements after run-in paragraph headings
- Phase 1: No-break pattern protection and natural-break injection for table cells
- Phase 2: Content-aware column width computation for tables with colwidths-given

Header row colouring is handled separately by Sphinx's ``colorrows`` machinery via
``\\sphinxTableRowColorHeader`` defined in the table ``.tex_t`` templates.
This works uniformly for all table types (tabular, tabulary, longtable).

The ``doxtr_enable_table_processor`` config flag gates execution of all
table processing (Phase 1, Phase 2, and the paragraph fix).

Architecture / Data Flow
------------------------

1. **Phase 1** (this module, priority 996): Walks all ``entry`` nodes in each
   table. For text nodes not inside references, applies nobreak pattern matching
   (wrapping matched tokens in ``\\mbox{}``) and break-char injection (inserting
   ``\\allowbreak`` after configurable characters in long tokens). Phase 1 also
   collects per-column nobreak metrics (max nobreak token length per column).

2. **Phase 2** (this module, same pass): For tables with the ``colwidths-given``
   class, or tables with ``colwidths-auto`` / no width class, uses the Phase 1
   metrics plus a full content analysis pass to compute optimal column widths
   via the configured algorithm (default: ``minfloor``). Updates ``colspec``
   node ``colwidth`` attributes with the new proportions and promotes
   non-colwidths-given tables to ``colwidths-given`` so Sphinx uses
   proportional ``\\X`` columns instead of tabulary auto-sizing.
   Stores ``doxtr_min_table_width_mm`` on the table node (sum of minimum column
   widths in mm) for downstream use.

3. **Phase 3** (in ``landscape.py``, priority 1001): Uses column-count
   heuristic and the ``doxtr_min_table_width_mm`` attribute from Phase 2 for
   adaptive page sizing. When the content-aware minimum exceeds the generic
   heuristic (col_count × 22mm), Phase 3 derives a synthetic effective column
   count to select a larger page. Child themes can replace the entire
   landscape wrapping logic via ``register_landscape_wrapper``.
"""

import re
from dataclasses import dataclass
from typing import Callable, Dict, List

from docutils import nodes
from sphinx.util import logging

from ..core_config import DOXTR_TABLES
from ..latex_escape import esc_latex

__all__ = [
    'process_tables_ast',
    'fix_block_after_paragraph',
    'PARAGRAPH_FIX_PRIORITY',
    'register_par_fix_block_type',
    'register_par_fix_skip_type',
    'register_column_width_algorithm',
    'ColumnInfo',
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default config values (used when config attributes are absent)
# ---------------------------------------------------------------------------

#: Default regex patterns for tokens that must never be line-broken.
#: Canonical source: DOXTR_TABLES['generic']['nobreak_patterns'] in core_config.py.
DEFAULT_NOBREAK_PATTERNS: List[str] = DOXTR_TABLES['generic']['nobreak_patterns']

#: Default characters at which non-protected values may be broken.
DEFAULT_BREAK_CHARS = '-/.:'

#: Default column width algorithm name.
DEFAULT_ALGORITHM = 'minfloor'

#: Conversion factor from typographic points to millimeters (1pt = 0.3528mm).
PT_TO_MM = 0.3528

#: Reference textwidth for proportional column width computation.
#: Derived from A4 landscape page width: 297mm - 2*15mm margins = 267mm.
#: .. deprecated:: 1.1.5
#:    No longer used internally; kept for child themes that may import it.
#:    Use ``_LANDSCAPE_TEXTWIDTHS_MM[0]`` for the A4 landscape textwidth.
A4_LANDSCAPE_TEXTWIDTH_MM = 267.0

#: Reference textwidth for portrait A4 (worst-case for proportional columns).
#: Derived from A4 portrait: 210mm - 2cm left margin - 3cm right margin = 160mm.
#: Using portrait as the reference ensures minimum column widths are sufficient
#: even when the table is NOT auto-rotated to landscape.
A4_PORTRAIT_TEXTWIDTH_MM = 160.0

#: Fallback character width in mm (11.5pt * 0.6 * PT_TO_MM).
FALLBACK_CHAR_WIDTH_MM = 2.43

#: Default minimum column width in mm, matching ``\doxtr@mincolwidth`` in the
#: LaTeX preamble.  Used by Phase 2 (tables.py) to predict page size and by
#: Phase 3 (landscape.py) to derive effective column counts.
DEFAULT_MIN_COL_WIDTH_MM = 22.0

#: Width multiplier for header text relative to body text.
#: Bold sans-serif fonts (e.g. Montserrat Bold) are typically 30-40% wider
#: per character than proportional body text. This factor ensures columns
#: are wide enough to display header words without clipping.
DEFAULT_HEADER_CHAR_WIDTH_FACTOR = 1.35

#: Width multiplier for words that are predominantly uppercase.
#: Uppercase letters in proportional serif/sans fonts (e.g. Spectral Regular)
#: are approximately 18% wider per character than the average (which includes
#: lowercase). Measured from actual Spectral font metrics:
#:   uppercase avg = 2.87mm vs mono-based estimate = 2.43mm at 11.5pt.
#: Applied when >50% of a word's alphabetic characters are uppercase.
DEFAULT_UPPERCASE_WIDTH_FACTOR = 1.2

#: Per-column overhead from LaTeX tabcolsep and arrayrulewidth, in mm.
#: Sphinx's \\X{w}{total} column type subtracts (2*tabcolsep + arrayrulewidth)
#: from each column's proportional share. Default tabcolsep = 6pt = 2.116mm,
#: arrayrulewidth ~ 0.4pt = 0.14mm. Total overhead per column ~ 4.37mm.
#: This is converted to character units and added to min_width_chars so that
#: the proportional allocation accounts for this fixed per-column cost.
TABCOLSEP_OVERHEAD_MM = 4.37

#: Additional padding characters to add to minimum column width.
#: Accounts for font metric estimation errors and rendering tolerances.
#: Expressed in character units.
MIN_WIDTH_PADDING_CHARS = 1

#: Minimum token length (without whitespace) before break-char injection.
MIN_TOKEN_LENGTH_FOR_BREAKS = 15

#: A-series landscape page textwidths (pagewidth - 2*15mm margins).
#: Used to predict which page size Phase 3 will select, so Phase 2 can
#: compute proportions against the correct available width.
_LANDSCAPE_TEXTWIDTHS_MM = [
    267.0,   # A4 landscape
    390.0,   # A3 landscape
    564.0,   # A2 landscape
    811.0,   # A1 landscape
    1159.0,  # A0 landscape
    1652.0,  # 2A0 landscape
    2348.0,  # 4A0 landscape
]

# ---------------------------------------------------------------------------
# Paragraph fix (existing functionality, unchanged)
# ---------------------------------------------------------------------------

#: Node types to skip when finding the first "real" body child of a section.
#: These are metadata/structural nodes that appear between the section title
#: and the actual content.
_SKIP_TYPES = (
    nodes.title,
    nodes.target,
    nodes.comment,
    nodes.system_message,
)

#: Block-level node types that need vertical mode when following a heading.
#: - table: csv-table, list-table, etc.
#: - figure: image with caption
#: - container: generic .. container:: directive (often wraps tables/figures
#:   from other extensions or custom directives)
_BLOCK_TYPES = (nodes.table, nodes.figure, nodes.container)

#: Event priority for the paragraph fix. Runs after the landscape processor
#: (985) -- landscape-wrapped content starts on a new page and does not need
#: the \par fix.
PARAGRAPH_FIX_PRIORITY = 980


def register_par_fix_block_type(node_type):
    """Register an additional node type that needs the vertical mode fix.

    Call at module level or inside ``setup()`` -- before ``config_inited``
    fires (priority 900).

    Args:
        node_type: A docutils node class (e.g., ``nodes.admonition``).
    """
    global _BLOCK_TYPES
    if node_type not in _BLOCK_TYPES:
        _BLOCK_TYPES = _BLOCK_TYPES + (node_type,)


def register_par_fix_skip_type(node_type):
    """Register an additional node type to skip when scanning for first body child.

    Call at module level or inside ``setup()`` -- before ``config_inited``
    fires (priority 900).

    Args:
        node_type: A docutils node class (e.g., ``nodes.decoration``).
    """
    global _SKIP_TYPES
    if node_type not in _SKIP_TYPES:
        _SKIP_TYPES = _SKIP_TYPES + (node_type,)


def fix_block_after_paragraph(app, doctree, docname):
    r"""Insert \leavevmode\par before block elements that follow section titles.

    In KOMA-Script, ``\paragraph`` and ``\subparagraph`` headings use a
    negative ``afterskip``, making them "run-in" headings where following
    content continues on the same line.  When a table, figure, or container
    is the first body element after such a heading, it renders to the side
    of the heading text instead of below it.

    This function inserts a raw ``\leavevmode\par`` LaTeX node before such
    block elements, forcing LaTeX back into vertical mode.  For block-level
    headings (section, subsection, etc.) that already have positive afterskip,
    ``\par`` in vertical mode is a no-op, making this safe at all depths.

    Skipped if ``doxtr_enable_table_processor`` is False.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if not getattr(app.config, 'doxtr_enable_table_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return

    for section_node in list(doctree.findall(nodes.section)):
        if section_node.get('doxtr_par_fix_processed'):
            continue
        section_node['doxtr_par_fix_processed'] = True

        # Find first non-metadata child after the title, tracking index
        first_block = None
        first_block_idx = None
        for idx, child in enumerate(section_node.children):
            if isinstance(child, _SKIP_TYPES):
                continue
            first_block = child
            first_block_idx = idx
            break

        if first_block is None:
            continue

        if not isinstance(first_block, _BLOCK_TYPES):
            continue

        # Insert \leavevmode\par before the block element
        par_node = nodes.raw('', '\n' + r'\leavevmode\par' + '\n', format='latex')
        section_node.insert(first_block_idx, par_node)
        logger.debug(
            '[Doxtr Tables] Inserted \\par before %s in %s',
            first_block.__class__.__name__, docname,
        )


# ---------------------------------------------------------------------------
# Phase 2: Column width algorithm registry (pluggable)
# ---------------------------------------------------------------------------

@dataclass
class ColumnInfo:
    """Per-column content metrics used by width algorithms.

    Attributes:
        min_width_chars: Effective minimum width in character units, accounting
            for header font width factor and padding.
        raw_body_min_chars: Longest unbreakable word in body cells (no scaling).
        raw_header_min_chars: Longest unbreakable word in header cells (no scaling).
        avg_content_chars: Average character count across all cells in this column.
        header_text: The column header text (if available).
    """
    min_width_chars: int = 0
    raw_body_min_chars: int = 0
    raw_header_min_chars: int = 0
    avg_content_chars: float = 0.0
    header_text: str = ''


#: Registry for pluggable column width algorithms.
#: Keys are algorithm names, values are callables with signature:
#:   fn(columns: list[ColumnInfo], available_width_chars: int) -> list[int]
#: Returns a list of relative column widths (same semantics as colspec values).
_column_width_algorithms: Dict[str, Callable[[List['ColumnInfo'], int], List[int]]] = {}


def register_column_width_algorithm(name: str, fn: Callable):
    """Register a custom column width algorithm.

    Logs a warning if overwriting an existing algorithm with the same name.

    Args:
        name: Algorithm identifier (referenced by doxtr_table_column_width_algorithm).
        fn: Callable with signature fn(columns: list[ColumnInfo], available_width_chars: int) -> list[int].
            Returns a list of relative column widths (same semantics as colspec).
    """
    if name in _column_width_algorithms:
        logger.warning('[Doxtr Tables] Overwriting column width algorithm: %s', name)
    _column_width_algorithms[name] = fn


def _algorithm_minfloor(columns: List[ColumnInfo], available_width_chars: int) -> List[int]:
    """Algorithm A (minfloor): floor each column at its longest word, distribute remainder.

    Each column gets at least its longest-word width. Remaining space is
    distributed proportional to avg_content_length of wrappable columns
    (those with avg_content > min_width).

    Args:
        columns: Per-column metrics.
        available_width_chars: Total available width in character units.

    Returns:
        List of relative column widths (integer proportions).
    """
    if not columns:
        return []

    min_widths = [max(c.min_width_chars, 1) for c in columns]
    total_min = sum(min_widths)

    if total_min >= available_width_chars:
        # Cannot fit; proportional to min_width (same as maxcontent).
        return min_widths

    remaining = available_width_chars - total_min
    # Distribute remaining based on avg_content_chars minus min_width.
    # Columns with more average content get more wrapping space.
    extras = [max(c.avg_content_chars - mw, 0.0) for c, mw in zip(columns, min_widths)]
    total_extra = sum(extras)

    if total_extra == 0:
        # All columns have avg == min; distribute evenly.
        per_col = remaining / len(columns)
        return [int(round(mw + per_col)) for mw in min_widths]

    result = []
    for mw, extra in zip(min_widths, extras):
        share = remaining * (extra / total_extra)
        result.append(int(round(mw + share)))
    return result


def _algorithm_maxcontent(columns: List[ColumnInfo], available_width_chars: int) -> List[int]:
    """Algorithm B (maxcontent): each column proportional to its longest word.

    Simple algorithm that ensures every column can fit its longest word
    but does not give extra wrapping space to description columns.

    Args:
        columns: Per-column metrics.
        available_width_chars: Total available width in character units.

    Returns:
        List of relative column widths (integer proportions).
    """
    if not columns:
        return []
    return [max(c.min_width_chars, 1) for c in columns]


# Register built-in algorithms.
_column_width_algorithms['minfloor'] = _algorithm_minfloor
_column_width_algorithms['maxcontent'] = _algorithm_maxcontent


# ---------------------------------------------------------------------------
# Phase 1: No-break protection and natural-break injection helpers
# ---------------------------------------------------------------------------

def _is_inside_reference(node):
    """Return True if node is a descendant of a reference node or has refuri.

    Args:
        node: A docutils node to check ancestry of.

    Returns:
        True if the node is inside a reference (hyperlink) node.
    """
    parent = node.parent
    while parent is not None:
        if isinstance(parent, nodes.reference):
            return True
        if hasattr(parent, 'get') and parent.get('refuri'):
            return True
        parent = parent.parent
    return False


def _compile_nobreak_patterns(pattern_strings: List[str]):
    """Compile a list of regex pattern strings into compiled regex objects.

    Invalid patterns are logged as warnings and skipped.

    Args:
        pattern_strings: List of regex pattern strings to compile.

    Returns:
        A single compiled regex with all patterns combined via alternation,
        or None if no valid patterns.
    """
    valid = []
    for ps in pattern_strings:
        try:
            re.compile(ps)
            valid.append(ps)
        except re.error as e:
            logger.warning(
                '[Doxtr Tables] Invalid nobreak pattern %r: %s', ps, e
            )
    if not valid:
        return None
    # Combine into a single regex with alternation for efficiency.
    combined = '|'.join(f'(?:{p})' for p in valid)
    return re.compile(combined)


def _split_by_nobreak(text: str, pattern) -> list:
    """Split text into segments: matched (nobreak) and unmatched (breakable).

    Args:
        text: The text string to split.
        pattern: Compiled regex (from _compile_nobreak_patterns) or None.
            If None, the entire text is returned as a single breakable segment.

    Returns:
        List of tuples ``(substring, is_nobreak)`` where ``is_nobreak`` is True
        for substrings that matched the nobreak pattern.
    """
    if pattern is None:
        return [(text, False)]

    result = []
    last_end = 0
    for match in pattern.finditer(text):
        start, end = match.span()
        if start > last_end:
            result.append((text[last_end:start], False))
        result.append((text[start:end], True))
        last_end = end
    if last_end < len(text):
        result.append((text[last_end:], False))
    return result


def _inject_breaks_into_text(text: str, break_chars: str) -> list:
    r"""Insert \allowbreak after break_chars in long tokens.

    Only injects breaks into tokens (whitespace-separated words) that
    exceed MIN_TOKEN_LENGTH_FOR_BREAKS characters.

    Args:
        text: The text content to process.
        break_chars: String of characters after which ``\allowbreak{}`` nodes
            are inserted (e.g. ``'-/.:``').

    Returns:
        List of docutils nodes (``nodes.Text`` for plain text segments and
        ``nodes.raw`` for LaTeX ``\allowbreak{}`` injections).
    """
    result_nodes = []
    # Split on whitespace to identify tokens, preserving whitespace.
    parts = re.split(r'(\s+)', text)
    for part in parts:
        if not part:
            continue
        # Whitespace parts pass through unchanged.
        if part.isspace():
            result_nodes.append(nodes.Text(part))
            continue
        # Short tokens pass through unchanged.
        if len(part) <= MIN_TOKEN_LENGTH_FOR_BREAKS:
            result_nodes.append(nodes.Text(part))
            continue
        # Long token: inject \allowbreak after each break_char.
        # We merge each text+\allowbreak pair into a single raw LaTeX node
        # so Sphinx's writer does not insert newlines between them (which
        # LaTeX would render as visible whitespace).
        segments = []
        current = []
        for ch in part:
            current.append(ch)
            if ch in break_chars:
                # Merge text + \allowbreak into one raw node.
                escaped = esc_latex(''.join(current))
                segments.append(escaped + r'\allowbreak{}')
                current = []
        if current:
            if segments:
                # Trailing segment after at least one break: escape and
                # merge into the same raw node so no newline appears
                # between the last \allowbreak and the remaining text.
                segments.append(esc_latex(''.join(current)))
            else:
                # No break chars found at all: keep as a Text node so
                # Sphinx's LaTeX writer applies its full escaping
                # (sphinxhyphen, etc.).
                result_nodes.append(nodes.Text(''.join(current)))
        if segments:
            result_nodes.append(nodes.raw(
                '', ''.join(segments), format='latex'
            ))
    return result_nodes


def _process_text_node(text_node, nobreak_pattern, break_chars: str):
    r"""Process a single Text node: apply nobreak wrapping and break injection.

    Args:
        text_node: A docutils ``nodes.Text`` instance to process.
        nobreak_pattern: Compiled regex for nobreak token detection, or None.
        break_chars: String of characters at which breakable text may be split.

    Returns:
        Tuple of ``(replacement_nodes, nobreak_lengths)``:
        - replacement_nodes: list of nodes to replace the original text node
        - nobreak_lengths: list of int lengths of nobreak-matched tokens found
    """
    text = text_node.astext()
    if not text:
        return [text_node], []

    segments = _split_by_nobreak(text, nobreak_pattern)
    replacement = []
    nobreak_lengths = []

    for segment_text, is_nobreak in segments:
        if not segment_text:
            continue
        if is_nobreak:
            # Escape for LaTeX and wrap in \mbox{} to prevent breaking.
            escaped = esc_latex(segment_text)
            raw_latex = r'\mbox{' + escaped + '}'
            replacement.append(nodes.raw('', raw_latex, format='latex'))
            nobreak_lengths.append(len(segment_text))
        else:
            # Inject \allowbreak at break_chars for long tokens.
            replacement.extend(_inject_breaks_into_text(segment_text, break_chars))

    return replacement, nobreak_lengths


def _is_predominantly_uppercase(word: str) -> bool:
    """Return True if more than 50% of alphabetic characters are uppercase.

    Non-alphabetic characters (digits, punctuation) are ignored for the ratio
    calculation. Returns False for words with no alphabetic characters.

    Args:
        word: The word to check.

    Returns:
        True if the word is predominantly uppercase.
    """
    alpha_chars = [c for c in word if c.isalpha()]
    if not alpha_chars:
        return False
    upper_count = sum(1 for c in alpha_chars if c.isupper())
    return upper_count > len(alpha_chars) * 0.5


def _effective_word_width_chars(word: str, uppercase_factor: float = DEFAULT_UPPERCASE_WIDTH_FACTOR) -> float:
    """Compute the effective width of a word in character units, accounting for uppercase.

    Words that are predominantly uppercase are scaled by the uppercase_factor
    to account for wider character glyphs in proportional fonts.

    Args:
        word: The word to measure.
        uppercase_factor: Multiplier for predominantly uppercase words.

    Returns:
        Effective width in character units (may be fractional).
    """
    if not word:
        return 0.0
    if _is_predominantly_uppercase(word):
        return len(word) * uppercase_factor
    return float(len(word))


def _get_longest_unbreakable_word(text: str, nobreak_pattern, break_chars: str,
                                  break_split_re=None) -> int:
    """Compute the length of the longest unbreakable word in a cell's text.

    An "unbreakable word" is either:
    - A nobreak-pattern match (its full length), or
    - A whitespace-delimited token shorter than MIN_TOKEN_LENGTH_FOR_BREAKS
      (Phase 1 does not inject break_chars breaks for short tokens), or
    - The longest substring between break_chars for tokens >= MIN_TOKEN_LENGTH_FOR_BREAKS.

    Args:
        text: The cell text content.
        nobreak_pattern: Compiled regex for nobreak patterns.
        break_chars: String of characters that allow breaking.
        break_split_re: Pre-compiled regex for splitting on whitespace and
            break_chars. If None, one is compiled on the fly (slower).

    Returns:
        Length in characters of the longest unbreakable segment.
    """
    if not text:
        return 0

    segments = _split_by_nobreak(text, nobreak_pattern)
    max_width = 0.0

    for segment_text, is_nobreak in segments:
        if not segment_text:
            continue
        if is_nobreak:
            # Nobreak tokens are rendered in \mbox{}; use effective width.
            max_width = max(max_width, _effective_word_width_chars(segment_text))
        else:
            # First split on whitespace to get individual tokens.
            ws_tokens = segment_text.split()
            for token in ws_tokens:
                if not token:
                    continue
                # Phase 1 only injects \allowbreak for tokens > MIN_TOKEN_LENGTH_FOR_BREAKS.
                # Shorter tokens are effectively unbreakable at break_chars.
                if len(token) <= MIN_TOKEN_LENGTH_FOR_BREAKS:
                    # Entire token is unbreakable; measure at full width.
                    max_width = max(max_width, _effective_word_width_chars(token))
                else:
                    # Long token: Phase 1 injects breaks at break_chars.
                    # Find longest segment between break points.
                    if break_split_re is not None:
                        parts = break_split_re.split(token)
                    else:
                        if break_chars:
                            split_pattern = r'[' + re.escape(break_chars) + r']+'
                        else:
                            split_pattern = r'\s+'
                        parts = re.split(split_pattern, token)
                    for part in parts:
                        if part:
                            max_width = max(max_width, _effective_word_width_chars(part))

    return int(round(max_width))


def _collect_entry_text(entry_node) -> str:
    """Collect all text content from a table entry node.

    Includes text from all children, including reference (hyperlink) nodes,
    since their visible text contributes to column width requirements.

    Args:
        entry_node: A docutils ``nodes.entry`` node representing a table cell.

    Returns:
        Concatenated plain text from the entry.
    """
    parts = []
    for text_node in entry_node.findall(nodes.Text):
        parts.append(text_node.astext())
    return ' '.join(parts)


def _get_entry_min_width(entry_node, nobreak_pattern, break_chars: str,
                         break_split_re=None) -> int:
    """Compute the minimum column width needed for a table entry, structure-aware.

    Unlike _collect_entry_text + _get_longest_unbreakable_word, this function
    preserves the document structure: text inside reference (hyperlink) nodes
    is treated as a single unbreakable unit (split only on whitespace, NOT on
    break_chars), matching Phase 1 behavior which does not inject \\allowbreak
    inside references.

    This fixes width underestimation for hyphenated IDs rendered as links
    (e.g., "ADR-0001", "ORCA-CRE-241", "ADFHS-EXC-SDR-0003").

    Args:
        entry_node: A docutils ``nodes.entry`` node representing a table cell.
        nobreak_pattern: Compiled regex for nobreak patterns.
        break_chars: String of break characters for non-reference text.
        break_split_re: Pre-compiled regex for splitting on whitespace and
            break_chars. If None, compiled on the fly.

    Returns:
        Length in character units of the longest unbreakable segment.
    """
    max_width = 0.0

    # Walk all reference nodes: their full text is unbreakable.
    for ref_node in entry_node.findall(nodes.reference):
        ref_text = ref_node.astext().strip()
        if not ref_text:
            continue
        # Reference text is unbreakable at break_chars (Phase 1 skips them).
        # But it CAN be broken at whitespace (multiple words in a link).
        # Also check nobreak patterns within the reference.
        segments = _split_by_nobreak(ref_text, nobreak_pattern)
        for segment_text, is_nobreak in segments:
            if not segment_text:
                continue
            if is_nobreak:
                max_width = max(max_width, _effective_word_width_chars(segment_text))
            else:
                # Split only on whitespace (NOT break_chars) for reference text.
                words = segment_text.split()
                for word in words:
                    if word:
                        max_width = max(max_width, _effective_word_width_chars(word))

    # Walk text nodes NOT inside references: standard break_chars splitting.
    for text_node in entry_node.findall(nodes.Text):
        if _is_inside_reference(text_node):
            continue  # Already handled above.
        text = text_node.astext()
        if not text:
            continue
        longest = _get_longest_unbreakable_word(text, nobreak_pattern, break_chars, break_split_re)
        max_width = max(max_width, float(longest))

    return int(round(max_width))


# ---------------------------------------------------------------------------
# Phase 1: Apply nobreak/break processing to table entry nodes
# ---------------------------------------------------------------------------

def _process_table_entries(table_node, nobreak_pattern, break_chars: str) -> dict:
    """Walk all entry nodes in a table and apply Phase 1 text processing.

    Modifies the doctree in place: replaces Text nodes with
    mbox-wrapped raw nodes (for nobreak tokens) and allowbreak-injected
    nodes (for breakable text).

    Args:
        table_node: The docutils ``nodes.table`` node to process.
        nobreak_pattern: Compiled regex for nobreak token detection, or None.
        break_chars: String of characters at which breakable text may be split.

    Returns:
        Dict mapping column index (int) to the maximum nobreak token length
        (int) found in that column. Used by Phase 2 to seed minimum column
        widths without a redundant tree walk.
    """
    col_nobreak_max: dict = {}  # col_idx -> max nobreak length

    for tgroup in table_node.findall(nodes.tgroup):
        for body in list(tgroup.findall(nodes.tbody)) + list(tgroup.findall(nodes.thead)):
            for row in body.findall(nodes.row):
                for col_idx, entry in enumerate(row.findall(nodes.entry)):
                    # Process ALL Text nodes, including those inside references.
                    # UUIDs inside hyperlinks still need mbox protection to prevent
                    # overflow. For reference children, we apply nobreak matching
                    # but skip break-char injection (Sphinx handles link formatting).
                    text_nodes = list(entry.findall(nodes.Text))
                    for text_node in text_nodes:
                        parent = text_node.parent
                        if parent is None:
                            continue
                        idx_in_parent = parent.children.index(text_node)

                        # For text inside references: only apply nobreak wrapping,
                        # skip allowbreak injection (pass empty break_chars).
                        effective_break_chars = '' if _is_inside_reference(text_node) else break_chars

                        replacement, nobreak_lengths = _process_text_node(
                            text_node, nobreak_pattern, effective_break_chars
                        )

                        # Track max nobreak length per column.
                        for nl in nobreak_lengths:
                            col_nobreak_max[col_idx] = max(
                                col_nobreak_max.get(col_idx, 0), nl
                            )

                        # Replace the text node with the processed nodes.
                        if replacement != [text_node]:
                            parent.children[idx_in_parent:idx_in_parent + 1] = replacement

    return col_nobreak_max


# ---------------------------------------------------------------------------
# Phase 2: Column width computation
# ---------------------------------------------------------------------------

def _compute_column_metrics(table_node, nobreak_pattern, break_chars: str,
                            header_char_width_factor: float = DEFAULT_HEADER_CHAR_WIDTH_FACTOR
                            ) -> List[ColumnInfo]:
    """Compute per-column content metrics for width calculation.

    Walks all cells in the table to determine:
    - min_width_chars: effective minimum (max of scaled header, body + padding)
    - raw_body_min_chars: longest unbreakable word in body cells
    - raw_header_min_chars: longest unbreakable word in header cells
    - avg_content_chars: average total character count across cells
    - header_text: text from the header row (if present)

    The effective min_width_chars accounts for:
    - Header font being wider than body font (scaled by header_char_width_factor)
    - Cell padding allowance (MIN_WIDTH_PADDING_CHARS)

    Args:
        table_node: The docutils table node.
        nobreak_pattern: Compiled nobreak regex.
        break_chars: Break characters string.
        header_char_width_factor: Multiplier for header character width relative
            to body text (default: DEFAULT_HEADER_CHAR_WIDTH_FACTOR).

    Returns:
        List of ColumnInfo, one per column.
    """
    # Pre-compile the break-split regex once for the entire table.
    # Only break_chars are included; whitespace is handled by .split() before
    # this regex is applied to individual tokens.
    if break_chars:
        break_split_re = re.compile(r'[' + re.escape(break_chars) + r']+')
    else:
        break_split_re = re.compile(r'\s+')

    # Determine column count from tgroup.
    col_count = 0
    for tgroup in table_node.findall(nodes.tgroup):
        col_count = tgroup.get('cols', 0)
        if col_count == 0:
            colspecs = list(tgroup.findall(nodes.colspec))
            col_count = len(colspecs)
        break

    if col_count == 0:
        return []

    # Initialize per-column accumulators.
    col_header_min = [0] * col_count
    col_body_min = [0] * col_count
    col_content_totals = [0.0] * col_count
    col_cell_counts = [0] * col_count
    col_headers = [''] * col_count

    for tgroup in table_node.findall(nodes.tgroup):
        # Process header rows.
        for thead in tgroup.findall(nodes.thead):
            for row in thead.findall(nodes.row):
                entries = list(row.findall(nodes.entry))
                for col_idx, entry in enumerate(entries):
                    if col_idx >= col_count:
                        break
                    text = _collect_entry_text(entry)
                    col_headers[col_idx] = text.strip()
                    # Headers use structure-aware measurement (reference text is unbreakable).
                    longest = _get_entry_min_width(entry, nobreak_pattern, break_chars, break_split_re)
                    col_header_min[col_idx] = max(col_header_min[col_idx], longest)
                    col_content_totals[col_idx] += len(text)
                    col_cell_counts[col_idx] += 1

        # Process body rows.
        for tbody in tgroup.findall(nodes.tbody):
            for row in tbody.findall(nodes.row):
                entries = list(row.findall(nodes.entry))
                for col_idx, entry in enumerate(entries):
                    if col_idx >= col_count:
                        break
                    text = _collect_entry_text(entry)
                    # Use structure-aware measurement: text inside reference nodes
                    # is treated as unbreakable (matching Phase 1 behavior).
                    longest = _get_entry_min_width(entry, nobreak_pattern, break_chars, break_split_re)
                    col_body_min[col_idx] = max(col_body_min[col_idx], longest)
                    col_content_totals[col_idx] += len(text)
                    col_cell_counts[col_idx] += 1

    # Build ColumnInfo list.
    # Effective min_width_chars accounts for:
    # - Header font being wider (scaled by header_char_width_factor)
    # - Uppercase body words being wider (already handled by _get_longest_unbreakable_word)
    # - Per-column tabcolsep overhead (converted to char units)
    # - Small padding for rendering tolerances
    # NOTE: Uppercase header words receive both factors (uppercase * header_bold).
    # This is intentionally conservative: bold uppercase (e.g. Montserrat Bold "SAST")
    # is genuinely ~60% wider than regular mixed-case body text.
    char_width_mm = FALLBACK_CHAR_WIDTH_MM  # used for overhead conversion
    tabcolsep_chars = int(round(TABCOLSEP_OVERHEAD_MM / char_width_mm))
    columns = []
    for i in range(col_count):
        avg = col_content_totals[i] / col_cell_counts[i] if col_cell_counts[i] > 0 else 0.0
        # Scale header minimum by the bold font width factor.
        scaled_header = int(round(col_header_min[i] * header_char_width_factor))
        # Body min already includes uppercase scaling from _get_longest_unbreakable_word.
        # Add tabcolsep overhead (accounts for \X formula per-column subtraction)
        # and a small padding for rendering tolerances.
        effective_min = max(scaled_header, col_body_min[i]) + tabcolsep_chars + MIN_WIDTH_PADDING_CHARS
        columns.append(ColumnInfo(
            min_width_chars=effective_min,
            raw_body_min_chars=col_body_min[i],
            raw_header_min_chars=col_header_min[i],
            avg_content_chars=avg,
            header_text=col_headers[i],
        ))
    return columns


def _apply_column_widths(table_node, new_widths: List[int]):
    """Update colspec nodes with computed relative widths.

    Modifies colwidth attributes on each colspec node in the table's tgroup.

    Args:
        table_node: The docutils table node.
        new_widths: List of relative column widths (one per column).
    """
    for tgroup in table_node.findall(nodes.tgroup):
        colspecs = list(tgroup.findall(nodes.colspec))
        for i, colspec in enumerate(colspecs):
            if i < len(new_widths):
                colspec['colwidth'] = new_widths[i]


def _compute_and_apply_widths(table_node, nobreak_pattern, break_chars: str, app,
                              phase1_col_nobreak_max: dict = None):
    """Phase 2 main logic: compute and apply content-aware column widths.

    Processes tables with 'colwidths-given' (explicit :widths:) and optionally
    tables with 'colwidths-auto' (no explicit widths, normally handled by
    tabulary). For colwidths-auto tables, injects computed proportions and
    promotes the table to colwidths-given so Sphinx uses \\X columns with
    the content-aware widths instead of tabulary's trial-pass algorithm.

    Uses portrait textwidth as the reference for tables that stay in portrait
    (below the landscape column threshold). For tables that will auto-rotate
    to landscape, predicts the adaptive landscape page size and uses that
    textwidth for proportional computation.

    Stores computed minimum table width in mm as a node attribute.

    Args:
        table_node: The docutils table node.
        nobreak_pattern: Compiled nobreak regex.
        break_chars: Break characters string.
        app: Sphinx application (for config access).
        phase1_col_nobreak_max: Optional dict mapping column index to max nobreak
            token length from Phase 1. Used to seed minimum widths in Phase 2
            without a redundant tree walk. If None, Phase 2 computes its own.
    """
    # Check table class: process colwidths-given, colwidths-auto, and tables
    # with no colwidths class (default csv-tables that would use tabulary).
    table_classes = table_node.get('classes', [])
    has_given = 'colwidths-given' in table_classes
    has_auto = 'colwidths-auto' in table_classes

    # All tables are eligible for Phase 2 width computation.
    # - colwidths-given: recompute with content-aware algorithm
    # - colwidths-auto / no class: inject computed widths, promote to colwidths-given

    # Check if auto column widths are enabled.
    auto_colwidths = getattr(app.config, 'doxtr_table_auto_colwidths', True)
    if not auto_colwidths:
        return

    # Get config values.
    char_width_mm = getattr(app.config, 'doxtr_table_char_width_mm', FALLBACK_CHAR_WIDTH_MM)
    if not char_width_mm or char_width_mm <= 0:
        char_width_mm = FALLBACK_CHAR_WIDTH_MM
    algorithm_name = getattr(
        app.config, 'doxtr_table_column_width_algorithm', DEFAULT_ALGORITHM
    )
    header_char_width_factor = getattr(
        app.config, 'doxtr_table_header_char_width_factor', DEFAULT_HEADER_CHAR_WIDTH_FACTOR
    )

    # Compute column metrics (with header font scaling).
    columns = _compute_column_metrics(
        table_node, nobreak_pattern, break_chars,
        header_char_width_factor=header_char_width_factor,
    )
    if not columns:
        return

    # Seed Phase 2 min widths from Phase 1 nobreak metrics (avoids redundant walk).
    # Add padding to nobreak tokens since they are rendered in \mbox{} which
    # cannot be broken and must fit entirely within the column.
    if phase1_col_nobreak_max:
        for col_idx, nobreak_len in phase1_col_nobreak_max.items():
            if col_idx < len(columns):
                columns[col_idx].min_width_chars = max(
                    columns[col_idx].min_width_chars,
                    nobreak_len + MIN_WIDTH_PADDING_CHARS,
                )

    # Compute available width in character units.
    # Strategy: predict what page size Phase 3 (landscape processor) will select
    # for this table, then use that textwidth as the available space.
    # This prevents the disconnect where Phase 2 uses portrait width (160mm)
    # but the table renders on a much wider landscape page.
    #
    # For tables that stay in portrait (few columns), use portrait textwidth.
    # For tables that go to adaptive landscape (many columns), predict the
    # selected page and use its textwidth.
    col_count = len(columns)
    auto_landscape = getattr(app.config, 'doxtr_table_auto_landscape', True)
    table_classes = table_node.get('classes', [])
    no_landscape = 'no-landscape' in table_classes
    min_columns_for_landscape = getattr(
        app.config, 'doxtr_landscape_min_columns', 4
    )

    if auto_landscape and not no_landscape and col_count >= min_columns_for_landscape:
        # Predict the adaptive landscape page selection.
        # The LaTeX \doxtradaptivelandscape macro uses:
        #   requiredwidth = col_count * doxtr@mincolwidth (default 22mm)
        # We replicate that logic here, BUT also account for the actual
        # computed minimum widths (which may be much larger for tables
        # with UUIDs, FQDNs, or other wide unbreakable content).
        min_col_width_mm = DEFAULT_MIN_COL_WIDTH_MM
        heuristic_width_mm = col_count * min_col_width_mm
        # Compute actual minimum from column metrics (before algorithm runs).
        actual_min_mm = sum(max(c.min_width_chars, 1) for c in columns) * char_width_mm
        # Use the larger of the two: the heuristic (matches Phase 3 LaTeX)
        # or the actual content-driven minimum.
        required_width_mm = max(heuristic_width_mm, actual_min_mm)
        # Select smallest landscape textwidth that fits.
        predicted_textwidth = _LANDSCAPE_TEXTWIDTHS_MM[-1]  # fallback to largest
        for tw in _LANDSCAPE_TEXTWIDTHS_MM:
            if tw >= required_width_mm:
                predicted_textwidth = tw
                break
        available_width_chars = int(predicted_textwidth / char_width_mm)
    else:
        # Table stays in portrait; use portrait textwidth as worst case.
        available_width_chars = int(A4_PORTRAIT_TEXTWIDTH_MM / char_width_mm)

    # Look up and run the selected algorithm.
    algorithm_fn = _column_width_algorithms.get(algorithm_name)
    if algorithm_fn is None:
        logger.warning(
            '[Doxtr Tables] Unknown column width algorithm %r; '
            'falling back to %r.', algorithm_name, DEFAULT_ALGORITHM
        )
        algorithm_fn = _column_width_algorithms.get(DEFAULT_ALGORITHM, _algorithm_minfloor)

    new_widths = algorithm_fn(columns, available_width_chars)

    if new_widths:
        _apply_column_widths(table_node, new_widths)
        # Promote tables without colwidths-given to colwidths-given so Sphinx
        # uses \X{w}{total} proportional columns instead of tabulary auto-sizing.
        # This ensures our content-aware widths are respected.
        if not has_given:
            if has_auto:
                table_classes.remove('colwidths-auto')
            table_classes.append('colwidths-given')

    # Store minimum table width in mm for Phase 3 (landscape page sizing).
    total_min_chars = sum(max(c.min_width_chars, 1) for c in columns)
    table_node['doxtr_min_table_width_mm'] = total_min_chars * char_width_mm


# ---------------------------------------------------------------------------
# Main entry point: process_tables_ast
# ---------------------------------------------------------------------------

def process_tables_ast(app, doctree, docname):
    """Process all tables in the doctree: apply nobreak protection, break
    injection, and content-aware column width computation.

    Phase 1: Walk all entry nodes in each table. For text nodes not inside
    reference nodes, apply nobreak pattern matching (wrapping in mbox) and
    break-char injection (inserting allowbreak).

    Phase 2: For tables with 'colwidths-given' or 'colwidths-auto', compute
    content-aware column widths using the configured algorithm and update
    colspec nodes. Tables with 'colwidths-auto' are promoted to
    'colwidths-given' so Sphinx uses proportional \\X columns.

    Skipped if ``doxtr_enable_table_processor`` is False or builder is not latex.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if not getattr(app.config, 'doxtr_enable_table_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return

    # Read config values with defaults.
    nobreak_pattern_strings = getattr(
        app.config, 'doxtr_table_nobreak_patterns', DEFAULT_NOBREAK_PATTERNS
    )
    break_chars = getattr(app.config, 'doxtr_table_break_chars', DEFAULT_BREAK_CHARS)

    # Compile nobreak patterns.
    nobreak_pattern = _compile_nobreak_patterns(nobreak_pattern_strings)

    # Process each table in the document.
    for table_node in list(doctree.findall(nodes.table)):
        if table_node.get('doxtr_table_overflow_processed'):
            continue
        table_node['doxtr_table_overflow_processed'] = True

        # Phase 1: nobreak protection and break injection.
        col_nobreak_max = _process_table_entries(table_node, nobreak_pattern, break_chars)

        # Phase 2: content-aware column width computation.
        _compute_and_apply_widths(
            table_node, nobreak_pattern, break_chars, app,
            phase1_col_nobreak_max=col_nobreak_max,
        )
