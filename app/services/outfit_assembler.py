from itertools import product
from sqlalchemy.orm import Session
from app.models.clothing import ClothingItem
from app.services.outfit_scorer import score_outfit
from typing import Optional

SLOTS = ["top", "bottom", "shoes"]
OPTIONAL_SLOTS = ["accessory", "outerwear"]

FORMALITY_MAP = {
    "casual": ["casual"],
    "smart_casual": ["smart_casual", "casual"],
    "formal": ["formal", "smart_casual"],
    "party": ["party", "smart_casual"],
}

SEASON_MAP = {
    "spring": "spring",
    "summer": "summer",
    "fall": "fall",
    "winter": "winter",
    "all": None,
}

def get_candidates(
    db: Session,
    owner_id: str,
    occasion: Optional[str],
    formality: Optional[str],
    current_season: Optional[str],
    slot: str,
    limit: int = 5
) -> list:
    query = db.query(ClothingItem).filter(
        ClothingItem.owner_id == owner_id,
        ClothingItem.category == slot,
        ClothingItem.clip_embedding.isnot(None)
    )

    if formality and formality in FORMALITY_MAP:
        allowed_formalities = FORMALITY_MAP[formality]
        query = query.filter(ClothingItem.formality.in_(allowed_formalities))

    items = query.limit(limit * 3).all()

    if current_season and current_season != "all":
        def season_priority(item):
            if item.season and current_season in item.season:
                return 0
            if not item.season:
                return 1
            return 2
        items = sorted(items, key=season_priority)

    return items[:limit]


def assemble_outfits(
    db: Session,
    owner_id: str,
    occasion: Optional[str] = None,
    formality: Optional[str] = "casual",
    current_season: Optional[str] = "all",
    top_k: int = 5
) -> list[dict]:
    tops = get_candidates(db, owner_id, occasion, formality, current_season, "top")
    bottoms = get_candidates(db, owner_id, occasion, formality, current_season, "bottom")
    shoes = get_candidates(db, owner_id, occasion, formality, current_season, "shoes")

    if not tops or not bottoms:
        return []

    outfits = []

    slot_lists = [tops, bottoms]
    if shoes:
        slot_lists.append(shoes)

    for combination in product(*slot_lists):
        items = list(combination)
        composite_score = score_outfit(items, current_season or "all")

        outfit = {
            "items": items,
            "score": composite_score,
            "slots": {
                "top": items[0],
                "bottom": items[1],
                "shoes": items[2] if len(items) > 2 else None,
            }
        }
        outfits.append(outfit)

    outfits.sort(key=lambda x: x["score"], reverse=True)
    return outfits[:top_k]