from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.outfit import Outfit, OutfitItem
from app.schemas.outfit import OutfitCreate, OutfitOut
from app.dependencies import get_current_user
from app.models.user import User
from app.models.clothing import ClothingItem

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