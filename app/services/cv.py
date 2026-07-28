import io
import os
import pickle
import torch
import timm
import torch.nn as nn
import open_clip
import numpy as np
from PIL import Image
from rembg import remove
from app.services.s3 import upload_image

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

clip_model, _, clip_preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32", pretrained="openai"
)
clip_model = clip_model.to(device)
clip_model.eval()

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")

with open(os.path.join(MODELS_DIR, "category_encoder.pkl"), "rb") as f:
    category_encoder = pickle.load(f)
with open(os.path.join(MODELS_DIR, "formality_encoder.pkl"), "rb") as f:
    formality_encoder = pickle.load(f)
with open(os.path.join(MODELS_DIR, "color_encoder.pkl"), "rb") as f:
    color_encoder = pickle.load(f)

class FashionClassifier(nn.Module):
    def __init__(self, num_categories, num_formalities, num_colors):
        super().__init__()
        self.backbone = timm.create_model("efficientnet_b3", pretrained=False, num_classes=0)
        backbone_features = self.backbone.num_features
        self.dropout = nn.Dropout(0.3)
        self.category_head = nn.Sequential(
            nn.Linear(backbone_features, 256), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(256, num_categories)
        )
        self.formality_head = nn.Sequential(
            nn.Linear(backbone_features, 256), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(256, num_formalities)
        )
        self.color_head = nn.Sequential(
            nn.Linear(backbone_features, 256), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(256, num_colors)
        )

    def forward(self, x):
        features = self.backbone(x)
        features = self.dropout(features)
        return {
            "category": self.category_head(features),
            "formality": self.formality_head(features),
            "color": self.color_head(features)
        }

classifier = FashionClassifier(
    num_categories=len(category_encoder.classes_),
    num_formalities=len(formality_encoder.classes_),
    num_colors=len(color_encoder.classes_)
)
checkpoint = torch.load(
    os.path.join(MODELS_DIR, "minoire_fashion_classifier.pth"),
    map_location=device
)
classifier.load_state_dict(checkpoint["model_state_dict"])
classifier = classifier.to(device)
classifier.eval()

from torchvision import transforms
inference_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# pipeline functions
def remove_background(image_bytes: bytes) -> bytes:
    return remove(image_bytes)

def generate_clip_embedding(image_bytes: bytes) -> list:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_tensor = clip_preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = clip_model.encode_image(image_tensor)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    return embedding.squeeze().cpu().numpy().tolist()

def classify_clothing(image_bytes: bytes) -> dict:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = inference_transform(image).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = classifier(tensor)
    category = category_encoder.classes_[outputs["category"].argmax(1).item()]
    formality = formality_encoder.classes_[outputs["formality"].argmax(1).item()]
    color = color_encoder.classes_[outputs["color"].argmax(1).item()]
    return {
        "category": category,
        "formality": formality,
        "color": color
    }

def process_clothing_image(raw_bytes: bytes, content_type: str) -> dict:
    # step 1: remove background
    clean_bytes = remove_background(raw_bytes)

    # step 2: upload clean image to R2
    clean_url = upload_image(clean_bytes, "image/png", folder="clean")

    # step 3: generate CLIP embedding
    embedding = generate_clip_embedding(clean_bytes)

    # step 4: classify clothing
    tags = classify_clothing(clean_bytes)

    return {
        "image_url_clean": clean_url,
        "clip_embedding": embedding,
        "category": tags["category"],
        "formality": tags["formality"],
        "color": tags["color"]
    }