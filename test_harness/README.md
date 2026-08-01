# Doxtr PDF Theme Core — Test Harness

A comprehensive test harness for **doxtr-pdf-theme-core** that demonstrates every
existing styling feature and validates LaTeX output.

## Quick Start

```bash
# Run all features
cd test_harness
python test_runner.py

# Run a specific feature
python test_runner.py --feature headings

# Clean build and run
python test_runner.py --clean

# Generate report without building LaTeX
python test_runner.py --report-only

# Verbose output
python test_runner.py --verbose

# Exit with code 1 if any tests are pending (CI-friendly)
python test_runner.py --fail-on-pending

# Assertion-only mode (no marker validation)
python test_runner.py --assertions-only
```

### Makefile Commands

```bash
make help                    # Show all available commands
make test                    # Run all features
make test-feature=headings   # Run specific feature
make clean                   # Clean build artifacts
make build                   # Build LaTeX only
make report                  # Generate report only
make summary                 # Show feature registry summary
make install                 # Install dependencies
make doc8                    # Validate all RST files
make ci                      # CI-friendly test
make list-features           # List features and status
```

## Architecture

```
test_harness/
├── features.py                    # ← Single source of truth (auto-discovers everything)
├── test_runner.py                 # Build + validation pipeline
├── assertions.py                  # Reusable assertion types for validation
├── conf.py                        # Base Sphinx configuration
├── conf_overrides/                # Per-feature conf.py overrides
├── source/
│   ├── _extensions/               # Sphinx extensions (auto-include)
│   ├── _test_cases/               # Per-feature RST test content
│   ├── _static/                   # Test assets (images, etc.)
│   └── index.rst                  # Entry point (auto-includes toctree)
├── build/                         # Generated build artifacts
│   ├── latex/                     # LaTeX output
│   └── reports/                   # Test reports
├── Makefile                       # Common commands
└── README.md                      # This file
```

## How It Works

### 1. Feature Registry (`features.py`)

Every feature and sub-test is defined in `features.py`. This is the **single source of truth**:

```python
FEATURE_REGISTRY = {
    "headings": Feature(
        name="Headings",
        description="Chapter, section, subsection alignment, margin, colors, lines",
        sub_tests=[
            FeatureSubTest(
                name="chapter_number_margin",
                description="Chapter numbers in margin with decorative line",
                rst_file="headings.rst",
                conf_override="test_headings.py",
                expected_latex_markers=[r"\\doxtr@chapter@align@right"],
                assertions=["COLOR_IN_CMYK", "FONT_SPEC_USED"],  # Phase 4
                status=FeatureStatus.PENDING,
            ),
        ],
    ),
    # ... more features
}
```

### 2. Auto-Inclusion

The `auto_include_tests` extension reads `features.py` and auto-generates the toctree.
**New features are automatically included** — no manual `index.rst` edits needed.

### 3. Per-Feature conf.py Overrides

Each feature can have its own conf.py override in `conf_overrides/`:

```python
# conf_overrides/test_headings.py
doxtr_headings = {
    'chapter': {
        'number_margin': True,
        'color': '#FF00D9',
    },
}
```

These are merged on top of the base `conf.py` at build time.

### 4. LaTeX Validation

The test runner:
1. Builds the LaTeX output
2. Parses the `.tex` file for `expected_latex_markers`
3. Checks `assertions` against predefined patterns
4. Compares against expected markers from `features.py`
5. Generates a summary report

### 5. Assertion Types (Phase 4)

Reusable assertions for validating LaTeX output:

```python
from assertions import AssertType

# Color assertions
AssertType.COLOR_DEFINED       # Any \definecolor command
AssertType.COLOR_IN_CMYK       # CMYK color definition
AssertType.COLOR_IN_RGB        # RGB color definition

# tcolorbox assertions
AssertType.TCOLORBOX_DEFINED   # \newtcolorbox command
AssertType.TCOLORBOX_WITH_STYLE # tcbset with style

# TikZ assertions
AssertType.TIKZ_LIBRARY_LOADED  # \usetikzlibrary command
AssertType.TIKZ_COMMAND_USED    # \tikz command

# Font assertions
AssertType.FONT_SPEC_USED       # \fontspec command
AssertType.FONT_FAMILY_LOADED   # \setmainfont/\setsansfont/\setmonofont

# KOMA-Script assertions
AssertType.KOMA_FONT_DEFINED    # \addtokomafont command
AssertType.KOMA_OPTIONS_SET     # \KOMAoptions command

# Document structure assertions
AssertType.GEOMETRY_SET         # \geometry command
AssertType.TOC_ENTRY            # \addtocontents/\addcontentsline
AssertType.CHAPTER_FORMAT_DEFINED  # \renewcommand.*\chapterformat
AssertType.SECTION_FORMAT_DEFINED  # \renewcommand.*\sectionformat

# List assertions
AssertType.LIST_OF_FIGURES      # \listoffigures
AssertType.LIST_OF_TABLES       # \listoftables
AssertType.LIST_OF_LISTINGS     # literalblock in list

# Meta assertions
AssertType.FILE_SIZE_RANGE      # Output file size in range
AssertType.COMPILATION_SUCCESS  # LaTeX compilation succeeded
```

Usage in `features.py`:

```python
FeatureSubTest(
    name="my_test",
    description="My test description",
    rst_file="my_feature.rst",
    conf_override="test_my_feature.py",
    expected_latex_markers=[r"my_marker"],
    assertions=[
        "COLOR_IN_CMYK",
        "TCOLORBOX_DEFINED",
        "FONT_SPEC_USED",
    ],
    status=FeatureStatus.PENDING,
),
```

### 6. Adding a New Test Case

### Step 1: Add to `features.py`

```python
FeatureSubTest(
    name="my_new_test",
    description="Description of what this tests",
    rst_file="my_feature.rst",
    conf_override="test_my_feature.py",
    expected_latex_markers=[r"\\myNewMacro"],
    assertions=["COLOR_IN_CMYK", "TCOLORBOX_DEFINED"],
    status=FeatureStatus.PENDING,
),
```

### Step 2: Create the RST File (optional)

```rst
# source/_test_cases/my_feature.rst

My Feature Test
===============

This is my custom test content.

.. code-block:: python

   def hello():
       return "world"
```

### Step 3: Create the conf.py Override (optional)

```python
# conf_overrides/test_my_feature.py
doxtr_my_setting = 'value'
```

### Step 4: Run and Verify

```bash
python test_runner.py --feature my_feature --verbose
```

### Step 5: Mark Complete

```python
# In features.py, update the status
status=FeatureStatus.COMPLETE,
```

## Running All Features

```bash
# Full test run
python test_runner.py

# With clean build
python test_runner.py --clean

# Fail if any tests are pending (CI-friendly)
python test_runner.py --fail-on-pending

# Assertion-only mode
python test_runner.py --assertions-only
```

## Reports

Reports are saved to `build/reports/`:

```
test_harness/build/reports/
├── report_all.txt          # Report for all features
└── report_<feature>.txt    # Report for individual features
```

## Feature Coverage

The harness covers all features from `core_config.py`:

| Feature | Sub-Tests | Status |
|---------|-----------|--------|
| Headings | 14 | Complete ✓ |
| Parts | 8 | Complete ✓ |
| Title Page | 15 | Complete ✓ |
| Code Blocks | 10 | Complete ✓ |
| Admonitions | 15 | Pending |
| Sphinx Needs | 9 | Pending |
| Containers | 15 | Pending |
| Tables | 13 | Pending |
| Figures | 6 | Pending |
| Epigraphs | 12 | Pending |
| Draft Watermark | 7 | Pending |
| Global Settings | 13 | Pending |

## CI Integration

The test harness is integrated into CI via `.github/workflows/test-harness.yml`:

```yaml
name: Test Harness
on: [push, pull_request]
jobs:
  test-harness:
    runs-on: ubuntu-latest
    container: authsec/doxtr:0.0.10
    steps:
      - uses: actions/checkout@v4
      - name: Run Test Harness
        run: |
          cd test_harness
          python test_runner.py --fail-on-pending
```

## Notes

- **Never edit `index.rst` manually** — it uses `.. include:: _generated_toctree.rst`
- **Never delete `features.py`** — it is the single source of truth
- **Use raw strings for LaTeX markers** — `r"\\definecolor"` not `"\\definecolor"`
- **8-digit hex opacity** is supported in conf.py overrides: `'#AABBCCDD'`
- **All RST files are validated with `doc8`** before being committed
- **Add new assertion types** in `assertions.py` following the existing pattern

## Adding New Assertion Types

To add a new assertion type:

1. Add a value to `AssertType` enum in `assertions.py`
2. Implement the check function in `_check_single_assertion()`
3. Add a description in `ASSERTION_DESCRIPTIONS`
4. Use in `features.py` via the `assertions` field

Example:

```python
# In assertions.py
class AssertType(Enum):
    MY_NEW_ASSERTION = "my_new_assertion"

ASSERTION_DESCRIPTIONS = {
    AssertType.MY_NEW_ASSERTION: "My new assertion description",
}

def _check_single_assertion(...):
    if assertion == AssertType.MY_NEW_ASSERTION:
        found = bool(re.search(r"my_pattern", tex_content))
        return AssertionResult(
            assertion_type=assertion,
            passed=found,
            description=desc,
            details="Found pattern" if found else "No pattern found",
        )
```
