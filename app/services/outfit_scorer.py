import colorsys
from typing import Optional

def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l

def hue_distance(h1: float, h2: float) -> float:
    diff = abs(h1-h2) % 360
    return min(diff, 360 - diff)

def color_harmony_score(hex_color: list[str]) -> float:
    valid_hexes = [h for h in hex_color if h and h.startswith("#") and len(h) == 7]

    if len(valid_hexes) == 0:
        return 0.5
    if len(valid_hexes) == 1:
        return 0.8

    hsl_values = [hex_to_hsl(h) for h in valid_hexes]

    neutrals = [(h, s, l) for h, s, l in hsl_values if s < 0.15]
    chromatics = [(h, s, l) for h, s, l in hsl_values if s >= 0.15]

    if len(neutrals) >= len(hsl_values) - 1:
        return 0.80

    if len(chromatics) < 2:
        return 0.75

    hues = [h for h, s, l in chromatics]

    max_hue_diff = max(hue_distance(hues[i], hues[j])
                       for i in range(len(hues))
                       for j in range(i + 1, len(hues)))

    if max_hue_diff <= 15:
        return 1.0

    if max_hue_diff <= 45:
        return 0.85

    if len(chromatics) == 2:
        dist = hue_distance(hues[0], hues[1])
        if 150 <= dist <= 210:
            return 0.75
        if 120 <= dist <= 150 or 210 <= dist <= 240:
            return 0.65
        return 0.30

    if len(chromatics) >= 3:
        sorted_hues = sorted(hues)
        gaps = [hue_distance(sorted_hues[i], sorted_hues[(i+1) % len(sorted_hues)])
                for i in range(len(sorted_hues))]
        if all(100 <= g <= 140 for g in gaps[:3]):
            # Penalize high saturation triadic combinations
            avg_saturation = sum(s for h, s, l in chromatics) / len(chromatics)
            if avg_saturation > 0.7:
                return 0.30  # Harsh high-saturation triadic
            return 0.55  # Muted triadic is acceptable

    return 0.20

def formality_score(formalities: list[str]) -> float:
    FORMALITY_TIERS = {
        "casual": 0,
        "smart_casual": 1,
        "formal": 2,
        "party": 1,
    }

    valid = [FORMALITY_TIERS[f] for f in formalities if f in FORMALITY_TIERS]

    if not valid:
        return 0.5

    spread = max(valid) - min(valid)

    if spread == 0:
        return 1.0
    if spread == 1:
        return 0.70
    if spread == 2:
        return 0.20
    return 0.0 

def season_score(seasons_list: list[Optional[list[str]]], current_season: str) -> float:
    if not any(seasons_list):
        return 0.5

    scores = []
    for seasons in seasons_list:
        if not seasons:
            scores.append(0.5)
            continue
        if current_season in seasons or "all" in seasons:
            scores.append(1.0)
        else:
            scores.append(0.0)

    return sum(scores) / len(scores)

def score_outfit(items: list, current_season: str = "all") -> float:
    hex_colors = []
    for item in items:
        if item.color_hex:
            hex_colors.append(item.color_hex)

    formalities = [item.formality for item in items if item.formality]

    seasons_list = [item.season for item in items]

    c_harmony = color_harmony_score(hex_colors)
    f_match = formality_score(formalities)
    s_season = season_score(seasons_list, current_season)

    w1, w2, w3 = 0.40, 0.40, 0.20
    composite = w1 * c_harmony + w2 * f_match + w3 * s_season

    return round(composite, 4)