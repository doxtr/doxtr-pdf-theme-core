"""
Doxtr Test Harness — Assertion Types

Provides reusable assertion functions for validating LaTeX output.
Each assertion checks a different aspect of the generated LaTeX.

Usage in features.py:
    expected_latex_markers=[
        r"my_regex_pattern",
    ],
    assertions=[
        AssertType.COLOR_DEFINED,
        AssertType.TCOLORBOX_DEFINED,
        AssertType.FONT_SPEC_USED,
    ],

New assertions can be added by:
    1. Adding a value to AssertType enum
    2. Implementing the check function in check_assertions()
    3. Adding a description in ASSERTION_DESCRIPTIONS
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AssertType(Enum):
    """Types of assertions that can be checked against LaTeX output."""

    # --- Color Assertions ---
    COLOR_DEFINED = "color_defined"
    COLOR_IN_CMYK = "color_in_cmyk"
    COLOR_IN_RGB = "color_in_rgb"

    # --- tcolorbox Assertions ---
    TCOLORBOX_DEFINED = "tcolorbox_defined"
    TCOLORBOX_WITH_STYLE = "tcolorbox_with_style"

    # --- TikZ Assertions ---
    TIKZ_LIBRARY_LOADED = "tikz_library_loaded"
    TIKZ_COMMAND_USED = "tikz_command_used"

    # --- Font Assertions ---
    FONT_SPEC_USED = "fontspec_used"
    FONT_FAMILY_LOADED = "font_family_loaded"

    # --- KOMA-Script Assertions ---
    KOMA_FONT_DEFINED = "koma_font_defined"
    KOMA_OPTIONS_SET = "koma_options_set"

    # --- Geometry Assertions ---
    GEOMETRY_SET = "geometry_set"
    MARGINPAR_SET = "marginpar_set"

    # --- Document Structure Assertions ---
    TOC_ENTRY = "toc_entry"
    CHAPTER_FORMAT_DEFINED = "chapter_format_defined"
    SECTION_FORMAT_DEFINED = "section_format_defined"

    # --- List Assertions ---
    LIST_OF_FIGURES = "list_of_figures"
    LIST_OF_TABLES = "list_of_tables"
    LIST_OF_LISTINGS = "list_of_listings"

    # --- Package Assertions ---
    MICROTYPE_NOT_LOADED = "microtype_not_loaded"

    # --- Meta Assertions ---
    FILE_SIZE_RANGE = "file_size_range"
    COMPILATION_SUCCESS = "compilation_success"


# Description mapping for reporting
ASSERTION_DESCRIPTIONS: dict[AssertType, str] = {
    AssertType.COLOR_DEFINED: "Color defined in output",
    AssertType.COLOR_IN_CMYK: "Color defined in CMYK format",
    AssertType.COLOR_IN_RGB: "Color defined in RGB format",
    AssertType.TCOLORBOX_DEFINED: "tcolorbox environment defined",
    AssertType.TCOLORBOX_WITH_STYLE: "tcolorbox with specific style",
    AssertType.TIKZ_LIBRARY_LOADED: "TikZ library loaded",
    AssertType.TIKZ_COMMAND_USED: "TikZ command used",
    AssertType.FONT_SPEC_USED: "fontspec command used",
    AssertType.FONT_FAMILY_LOADED: "Font family loaded",
    AssertType.KOMA_FONT_DEFINED: "KOMA font defined",
    AssertType.KOMA_OPTIONS_SET: "KOMA option set",
    AssertType.GEOMETRY_SET: "Geometry setting present",
    AssertType.MARGINPAR_SET: "Marginpar setting present",
    AssertType.TOC_ENTRY: "TOC entry present",
    AssertType.CHAPTER_FORMAT_DEFINED: "Chapter format defined",
    AssertType.SECTION_FORMAT_DEFINED: "Section format defined",
    AssertType.LIST_OF_FIGURES: "List of Figures present",
    AssertType.LIST_OF_TABLES: "List of Tables present",
    AssertType.LIST_OF_LISTINGS: "List of Listings present",
    AssertType.MICROTYPE_NOT_LOADED: "microtype package NOT loaded",
    AssertType.FILE_SIZE_RANGE: "Output file size in range",
    AssertType.COMPILATION_SUCCESS: "LaTeX compilation succeeded",
}


@dataclass
class AssertionResult:
    """Result of a single assertion check."""
    assertion_type: AssertType
    passed: bool
    description: str
    details: Optional[str] = None


def check_assertions(
    tex_content: str,
    assertions: list[AssertType],
    file_size: Optional[int] = None,
) -> list[AssertionResult]:
    """
    Check assertions against LaTeX output.

    Args:
        tex_content: The content of the generated .tex file
        assertions: List of AssertType values to check
        file_size: Optional file size in bytes for FILE_SIZE_RANGE checks

    Returns:
        List of AssertionResult objects
    """
    results = []

    for assertion in assertions:
        result = _check_single_assertion(assertion, tex_content, file_size)
        results.append(result)

    return results


def _check_single_assertion(
    assertion: AssertType,
    tex_content: str,
    file_size: Optional[int] = None,
) -> AssertionResult:
    """Check a single assertion type."""
    desc = ASSERTION_DESCRIPTIONS.get(assertion, str(assertion.value))

    if assertion == AssertType.COLOR_DEFINED:
        # Check for any \definecolor command
        found = bool(re.search(r"\\definecolor\{", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details=r"Found \definecolor commands" if found else r"No \definecolor commands found",
        )

    elif assertion == AssertType.COLOR_IN_CMYK:
        # Check for CMYK color definition
        found = bool(re.search(r"\\definecolor\{[^}]+\}\{cmyk\}", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found CMYK color definitions" if found else "No CMYK color definitions found",
        )

    elif assertion == AssertType.COLOR_IN_RGB:
        # Check for RGB color definition (255 format)
        found = bool(re.search(r"\\definecolor\{[^}]+\}\{rgb,255:", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found RGB color definitions" if found else "No RGB color definitions found",
        )

    elif assertion == AssertType.TCOLORBOX_DEFINED:
        # Check for \newtcolorbox command
        found = bool(re.search(r"\\newtcolorbox\{", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found tcolorbox definitions" if found else "No tcolorbox definitions found",
        )

    elif assertion == AssertType.TCOLORBOX_WITH_STYLE:
        # Check for tcbset with specific style pattern
        found = bool(re.search(r"tcbset\{[^}]*style", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found tcbset with styles" if found else "No tcbset styles found",
        )

    elif assertion == AssertType.TIKZ_LIBRARY_LOADED:
        # Check for \usetikzlibrary command
        found = bool(re.search(r"\\usetikzlibrary\{", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found TikZ library loads" if found else "No TikZ library loads found",
        )

    elif assertion == AssertType.TIKZ_COMMAND_USED:
        # Check for TikZ commands
        found = bool(re.search(r"\\tikz", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found TikZ commands" if found else "No TikZ commands found",
        )

    elif assertion == AssertType.FONT_SPEC_USED:
        # Check for \fontspec command
        found = bool(re.search(r"\\fontspec\{", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found fontspec commands" if found else "No fontspec commands found",
        )

    elif assertion == AssertType.FONT_FAMILY_LOADED:
        # Check for \setmainfont, \setsansfont, or \setmonofont
        found = bool(
            re.search(r"\\setmainfont\{", tex_content)
            or re.search(r"\\setsansfont\{", tex_content)
            or re.search(r"\\setmonofont\{", tex_content)
        )
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found font family settings" if found else "No font family settings found",
        )

    elif assertion == AssertType.KOMA_FONT_DEFINED:
        # Check for \addtokomafont command
        found = bool(re.search(r"\\addtokomafont\{", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found KOMA font definitions" if found else "No KOMA font definitions found",
        )

    elif assertion == AssertType.KOMA_OPTIONS_SET:
        # Check for \KOMAoptions command
        found = bool(re.search(r"\\KOMAoptions\{", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found KOMA options" if found else "No KOMA options found",
        )

    elif assertion == AssertType.GEOMETRY_SET:
        # Check for \geometry command
        found = bool(re.search(r"\\geometry\{", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found geometry settings" if found else "No geometry settings found",
        )

    elif assertion == AssertType.MARGINPAR_SET:
        # Check for marginpar setting
        found = bool(re.search(r"marginpar", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found marginpar settings" if found else "No marginpar settings found",
        )

    elif assertion == AssertType.TOC_ENTRY:
        # Check for \addtocontents or \addcontentsline
        found = bool(re.search(r"\\addtocontents\{|\\addcontentsline\{", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found TOC entries" if found else "No TOC entries found",
        )

    elif assertion == AssertType.CHAPTER_FORMAT_DEFINED:
        # Check for \renewcommand.*\chapterformat
        found = bool(re.search(r"\\renewcommand.*\\chapterformat", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found chapter format definition" if found else "No chapter format definition found",
        )

    elif assertion == AssertType.SECTION_FORMAT_DEFINED:
        # Check for \renewcommand.*\sectionformat
        found = bool(re.search(r"\\renewcommand.*\\sectionformat", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found section format definition" if found else "No section format definition found",
        )

    elif assertion == AssertType.LIST_OF_FIGURES:
        # Check for \listoffigures
        found = bool(re.search(r"\\listoffigures", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found List of Figures" if found else "No List of Figures found",
        )

    elif assertion == AssertType.LIST_OF_TABLES:
        # Check for \listoftables
        found = bool(re.search(r"\\listoftables", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found List of Tables" if found else "No List of Tables found",
        )

    elif assertion == AssertType.LIST_OF_LISTINGS:
        # Check for literalblock in list
        found = bool(re.search(r"literalblock", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found List of Listings" if found else "No List of Listings found",
        )

    elif assertion == AssertType.MICROTYPE_NOT_LOADED:
        # Check that microtype package is NOT loaded
        # This is used when draft mode is active — microtype should be disabled
        not_loaded = not bool(re.search(r"\\usepackage\{microtype\}", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=not_loaded,
            description=desc,
            details="microtype package is NOT loaded (as expected)" if not_loaded else "microtype package IS loaded (should be disabled)",
        )

    elif assertion == AssertType.FILE_SIZE_RANGE:
        # Check if file size is within expected range
        if file_size is None:
            return AssertionResult(
                assertion_type=assertion,
                passed=False,
                description=desc,
                details="No file size provided for check",
            )
        # Reasonable LaTeX output should be between 1KB and 5MB
        passed = 1024 <= file_size <= 5 * 1024 * 1024
        return AssertionResult(
            assertion_type=assertion,
            passed=passed,
            description=desc,
            details=f"File size: {file_size} bytes" if passed else f"File size {file_size} out of range",
        )

    elif assertion == AssertType.COMPILATION_SUCCESS:
        # This is checked by the test runner, not the tex content
        return AssertionResult(
            assertion_type=assertion,
            passed=True,
            description=desc,
            details="LaTeX build completed",
        )

    # Default fallback
    return AssertionResult(
        assertion_type=assertion,
        passed=False,
        description=desc,
        details=f"Unknown assertion type: {assertion}",
    )


def format_assertion_results(results: list[AssertionResult]) -> list[str]:
    """Format assertion results for display in reports."""
    lines = []
    for result in results:
        icon = "✓" if result.passed else "✗"
        line = f"    [{icon}] {result.description}"
        if result.details:
            line += f" — {result.details}"
        lines.append(line)
    return lines
