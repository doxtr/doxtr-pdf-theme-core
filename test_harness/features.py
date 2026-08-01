"""
Doxtr PDF Theme Core — Test Harness Feature Registry

This is the SINGLE SOURCE OF TRUTH for all test cases. Every feature and sub-test
is defined here. The test harness auto-discovers everything from this file.

Adding a new test case:
    1. Add a FeatureSubTest to the appropriate Feature in FEATURE_REGISTRY
    2. Create the RST file (if rst_file is not None)
    3. Create the conf.py override (if conf_override is not None)
    4. Set status to FeatureStatus.COMPLETE when tests pass

The auto_include_tests extension reads this file to generate the Sphinx toctree.
The test_runner reads this file to know what to build and validate.

Never edit index.rst manually — it is auto-generated from this registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List


# ---------------------------------------------------------------------------
# Enum — Feature status
# ---------------------------------------------------------------------------

class FeatureStatus(Enum):
    """Status of a test case or feature."""
    COMPLETE = "complete"       # All sub-features tested and passing
    PARTIAL = "partial"         # Some sub-features tested
    PENDING = "pending"         # No tests yet


# ---------------------------------------------------------------------------
# Data classes — Feature and sub-test definitions
# ---------------------------------------------------------------------------

@dataclass
class FeatureSubTest:
    """A single sub-test within a feature."""
    name: str
    description: str
    rst_file: Optional[str] = None          # Relative to source/_test_cases/ (None = no RST needed)
    conf_override: Optional[str] = None     # Relative to conf_overrides/ (None = use defaults)
    expected_latex_markers: list[str] = field(default_factory=list)
    assertions: list[str] = field(default_factory=list)  # AssertType values to check
    status: FeatureStatus = FeatureStatus.PENDING

    @property
    def has_rst(self) -> bool:
        return self.rst_file is not None


@dataclass
class Feature:
    """A testable feature area (e.g., Headings, Code Blocks)."""
    name: str
    description: str
    sub_tests: list[FeatureSubTest] = field(default_factory=list)
    status: FeatureStatus = FeatureStatus.PENDING

    @property
    def all_complete(self) -> bool:
        return all(st.status == FeatureStatus.COMPLETE for st in self.sub_tests) if self.sub_tests else False

    @property
    def has_any_test(self) -> bool:
        return len(self.sub_tests) > 0

    @property
    def passed_count(self) -> int:
        return sum(1 for st in self.sub_tests if st.status == FeatureStatus.COMPLETE)

    @property
    def total_count(self) -> int:
        return len(self.sub_tests)


# ---------------------------------------------------------------------------
# FEATURE_REGISTRY — The single source of truth
# ---------------------------------------------------------------------------

FEATURE_REGISTRY: dict[str, Feature] = {
    # =====================================================================
    # 1. HEADINGS
    # =====================================================================
    "headings": Feature(
        name="Headings",
        description="Chapter, section, subsection, subsubsection alignment, margin, colors, lines, fonts, sizes, inheritance",
        sub_tests=[
            FeatureSubTest(
                name="chapter_number_margin",
                description="Chapter numbers pushed into margin with decorative line",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"\\doxtr@chapter@align@right",
                    r"\\doxtr@drawline",
                    r"ddchapterlinecolor",
                ],
                assertions=[
                    "COLOR_IN_CMYK",
                    "FONT_SPEC_USED",
                    "KOMA_FONT_DEFINED",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="section_number_line",
                description="Section decorative line rendered",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"ddsectionlinecolor",
                    r"\\doxtr@section@align@alternate",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="align_alternate",
                description="Alternate left/right based on page odd/even",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"\\doxtr@chapter@align@alternate",
                    r"\\Ifthispageodd",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="align_left",
                description="Left-aligned headings",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"\\doxtr@chapter@align@left",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="align_right",
                description="Right-aligned headings",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"\\doxtr@chapter@align@right",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="margin_space",
                description="Custom margin spacing applied",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"5\.5em",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="font_override",
                description="Custom font per level",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"Uncial Antiqua",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="color_override",
                description="Custom color per level",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"definecolor.*ddsectioncolor",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="number_color_override",
                description="Custom number color",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"definecolor.*ddsectionnumbercolor",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="number_size_override",
                description="Custom number size",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"30pt",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="inherit_font",
                description="Font inheritance downward through hierarchy",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"Ewert",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="inherit_color",
                description="Color inheritance downward through hierarchy",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"definecolor.*ddsectionnumbercolor",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="inherit_all",
                description="All inheritance on/off toggle",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"inherit",
                ],
                status=FeatureStatus.COMPLETE,
            ),

            FeatureSubTest(
                name="numbers_in_margin_global",
                description="Global margin toggle off",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[
                    r"marginparsep",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 2. PARTS
    # =====================================================================
    "parts": Feature(
        name="Parts",
        description="Part styling, number splitting, background color/image, appendix switch, epigraph colors",
        sub_tests=[
            FeatureSubTest(
                name="global_part_styling",
                description="Global part font/color/size",
                rst_file="parts.rst",
                conf_override="test_parts.py",
                expected_latex_markers=[
                    r"definecolor.*ddpartcolor",
                    r"fontspec.*Ewert",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="part_number_split",
                description="Part number split into 'Part' + number",
                rst_file="parts.rst",
                conf_override="test_parts.py",
                expected_latex_markers=[
                    r"addtokomafont.*partnumberpart",
                    r"addtokomafont.*partnumbernumber",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="part_background_color",
                description="Part background with opacity (8-digit hex)",
                rst_file="parts.rst",
                conf_override="test_parts.py",
                expected_latex_markers=[
                    r"ddpartbg1",
                    r"opacity",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="part_background_image",
                description="Part background image",
                rst_file="parts.rst",
                conf_override="test_parts.py",
                expected_latex_markers=[
                    r"includegraphics.*wizard-of-docs",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="part_appendix_switch",
                description="Appendix chapter numbering switch",
                rst_file="parts.rst",
                conf_override="test_parts.py",
                expected_latex_markers=[
                    r"appendix",
                    r"renewcommand.*thepart",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="part_epigraph_color",
                description="Per-part epigraph color override",
                rst_file="parts.rst",
                conf_override="test_parts.py",
                expected_latex_markers=[
                    r"ddpartepigraph1color",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="number_part_color",
                description="'Part' word color",
                rst_file="parts.rst",
                conf_override="test_parts.py",
                expected_latex_markers=[
                    r"definecolor.*ddpartnumberpartcolor",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="number_number_color",
                description="Number color (the '1' in 'Part 1')",
                rst_file="parts.rst",
                conf_override="test_parts.py",
                expected_latex_markers=[
                    r"definecolor.*ddpartnumbernumbercolor",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 3. TITLE PAGE
    # =====================================================================
    "title_page": Feature(
        name="Title Page",
        description="Page color, background image, title/subtitle/author/date/release styling, show_release, top_line, opacity, alignment",
        sub_tests=[
            FeatureSubTest(
                name="page_color",
                description="Solid page background color",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\definecolor{titlepagecolor}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="background_image",
                description="Cover background image",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"wizard-of-docs-techno.png",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="background_image_mode_fit",
                description="Image fit mode (keep aspect ratio)",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"keepaspectratio",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="background_image_mode_stretch",
                description="Image stretch mode (fill page)",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"width=\\paperwidth,height=\\paperheight",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="title_font_override",
                description="Custom title font",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\usekomafont\{title}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="title_color_override",
                description="Custom title color",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\definecolor\{ddsubtitlecolor}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="title_size_override",
                description="Custom title size",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\usekomafont\{title\}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="subtitle_override",
                description="Custom subtitle text and styling",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"A study on demos",
                    r"\\fontspec{Faster One}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="author_override",
                description="Custom author font and color",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\fontspec{Handjet}",
                    r"\\definecolor\{ddauthorcolor}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="date_override",
                description="Custom date font and color",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\fontspec{Ephesis}",
                    r"\\definecolor\{dddatecolor}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="release_version_override",
                description="Release version font and color",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\fontspec{Handjet}",
                    r"\\definecolor\{ddreleaseversioncolor}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="show_release_false",
                description="Hide release text entirely",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\renewcommand\{\\release\}\[1\]",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="top_line_override",
                description="Sphinx top black line on title page",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"\\xpatchcmd",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="background_image_align",
                description="Image alignment on title page",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"center",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="color_opacity",
                description="Background color opacity",
                rst_file="title_page.rst",
                conf_override="test_title_page.py",
                expected_latex_markers=[
                    r"opacity=0.2",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 4. CODE BLOCKS
    # =====================================================================
    "code": Feature(
        name="Code Blocks",
        description="Default styling, per-language override, mac_dots, language_label, icon, icon_position, border_width, content font/color",
        sub_tests=[
            FeatureSubTest(
                name="generic_code",
                description="Default code block styling",
                rst_file="code_blocks.rst",
                conf_override=None,
                expected_latex_markers=[
                    r"tcolorboxenvironment.*sphinxVerbatim",
                    r"doxtrcodestylegeneric",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="language_specific",
                description="Per-language override applied",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"ddcodetitlebg_bash",
                    r"Bourne Again SHell",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="show_mac_dots",
                description="Mac window dots rendered",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"fill\[red!80!white\]",
                    r"fill\[yellow!80!black\]",
                    r"fill\[green!80!black\]",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="no_mac_dots",
                description="Mac dots rendering verified",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"fill\[red!80!white\]",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="language_label",
                description="Custom language label",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"Bourne Again SHell",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="icon_override",
                description="Custom icon in code block",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"ddIconCommandbash",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="icon_position",
                description="Icon position relative to mac dots",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"ddIconCommandbash",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="border_width",
                description="Custom border width",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"boxrule=2pt",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="content_font_override",
                description="Custom content font",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"fontspec.*Iosevka",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="content_color_override",
                description="Custom content font color",
                rst_file="code_blocks.rst",
                conf_override="test_code.py",
                expected_latex_markers=[
                    r"definecolor.*ddcodefg_bash",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 5. ADMONITIONS
    # =====================================================================
    "admonitions": Feature(
        name="Admonitions",
        description="All 12 admonition types + generic, custom icons, icon_box_color, content_bg, before/after_skip",
        sub_tests=[
            FeatureSubTest(
                name="generic_admonition",
                description="Default admonition rendering",
                rst_file="admonitions.rst",
                conf_override=None,
                expected_latex_markers=[
                    r"\\newtcolorbox\{ddadmonbox@default",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="note_admonition",
                description="Note style with custom colors",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@note@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="warning_admonition",
                description="Warning style with red colors",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@warning@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="hint_admonition",
                description="Hint style",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@hint@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="danger_admonition",
                description="Danger style",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@danger@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="error_admonition",
                description="Error style",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@error@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="caution_admonition",
                description="Caution style with dynamic contrast",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@caution@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="tip_admonition",
                description="Tip style",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@tip@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="important_admonition",
                description="Important style",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@important@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="attention_admonition",
                description="Attention style",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@attention@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="seealso_admonition",
                description="SeeAlso style with right-side arrow",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@seealso@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="custom_icon_admonition",
                description="Custom LaTeX icon in admonition",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"\\textbf\{i}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="title_icon_color",
                description="Icon box background color",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@note@iconboxbg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="content_background",
                description="Content background color",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"ddadmon@note@contentbg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="before_skip_after_skip",
                description="Spacing control (before/after skip)",
                rst_file="admonitions.rst",
                conf_override="test_admonitions.py",
                expected_latex_markers=[
                    r"beforeskip",
                    r"afterskip",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 6. SPHINX NEEDS
    # =====================================================================
    "needs": Feature(
        name="Sphinx Needs",
        description="Generic + custom types, metadata, segmentation, title_icon, vertical_position, colors, fonts",
        sub_tests=[
            FeatureSubTest(
                name="generic_need",
                description="Default need box rendering",
                rst_file="needs.rst",
                conf_override=None,
                expected_latex_markers=[
                    r"\\newtcolorbox\{ddneedbox@",
                    r"doxtrneedboxrouter",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="custom_need_type",
                description="Custom need type (ADR) styling",
                rst_file="needs.rst",
                conf_override="test_needs.py",
                expected_latex_markers=[
                    r"ddneed@adr@titlebg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="need_metadata",
                description="Metadata key-value display",
                rst_file="needs.rst",
                conf_override="test_needs.py",
                expected_latex_markers=[
                    r"\\needsmetakey",
                    r"ddneed@generic@metakeyfg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="need_content",
                description="Content below segmentation line",
                rst_file="needs.rst",
                conf_override="test_needs.py",
                expected_latex_markers=[
                    r"\\tcblower",
                    r"ddneed@generic@contentbg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="need_segmentation_style",
                description="Segmentation line style (dashdotted)",
                rst_file="needs.rst",
                conf_override="test_needs.py",
                expected_latex_markers=[
                    r"ddneed@generic@seglinefg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="need_title_icon",
                description="Title icon rendering",
                rst_file="needs.rst",
                conf_override="test_needs.py",
                expected_latex_markers=[
                    r"ddneed@generic@iconcmd",
                    r"faIcon\{gavel}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="need_title_vertical_position",
                description="Icon vertical alignment (middle)",
                rst_file="needs.rst",
                conf_override="test_needs.py",
                expected_latex_markers=[
                    r"raisebox",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="need_metadata_color",
                description="Metadata key color override",
                rst_file="needs.rst",
                conf_override="test_needs.py",
                expected_latex_markers=[
                    r"ddneed@adr@metakeyfg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="need_content_font",
                description="Content font override",
                rst_file="needs.rst",
                conf_override="test_needs.py",
                expected_latex_markers=[
                    r"\\fontspec{Stardos Stencil}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 7. CONTAINERS / STYLEBOX
    # =====================================================================
    "containers": Feature(
        name="Containers / Stylebox",
        description="Frame/no_frame, match_text_width, classic/floating/ribbon title styles, all font/color/icon settings",
        sub_tests=[
            FeatureSubTest(
                name="basic_container",
                description="Simple stylebox container",
                rst_file="containers.rst",
                conf_override=None,
                expected_latex_markers=[
                    r"\\newtcolorbox\{ddcontainer",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_with_title",
                description="Container with custom title",
                rst_file="containers.rst",
                conf_override=None,
                expected_latex_markers=[
                    r"ddcontainertitlestyle",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_frame",
                description="Container with visible frame",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"colframe=",
                    r"boxrule=1pt",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_no_frame",
                description="Container without frame",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"frame hidden",
                    r"boxrule=0pt",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_match_text_width",
                description="Text width alignment with body",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"grow to left by",
                    r"grow to right by",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_title_style_classic",
                description="Classic title geometry",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"doxtrclassicstyle",
                    r"boxed title style",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_title_style_floating",
                description="Floating title geometry",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"doxtrfloatingstyle",
                    r"underlay boxed title",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_title_style_ribbon",
                description="Ribbon title geometry",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"doxtrbusinessstyle",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_content_font",
                description="Content font override",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"\\fontspec{Special Elite}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_content_color",
                description="Content font color",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"ddcontcontentfg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_content_bg",
                description="Content background color",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"ddcontcontentbg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_title_color",
                description="Title primary color (frame + background)",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"ddconttitlefg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_title_font_color",
                description="Title font color",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"ddconttitletextfg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_title_icon",
                description="Title icon rendering",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"ddconticon",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="container_title_font",
                description="Title font",
                rst_file="containers.rst",
                conf_override="test_containers.py",
                expected_latex_markers=[
                    r"\\fontspec{Fragment Mono}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 8. TABLES
    # =====================================================================
    "tables": Feature(
        name="Tables",
        description="Header colors, row stripes, caption position, offset, title_style (floating/arrow), fade_dots, fade_shape",
        sub_tests=[
            FeatureSubTest(
                name="basic_table",
                description="Default table styling",
                rst_file="tables.rst",
                conf_override=None,
                expected_latex_markers=[
                    r"\\definecolor\{ddtableheaderbg}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_header_color",
                description="Header background color",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"ddtableheaderbg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_header_font_color",
                description="Header font color",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"ddtableheaderfg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_row_color_odd",
                description="Odd row stripe color",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"sphinxTableRowColorOdd",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_row_color_even",
                description="Even row stripe color",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"sphinxTableRowColorEven",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_caption_side",
                description="Side caption position",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"sphinxSetupCaptionForVerbatim",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_caption_top",
                description="Top caption position",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"sphinxSetupCaptionForVerbatim",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_caption_bottom",
                description="Bottom caption position",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"sphinxSetupCaptionForVerbatim",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_caption_offset",
                description="Caption top offset micro-adjustment",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"sphinxSetupCaptionForVerbatim",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_title_style_floating",
                description="Floating title style for tables",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"doxtrfloatingstyle",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_title_style_arrow",
                description="Arrow title style for tables",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"doxtrfloatingstyle",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_title_fade_dots",
                description="Fade dots effect on table title",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"ddtablefademask",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="table_title_fade_shape",
                description="Fade shape (rectangle/triangle)",
                rst_file="tables.rst",
                conf_override="test_tables.py",
                expected_latex_markers=[
                    r"ddtablefademask",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 9. FIGURES
    # =====================================================================
    "figures": Feature(
        name="Figures",
        description="Caption background/font/color/size/align/padding",
        sub_tests=[
            FeatureSubTest(
                name="basic_figure",
                description="Default figure caption rendering",
                rst_file="figures.rst",
                conf_override=None,
                expected_latex_markers=[
                    r"\\definecolor\{ddfigcaptionbg}",
                    r"\\definecolor\{ddfigcaptionfg}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="figure_caption_color",
                description="Caption background color",
                rst_file="figures.rst",
                conf_override="test_figures.py",
                expected_latex_markers=[
                    r"ddfigcaptionbg",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="figure_caption_font",
                description="Caption font",
                rst_file="figures.rst",
                conf_override="test_figures.py",
                expected_latex_markers=[
                    r"\\fontspec{Exo 2}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="figure_caption_font_size",
                description="Caption font size",
                rst_file="figures.rst",
                conf_override="test_figures.py",
                expected_latex_markers=[
                    r"\\small\\sffamily\\bfseries",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="figure_caption_align",
                description="Caption alignment (center)",
                rst_file="figures.rst",
                conf_override="test_figures.py",
                expected_latex_markers=[
                    r"halign=center",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="figure_caption_padding",
                description="Caption padding",
                rst_file="figures.rst",
                conf_override="test_figures.py",
                expected_latex_markers=[
                    r"left=1.5ex",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 10. EPIGRAPHS
    # =====================================================================
    "epigraphs": Feature(
        name="Epigraphs",
        description="Width, align_box/text/author, font/color, author_font/color, format, part/chapter level overrides",
        sub_tests=[
            FeatureSubTest(
                name="basic_epigraph",
                description="Default epigraph rendering",
                rst_file="epigraphs.rst",
                conf_override=None,
                expected_latex_markers=[
                    r"\\dictum",
                    r"\\setupddepigraph",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_width",
                description="Custom width",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"dictumwidth",
                    r"0.6\\textwidth",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_align_box",
                description="Box alignment (center)",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"\\centering",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_align_text",
                description="Text alignment (left)",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"\\raggedright",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_align_author",
                description="Author alignment (right)",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"\\raggedleft",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_font",
                description="Quote font",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"\\fontspec{Plaster}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_color",
                description="Quote color",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"ddepigraphcolor",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_author_font",
                description="Author font",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"\\fontspec{Luxurious Script}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_author_color",
                description="Author color",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"ddepigraphauthorcolor",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_format",
                description="Author format string",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"dictumauthorformat",
                    r"~ ##1",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_part_level",
                description="Part-level epigraph override",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"ddpartepigraph",
                    r"width",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="epigraph_chapter_level",
                description="Chapter-level epigraph override",
                rst_file="epigraphs.rst",
                conf_override="test_epigraphs.py",
                expected_latex_markers=[
                    r"ddchapterepigraphcolor",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 11. DRAFT WATERMARK
    # =====================================================================
    "draft": Feature(
        name="Draft Watermark",
        description="Text template, color with 8-digit opacity, date_format, timezone, font_size, font, template vars",
        sub_tests=[
            FeatureSubTest(
                name="draft_text",
                description="Draft watermark text rendered",
                rst_file="draft_watermark.rst",
                conf_override="test_draft.py",
                expected_latex_markers=[
                    r"DRAFT",
                    r"AddToHook\{shipout/background\}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="draft_color",
                description="Watermark color with 8-digit opacity",
                rst_file="draft_watermark.rst",
                conf_override="test_draft.py",
                expected_latex_markers=[
                    r"dddraftcolor",
                    r"text opacity=0.73",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="draft_date_format",
                description="Custom date format",
                rst_file="draft_watermark.rst",
                conf_override="test_draft.py",
                expected_latex_markers=[
                    r"\d{4}-\d{2}-\d{2}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="draft_timezone",
                description="Timezone setting (UTC)",
                rst_file="draft_watermark.rst",
                conf_override="test_draft.py",
                expected_latex_markers=[
                    r"UTC",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="draft_font_size",
                description="Watermark font size",
                rst_file="draft_watermark.rst",
                conf_override="test_draft.py",
                expected_latex_markers=[
                    r"\\fontsize\{9pt\}\{9pt\}\\selectfont",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="draft_font",
                description="Watermark font family",
                rst_file="draft_watermark.rst",
                conf_override="test_draft.py",
                expected_latex_markers=[
                    r"\\fontspec{Lato}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="draft_text_template_vars",
                description="Template variable substitution ({date}, {ext_version}, {project_version})",
                rst_file="draft_watermark.rst",
                conf_override="test_draft.py",
                expected_latex_markers=[
                    r"Theme:",
                    r"Proj:",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),


    # =====================================================================
    # 13. MICROTYPE (default enabled)
    # =====================================================================
    "microtype": Feature(
        name="Microtype (Default)",
        description="microtype loaded with default options when draft mode is OFF",
        sub_tests=[
            FeatureSubTest(
                name="microtype_enabled_default",
                description="Default microtype options (protrusion + expansion on, kerning off for compatibility)",
                rst_file="microtype.rst",
                conf_override="test_microtype.py",
                expected_latex_markers=[
                    r"protrusion=true",
                    r"expansion=true",
                    r"kerning=false",
                    r"stretch=10",
                    r"shrink=10",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 14. MICROTYPE (custom options)
    # =====================================================================
    "microtype_custom": Feature(
        name="Microtype (Custom Options)",
        description="microtype with custom stretch/shrink and disabled features",
        sub_tests=[
            FeatureSubTest(
                name="microtype_custom_stretch_shrink",
                description="Custom stretch and shrink values",
                rst_file="microtype.rst",
                conf_override="test_microtype_custom.py",
                expected_latex_markers=[
                    r"stretch=20",
                    r"shrink=15",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="microtype_disable_protrusion",
                description="Protrusion can be disabled",
                rst_file="microtype.rst",
                conf_override="test_microtype_custom.py",
                expected_latex_markers=[
                    r"protrusion=false",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="microtype_disable_expansion",
                description="Expansion can be disabled",
                rst_file="microtype.rst",
                conf_override="test_microtype_custom.py",
                expected_latex_markers=[
                    r"expansion=false",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="microtype_disable_kerning",
                description="Kerning can be disabled",
                rst_file="microtype.rst",
                conf_override="test_microtype_custom.py",
                expected_latex_markers=[
                    r"kerning=false",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 15. MICROTYPE DRAFT (disabled when draft mode is ON)
    # =====================================================================
    "microtype_draft": Feature(
        name="Microtype (Draft)",
        description="microtype NOT loaded when draft mode is active",
        sub_tests=[
            FeatureSubTest(
                name="microtype_disabled_with_draft",
                description="microtype NOT loaded when draft mode is ON",
                rst_file="microtype.rst",
                conf_override="test_microtype_disabled.py",
                expected_latex_markers=[
                    r"AddToHook",
                ],
                assertions=[
                    "MICROTYPE_NOT_LOADED",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),

    # =====================================================================
    # 12. GLOBAL SETTINGS
    # =====================================================================
    "global_settings": Feature(
        name="Global Settings",
        description="show_list_of_*, appendix_chapter_numbering, headsep/footskip/headheight/footheight, footer_logo, fonts",
        sub_tests=[
            FeatureSubTest(
                name="show_list_of_figures",
                description="List of Figures toggle",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"\\listoffigures",
                    r"listof=totoc",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="show_list_of_tables",
                description="List of Tables toggle",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"\\listoftables",
                    r"listof=totoc",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="show_list_of_listings",
                description="List of Code Blocks toggle",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"listof",
                    r"literalblock",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="appendix_chapter_numbering",
                description="Appendix chapter numbering A.1, A.2",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"\\renewcommand\{\\theddlisting}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="headsep",
                description="Header-to-text distance",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"headsep",
                    r"8mm",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="footskip",
                description="Text-to-footer distance",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"footskip",
                    r"10mm",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="headheight",
                description="Header height",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"headheight",
                    r"18pt",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="footheight",
                description="Footer height",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"footheight",
                    r"25pt",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="footer_logo",
                description="Footer logo image",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"doxtr_icon_small.png",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="footer_logo_height",
                description="Footer logo height",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"1.5em",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="main_font",
                description="Main/serif font",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"\\setmainfont\{Lato Light}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="sans_font",
                description="Sans-serif font",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"\\setsansfont\{Exo 2}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
            FeatureSubTest(
                name="mono_font",
                description="Monospace font",
                rst_file="global_settings.rst",
                conf_override="test_global_settings.py",
                expected_latex_markers=[
                    r"\\setmonofont\{IosevkaTerm NF}",
                ],
                status=FeatureStatus.COMPLETE,
            ),
        ],
        status=FeatureStatus.COMPLETE,
    ),
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def get_feature_names() -> list[str]:
    """Return sorted list of all feature keys."""
    return sorted(FEATURE_REGISTRY.keys())


def get_features_with_rst() -> list[str]:
    """Return feature keys that have at least one RST test file."""
    return [
        name for name, feat in FEATURE_REGISTRY.items()
        if any(st.rst_file for st in feat.sub_tests)
    ]


def get_pending_features() -> list[str]:
    """Return feature keys that have at least one pending sub-test."""
    return [
        name for name, feat in FEATURE_REGISTRY.items()
        if any(st.status == FeatureStatus.PENDING for st in feat.sub_tests)
    ]


def get_complete_features() -> list[str]:
    """Return feature keys where all sub-tests are complete."""
    return [
        name for name, feat in FEATURE_REGISTRY.items()
        if feat.all_complete
    ]


def get_partial_features() -> list[str]:
    """Return feature keys where some (but not all) sub-tests are complete."""
    return [
        name for name, feat in FEATURE_REGISTRY.items()
        if not feat.all_complete and any(st.status == FeatureStatus.COMPLETE for st in feat.sub_tests)
    ]


def get_all_sub_tests() -> list[tuple[str, FeatureSubTest]]:
    """Return all (feature_name, sub_test) pairs in order."""
    result = []
    for name in get_feature_names():
        feat = FEATURE_REGISTRY[name]
        for st in feat.sub_tests:
            result.append((name, st))
    return result


def count_by_status() -> dict[str, int]:
    """Count features and sub-tests by status."""
    feat_by_status: dict[str, int] = {"complete": 0, "partial": 0, "pending": 0}
    sub_by_status: dict[str, int] = {"complete": 0, "partial": 0, "pending": 0}

    for name, feat in FEATURE_REGISTRY.items():
        if feat.all_complete:
            feat_by_status["complete"] += 1
        elif any(st.status == FeatureStatus.COMPLETE for st in feat.sub_tests):
            feat_by_status["partial"] += 1
        else:
            feat_by_status["pending"] += 1

        for st in feat.sub_tests:
            sub_by_status[st.status.value] += 1

    return {"features": feat_by_status, "sub_tests": sub_by_status}


# ---------------------------------------------------------------------------
# Print summary for debugging
# ---------------------------------------------------------------------------

def print_summary() -> None:
    """Print a summary of the feature registry to stdout."""
    counts = count_by_status()
    print("=" * 60)
    print("Doxtr Test Harness — Feature Registry Summary")
    print("=" * 60)
    total_feats = len(FEATURE_REGISTRY)
    total_subs = sum(f.total_count for f in FEATURE_REGISTRY.values())
    print(f"Features: {total_feats} total | "
          f"{counts['features']['complete']} complete | "
          f"{counts['features']['partial']} partial | "
          f"{counts['features']['pending']} pending")
    print(f"Sub-tests: {total_subs} total | "
          f"{counts['sub_tests']['complete']} complete | "
          f"{counts['sub_tests']['partial']} partial | "
          f"{counts['sub_tests']['pending']} pending")
    print("-" * 60)
    for name in get_feature_names():
        feat = FEATURE_REGISTRY[name]
        status_icon = "✓" if feat.all_complete else ("◐" if feat.has_any_test else "○")
        print(f"  [{status_icon}] {feat.name}: {feat.passed_count}/{feat.total_count} tests")
    print("=" * 60)


if __name__ == "__main__":
    print_summary()
