"""AWS. SageMaker AI.

SageMaker's classical ML tooling is its most mature part, and Feature Store has
no direct Azure equivalent. If feature management is a real part of your
workflow, that is a genuine differentiator rather than a checkbox.

Note the service name. SageMaker AI is the ML platform; SageMaker Unified
Studio is the broader data product. This is the former.

Reference script. Needs AWS credentials and a role.
"""
import os

from sagemaker.sklearn.estimator import SKLearn


def train_and_deploy():
    estimator = SKLearn(
        entry_point="train_entry.py",
        source_dir="platforms/sagemaker_src",
        framework_version="1.2-1",
        py_version="py3",
        instance_type="ml.m5.large",
        role=os.environ["SAGEMAKER_ROLE_ARN"],
        hyperparameters={"max-iter": 1000},
        # Spend lands against these in Cost Explorer.
        tags=[{"Key": "CostCentre", "Value": "scheduling"},
              {"Key": "Model", "Value": "noshow-lr"}],
    )
    estimator.fit({"train": os.environ["TRAIN_S3_URI"]})

    return estimator.deploy(
        initial_instance_count=1,
        instance_type="ml.t2.medium",
        endpoint_name="noshow-lr",
    )


if __name__ == "__main__":
    predictor = train_and_deploy()
    print(f"endpoint live: {predictor.endpoint_name}")
