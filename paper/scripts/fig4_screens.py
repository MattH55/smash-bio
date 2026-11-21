#!/usr/bin/env python3
"""Figure 4: real screenshots of the local site build (website/), taken at 2x device-pixel ratio with Playwright.

(A) record page SMFS-000457 (has a linked Zenodo deposit and raw traces); (B) system page t7-rna-polymerase.
The site is served from ../website on a loopback port for the duration of the capture only.
    python scripts/fig4_screens.py            # capture + compose
    python scripts/fig4_screens.py --compose  # recompose from the saved PNGs in figures/_screens/
"""
from __future__ import annotations

import functools
import http.server
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from figstyle import COL2, FIGS, panel_letter, save  # noqa: E402

SITE = Path(__file__).resolve().parents[2] / "website"
SHOTS = FIGS / "_screens"
PAGES = {"record": "record.html?id=SMFS-000457", "system": "system.html?s=t7-rna-polymerase"}
VIEWPORT = {"width": 1100, "height": 1500}
# crop heights in device pixels (2x): record page down to the end of "Biological system", system page to the end of
# "Studies over time"; chosen by inspecting the full-page captures
CROP_PX = {"record": 2180, "system": 2560}


def capture() -> None:
    from playwright.sync_api import sync_playwright

    SHOTS.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None  # type: ignore[method-assign]
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
            for name, page_url in PAGES.items():
                page = ctx.new_page()
                page.goto(base + page_url, wait_until="networkidle")
                page.wait_for_timeout(1500)  # data shards are injected by script tags after load
                page.screenshot(path=str(SHOTS / f"{name}_full.png"), full_page=True)
                print(f"captured {name}: {page_url}")
            browser.close()
    finally:
        srv.shutdown()


def compose() -> None:
    import numpy as np

    from PIL import Image

    imgs = []
    for name, h_px in CROP_PX.items():
        full = Image.open(SHOTS / f"{name}_full.png").convert("RGB")
        imgs.append(np.asarray(full.crop((0, 0, full.width, min(h_px, full.height)))) / 255.0)
    heights = [im.shape[0] / im.shape[1] for im in imgs]
    h = max(heights)
    fig, axes = plt.subplots(1, 2, figsize=(COL2, COL2 / 2 * h + 0.05), gridspec_kw={"wspace": 0.03, "left": 0.01, "right": 0.99, "top": 0.94, "bottom": 0.01})
    for ax, im, letter in zip(axes, imgs, "AB"):
        ax.imshow(im)
        ax.axis("off")
        ax.set_anchor("N")
        ax.text(0.0, 1.015, letter, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom")
    save(fig, "fig4_interface")


if __name__ == "__main__":
    if "--compose" not in sys.argv:
        capture()
    compose()
