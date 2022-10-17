.DEFAULT_TARGET: deps

.PHONY: deps format format-check run lint test build publish clean

deps:
	pip install --progress-bar off -e .[dev]

format:
	python -m black .

format-check:
	python -m black --check .

run:
	python -m mysql_mimic.server

lint:
	python -m pylint mysql_mimic/ tests/

types:
	python -m mypy -p mysql_mimic -p tests

test:
	coverage run --source=mysql_mimic -m pytest
	coverage report
	coverage html

check: format-check lint types test

build: clean
	python setup.py sdist bdist_wheel

publish: build
	twine upload dist/*

clean:
	rm -rf build dist
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
