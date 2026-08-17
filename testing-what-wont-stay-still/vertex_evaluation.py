"""Google. Vertex Gen AI Evaluation Service.

Three modes: pointwise for an absolute score, pairwise for a preference between
two candidates, and rubric-based.

Pairwise deserves more attention than it gets. Judges are considerably better
at "which of these two is better" than at "score this one to five", because the
comparison cancels much of the judge's own calibration error. If you are
choosing between two prompt versions, that is a pairwise question, and framing
it as two pointwise measurements throws away power you cannot spare. See the
sample size table in evals/judge.py for how little you have.
"""
import os

import pandas as pd
import vertexai
from vertexai.evaluation import EvalTask, PairwiseMetric


def compare_prompt_versions(dataset: pd.DataFrame, baseline_model, candidate_model):
    vertexai.init(project=os.environ["GCP_PROJECT"],
                  location=os.environ.get("GCP_LOCATION", "us-central1"))

    task = EvalTask(
        dataset=dataset,
        metrics=[PairwiseMetric(
            metric="pairwise_booking_extraction_quality",
            baseline_model=baseline_model,
        )],
        experiment="booking-extraction",
    )
    return task.evaluate(model=candidate_model)
