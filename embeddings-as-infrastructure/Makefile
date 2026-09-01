.PHONY: install test metric dims version reproduce clean

install:
	pip install -r requirements.txt

test:
	@python -m pytest tests -v

# Invariant 1: the metric must match how the vectors were scaled.
metric:
	@python -m embeddings.invariant_metric

# Invariant 2: truncating breaks unit norm. Plus the cost curve.
dims:
	@python -m embeddings.invariant_dims

# Invariants 3 and 4: encoder skew and index staleness.
version:
	@python -m embeddings.invariant_version

reproduce: metric dims version

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache
