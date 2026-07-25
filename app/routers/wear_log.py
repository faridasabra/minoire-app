from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.wear_log import WearLog
from app.schemas.wear_log import WearLogCreate, WearLogOut
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/wear-logs", tags=["wear-logs"])

@router.get("/", response_model=List[WearLogOut])
def get_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(WearLog).filter(WearLog.user_id == current_user.id).all()

@router.post("/", response_model=WearLogOut)
def create_log(
    log_in: WearLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    log = WearLog(**log_in.model_dump(), user_id=current_user.id)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

@router.delete("/{log_id}")
def delete_log(log_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log = db.query(WearLog).filter(
        WearLog.id == log_id,
        WearLog.user_id == current_user.id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    db.delete(log)
    db.commit()
    return {"detail": "Deleted"}