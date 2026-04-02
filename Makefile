.DEFAULT_TARGET: deps

.PHONY: deps format format-check run test build publish clean

# Install dev dependencies; skip Kerberos deps on Windows (requires libkrb5-dev)
ifeq ($(OS),Windows_NT)
deps:
	pip install --progress-bar off -e ".[dev]"
else
deps:
	pip install --progress-bar off -e ".[dev,dev-krb5]"
endif

format:
	python -m black .

format-check:
	python -m black --check .

run:
	python -m mysql_mimic.server

types:
	python -m mypy -p mysql_mimic -p tests

test:
	coverage run --source=mysql_mimic -m pytest
	coverage report
	coverage html

check: format-check types test

build: clean
	python setup.py sdist bdist_wheel

publish: build
	twine upload dist/*

clean:
	rm -rf build dist
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
