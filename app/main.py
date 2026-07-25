from fastapi import FastAPI
from app.database import Base, engine
from app.models import user, clothing, outfit, wear_log, profile
from app.routers import auth, clothing as clothing_router, outfits, wear_log as wear_log_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="minoire API", version="1.0.0")

app.include_router(auth.router)
app.include_router(clothing_router.router)
app.include_router(outfits.router)
app.include_router(wear_log_router.router)

@app.get("/health")
def health():
    return {"status": "ok"}