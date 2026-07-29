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

COLOR_LOOKUP = {
    "black":  [0, 0, 0],
    "white":  [100, 0, 0],
    "grey":   [55, 0, 2],
    "beige":  [65, 4, 8],
    "brown":  [35, 15, 20],
    "red":    [40, 55, 45],
    "orange": [60, 30, 50],
    "yellow": [90, -10, 80],
    "green":  [45, -35, 35],
    "blue":   [35, 10, -45],
    "purple": [35, 35, -30],
    "pink":   [75, 30, 5],
    "multi":  [50, 0, 0],
}

def extract_dominant_color(image_bytes: bytes) -> tuple[str, str]:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    arr = np.array(image)

    mask = arr[:, :, 3] > 128
    pixels = arr[mask][:, :3].astype(np.float32)

    if len(pixels) < 10:
        return "unknown", "#000000"

    if len(pixels) > 5000:
        idx = np.random.choice(len(pixels), 5000, replace=False)
        pixels = pixels[idx]

    k = min(3, len(pixels))
    kmeans = KMeans(n_clusters=k, n_init=5, random_state=42)
    kmeans.fit(pixels)

    counts = np.bincount(kmeans.labels_)
    dominant_rgb = kmeans.cluster_centers_[counts.argmax()]

    r, g, b = [int(c) for c in dominant_rgb]
    hex_color = f"#{r:02x}{g:02x}{b:02x}"

    from skimage.color import rgb2lab
    rgb_normalized = np.array([[[r / 255, g / 255, b / 255]]], dtype=np.float32)
    lab = rgb2lab(rgb_normalized)[0][0]

    min_dist = float("inf")
    nearest_color = "black"
    for name, lab_ref in COLOR_LOOKUP.items():
        if name == "multi":
            continue
        dist = np.sqrt(sum((lab[i] - lab_ref[i]) ** 2 for i in range(3)))
        if dist < min_dist:
            min_dist = dist
            nearest_color = name

    return nearest_color, hex_color

def process_clothing_image(raw_bytes: bytes, content_type: str) -> dict:
    clean_bytes = remove_background(raw_bytes)

    clean_url = upload_image(clean_bytes, "image/png", folder="clean")

    embedding = generate_clip_embedding(clean_bytes)

    tags = classify_clothing(clean_bytes)

    color_name, color_hex = extract_dominant_color(clean_bytes)

    return {
        "image_url_clean": clean_url,
        "clip_embedding": embedding,
        "category": tags["category"],
        "formality": tags["formality"],
        "color": color_name,
        "color_hex": color_hex,
    }