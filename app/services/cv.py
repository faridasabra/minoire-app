import io
import torch
import open_clip
import numpy as np
from PIL import Image
from rembg import remove
from app.services.s3 import upload_image

# load clip model once at module level so it's not reloaded on every request
device = "cuda" if torch.cuda.is_available() else "cpu"
clip_model, _, clip_preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32", pretrained="openai"
)
clip_model = clip_model.to(device)
clip_model.eval()

def remove_background(image_bytes: bytes) -> bytes:
    output = remove(image_bytes)
    return output

def generate_clip_embedding(image_bytes: bytes) -> list:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_tensor = clip_preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = clip_model.encode_image(image_tensor)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    return embedding.squeeze().cpu().numpy().tolist()

def process_clothing_image(raw_bytes: bytes, content_type: str) -> dict:
    clean_bytes = remove_background(raw_bytes)

    clean_url = upload_image(clean_bytes, "image/png", folder="clean")

    embedding = generate_clip_embedding(clean_bytes)

    return {
        "image_url_clean": clean_url,
        "clip_embedding": embedding
    }