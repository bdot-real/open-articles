.PHONY: install data train bench calib decide costs hybrid test reproduce clean

install:
	pip install -r requirements.txt

data:
	@python -m noshow.generate

train: data
	@python -m noshow.train

bench: data
	@python -m noshow.benchmark

calib: train
	@python -m noshow.calibration

decide: train
	@python -m noshow.decisions

costs:
	@python -m noshow.costs

hybrid:
	@python -m hybrid.extract

test:
	@python -m pytest tests -v

# Every table in the article, in order, from scratch.
reproduce: data train bench calib decide costs hybrid

clean:
	rm -rf data __pycache__ */__pycache__ .pytest_cache
