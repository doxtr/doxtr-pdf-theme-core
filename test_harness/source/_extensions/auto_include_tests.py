"""
Doxtr Test Harness — Auto-Include Sphinx Extension

This extension reads features.py and auto-generates the toctree for the test
harness. New features are automatically included — no manual index.rst edits needed.

Usage:
    Add "auto_include_tests" to your extensions list in conf.py.
    The extension will automatically:
    1. Read FEATURE_REGISTRY from features.py
    2. Generate _generated_toctree.rst with all features that have RST files
    3. Group features by status (complete, partial, pending)
"""

from __future__ import annotations

from pathlib import Path

# Import features at module level
import sys

# Ensure we can import features.py from the test_harness directory
_harness_dir = Path(__file__).resolve().parent.parent
if str(_harness_dir) not in sys.path:
    sys.path.insert(0, str(_harness_dir))

from features import FEATURE_REGISTRY, FeatureStatus


def setup(app):
    """Register the extension with Sphinx."""
    app.add_config_value("test_harness_features", None, "env")
    app.connect("builder-inited", on_builder_inited)
    return {
        "version": "0.0.1",
        "parallel_read_safe": True,
    }


def on_builder_inited(app):
    """
    Called when the Sphinx builder is initialized.
    Generates the auto toctree from the feature registry.
    """
    # Store feature registry in app config for access by other extensions/templates
    app.config.test_harness_features = FEATURE_REGISTRY

    # Generate the toctree
    toctree_content = _generate_toctree()

    # Write to a file that index.rst will include
    toctree_path = Path(app.srcdir) / "_generated_toctree.rst"
    toctree_path.write_text(toctree_content, encoding="utf-8")


def _generate_toctree() -> str:
    """Generate the toctree content from the feature registry."""
    lines = [
        ".. toctree::\n",
        "   :maxdepth: 1\n",
        "   :caption: Test Cases\n",
        "   :hidden:\n",
        "\n",
    ]

    # Group features by status
    for status in [FeatureStatus.COMPLETE, FeatureStatus.PARTIAL, FeatureStatus.PENDING]:
        features_with_status = [
            name for name, feat in FEATURE_REGISTRY.items()
            if any(st.status == status for st in feat.sub_tests)
        ]
        if not features_with_status:
            continue

        lines.append(f"\n**{status.value.upper()}**\n\n")
        for name in sorted(features_with_status):
            feat = FEATURE_REGISTRY[name]
            has_rst = any(st.rst_file for st in feat.sub_tests)
            if has_rst:
                lines.append(f"   _test_cases/{name}\n")

    return "".join(lines)
