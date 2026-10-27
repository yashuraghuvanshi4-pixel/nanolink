.PHONY: test verify serve clean install

test:
	python3 -m unittest discover tests -v

verify:
	python3 scripts/verify.py

serve:
	python3 -m nanolink.cli serve --port 8000

install:
	pip install -e .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf *.egg-info build dist .coverage
