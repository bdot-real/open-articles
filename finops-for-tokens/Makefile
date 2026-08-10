.PHONY: install test demo cost gateway keys

install:
	pip install -r requirements.txt

test:
	python -m pytest tests -v

# The four failure modes as arithmetic. No model calls, no credentials, no cost.
demo:
	@python -m simulate

# Show what a prompt change does to the bill, for the last commit.
cost:
	@python -m tools.prompt_cost_diff --base HEAD~1 --head HEAD || true

# A local gateway with real budget enforcement.
gateway:
	cd platforms/litellm && docker compose up -d
	@echo "LiteLLM on :4000. Create a tenant key with: make keys TENANT=acme"

keys:
	@platforms/litellm/tenant-key.sh $(TENANT) $(BUDGET)
