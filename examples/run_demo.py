"""Run the reproducible offline ClothingMatching-CN Skill demonstration."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.outfit_matcher import generate_outfits


def load_json(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    profile = load_json("user_profile.json")
    wardrobe = load_json("wardrobe.json")
    request = load_json("sample_request.json")
    result = generate_outfits(
        profile,
        wardrobe,
        request["occasion"],
        must_use_item_ids=request["must_use_item_ids"],
        avoid_item_ids=request["avoid_item_ids"],
        requested_outfit_count=request["requested_outfit_count"],
    )
    print(f"outfit_count={len(result['outfit_plans'])}")
    for plan in result["outfit_plans"]:
        item_ids = {
            slot: item["item_id"]
            for slot, item in plan["items"].items()
            if item and item.get("item_id")
        }
        print(
            f"rank={plan['rank']} score={plan['ranking_score']:.4f} "
            f"major_item_ids={item_ids}"
        )
    for warning in result["warnings"]:
        print(f"warning={warning}")


if __name__ == "__main__":
    main()
