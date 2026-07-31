"""
Generates color_lookup.json from the XKCD color survey.
Run once: python scripts/generate_color_lookup.py
"""

import json
import os
import urllib.request
import numpy as np
from skimage.color import rgb2lab

# Download XKCD color list
url = "https://xkcd.com/color/rgb.txt"
response = urllib.request.urlopen(url)
lines = response.read().decode("utf-8").strip().split("\n")

colors = {}
for line in lines:
    if line.startswith("#") or not line.strip():
        continue
    parts = line.strip().split("\t")
    if len(parts) != 2:
        continue
    name, hex_val = parts[0].strip(), parts[1].strip()
    if not hex_val.startswith("#") or len(hex_val) != 7:
        continue

    r = int(hex_val[1:3], 16) / 255
    g = int(hex_val[3:5], 16) / 255
    b = int(hex_val[5:7], 16) / 255

    rgb = np.array([[[r, g, b]]], dtype=np.float32)
    lab = rgb2lab(rgb)[0][0]

    colors[name] = {
        "hex": hex_val,
        "lab": [round(float(lab[0]), 2), round(float(lab[1]), 2), round(float(lab[2]), 2)]
    }

# Save to config/
os.makedirs("config", exist_ok=True)
output_path = "config/color_lookup.json"
with open(output_path, "w") as f:
    json.dump(colors, f, indent=2)

print(f"Generated {len(colors)} colors → {output_path}")