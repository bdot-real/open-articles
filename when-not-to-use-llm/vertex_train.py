"""Google. Vertex AI.

The April 2026 rebrand to the Gemini Enterprise Agent Platform covers the
generative side. Classical training and prediction are unchanged and existing
code keeps working, which is worth knowing before someone tells you the service
you are using no longer exists.

Reference script. Needs a GCP project.
"""
import os

from google.cloud import aiplatform

REGION = os.environ.get("GCP_LOCATION", "us-central1")
BASE = "us-docker.pkg.dev/vertex-ai"


def train_and_deploy():
    aiplatform.init(project=os.environ["GCP_PROJECT"], location=REGION)

    job = aiplatform.CustomTrainingJob(
        display_name="noshow-lr",
        script_path="platforms/vertex_src/train_entry.py",
        container_uri=f"{BASE}/training/sklearn-cpu.1-0:latest",
        model_serving_container_image_uri=f"{BASE}/prediction/sklearn-cpu.1-0:latest",
        requirements=["scikit-learn>=1.5", "numpy"],
    )
    model = job.run(
        model_display_name="noshow-lr",
        args=["--max-iter", "1000"],
        replica_count=1,
        machine_type="n1-standard-4",
        labels={"cost_centre": "scheduling", "model": "noshow_lr"},
    )
    return model.deploy(machine_type="n1-standard-2", min_replica_count=1)


if __name__ == "__main__":
    endpoint = train_and_deploy()
    print(f"endpoint live: {endpoint.resource_name}")
