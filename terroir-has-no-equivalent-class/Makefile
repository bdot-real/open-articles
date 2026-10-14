.PHONY: install test naive defined words law tax gate reproduce clean

install:
	pip install -r requirements.txt

test:
	@PYTHONPATH=src python -m pytest tests -v

# 1. fr:Terroir owl:equivalentClass en:Soil, and what the reasoner does with it.
naive:
	@PYTHONPATH=src python -m terroir_onto naive

# 2. The minted class, classified from its definition alone.
defined:
	@PYTHONPATH=src python -m terroir_onto defined

# 3. Words with no English equivalent: borrowed or paraphrased.
words:
	@PYTHONPATH=src python -m terroir_onto words

# 4. Trusts across legal systems, and bijural labels.
law:
	@PYTHONPATH=src python -m terroir_onto law

# 5. Tax class per jurisdiction, and the global-class inconsistency.
tax:
	@PYTHONPATH=src python -m terroir_onto tax

# 6. The SHACL mapping gate.
gate:
	@PYTHONPATH=src python -m terroir_onto gate

reproduce: test
	@PYTHONPATH=src python -m terroir_onto all

clean:
	find . -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache src/*.egg-info
