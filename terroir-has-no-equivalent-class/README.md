# Terroir Has No Equivalent Class

Companion code for **Terroir Has No Equivalent Class**, an article on ontology alignment when one vocabulary contains a concept the other lacks. Full article: [thebdot.substack.com](https://thebdot.substack.com/).

Every claim the article makes about reasoning, mapping and classification is a test in `tests/test_article_claims.py`. If a test fails, the prose is wrong.

## Run it

```bash
make install
make test       # one test per article claim
make reproduce  # all six demos
make gate       # or one at a time: naive, defined, words, law, tax, gate
```

Or install it as a package: `pip install -e ".[dev]"`, then `terroir-onto`.

Python 3.10+. Dependencies: `rdflib`, `owlrl` (OWL 2 RL reasoning), `pyshacl` (SHACL validation). No network access, no model downloads.

## The six demos

| # | Demo | Article section | What it shows |
| --- | --- | --- | --- |
| 1 | `naive` | Modelling terroir | `fr:Terroir owl:equivalentClass en:Soil` makes a bag of potting mix a terroir and Clos de Vougeot a kind of dirt. No error is raised. |
| 2 | `defined` | Modelling terroir | `ex:Terroir` defined by `owl:intersectionOf`. No instance is asserted to be a terroir; the reasoner decides from the parts. A Burgundy vineyard and an Ontario sugar bush qualify. A hydroponic greenhouse does not, and the demo says which dimensions it lacks. |
| 3 | `words` | Words with no English equivalent | The article's table as a SKOS vocabulary. "Borrowed" versus "paraphrased" is computed from the labels: English borrowed a word when it carries an `@en` label identical to a native form. |
| 4 | `law` | Law and tax | Common-law trust (owner: trustee), French *fiducie* (owner: fiduciaire), Quebec trust (owner: nobody). Plus one Canadian federal concept carrying four bijural labels. |
| 5 | `tax` | Law and tax | Tax classification indexed by jurisdiction. Flatten it to a single global class and the reasoner reports each hybrid entity as a disjointness violation. |
| 6 | `gate` | Why this matters | A SHACL gate for machine-proposed mappings. Weak SKOS relations pass. `owl:equivalentClass` and `skos:exactMatch` are blocked until a named person and a date are attached. |

Sample output from demo 6:

```
  BLOCK  0.82  Terroir equivalentClass Soil
  ACCEPT 0.82  Terroir relatedMatch Soil
  ACCEPT 0.79  Terroir closeMatch SenseOfPlace
  BLOCK  0.88  Saudade exactMatch Longing
  ACCEPT 0.88  Saudade broadMatch Longing
  BLOCK  0.91  QuebecTrust exactMatch Trust
  ACCEPT 0.77  Usufruct closeMatch LifeEstate
  ACCEPT 0.97  Trust exactMatch Trust
```

The first two rows have the same pair and the same score, and opposite verdicts. The score never decided anything; the relation did.

## Layout

```
ontology/
  terroir_naive.ttl       the mistake
  terroir.ttl             the minted, defined class and instance data
  untranslatables.ttl     terroir, Schadenfreude, hygge, saudade, hiraeth, komorebi, wabi-sabi
  law_tax.ttl             trusts, usufruct, bijural doublets, hybrid tax entities
  mapping_gate.shacl.ttl  the human-signature rule
  proposals.csv           illustrative mapping proposals (scores are examples, not model output)
src/terroir_onto/         loaders, reasoning and the demo CLI
tests/                    one test per article claim
reproduce.yml             CI workflow, same pattern as the other articles
```

## Things the code corrected

Building this surfaced two errors in early drafts of the data:

- **The French *fiducie* was modelled with no owner**, copying the Quebec trust. That is wrong: under the French Civil Code the fiduciaire holds the property in a separate patrimony. Only the Quebec trust is ownerless. The ownership test now pins all three.
- **wabi-sabi came out as "paraphrased"** because the only native label was in kanji, so the borrowing check could not see that English uses the romanised form. Adding the `ja-Latn` label fixed it, and the test now matches the article's table.

## Limits, on purpose

OWL membership is not causation. The model can say a terroir *has* soil, climate and tradition. It cannot say those things *produce* a recognisable taste. That claim lives in `skos:scopeNote`, which is exactly where the article says it has to live.

The legal and tax data is illustrative. It is not legal or tax advice, and real entity classification depends on elections, treaties and facts this repository does not model.

## Licence

MIT, declared in pyproject.toml.
