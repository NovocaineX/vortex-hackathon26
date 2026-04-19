from __future__ import annotations

from typing import Iterable


def clamp_box(x: int, y: int, w: int, h: int, image_w: int, image_h: int) -> dict[str, int]:
    x = max(0, min(x, image_w - 1))
    y = max(0, min(y, image_h - 1))
    w = max(1, min(w, image_w - x))
    h = max(1, min(h, image_h - y))
    return {"x": x, "y": y, "width": w, "height": h}


def to_overlay(region: dict[str, int], image_w: int, image_h: int, color: str, label: str) -> dict[str, str]:
    x = round(region["x"] / max(image_w, 1) * 100, 2)
    y = round(region["y"] / max(image_h, 1) * 100, 2)
    w = round(region["width"] / max(image_w, 1) * 100, 2)
    h = round(region["height"] / max(image_h, 1) * 100, 2)
    return {
        "id": f"ov_{region['x']}_{region['y']}",
        "x": f"{x}%",
        "y": f"{y}%",
        "w": f"{max(w, 1.0)}%",
        "h": f"{max(h, 1.0)}%",
        "color": color,
        "label": label,
    }


def dedupe_regions(regions: Iterable[dict[str, int]]) -> list[dict[str, int]]:
    seen: set[tuple[int, int, int, int]] = set()
    out: list[dict[str, int]] = []
    for region in regions:
        key = (region["x"], region["y"], region["width"], region["height"])
        if key in seen:
            continue
        seen.add(key)
        out.append(region)
    return out
