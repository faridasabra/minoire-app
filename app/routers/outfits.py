from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.outfit import Outfit, OutfitItem
from app.schemas.outfit import OutfitCreate, OutfitOut
from app.dependencies import get_current_user
from app.models.user import User
from app.models.clothing import ClothingItem
from app.services.outfit_assembler import assemble_outfits

router = APIRouter(prefix="/outfits", tags=["outfits"])

@router.get("/", response_model=List[OutfitOut])
def get_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Outfit).filter(Outfit.owner_id == current_user.id).all()

@router.get("/{outfit_id}", response_model=OutfitOut)
def get_one(outfit_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    outfit = db.query(Outfit).filter(
        Outfit.id == outfit_id,
        Outfit.owner_id == current_user.id
    ).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return outfit

@router.post("/", response_model=OutfitOut)
def create_outfit(
    outfit_in: OutfitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    outfit = Outfit(
        owner_id=current_user.id,
        name=outfit_in.name,
        occasion=outfit_in.occasion,
        season=outfit_in.season,
        notes=outfit_in.notes,
    )
    db.add(outfit)
    db.flush()

    for i, item_id in enumerate(outfit_in.clothing_item_ids):
        item = db.query(ClothingItem).filter(
            ClothingItem.id == item_id,
            ClothingItem.owner_id == current_user.id
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Clothing item {item_id} not found")
        slot = outfit_in.slots[i] if outfit_in.slots and i < len(outfit_in.slots) else None
        outfit_item = OutfitItem(outfit_id=outfit.id, clothing_item_id=item_id, slot=slot)
        db.add(outfit_item)

    db.commit()
    db.refresh(outfit)
    return outfit

@router.delete("/{outfit_id}")
def delete_outfit(outfit_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    outfit = db.query(Outfit).filter(
        Outfit.id == outfit_id,
        Outfit.owner_id == current_user.id
    ).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    db.delete(outfit)
    db.commit()
    return {"detail": "Deleted"}

@router.post("/generate")
def generate_outfits(
    occasion: str = None,
    formality: str = "casual",
    season: str = "all",
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = assemble_outfits(
        db=db,
        owner_id=str(current_user.id),
        occasion=occasion,
        formality=formality,
        current_season=season,
        top_k=top_k
    )

    if not results:
        raise HTTPException(
            status_code=404,
            detail="Not enough wardrobe items to generate outfits. Add more clothing first."
        )

    return [
        {
            "score": r["score"],
            "top": {
                "id": str(r["slots"]["top"].id),
                "name": r["slots"]["top"].name,
                "color": r["slots"]["top"].color,
                "color_hex": r["slots"]["top"].color_hex,
                "image_url_clean": r["slots"]["top"].image_url_clean,
            },
            "bottom": {
                "id": str(r["slots"]["bottom"].id),
                "name": r["slots"]["bottom"].name,
                "color": r["slots"]["bottom"].color,
                "color_hex": r["slots"]["bottom"].color_hex,
                "image_url_clean": r["slots"]["bottom"].image_url_clean,
            },
            "shoes": {
                "id": str(r["slots"]["shoes"].id),
                "name": r["slots"]["shoes"].name,
                "color": r["slots"]["shoes"].color,
                "color_hex": r["slots"]["shoes"].color_hex,
                "image_url_clean": r["slots"]["shoes"].image_url_clean,
            } if r["slots"]["shoes"] else None,
        }
        for r in results
    ]

@router.post("/{outfit_id}/score")
def score_existing_outfit(
    outfit_id: str,
    season: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    outfit = db.query(Outfit).filter(
        Outfit.id == outfit_id,
        Outfit.owner_id == current_user.id
    ).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    items = [oi.clothing_item for oi in outfit.items]
    if not items:
        raise HTTPException(status_code=400, detail="Outfit has no items")

    from app.services.outfit_scorer import score_outfit
    score = score_outfit(items, season)

    return {
        "outfit_id": outfit_id,
        "score": score,
        "item_count": len(items)
    }