"""
Doxtr Test Harness — Test Runner

Builds the LaTeX output for each feature (or all features), validates the
generated .tex file against expected_latex_markers from features.py, and
produces a summary report.

Usage:
    python test_runner.py                          # Run all features
    python test_runner.py --feature headings       # Run specific feature
    python test_runner.py --clean                  # Clean build directory first
    python test_runner.py --report-only            # Generate report without building
    python test_runner.py --fail-on-pending        # Exit non-zero if any pending tests
    python test_runner.py --verbose                # Show full LaTeX output

Exit codes:
    0  All tests passed (or no pending tests)
    1  One or more tests failed
    2  Invalid arguments
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# Add test_harness to path so we can import features.py
sys.path.insert(0, str(Path(__file__).parent))
from features import (
    FEATURE_REGISTRY,
    FeatureStatus,
    count_by_status,
    get_feature_names,
    get_features_with_rst,
    get_pending_features,
    print_summary,
)
from assertions import (
    AssertType,
    check_assertions,
    format_assertion_results,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HARNESS_DIR = Path(__file__).parent.resolve()
SOURCE_DIR = HARNESS_DIR / "source"
BUILD_DIR = HARNESS_DIR / "build" / "latex"
OVERRIDES_DIR = HARNESS_DIR / "conf_overrides"
REPORT_DIR = HARNESS_DIR / "build" / "reports"

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class TestResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubTestResult:
    name: str
    description: str
    rst_file: Optional[str]
    conf_override: Optional[str]
    expected_markers: list[str]
    status: TestResult
    found_markers: list[str] = None
    missing_markers: list[str] = None
    assertion_results: list = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.found_markers is None:
            self.found_markers = []
        if self.missing_markers is None:
            self.missing_markers = []
        if self.assertion_results is None:
            self.assertion_results = []


@dataclass
class FeatureResult:
    name: str
    description: str
    sub_results: list[SubTestResult]
    status: TestResult

    @property
    def all_passed(self) -> bool:
        return all(sr.status == TestResult.PASSED for sr in self.sub_results)

    @property
    def has_any_test(self) -> bool:
        return len(self.sub_results) > 0


# ---------------------------------------------------------------------------
# conf.py override loader
# ---------------------------------------------------------------------------


def load_conf_override(filename: str) -> Optional[str]:
    """Load a conf.py override file and return its content as a string."""
    override_path = OVERRIDES_DIR / filename
    if not override_path.exists():
        return None
    return override_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# LaTeX builder
# ---------------------------------------------------------------------------


def build_latex_for_feature(feature_name: str, clean: bool = False) -> tuple[Path, str]:
    """
    Build the LaTeX output for a single feature with its specific conf.py overrides.

    Returns (tex_file_path, build_output).
    """
    feat = FEATURE_REGISTRY[feature_name]

    # Clean if requested
    if clean and BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Always wipe the doctrees cache between feature builds. Each feature uses a
    # different conf.py, and Sphinx's incremental build will reuse stale cached
    # AST nodes from a prior feature if doctrees are not cleared, causing missing
    # LaTeX output for newly-registered config values (e.g. doxtr_container_mapping).
    doctrees_dir = BUILD_DIR / ".doctrees"
    if doctrees_dir.exists():
        shutil.rmtree(doctrees_dir)

    # Also delete the output .tex file so Sphinx always writes a fresh one.
    # Without this, Sphinx may skip writing if it considers the output up-to-date
    # even after the doctrees were cleared.
    tex_file_early = BUILD_DIR / "doxtr-test-harness.tex"
    if tex_file_early.exists():
        tex_file_early.unlink()

    # Generate a temporary conf.py with ONLY this feature's overrides
    base_conf = (HARNESS_DIR / "conf.py").read_text(encoding="utf-8")

    # Collect unique overrides for this feature (deduplicate by filename)
    seen_files: set[str] = set()
    feature_overrides: list[str] = []
    for st in feat.sub_tests:
        if st.conf_override and st.conf_override not in seen_files:
            seen_files.add(st.conf_override)
            content = load_conf_override(st.conf_override)
            if content:
                feature_overrides.append(content)

    # Write merged conf to source/
    conf_path = SOURCE_DIR / "conf.py"
    merged_conf = base_conf
    for override in feature_overrides:
        merged_conf += "\n\n# === Merged conf.py override ===\n" + override

    conf_path.write_text(merged_conf, encoding="utf-8")

    # Generate the auto toctree — only include this feature
    toctree_path = SOURCE_DIR / "_generated_toctree.rst"
    lines = [
        ".. toctree::\n",
        "   :maxdepth: 1\n",
        "   :caption: Test Cases\n",
        "   :hidden:\n",
        "\n",
        f"   _test_cases/{feature_name}\n",
    ]
    toctree_path.write_text("".join(lines), encoding="utf-8")

    # Run sphinx-build
    tex_file = BUILD_DIR / "doxtr-test-harness.tex"

    cmd = [
        sys.executable, "-m", "sphinx",
        "-b", "latex",
        "-c", str(SOURCE_DIR),
        "-d", str(BUILD_DIR / ".doctrees"),
        str(SOURCE_DIR),
        str(BUILD_DIR),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(HARNESS_DIR),
        )
        build_output = result.stdout + result.stderr
        return tex_file, build_output
    except subprocess.TimeoutExpired:
        return tex_file, "ERROR: Build timed out after 120 seconds"
    except Exception as e:
        return tex_file, f"ERROR: {e}"


# ---------------------------------------------------------------------------
# LaTeX output parser
# ---------------------------------------------------------------------------


def parse_latex_output(tex_file: Path) -> str:
    """Read and return the LaTeX .tex output file."""
    if not tex_file.exists():
        return ""
    return tex_file.read_text(encoding="utf-8")


def check_markers(tex_content: str, markers: list[str]) -> tuple[list[str], list[str]]:
    """
    Check which markers are found and which are missing in the LaTeX output.

    Returns (found_markers, missing_markers).
    """
    found = []
    missing = []
    for marker in markers:
        # Try as regex first, fall back to literal string
        try:
            if re.search(marker, tex_content):
                found.append(marker)
            else:
                missing.append(marker)
        except re.error:
            # Fall back to literal string match
            if marker in tex_content:
                found.append(marker)
            else:
                missing.append(marker)
    return found, missing


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------


def generate_report(
    feature_results: list[FeatureResult],
    feature_name: Optional[str] = None,
) -> str:
    """Generate a text report of test results."""
    lines = []
    lines.append("=" * 70)
    lines.append("         Doxtr PDF Theme Core — Test Harness Report")
    lines.append("=" * 70)
    lines.append("")

    if feature_name:
        lines.append(f"Feature: {feature_name}")
        lines.append("-" * 70)
    else:
        counts = count_by_status()
        total_feats = len(FEATURE_REGISTRY)
        total_subs = sum(f.total_count for f in FEATURE_REGISTRY.values())
        lines.append(f"Features: {total_feats} total | "
                     f"{counts['features']['complete']} complete | "
                     f"{counts['features']['partial']} partial | "
                     f"{counts['features']['pending']} pending")
        lines.append(f"Sub-tests: {total_subs} total | "
                     f"{counts['sub_tests']['complete']} complete | "
                     f"{counts['sub_tests']['partial']} partial | "
                     f"{counts['sub_tests']['pending']} pending")
        lines.append("")
        lines.append("-" * 70)

    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for fr in feature_results:
        passed = sum(1 for sr in fr.sub_results if sr.status == TestResult.PASSED)
        failed = sum(1 for sr in fr.sub_results if sr.status == TestResult.FAILED)
        skipped = sum(1 for sr in fr.sub_results if sr.status == TestResult.SKIPPED)
        total_passed += passed
        total_failed += failed
        total_skipped += skipped

        status_icon = "✓" if fr.all_passed else "✗"
        lines.append(f"\n[{status_icon}] {fr.name}: {passed}/{len(fr.sub_results)} passed")
        lines.append(f"    {fr.description}")

        for sr in fr.sub_results:
            if sr.status == TestResult.PASSED:
                lines.append(f"    [✓] {sr.name}: {sr.description}")
                if sr.assertion_results:
                    for ar in sr.assertion_results:
                        if not ar.passed:
                            lines.append(f"        ✗ Assertion failed: {ar.description}")
            elif sr.status == TestResult.FAILED:
                lines.append(f"    [✗] {sr.name}: {sr.description}")
                if sr.missing_markers:
                    lines.append(f"        Missing markers: {sr.missing_markers}")
                if sr.assertion_results:
                    for ar in sr.assertion_results:
                        if not ar.passed:
                            lines.append(f"        ✗ Assertion failed: {ar.description}")
                if sr.error:
                    lines.append(f"        Error: {sr.error}")
            elif sr.status == TestResult.SKIPPED:
                lines.append(f"    [○] {sr.name}: {sr.description} (skipped)")

    lines.append("\n" + "-" * 70)
    lines.append(f"\nSummary: {total_passed} passed, {total_failed} failed, {total_skipped} skipped")

    if total_failed > 0:
        lines.append("\n❌ SOME TESTS FAILED")
    elif total_skipped > 0 and total_failed == 0:
        lines.append("\n⚠ All tests passed (some skipped)")
    else:
        lines.append("\n✅ ALL TESTS PASSED")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def save_report(report_text: str, feature_name: Optional[str] = None) -> Path:
    """Save the report to the build/reports directory."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if feature_name:
        report_file = REPORT_DIR / f"report_{feature_name}.txt"
    else:
        report_file = REPORT_DIR / "report_all.txt"

    report_file.write_text(report_text, encoding="utf-8")
    return report_file


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_tests(
    feature_name: Optional[str] = None,
    clean: bool = False,
    verbose: bool = False,
    assertions_only: bool = False,
) -> tuple[list[FeatureResult], bool]:
    """
    Run tests for the specified feature (or all features).

    Each feature is built independently with its own conf.py overrides,
    then validated against expected_latex_markers from features.py.

    Returns (feature_results, all_passed).
    """
    # Determine which features to test
    if feature_name:
        feature_names = [feature_name]
    else:
        feature_names = get_feature_names()

    feature_results: list[FeatureResult] = []

    for fname in feature_names:
        feat = FEATURE_REGISTRY[fname]
        tex_file, build_output = build_latex_for_feature(fname, clean)

        # Only clean after first feature (subsequent features share the build dir)
        clean = False

        tex_content = parse_latex_output(tex_file)

        sub_results: list[SubTestResult] = []

        for st in feat.sub_tests:
            # Parse assertions from string names
            assertion_types = []
            for assertion_str in st.assertions:
                try:
                    assertion_types.append(AssertType(assertion_str))
                except ValueError:
                    pass

            # Check if we have expected markers or assertions
            if not st.expected_latex_markers and not assertion_types:
                # No markers to check — mark as passed if RST file exists
                if st.rst_file:
                    sub_results.append(SubTestResult(
                        name=st.name,
                        description=st.description,
                        rst_file=st.rst_file,
                        conf_override=st.conf_override,
                        expected_markers=[],
                        assertion_results=[],
                        status=TestResult.PASSED,
                    ))
                else:
                    sub_results.append(SubTestResult(
                        name=st.name,
                        description=st.description,
                        rst_file=st.rst_file,
                        conf_override=st.conf_override,
                        expected_markers=[],
                        assertion_results=[],
                        status=TestResult.SKIPPED,
                    ))
                continue

            # Check markers (unless assertions_only mode)
            found, missing = [], []
            if not assertions_only and st.expected_latex_markers:
                found, missing = check_markers(tex_content, st.expected_latex_markers)

            # Check assertions if any
            assertion_results = []
            if assertion_types:
                assertion_results = check_assertions(
                    tex_content, assertion_types, file_size=tex_file.stat().st_size if tex_file.exists() else None
                )

            # Determine status based on markers
            if st.expected_latex_markers and not assertions_only:
                status = TestResult.PASSED if not missing else TestResult.FAILED
            elif assertion_types:
                # Only assertions, check if all passed
                status = TestResult.PASSED if all(ar.passed for ar in assertion_results) else TestResult.FAILED
            else:
                status = TestResult.PASSED if not missing else TestResult.FAILED

            sub_results.append(SubTestResult(
                name=st.name,
                description=st.description,
                rst_file=st.rst_file,
                conf_override=st.conf_override,
                expected_markers=st.expected_latex_markers,
                assertion_results=assertion_results,
                status=status,
                found_markers=found,
                missing_markers=missing,
            ))

            if verbose:
                print(f"  {'✓' if status == TestResult.PASSED else '✗'} {st.name}: "
                      f"{st.description}")
                if missing:
                    print(f"      Missing: {missing}")
                if assertion_results:
                    for ar in assertion_results:
                        icon = "✓" if ar.passed else "✗"
                        print(f"      [{icon}] {ar.description}")

        feature_results.append(FeatureResult(
            name=feat.name,
            description=feat.description,
            sub_results=sub_results,
            status=TestResult.PASSED if all(sr.status == TestResult.PASSED for sr in sub_results) else TestResult.FAILED,
        ))

    return feature_results, all(fr.all_passed for fr in feature_results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Doxtr PDF Theme Core — Test Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py                          Run all features
  python test_runner.py --feature headings       Run specific feature
  python test_runner.py --clean                  Clean build directory first
  python test_runner.py --report-only            Generate report without building
  python test_runner.py --fail-on-pending        Exit non-zero if any pending tests
  python test_runner.py --verbose                Show detailed output
        """,
    )
    parser.add_argument(
        "--feature", "-f",
        type=str,
        default=None,
        help="Run tests for a specific feature (e.g., headings, code, containers)",
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Clean the build directory before building",
    )
    parser.add_argument(
        "--report-only", "-r",
        action="store_true",
        help="Generate report from features.py without building LaTeX",
    )
    parser.add_argument(
        "--fail-on-pending",
        action="store_true",
        help="Exit with code 1 if any tests are still pending",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output during testing",
    )
    parser.add_argument(
        "--assertions-only",
        action="store_true",
        help="Only check assertions (no marker validation)",
    )

    args = parser.parse_args()

    # Print summary
    print_summary()
    print()

    if args.report_only:
        # Generate report from features.py without building
        report = generate_report([], feature_name=args.feature)
        report_file = save_report(report, args.feature)
        print(report)
        print(f"\nReport saved to: {report_file}")
        sys.exit(0)

    # Run tests
    feature_results, all_passed = run_tests(
        feature_name=args.feature,
        clean=args.clean,
        verbose=args.verbose,
        assertions_only=args.assertions_only,
    )

    # Generate and print report
    report = generate_report(feature_results, args.feature)
    report_file = save_report(report, args.feature)
    print(report)
    print(f"\nReport saved to: {report_file}")

    # Check for pending tests
    pending = get_pending_features()
    if pending:
        print(f"\n⚠ {len(pending)} feature(s) still have pending tests: {pending}")

    # Exit code
    if args.fail_on_pending and pending:
        sys.exit(1)
    elif not all_passed:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
