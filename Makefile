.DEFAULT_TARGET: deps

.PHONY: deps format format-check run test build publish clean

deps:
	pip install --progress-bar off -e .[dev]

format:
	python -m black .

format-check:
	python -m black --check .

run:
	python -m mysql_mimic.server

types:
	python -m mypy -p mysql_mimic -p tests

types-mypyc:
	python -c "exec(open('setup.py').read().split('import sys')[0]); from mypyc.build import mypycify; mypycify(MYPYC_MODULES)"

test:
	coverage run --source=mysql_mimic -m pytest
	coverage report
	coverage html

check: format-check types types-mypyc test

build: clean
	python setup.py sdist bdist_wheel

publish: build
	twine upload dist/*

clean:
	rm -rf build dist
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
