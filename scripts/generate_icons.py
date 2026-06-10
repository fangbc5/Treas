#!/usr/bin/env python3
"""
Treas 图标生成工具 - 绘制高清矢量风格图标并生成各平台图标

用法:
    python3 scripts/generate_icons.py

功能:
    - 用 Python 绘制高清百宝箱风格图标 (4x 超采样抗锯齿)
    - 生成 Windows icon.ico (包含 16/24/32/48/64/128/256 多尺寸)
    - 生成各尺寸 PNG 文件
    - 生成 macOS icon.icns

依赖:
    pip3 install Pillow
"""

import os
import sys
import math
import subprocess
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ============ 配置 ============
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ICON = PROJECT_ROOT / "resources" / "icon_1024.png"
OUTPUT_DIR = PROJECT_ROOT / "resources"

# ICO 中需要包含的尺寸
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

# 单独导出的 PNG 尺寸
PNG_SIZES = [16, 24, 32, 48, 64, 128, 256, 512]

# 超采样倍数 (4x = 在 4096x4096 上绘制，缩小到 1024x1024)
SUPERSAMPLE = 4
CANVAS_SIZE = 1024 * SUPERSAMPLE  # 4096


# ============ 颜色定义 ============
COLOR_CHEST_BODY = (255, 209, 102)       # 金色箱体
COLOR_CHEST_BODY_DARK = (230, 175, 60)   # 金色暗部
COLOR_CHEST_LID = (255, 224, 130)        # 浅金盖子
COLOR_CHEST_LID_DARK = (240, 195, 80)    # 盖子暗部
COLOR_LOCK = (139, 90, 43)               # 锁扣
COLOR_LOCK_SHINE = (255, 215, 0)         # 锁扣高光
COLOR_GEM = (255, 82, 82)               # 红宝石
COLOR_GEM_SHINE = (255, 138, 128)        # 宝石高光
COIN_GOLD = (255, 193, 7)               # 金币
COIN_GOLD_DARK = (245, 170, 0)           # 金币暗部


def lerp_color(c1, c2, t):
    """线性插值两个颜色"""
    t = max(0, min(1, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_icon(size=CANVAS_SIZE):
    """
    绘制 Treas 百宝箱图标 (透明背景)
    设计：金色百宝箱 + 金币 + 闪光效果
    """
    S = size
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ============ 箱体位置 (居中放大) ============
    chest_left = int(S * 0.10)
    chest_right = int(S * 0.90)
    chest_top = int(S * 0.35)
    chest_bottom = int(S * 0.82)
    chest_mid = int(S * 0.50)  # 盖子与箱体分界线

    shadow_offset = int(S * 0.015)

    # --- 箱体底部阴影 ---
    draw.rounded_rectangle(
        [chest_left + shadow_offset, chest_mid + shadow_offset,
         chest_right + shadow_offset, chest_bottom + shadow_offset],
        radius=int(S * 0.025),
        fill=(0, 0, 0, 50)
    )

    # --- 箱体下半部分 (深金) ---
    draw.rounded_rectangle(
        [chest_left, chest_mid, chest_right, chest_bottom],
        radius=int(S * 0.02),
        fill=COLOR_CHEST_BODY_DARK
    )

    # --- 箱体高光渐变 (上亮下暗) ---
    for y in range(chest_mid, chest_bottom):
        t = 1.0 - (y - chest_mid) / max(1, (chest_bottom - chest_mid))
        base = lerp_color(COLOR_CHEST_BODY_DARK, COLOR_CHEST_BODY, t * 0.5)
        draw.line([(chest_left + 2, y), (chest_right - 2, y)], fill=base)

    # --- 箱体横条装饰 ---
    band_height = int(S * 0.03)
    band_y = chest_mid + int((chest_bottom - chest_mid) * 0.3)
    draw.rectangle(
        [chest_left, band_y, chest_right, band_y + band_height],
        fill=COLOR_CHEST_BODY_DARK
    )
    draw.rectangle(
        [chest_left, band_y, chest_right, band_y + 2],
        fill=(200, 150, 40)
    )

    # --- 盖子阴影 ---
    draw.rounded_rectangle(
        [chest_left + shadow_offset, chest_top + shadow_offset,
         chest_right + shadow_offset, chest_mid + shadow_offset],
        radius=int(S * 0.035),
        fill=(0, 0, 0, 40)
    )

    # --- 盖子 (浅金) ---
    draw.rounded_rectangle(
        [chest_left, chest_top, chest_right, chest_mid + int(S * 0.008)],
        radius=int(S * 0.035),
        fill=COLOR_CHEST_LID
    )

    # --- 盖子渐变高光 ---
    for y in range(chest_top, chest_mid):
        t = 1.0 - (y - chest_top) / max(1, (chest_mid - chest_top))
        base = lerp_color(COLOR_CHEST_LID, COLOR_CHEST_LID_DARK, t * 0.3)
        draw.line([(chest_left + 4, y), (chest_right - 4, y)], fill=base)

    # --- 盖子弧形顶部 ---
    arch_top = int(S * 0.24)
    draw.pieslice(
        [chest_left + int(S * 0.04), arch_top,
         chest_right - int(S * 0.04), chest_top + int(S * 0.12)],
        180, 360,
        fill=COLOR_CHEST_LID_DARK
    )
    draw.pieslice(
        [chest_left + int(S * 0.06), arch_top + int(S * 0.01),
         chest_right - int(S * 0.06), chest_top + int(S * 0.09)],
        180, 360,
        fill=COLOR_CHEST_LID
    )

    # ============ 锁扣 ============
    lock_cx = (chest_left + chest_right) // 2
    lock_cy = chest_mid
    lock_w = int(S * 0.06)
    lock_h = int(S * 0.05)

    draw.rounded_rectangle(
        [lock_cx - lock_w, lock_cy - lock_h // 2,
         lock_cx + lock_w, lock_cy + lock_h // 2],
        radius=int(S * 0.012),
        fill=COLOR_LOCK
    )
    draw.rounded_rectangle(
        [lock_cx - lock_w + 3, lock_cy - lock_h // 2 + 3,
         lock_cx + lock_w - 3, lock_cy],
        radius=int(S * 0.008),
        fill=COLOR_LOCK_SHINE
    )
    key_r = int(S * 0.012)
    draw.ellipse(
        [lock_cx - key_r, lock_cy - key_r - int(S * 0.004),
         lock_cx + key_r, lock_cy + key_r - int(S * 0.004)],
        fill=(60, 40, 20)
    )
    draw.rectangle(
        [lock_cx - key_r // 3, lock_cy,
         lock_cx + key_r // 3, lock_cy + key_r],
        fill=(60, 40, 20)
    )

    # ============ 金币从箱子里冒出来 ============
    coins = [
        (int(S * 0.32), int(S * 0.26), int(S * 0.055)),
        (int(S * 0.50), int(S * 0.20), int(S * 0.06)),
        (int(S * 0.68), int(S * 0.28), int(S * 0.05)),
        (int(S * 0.42), int(S * 0.15), int(S * 0.048)),
        (int(S * 0.58), int(S * 0.12), int(S * 0.042)),
    ]

    for cx, cy, cr in coins:
        draw.ellipse([cx - cr + 3, cy - cr + 3, cx + cr + 3, cy + cr + 3],
                     fill=(0, 0, 0, 40))
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=COIN_GOLD)
        draw.ellipse([cx - cr + 4, cy - cr + 4, cx + cr - 8, cy + cr - 12],
                     fill=COIN_GOLD_DARK)
        draw.ellipse([cx - cr + 6, cy - cr + 6, cx - cr + cr // 2, cy - cr + cr // 2],
                     fill=(255, 220, 80))
        font_size = int(cr * 1.2)
        try:
            if sys.platform == 'darwin':
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            elif sys.platform == 'win32':
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
            else:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        text = "$"
        bbox_t = draw.textbbox((0, 0), text, font=font)
        tw = bbox_t[2] - bbox_t[0]
        th = bbox_t[3] - bbox_t[1]
        draw.text((cx - tw // 2, cy - th // 2 - 2), text, fill=COIN_GOLD_DARK, font=font)

    # ============ 星星闪光 ============
    def draw_star(cx, cy, r_outer, r_inner, color, alpha=255):
        points = []
        for i in range(8):
            angle = math.pi / 4 * i - math.pi / 2
            r = r_outer if i % 2 == 0 else r_inner
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
        star_color = color if len(color) == 4 else color + (alpha,)
        draw.polygon(points, fill=star_color)

    draw_star(int(S * 0.80), int(S * 0.10), int(S * 0.04), int(S * 0.012), (255, 255, 255))
    draw_star(int(S * 0.20), int(S * 0.08), int(S * 0.03), int(S * 0.009), (255, 255, 230))
    draw_star(int(S * 0.88), int(S * 0.20), int(S * 0.022), int(S * 0.007), (255, 255, 200))
    draw_star(int(S * 0.12), int(S * 0.20), int(S * 0.018), int(S * 0.005), (255, 255, 210))

    # ============ 宝石装饰 (箱体上) ============
    gem_cx = lock_cx
    gem_cy = chest_mid + int((chest_bottom - chest_mid) * 0.65)
    gem_r = int(S * 0.02)
    draw.ellipse([gem_cx - gem_r + 2, gem_cy - gem_r + 2, gem_cx + gem_r + 2, gem_cy + gem_r + 2],
                 fill=(0, 0, 0, 40))
    draw.ellipse([gem_cx - gem_r, gem_cy - gem_r, gem_cx + gem_r, gem_cy + gem_r],
                 fill=COLOR_GEM)
    draw.ellipse([gem_cx - gem_r + 6, gem_cy - gem_r + 6, gem_cx, gem_cy],
                 fill=COLOR_GEM_SHINE)

    return img


def generate_source_icon():
    """生成高清源图标"""
    print("🎨 绘制高清图标 (4x 超采样)...")

    big_img = draw_icon(CANVAS_SIZE)

    final_size = 1024
    img = big_img.resize((final_size, final_size), Image.LANCZOS)

    source_path = OUTPUT_DIR / "icon_1024.png"
    img.save(source_path, "PNG")
    file_size = source_path.stat().st_size
    print(f"  ✅ 源图标: {source_path} ({file_size:,} bytes)")

    return img


def generate_ico(img):
    """生成 Windows ICO 文件 (包含多尺寸)"""
    ico_path = OUTPUT_DIR / "icon.ico"
    sizes = ICO_SIZES

    icon_images = []
    for size in sizes:
        resized = img.resize((size, size), Image.LANCZOS)
        icon_images.append(resized)

    icon_images[-1].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
    )

    file_size = ico_path.stat().st_size
    print(f"\n✅ 已生成: {ico_path} ({file_size:,} bytes)")
    print(f"   包含尺寸: {', '.join(f'{s}x{s}' for s in sizes)}")


def generate_pngs(img):
    """生成各尺寸 PNG 文件"""
    png_dir = OUTPUT_DIR / "icons"
    png_dir.mkdir(exist_ok=True)

    for size in PNG_SIZES:
        resized = img.resize((size, size), Image.LANCZOS)
        out_path = png_dir / f"icon_{size}.png"
        resized.save(out_path, "PNG")
        print(f"  ✅ {out_path.name}")

    print(f"\n✅ 已生成 {len(PNG_SIZES)} 个 PNG 文件到 {png_dir}/")


def generate_icns(img):
    """生成 macOS ICNS 文件 (仅在 macOS 上)"""
    if sys.platform != "darwin":
        print("\n⏭️  跳过 ICNS 生成 (非 macOS 系统)")
        return

    iconset_dir = OUTPUT_DIR / "icon.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir()

    iconset_files = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }

    for filename, size in iconset_files.items():
        resized = img.resize((size, size), Image.LANCZOS)
        resized.save(iconset_dir / filename, "PNG")

    icns_path = OUTPUT_DIR / "icon.icns"
    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        file_size = icns_path.stat().st_size
        print(f"\n✅ 已生成: {icns_path} ({file_size:,} bytes)")
    else:
        print(f"\n❌ iconutil 失败: {result.stderr}")

    shutil.rmtree(iconset_dir)


def main():
    print("=" * 50)
    print("  Treas 高清图标生成工具")
    print("=" * 50)

    img = generate_source_icon()

    print("\n--- 生成 Windows ICO ---")
    generate_ico(img)

    print("\n--- 生成各尺寸 PNG ---")
    generate_pngs(img)

    print("\n--- 生成 macOS ICNS ---")
    generate_icns(img)

    print("\n" + "=" * 50)
    print("  全部完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()