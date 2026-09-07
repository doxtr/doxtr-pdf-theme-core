"""
Regression guard for FontAwesome icon-name compatibility.

A TeX Live update installed ``fontawesome7.sty`` and Sphinx auto-selects the
newest available icon package, switching its default ``iconpackage`` from
fontawesome5 to fontawesome7. Several icon names were renamed between
fontawesome5 and fontawesome6/7 (``info-circle`` -> ``circle-info``, etc.), and
the old fa5 names no longer exist in fa7 -- referencing one produces a fatal
``"Package fontawesome7 Error: The requested icon ... was not found."`` during
the LaTeX build, and no PDF is produced.

These tests assert that none of the renamed fa5 icon names remain hardcoded in
the core config defaults. They are string-only checks that need no
Sphinx/LaTeX build, so they run in the ordinary ``pytest tests/`` job and lock
in the fa5 -> fa7 rename against future regressions.
"""

import json

from doxtr_pdf_theme_core.core_config import (
    DOXTR_ADMONITIONS,
    DOXTR_CODE,
    DOXTR_CONTAINERS,
    DOXTR_CONTENTS,
    DOXTR_NEEDS,
    DOXTR_SIDEBAR,
)

# fontawesome5 icon names that were renamed in fontawesome6/7 and are therefore
# invalid under the now-default fontawesome7 package.
RENAMED_FA5_ICONS = (
    "info-circle",
    "exclamation-triangle",
    "times-circle",
    "external-link-alt",
    "file-alt",
    "cogs",
    "columns",
)

# All core config dicts that hold ``\faIcon{...}`` values.
_ICON_BEARING_CONFIGS = {
    "DOXTR_ADMONITIONS": DOXTR_ADMONITIONS,
    "DOXTR_CODE": DOXTR_CODE,
    "DOXTR_CONTAINERS": DOXTR_CONTAINERS,
    "DOXTR_CONTENTS": DOXTR_CONTENTS,
    "DOXTR_NEEDS": DOXTR_NEEDS,
    "DOXTR_SIDEBAR": DOXTR_SIDEBAR,
}


class TestNoStaleFa5IconNames:
    """Verify the core defaults use fontawesome7 icon names, not fa5."""

    def test_no_renamed_fa5_icon_in_core_defaults(self):
        """No renamed fa5 icon token may appear in any icon-bearing config."""
        for config_name, config in _ICON_BEARING_CONFIGS.items():
            blob = json.dumps(config)
            for name in RENAMED_FA5_ICONS:
                # Match the exact ``\faIcon{<name>}`` token so substrings of
                # valid names (e.g. 'code') never trigger a false positive.
                token = r"\faIcon{%s}" % name
                assert token not in blob, (
                    f"Stale fontawesome5 icon {token!r} found in "
                    f"{config_name}; rename it to its fontawesome7 equivalent."
                )
