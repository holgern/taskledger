.PHONY: release-check

release-check:
	python3 -m compileall -q taskledger tests
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
	python3 -m ruff check --config=.ruff.toml .
	python3 -m mypy taskledger
	python3 -m build
	python3 -m twine check dist/*
