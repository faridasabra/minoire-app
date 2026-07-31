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
from sklearn.cluster import KMeans
import numpy as np
from PIL import Image
import io
import json

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

_COLOR_LOOKUP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    "config", "color_lookup.json"
)
with open(_COLOR_LOOKUP_PATH, "r") as f:
    _COLOR_DATA = json.load(f)

_COLOR_NAMES = list(_COLOR_DATA.keys())
_COLOR_LABS = np.array([_COLOR_DATA[name]["lab"] for name in _COLOR_NAMES], dtype=np.float32)

def extract_dominant_color(image_bytes: bytes) -> tuple[str, str, str, str]:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    arr = np.array(image)

    mask = arr[:, :, 3] > 128
    pixels = arr[mask][:, :3].astype(np.float32)

    if len(pixels) < 10:
        return "unknown", "#000000", None, None

    if len(pixels) > 8000:
        idx = np.random.choice(len(pixels), 8000, replace=False)
        pixels = pixels[idx]

    from skimage.color import rgb2lab
    pixels_normalized = pixels / 255.0
    pixels_lab = rgb2lab(pixels_normalized.reshape(1, -1, 3)).reshape(-1, 3).astype(np.float32)

    lab_variance = pixels_lab.var(axis=0).sum()
    is_multicolor = lab_variance > 800

    k = 5 if is_multicolor else 3
    kmeans = KMeans(n_clusters=min(k, len(pixels)), n_init=10, random_state=42)
    kmeans.fit(pixels_lab)

    counts = np.bincount(kmeans.labels_)
    sorted_indices = counts.argsort()[::-1]
    #dominant_rgb = kmeans.cluster_centers_[counts.argmax()]
    #sorted_lab_centers = kmeans.cluster_centers_[sorted_indices]
    #sorted_rgb_centers = pixels[[np.where(kmeans.labels_ == i)[0][0] for i in sorted_indices]]

    results = []
    seen_colors = set()

    for i in sorted_indices:
        lab_center = kmeans.cluster_centers_[i]

        diffs = _COLOR_LABS - lab_center
        distances = np.sqrt((diffs ** 2).sum(axis=1))
        nearest_idx = distances.argmin()
        nearest_color = _COLOR_NAMES[nearest_idx]

        if nearest_color in seen_colors:
            continue
        seen_colors.add(nearest_color)

        cluster_pixels = pixels[kmeans.labels_ == i]
        avg_rgb = cluster_pixels.mean(axis=0)
        r, g, b = [int(c) for c in avg_rgb]
        hex_color = f"#{r:02x}{g:02x}{b:02x}"

        results.append((nearest_color, hex_color))

        if len(results) == 3:
            break

    while len(results) < 3:
        results.append((None, None))

    if is_multicolor:
        return "multi", results[0][1], results[1][0] if len(results) > 1 else None, results[2][0] if len(results) > 2 else None

    return results[0][0], results[0][1], results[1][0] if len(results) > 1 else None, results[2][0] if len(results) > 2 else None

def process_clothing_image(raw_bytes: bytes, content_type: str) -> dict:
    clean_bytes = remove_background(raw_bytes)

    clean_url = upload_image(clean_bytes, "image/png", folder="clean")

    embedding = generate_clip_embedding(clean_bytes)

    tags = classify_clothing(clean_bytes)

    color, color_hex, color_secondary, color_tertiary = extract_dominant_color(clean_bytes)

    return {
        "image_url_clean": clean_url,
        "clip_embedding": embedding,
        "category": tags["category"],
        "formality": tags["formality"],
        "color": color,
        "color_hex": color_hex,
        "color_secondary": color_secondary,
        "color_tertiary": color_tertiary,
    }