# When Not to Use an LLM

Companion code for the article. Every number in the piece comes from here.

```bash
pip install -r requirements.txt
make reproduce
```

That runs the whole thing from scratch: generate, train, benchmark, calibrate,
decide, cost, hybrid. Takes about ten seconds and needs no credentials.

## What it shows

**The model is small and fast.**

```
model                     AUC     AP   Brier    train       p50       p99       rows/s
--------------------------------------------------------------------------------------
Base rate (no model)    0.500  0.331   0.221    0.00s    0.000ms   0.000ms          n/a
Logistic regression     0.737  0.601   0.185    0.03s    0.180ms   0.307ms    9,329,028
Gradient boosting       0.735  0.594   0.186    0.42s    0.507ms   0.944ms      297,752
```

1,511 bytes on disk. Latency depends on your CPU, so expect different absolute
figures; the ratio between the two models is stable.

**Boosting lost, and the honest reason is in the code.** The generator in
[`noshow/generate.py`](noshow/generate.py) writes out the full data-generating
process, and it is mostly log-linear by construction. That is why the linear
model edges ahead. Real no-show data has more interaction structure and trees
usually win on it. The latency, size and calibration findings are properties of
the method and do not depend on that choice.

**Predictions are calibrated.** Largest gap between predicted and observed
across ten bands: 0.030.

```
predicted band          n   predicted   observed      gap
---------------------------------------------------------
0.1 - 0.2            2550       0.152      0.155   -0.003
0.4 - 0.5            1089       0.448      0.441   +0.007
0.7 - 0.8             337       0.745      0.736   +0.009
```

**And that is what makes the decision layer work.** Overbooking, where a
recovered slot is worth $120 and a collision costs $260:

```
 threshold  source                        overbooks           net
-----------------------------------------------------------------
     0.684  derived from the economics        6.7%       $24,040
     0.500  seems reasonable                 19.4%      $-28,880
     0.331  the base rate                    41.5%     $-256,420
```

Same model, same predictions, same data. The only thing that changed is where
the threshold came from.

## The test that makes the argument

`tests/test_decisions.py` contains the one worth reading:

```python
def test_calibration_breaks_under_a_monotone_transform(fitted):
    _, _, _, yte, p = fitted
    squashed = p ** 2
    assert roc_auc_score(yte, squashed) == pytest.approx(roc_auc_score(yte, p))
    assert max_gap(table(squashed, yte)) > 0.05
```

Squaring every probability leaves AUC completely untouched and destroys
calibration. A model can rank perfectly and be useless for thresholding, and
AUC will not tell you. That gap is the shape of what you get from anything
emitting plausible-looking numbers rather than probabilities.

```bash
make test    # 10 tests, pinning every deterministic claim in the article
```

## The cost argument, including the part that weakens it

```bash
make costs
```

```
path                          per call      monthly  vs classical
-----------------------------------------------------------------
LLM, frontier tier        $   0.001440       $8,640          139x
LLM, small tier           $   0.000070         $421            7x
Classical endpoint         ~0 marginal          $62            1x
```

139x against a frontier model is real. 7x against a small one is $400 a month,
which plenty of teams would happily pay to avoid owning a training pipeline.
If you argue against an LLM purely on token cost, someone points at that middle
row and you lose. The rates in `noshow/costs.py` are illustrative; replace them
with current pricing before quoting a figure.

## The hybrid pattern

```bash
make hybrid
```

The LLM turns language into features **at write time**. The classical model
makes the decision.

```
4 notes, 3 model calls. The repeat was cached.
At write time, so none of this is in the scoring path.
```

Three properties follow from moving extraction to write time: a second of
latency becomes invisible, cost collapses from once-per-score to once-per-note,
and a provider outage delays enrichment instead of stopping scoring.
Extraction failure returns zeros rather than raising, so a missing enrichment
degrades the prediction slightly and never blocks an appointment from being
scored.

Watch the seam under drift. `EXTRACTOR_VERSION` is part of the cache key
because upgrading the extraction model shifts the meaning of those columns with
no code change on your side. Treat a version bump as a retraining trigger.

## The four platforms

Same thirteen features, same model.

| | [scikit-learn](platforms/sklearn_local.py) | [SageMaker AI](platforms/sagemaker_train.py) | [Azure ML](platforms/azureml_job.py) | [Vertex AI](platforms/vertex_train.py) |
|---|---|---|---|---|
| Time to first model | Minutes | Hours | Hours | Hours |
| Retraining | Yours | Pipelines | Jobs plus MLflow | Pipelines |
| Drift monitoring | Build it | Model Monitor | Native | Model Monitoring |
| Feature store | Build it | Mature | Via Databricks | Native |
| Idle cost | Zero | Per endpoint hour | Per endpoint hour | Per endpoint hour |

Only `sklearn_local.py` runs here. The other three are reference scripts needing
cloud credentials.

One naming trap worth knowing: on Azure, this model belongs in **Azure ML**, not
AI Foundry. Foundry is the generative platform. Reaching for it because it is
the newer service puts a 1.5 KB logistic regression on infrastructure built for
a different problem.

## Layout

```
noshow/
  generate.py     synthetic data, generative process written out in full
  train.py        two lines of modelling
  benchmark.py    accuracy and latency, single-row and batch
  calibration.py  predicted against observed, per band
  decisions.py    threshold from economics, and what it is worth
  costs.py        LLM against classical at 200k scores/day
hybrid/
  extract.py      LLM to features at write time, cached, version-keyed
platforms/        sklearn, SageMaker AI, Azure ML, Vertex AI
tests/
```

## Caveats, stated once and clearly

The data is synthetic and the generator says exactly how. Latency varies by
machine. The cost rates are illustrative placeholders, not a rate card. The
$120 and $260 in `decisions.py` are made up, and you should substitute your own
economics, because the entire point is that those two numbers determine your
threshold and nobody else's numbers will do.
