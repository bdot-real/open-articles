.PHONY: install test flakiness judge layers reproduce clean

install:
	pip install -r requirements.txt

# 18 tests across all three layers. Not one calls a model provider.
test:
	@python -m pytest tests -v

# Why non-deterministic tests do not compose.
flakiness:
	@python -m evals.flakiness

# What your eval set can and cannot see.
judge:
	@python -m evals.judge

# How much of a real failure catalogue needs a judge at all.
layers:
	@python -m evals.coverage_split

reproduce: flakiness layers judge

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache
