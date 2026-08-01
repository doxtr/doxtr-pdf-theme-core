# Doxtr Test Harness — Makefile
# Common commands for running tests and managing the harness

.PHONY: help test test-feature clean build report report-all summary install latexpdf

# Default target
help:
	@echo "Doxtr Test Harness — Available Commands:"
	@echo ""
	@echo "  make test                  Run all features"
	@echo "  make test-feature=FEATURE  Run a specific feature (e.g., headings)"
	@echo "  make clean                 Clean build artifacts"
	@echo "  make build                 Build LaTeX output only"
	@echo "  make latexpdf              Build LaTeX output + compile PDF"
	@echo "  make report                Generate report only (no build)"
	@echo "  make report-all            Generate report for all features"
	@echo "  make summary               Show feature registry summary"
	@echo "  make install               Install dependencies"
	@echo "  make doc8                  Run doc8 on all RST files"
	@echo ""
	@echo "  make test-verbose          Run with verbose output"
	@echo "  make test-clean            Run with clean build"
	@echo "  make test-assertions       Run assertion-only mode"
	@echo ""
	@echo "  make ci                    Run CI-friendly test (fail on pending)"
	@echo "  make list-features         List all features and their status"
	@echo ""

# Run all features
test:
	python test_runner.py

# Run a specific feature
test-feature:
ifndef FEATURE
	$(error FEATURE is not set. Usage: make test-feature FEATURE=headings)
endif
	python test_runner.py --feature $(FEATURE)

# Run with verbose output
test-verbose:
	python test_runner.py --verbose

# Run with clean build
test-clean:
	python test_runner.py --clean

# Run with assertion-only mode
test-assertions:
	python test_runner.py --assertions-only

# Clean build artifacts
clean:
	rm -rf build/
	rm -f source/conf.py
	rm -f source/_generated_toctree.rst

# Build LaTeX output only
build:
	python test_runner.py --report-only || true
	sphinx-build -b latex source/ build/latex/ 2>/dev/null || echo "Build failed - check source/conf.py"

# Build LaTeX output + compile PDF
latexpdf:
	python test_runner.py --report-only || true
	sphinx-build -b latex source/ build/latex/ 2>/dev/null || (echo "Build failed - check source/conf.py" && exit 1)
	cd build/latex && make

# Generate report only (no build)
report:
	python test_runner.py --report-only

# Generate report for all features
report-all:
	python test_runner.py --report-only

# Show feature registry summary
summary:
	python features.py

# Install dependencies
install:
	pip install -q sphinx sphinx-needs doc8

# Run doc8 on all RST files
doc8:
	@echo "Running doc8 on all RST files..."
	@for f in source/_test_cases/*.rst; do \
		echo "Checking $$f..."; \
		doc8 "$$f" || echo "FAILED: $$f"; \
	done
	@echo "doc8 complete."

# CI-friendly test (fail on pending)
ci:
	python test_runner.py --fail-on-pending

# List all features and their status
list-features:
	@python3 -c "\
	from features import FEATURE_REGISTRY, FeatureStatus; \
	for name, feat in sorted(FEATURE_REGISTRY.items()): \
		status_icon = '✓' if feat.status == FeatureStatus.COMPLETE else ('◐' if any(st.status == FeatureStatus.COMPLETE for st in feat.sub_tests) else '○'); \
		print(f'[{status_icon}] {feat.name}: {feat.passed_count}/{feat.total_count} tests'); \
	"

# Run all features with verbose output
test-all-verbose:
	python test_runner.py --verbose --fail-on-pending || true

# Quick test (no clean, just run)
quick:
	python test_runner.py 2>&1 | grep -E "Summary|PASSED|FAILED"
