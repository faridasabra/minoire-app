from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.clothing import ClothingItem
from app.schemas.clothing import ClothingItemCreate, ClothingItemUpdate, ClothingItemOut
from app.dependencies import get_current_user
from app.models.user import User
from app.services.s3 import upload_image, delete_image

router = APIRouter(prefix="/clothing", tags=["clothing"])

@router.get("/", response_model=List[ClothingItemOut])
def get_all(
    category: str = None,
    color: str = None,
    formality: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ClothingItem).filter(ClothingItem.owner_id == current_user.id)
    if category:
        query = query.filter(ClothingItem.category == category)
    if color:
        query = query.filter(ClothingItem.color == color)
    if formality:
        query = query.filter(ClothingItem.formality == formality)
    return query.all()

@router.get("/{item_id}", response_model=ClothingItemOut)
def get_one(item_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.owner_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.post("/", response_model=ClothingItemOut)
def create_item(
    item_in: ClothingItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = ClothingItem(**item_in.model_dump(), owner_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.post("/{item_id}/upload-image", response_model=ClothingItemOut)
async def upload_item_image(
    item_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.owner_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    contents = await file.read()

    raw_url = upload_image(contents, file.content_type, folder="raw")
    item.image_url = raw_url

    from app.services.cv import process_clothing_image
    cv_results = process_clothing_image(contents, file.content_type)
    item.image_url_clean = cv_results["image_url_clean"]
    item.clip_embedding = cv_results["clip_embedding"]
    item.category = cv_results["category"]
    item.formality = cv_results["formality"]
    item.color = cv_results["color"]

    db.commit()
    db.refresh(item)
    return item

@router.patch("/{item_id}", response_model=ClothingItemOut)
def update_item(
    item_id: str,
    item_in: ClothingItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.owner_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in item_in.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{item_id}")
def delete_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.owner_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}