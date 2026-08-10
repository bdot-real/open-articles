"""Projected monthly cost delta for a pull request.

The control the article argues is missing. A Terraform plan tells you what a
change does to your infrastructure bill before you merge it. Nothing does that
for a prompt change, so a fifteen-line diff can carry a five-figure monthly
delta through review without comment.

This closes that gap crudely but usefully:

    python -m tools.prompt_cost_diff --base origin/main --head HEAD

It counts tokens added to and removed from files matching the configured globs,
multiplies by the traffic in finops.yaml, and prints a markdown comment.

Deliberately conservative. It cannot know that your new prompt will be cached,
or that it only fires on ten percent of requests. Treat it as a prompt to think,
not as a forecast. Being roughly right in review beats being exactly right on
the invoice.
"""
import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

from finops.pricing import RATES, Usage, cost, fmt, monthly

DEFAULT_CONFIG = {
    "globs": ["prompts/**", "**/*.prompt", "**/prompts.yaml", "**/system_prompt*"],
    "requests_per_day": 100_000,
    "tier": "frontier",
    "cached": False,
    "warn_threshold_monthly": 500.0,
}


def load_config(path: str = "finops.yaml") -> dict:
    cfg = dict(DEFAULT_CONFIG)
    p = Path(path)
    if not p.exists():
        return cfg
    try:
        import yaml
        cfg.update(yaml.safe_load(p.read_text()) or {})
    except ImportError:
        # No PyYAML in the runner. Fall back to a minimal key: value parse.
        for line in p.read_text().splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, v = line.split(":", 1)
                v = v.strip()
                if v and not v.startswith("["):
                    cfg[k.strip()] = (
                        int(v) if v.isdigit()
                        else float(v) if v.replace(".", "", 1).isdigit()
                        else v.strip('"\'')
                    )
    return cfg


def count_tokens(text: str) -> int:
    """tiktoken when available, otherwise a chars/4 approximation.

    The approximation is wrong by 10 to 20 percent depending on content, which
    does not matter when the answer is "this adds thirty thousand dollars".
    """
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return max(1, len(text) // 4)


def matches(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, f"*/{g}")
               for g in globs)


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", base, head], text=True)
    return [f for f in out.splitlines() if f.strip()]


def file_at(rev: str, path: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "show", f"{rev}:{path}"], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return ""


def analyse(base: str, head: str, cfg: dict) -> dict:
    rows = []
    total_delta = 0
    for path in changed_files(base, head):
        if not matches(path, cfg["globs"]):
            continue
        before = count_tokens(file_at(base, path))
        after = count_tokens(file_at(head, path))
        if before == after:
            continue
        rows.append({"path": path, "before": before, "after": after,
                     "delta": after - before})
        total_delta += after - before

    tier = cfg["tier"]
    usage = (Usage(cache_read_tokens=abs(total_delta)) if cfg.get("cached")
             else Usage(input_tokens=abs(total_delta)))
    per_request = cost(tier, usage) * (1 if total_delta >= 0 else -1)
    delta_monthly = monthly(per_request, int(cfg["requests_per_day"]))

    return {"rows": rows, "total_delta_tokens": total_delta,
            "monthly_delta": delta_monthly, "config": cfg}


def render(result: dict) -> str:
    cfg = result["config"]
    d = result["monthly_delta"]
    if not result["rows"]:
        return ""

    verdict = (
        "No material cost change." if abs(d) < 1
        else f"**Projected monthly change: {fmt(d)}**"
    )
    over = abs(d) >= float(cfg["warn_threshold_monthly"])

    lines = ["## Prompt cost estimate", "", verdict, ""]
    if over:
        lines += [
            f"> This exceeds the review threshold of "
            f"{fmt(float(cfg['warn_threshold_monthly']))} per month. "
            f"Consider whether the static portion can sit behind a cache "
            f"boundary before merging.", "",
        ]
    lines += ["| File | Before | After | Delta |", "|---|---:|---:|---:|"]
    for r in result["rows"]:
        lines.append(
            f"| `{r['path']}` | {r['before']:,} | {r['after']:,} | "
            f"{r['delta']:+,} |")
    lines += [
        "",
        f"<sub>At {int(cfg['requests_per_day']):,} requests/day, tier "
        f"`{cfg['tier']}`, "
        f"{'cached' if cfg.get('cached') else 'uncached'} input. "
        f"Assumes every request pays the delta. Tune in `finops.yaml`.</sub>",
    ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="origin/main")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--config", default="finops.yaml")
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-over-threshold", action="store_true",
                   help="Exit 1 when the projection exceeds the threshold.")
    a = p.parse_args()

    result = analyse(a.base, a.head, load_config(a.config))

    if a.json:
        print(json.dumps(result, indent=2))
    else:
        out = render(result)
        if out:
            print(out)

    if a.fail_over_threshold and abs(result["monthly_delta"]) >= float(
            result["config"]["warn_threshold_monthly"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
