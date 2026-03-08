# Makefile for lattice runtime

PREFIX ?= /usr/local
BINDIR = $(PREFIX)/bin
PYTHON = python3

.PHONY: help test validate install uninstall clean examples

help:
	@echo "Lattice Runtime Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  test       - Run test suite"
	@echo "  validate   - Validate example boards"
	@echo "  install    - Install to $(PREFIX)"
	@echo "  uninstall  - Remove from $(PREFIX)"
	@echo "  clean      - Remove generated files"
	@echo "  examples   - Run example boards"
	@echo ""
	@echo "Variables:"
	@echo "  PREFIX     - Installation prefix (default: /usr/local)"

test:
	@echo "Running validation tests..."
	@./lattice validate examples/simple-board
	@echo "✓ Simple board valid"
	@echo ""
	@echo "Running single tick test..."
	@./lattice run examples/simple-board --once
	@echo "✓ Single tick complete"

validate:
	@echo "Validating all example boards..."
	@for board in examples/*/board.json; do \
		dir=$$(dirname $$board); \
		echo "Validating $$dir..."; \
		./lattice validate $$dir || exit 1; \
	done
	@echo "✓ All boards valid"

install:
	@echo "Installing lattice to $(BINDIR)..."
	install -d $(BINDIR)
	install -m 755 lattice $(BINDIR)/lattice
	@echo "✓ Installed to $(BINDIR)/lattice"

uninstall:
	@echo "Removing lattice from $(BINDIR)..."
	rm -f $(BINDIR)/lattice
	@echo "✓ Uninstalled"

clean:
	@echo "Cleaning generated files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find examples -type d -name state -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Clean"

examples: examples/simple-board
	@echo "Running simple-board example..."
	@echo "Press Ctrl-C to stop"
	./lattice run examples/simple-board

.PHONY: check-python
check-python:
	@$(PYTHON) --version >/dev/null 2>&1 || (echo "Error: Python 3 required" && exit 1)
