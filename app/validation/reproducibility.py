"""Run two isolated logical generation passes and compare their SHA-256 digests."""
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.generator.__main__ import run_generator


def verify(profile: str = "full", seed: int = 20261022):
    first = run_generator(profile, seed=seed, load_db=False, export=False)
    second = run_generator(profile, seed=seed, load_db=False, export=False)
    same_counts = first["counts"] == second["counts"] and first["ground_truth_count"] == second["ground_truth_count"]
    same_checksums = first["checksums"] == second["checksums"]
    result = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "seed": seed,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "pass_1_counts": first["counts"],
        "pass_2_counts": second["counts"],
        "ground_truth_count": first["ground_truth_count"],
        "pass_1_checksums": first["checksums"],
        "pass_2_checksums": second["checksums"],
        "counts_match": same_counts,
        "checksums_match": same_checksums,
        "reproducible": same_counts and same_checksums,
        "excluded_metadata": ["created_at", "updated_at"],
    }
    output = Path(settings.EXPORTS_DIR) / "reproducibility_results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("starter", "full"), default="full")
    parser.add_argument("--seed", type=int, default=settings.RANDOM_SEED)
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.profile, args.seed)["reproducible"] else 1)
