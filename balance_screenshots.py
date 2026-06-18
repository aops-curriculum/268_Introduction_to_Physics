#!/usr/bin/env python3
"""
balance_screenshots.py

Brute-force solves all 10 levels of balance_game.html,
screenshots each level showing the balanced beam, adds a badge
for levels with multiple solutions, and saves individual PNGs
plus a combined 3x3+1 grid image.
"""

import os
import sys
import base64
import itertools
from io import BytesIO

# ── Install dependencies if needed ───────────────────────────────────────────
def ensure_deps():
    import importlib
    missing = []
    for pkg in ['PIL', 'playwright']:
        try:
            importlib.import_module(pkg if pkg != 'PIL' else 'PIL.Image')
        except ImportError:
            missing.append('Pillow' if pkg == 'PIL' else pkg)
    if missing:
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)

ensure_deps()

from PIL import Image, ImageDraw, ImageFont

# ── Brute-force solver ───────────────────────────────────────────────────────
LEVELS = [
    {'fx': [{'m':5,'p':1}],                              'ck': [{'m':5}]              },
    {'fx': [{'m':4,'p':2}],                              'ck': [{'m':8}]              },
    {'fx': [{'m':6,'p':1}],                              'ck': [{'m':3}]              },
    {'fx': [{'m':10,'p':1.5}],                           'ck': [{'m':3},{'m':6}]      },
    {'fx': [{'m':6,'p':2}],                              'ck': [{'m':20},{'m':3}]     },
    {'fx': [{'m':8,'p':1},{'m':3,'p':2}],                'ck': [{'m':4},{'m':10}]     },
    {'fx': [{'m':2,'p':.5},{'m':4,'p':1},{'m':6,'p':2}],'ck': [{'m':4},{'m':8}]      },
    {'fx': [{'m':4,'p':2}],                              'ck': [{'m':15},{'m':7}]     },
    {'fx': [{'m':3,'p':1},{'m':5,'p':1.5},{'m':4,'p':2}],'ck':[{'m':2},{'m':6},{'m':8}]},
    {'fx': [{'m':8,'p':2},{'m':3,'p':1},{'m':4,'p':1.5}],'ck':[{'m':4},{'m':6},{'m':3}]},
]

# Valid positions: -2 to +2, steps of 0.25, excluding 0
VALID_POS = []
v = -2.0
while v <= 2.0 + 1e-9:
    if abs(v) > 1e-9:
        VALID_POS.append(round(v, 2))
    v += 0.25

def fixed_torque(level):
    return sum(b['m'] * b['p'] for b in level['fx'])

def solve_level(level):
    """Returns list of all solutions as tuples of positions (one per cloud brick)."""
    fx_torque = fixed_torque(level)
    cloud_masses = [b['m'] for b in level['ck']]
    solutions = []
    for positions in itertools.product(VALID_POS, repeat=len(cloud_masses)):
        total = fx_torque + sum(m * p for m, p in zip(cloud_masses, positions))
        if abs(total) < 0.1:
            solutions.append(positions)
    return solutions

# Featured solutions (from the task specification)
FEATURED = [
    [-1],            # Level 1
    [-1],            # Level 2
    [-2],            # Level 3
    [-1, -2],        # Level 4
    [-0.75, 1],      # Level 5
    [-1, -1],        # Level 6
    [-0.25, -2],     # Level 7
    [-1, 1],         # Level 8
    [-0.25, -1, -1.5],  # Level 9
    [-1.75, -2, -2],    # Level 10
]

print("Running brute-force solver...")
all_solutions = []
for i, level in enumerate(LEVELS):
    sols = solve_level(level)
    all_solutions.append(sols)
    featured = FEATURED[i]
    in_sols = tuple(round(x, 2) for x in featured) in [tuple(round(x,2) for x in s) for s in sols]
    print(f"  Level {i+1}: {len(sols)} solution(s)  featured={featured}  valid={in_sols}")

print()

# ── Playwright screenshot ─────────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

TARGET_DIR = r"G:\My Drive\AoPS\courses\Introduction to Physics\01 - Designing Experiments"
os.makedirs(TARGET_DIR, exist_ok=True)

# CSS and internal dimensions
CSS_W, CSS_H = 740, 540
INTERNAL_W, INTERNAL_H = 548, 400
SB = 340  # scene bottom in internal coords
# Scene crop: SB/H * CSS_H
SCENE_CSS_H = int(round(SB / INTERNAL_H * CSS_H))  # 459
print(f"Scene CSS height: {SCENE_CSS_H}px (out of {CSS_H}px)")

# At deviceScaleFactor=2, canvas is 1480x1080
# Scene crop: 1480 x 918
DPR = 2
FULL_W = CSS_W * DPR     # 1480
FULL_H = CSS_H * DPR     # 1080
SCENE_H = SCENE_CSS_H * DPR  # 918

EXPORT_URL = "http://localhost:8973/balance_export.html"

def get_level_image(page, lvl_idx, positions):
    """Call renderLevel JS and decode the returned data URL."""
    js_positions = str(list(positions)).replace("'", "")
    data_url = page.evaluate(f"window.renderLevel({lvl_idx}, {js_positions})")
    # data_url = "data:image/png;base64,..."
    b64 = data_url.split(',', 1)[1]
    img_bytes = base64.b64decode(b64)
    img = Image.open(BytesIO(img_bytes))
    return img

def add_badge(img, text, dpr=DPR):
    """Add a badge in the top-right corner of img (at 2x resolution)."""
    draw = ImageDraw.Draw(img)
    # Try to get a font; fall back to default
    font_size = int(22 * dpr / 2)  # scale for dpr
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    # Measure text
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x = int(12 * dpr / 2)
    pad_y = int(8 * dpr / 2)
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    margin = int(14 * dpr / 2)
    x0 = img.width - bw - margin
    y0 = margin
    x1 = img.width - margin
    y1 = y0 + bh
    r = int(8 * dpr / 2)  # corner radius

    # Draw rounded rect background
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r,
                            fill=(255, 255, 255, 230),
                            outline=(80, 80, 100), width=max(1, int(2*dpr/2)))
    draw.text((x0 + pad_x, y0 + pad_y), text, font=font, fill=(40, 40, 80))
    return img

def capture_all_levels():
    print("Launching Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': CSS_W, 'height': CSS_H},
            device_scale_factor=DPR
        )
        page = context.new_page()
        print(f"Loading {EXPORT_URL} ...")
        page.goto(EXPORT_URL, wait_until='networkidle')
        # Wait for fonts etc.
        page.wait_for_timeout(500)

        level_images = []
        for i in range(10):
            positions = FEATURED[i]
            n_solutions = len(all_solutions[i])
            print(f"  Rendering Level {i+1} (positions={positions}, solutions={n_solutions})...")

            img = get_level_image(page, i, positions)
            # img is the full canvas at devicePixelRatio * CSS size
            actual_w, actual_h = img.size
            print(f"    Canvas image size: {actual_w}x{actual_h}")

            # Crop to scene (top portion only, exclude UI zone)
            # Scene is SB/H fraction of the internal height
            scene_frac = SB / INTERNAL_H
            crop_h = int(round(actual_h * scene_frac))
            img_cropped = img.crop((0, 0, actual_w, crop_h))

            # Add badge if multiple solutions
            if n_solutions > 1:
                img_with_badge = add_badge(img_cropped.copy(), f"{n_solutions} solutions")
            else:
                img_with_badge = img_cropped

            # Scale down to 740 x 459 (CSS pixels) for file size
            final_w = CSS_W
            final_h = int(round(CSS_W * crop_h / actual_w))
            img_final = img_with_badge.resize((final_w, final_h), Image.LANCZOS)

            out_path = os.path.join(TARGET_DIR, f"level_{i+1:02d}.png")
            img_final.save(out_path, "PNG")
            print(f"    Saved: {out_path}  ({img_final.size})")
            level_images.append(img_final)

        browser.close()
    return level_images

def build_grid(level_images):
    """Build a 3×3+1 grid image."""
    if not level_images:
        return
    img_w, img_h = level_images[0].size
    gap = 8
    bg_color = (232, 232, 232)

    # 3 cols x 4 rows (last row has 1 image centered)
    cols = 3
    rows = 4
    grid_w = cols * img_w + (cols - 1) * gap
    grid_h = rows * img_h + (rows - 1) * gap

    grid = Image.new('RGB', (grid_w, grid_h), bg_color)

    for idx, img in enumerate(level_images[:9]):
        row = idx // cols
        col = idx % cols
        x = col * (img_w + gap)
        y = row * (img_h + gap)
        grid.paste(img, (x, y))

    # Level 10 centered in middle column of row 3
    if len(level_images) >= 10:
        img10 = level_images[9]
        # Center in the grid width
        x = (grid_w - img_w) // 2
        y = 3 * (img_h + gap)
        grid.paste(img10, (x, y))

    out_path = os.path.join(TARGET_DIR, "balance_solutions_grid.png")
    grid.save(out_path, "PNG")
    print(f"\nGrid saved: {out_path}  ({grid.size})")
    return out_path

if PLAYWRIGHT_AVAILABLE:
    try:
        level_images = capture_all_levels()
        build_grid(level_images)
        print("\nDone!")
    except Exception as e:
        print(f"\nPlaywright error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
else:
    print("Playwright not available. Run: pip install playwright && python -m playwright install chromium")
    sys.exit(1)
