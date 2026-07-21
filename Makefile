.PHONY: install test demo lint docs clean

install:
	pip install -e ".[dev]"

test:
	pytest

demo:
	streamlit run vireon_lab/dashboard/app.py

lint:
	ruff check .
	mypy vireon_lab

docs:
	mkdocs build

clean:
	rm -rf dist build *.egg-info .pytest_cache .mypy_cache .ruff_cache
