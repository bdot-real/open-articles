.PHONY: install test reliability effects reproduce clean

install:
	pip install -r requirements.txt

test:
	@python -m pytest tests -v

# Why blind retry saturates and replanning does not.
reliability:
	@python -m agent.reliability

# Duplicate operations from retrying timed-out calls.
effects:
	@python -m agent.side_effects

reproduce: reliability effects

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache
