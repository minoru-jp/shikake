.PHONY: test lint format-check typecheck check

test:
	python -m unittest discover -s tests -v

lint:
	ruff check .

format-check:
	ruff format --check .

typecheck:
	basedpyright

check: test lint format-check typecheck
