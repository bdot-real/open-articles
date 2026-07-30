.PHONY: test demo review-dry install

install:
	pip install -r requirements.txt

# The conformance suite against the reference implementation. Should pass.
test:
	OSSS_IMPL=reference python -m pytest conformance -v

# The same suite against the machine-written implementation. Should fail,
# on four spec rules, in about 50 milliseconds.
demo:
	@echo "Running the conformance suite against conformance/plausible.py"
	@echo "Read that file first and see how many you can find by eye."
	@echo
	-@OSSS_IMPL=plausible python -m pytest conformance -q

# Assemble the review prompt without calling a model. Costs nothing.
review-dry:
	python -m review.cli --base origin/main --head HEAD --dry-run
