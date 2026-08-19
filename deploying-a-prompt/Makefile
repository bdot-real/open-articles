.PHONY: install test canary blast versions reproduce clean

install:
	pip install -r requirements.txt

test:
	@python -m pytest tests -v

# Can your canary see the regression it is meant to catch?
canary:
	@python -m deploy.canary

# Why detection time, not rollback time, sets the cost of a bad deploy.
blast:
	@python -m deploy.blast_radius

# What "roll back to last known good" means when two things version.
versions:
	@python -m deploy.version_matrix

reproduce: versions canary blast

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache
