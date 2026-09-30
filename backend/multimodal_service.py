"""Gemini multimodal reasoning over a generated hazard-map image and structured data."""
from __future__ import annotations
import io
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def build_hazard_map_png(latitude, longitude, risk_score, hazard, infrastructure):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_title("CycloneShield AI — Scenario Hazard Overview")
    ax.scatter([0], [0], s=100, label="Assessment center")
    radii = [1.0, 0.75, 0.5, 0.25]
    labels = ["Outer assessment", "Medium", "High", "Very High"]
    for r, label in zip(radii, labels):
        c = plt.Circle((0, 0), r, fill=False, linewidth=2, label=label)
        ax.add_patch(c)
    affected = hazard.get("affected_asset_count", 0)
    ax.text(-0.95, -1.18, f"Risk: {risk_score}/100\nAffected mapped assets: {affected}\nLat/Lon: {latitude:.4f}, {longitude:.4f}", fontsize=9)
    ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.35, 1.2); ax.set_aspect("equal"); ax.grid(alpha=0.2)
    ax.legend(loc="upper right", fontsize=8)
    buf = io.BytesIO(); fig.tight_layout(); fig.savefig(buf, format="png", dpi=130); plt.close(fig)
    return buf.getvalue()
