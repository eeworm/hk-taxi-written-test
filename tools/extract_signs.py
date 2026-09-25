#!/usr/bin/env python3
"""由運輸署《道路使用者守則》PDF 抽取「發出指令的交通標誌」圖示。

來源：https://www.roadsafety.gov.hk/doc/tc/dnload/road_users_code_2020_chi.pdf
     第八章「道路語言」，PDF 第 113-116 頁（印刷版第 111-114 頁）。

輸出：
  assets/signs/ch8/<編號>-<slug>.png   PNG-8 / 4 色 / 原生 201px（約 2KB 一個）
  assets/signs/ch8/manifest.json       編號 → 檔名、官方中文名

為何以 PNG-8 而唔係 SVG：
  呢個 InDesign 匯出嘅 PDF，pdftocairo -svg 出嘅 viewBox（0 0 595.276 419.528）
  同實際 path 座標（x -81.6..572.0, y -40.8..406.3）唔一致，切圖會靜靜哋切歪。
  PNG-8 4 色每個約 1.9KB，104 個約 268KB（base64），肉眼同 300dpi 原圖無分別。

用法：
  python3 tools/extract_signs.py            # 抽取（會 cache PDF 落 tools/.cache/）
  python3 tools/extract_signs.py --sheet    # 另出 contact sheet 供肉眼核對
"""
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "signs", "ch8")
CACHE = os.path.join(ROOT, "tools", ".cache")
PDF_URL = "https://www.roadsafety.gov.hk/doc/tc/dnload/road_users_code_2020_chi.pdf"
PDF = os.path.join(CACHE, "ruc.pdf")

PAGES = (113, 114, 115, 116)   # PDF pages holding signs 1..104
DPI = 300
PX_PER_PT = DPI / 72.0         # 4.1667
QUANT_COLORS = 4               # 標誌係平色幾何圖形，4 色已經足夠

SIGN_MIN_H_PX = 120            # 標誌列高 ~201px；說明文字列高 ~34px


# --------------------------------------------------------------------------
# 抓 PDF
# --------------------------------------------------------------------------
def ensure_pdf():
    os.makedirs(CACHE, exist_ok=True)
    if not os.path.isfile(PDF) or os.path.getsize(PDF) < 1_000_000:
        print(f"下載 {PDF_URL} …")
        urllib.request.urlretrieve(PDF_URL, PDF)
    return PDF


def render(page, out_stem):
    subprocess.run(
        ["pdftocairo", "-png", "-r", str(DPI), "-f", str(page), "-l", str(page),
         PDF, out_stem],
        check=True, capture_output=True)
    return f"{out_stem}-{page}.png"


# --------------------------------------------------------------------------
# 偵測標誌格
# --------------------------------------------------------------------------
def _bands(counts, min_len):
    out, inb, start = [], False, 0
    for i, n in enumerate(counts):
        if n > 0 and not inb:
            start, inb = i, True
        elif n == 0 and inb:
            out.append((start, i - 1)); inb = False
    if inb:
        out.append((start, len(counts) - 1))
    return [b for b in out if b[1] - b[0] + 1 >= min_len]


def detect_cells(png):
    """回傳 [(x0, y0, x1, y1)]，px 座標，閱讀次序（上→下、左→右）。"""
    from PIL import Image
    im = Image.open(png).convert("L")
    W, H = im.size
    px = im.load()
    rows = [sum(1 for x in range(0, W, 2) if px[x, y] < 200) for y in range(H)]
    cells = []
    sign_rows = _bands(rows, SIGN_MIN_H_PX)
    # 用其餘列嘅格距推斷被合併嘅闊格要切幾多份
    pitch = None
    per_row = []
    for (y0, y1) in sign_rows:
        cols = [sum(1 for y in range(y0, y1) if px[x, y] < 200) for x in range(W)]
        segs = _bands(cols, 1)
        merged = []
        for s in segs:
            if merged and s[0] - merged[-1][1] <= 12:
                merged[-1] = (merged[-1][0], s[1])
            else:
                merged.append(s)
        per_row.append((y0, y1, merged))
    # 由最窄嘅格推格距（標誌本身 201px）
    widths = [e - s for (_, _, segs) in per_row for (s, e) in segs]
    if widths:
        pitch = min(widths) + 22      # 格距 = 標誌闊 + 空隙
    for (y0, y1, segs) in per_row:
        for (x0, x1) in segs:
            w = x1 - x0
            if pitch and w > pitch * 1.6:
                n = max(1, round((w + 22) / pitch))
                step = w / n
                for k in range(n):
                    cells.append((int(x0 + k * step), y0, int(x0 + (k + 1) * step) - 1, y1))
            else:
                cells.append((x0, y0, x1, y1))
    return cells


# --------------------------------------------------------------------------
# 說明文字 → 編號
# --------------------------------------------------------------------------
def caption_numbers(page):
    """由 pdftotext -bbox 攞每條說明文字嘅「N.」位置 → [(n, x_centre_pt, y_pt)]。"""
    subprocess.run(["pdftotext", "-bbox", "-f", str(page), "-l", str(page), PDF, "/tmp/_bb.xml"],
                   check=True, capture_output=True)
    xml = open("/tmp/_bb.xml", encoding="utf-8").read()
    words = re.findall(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', xml)
    out = []
    for xs, ys, xe, ye, txt in words:
        # 有啲係「29.公共小」咁黐埋一齊（PDF 無 word break），唔可以要求純數字
        m = re.match(r"^(\d{1,3})\.", txt.strip())
        if m:
            out.append((int(m.group(1)), (float(xs) + float(xe)) / 2, float(ys)))
    return out


def assign_numbers(cells, caps):
    """說明編號 → (格, 說明 y)。

    由編號出發（官方 104 個先係權威），揀正上方、x 中點最接近嘅格。
    反方向做嘅話，一個格會「偷」走隔籬格嘅說明。

    回傳埋說明嘅 y：有啲頁（例如 p115）標誌牌高，說明文字會落喺
    偵測到嘅格範圍之內——切圖時要夾硬切喺說明之上，唔係就會連
    答案文字都烤埋入張圖。
    """
    pairs = {}
    for (n, xc, y) in caps:
        best, best_key = None, None
        for cell in cells:
            x0, y0, x1, y1 = cell
            cx_pt = (x0 + x1) / 2 / PX_PER_PT
            y1_pt = y1 / PX_PER_PT
            gap = y - y1_pt
            # 容許說明落喺格內（p115 嘅牌高，說明會喺偵測到嘅格範圍內）。
            # 上下界 60pt：列距約 118pt，夠窄可以擋走上一列嘅說明。
            if gap < -60 or gap > 60:
                continue
            if abs(xc - cx_pt) > 45:      # 同一直行
                continue
            key = (abs(xc - cx_pt), abs(gap))
            if best_key is None or key < best_key:
                best, best_key = cell, key
        if best:
            pairs[best] = (n, y)
    return pairs


# --------------------------------------------------------------------------
# 切圖 + 壓縮
# --------------------------------------------------------------------------
def slug(name):
    s = re.sub(r"[（）()/,、。\s]+", "-", name)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:28]


INK_LEVEL = 200      # 背景約 246；標誌顏色約 55-95。200 分得開。


def _bg_of(im):
    """PDF 底色唔係純白（約 244,247,249）——由四角取樣。"""
    w, h = im.size
    corners = [im.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    return tuple(sum(c[i] for c in corners) // len(corners) for i in range(3))


def extract(png, box, dest):
    """切出一格：trim 底邊 → 補成正方 → PNG-8 量化。"""
    from PIL import Image
    im = Image.open(png).convert("RGB").crop(box)
    bg = _bg_of(im)
    # 以底色做去背，容差 12 擋走 PDF 輕微色差
    mask = Image.new("L", im.size, 0)
    px, mp = im.load(), mask.load()
    for y in range(im.height):
        for x in range(im.width):
            p = px[x, y]
            if abs(p[0]-bg[0]) > 12 or abs(p[1]-bg[1]) > 12 or abs(p[2]-bg[2]) > 12:
                mp[x, y] = 255
    bbox = mask.getbbox()
    if bbox:
        im = im.crop(bbox)
    side = max(im.size)
    canvas = Image.new("RGB", (side, side), bg)
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    canvas.quantize(colors=QUANT_COLORS, method=Image.MEDIANCUT).save(
        dest, "PNG", optimize=True)
    return os.path.getsize(dest)


def ink_ratio(path):
    """非底色像素比例——用嚟擋走空白／切歪嘅圖（空白圖 = 靜靜哋出錯）。"""
    from PIL import Image
    im = Image.open(path).convert("L")
    hist = im.histogram()
    return sum(hist[:INK_LEVEL]) / float(im.width * im.height)


def main():
    make_sheet = "--sheet" in sys.argv
    ensure_pdf()
    os.makedirs(OUT_DIR, exist_ok=True)
    names = json.load(open(os.path.join(ROOT, "tools", "sign_names.json"), encoding="utf-8"))
    names = {int(k): v for k, v in names.items()}

    manifest, problems, sheet_rows = [], [], []
    for page in PAGES:
        png = render(page, os.path.join(CACHE, f"pg{page}"))
        cells = detect_cells(png)
        mapping = assign_numbers(cells, caption_numbers(page))
        print(f"PDF p{page}: {len(cells)} 格, 對到編號 {len(mapping)} 個")
        for box, (n, cap_y) in sorted(mapping.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            name = names.get(n, f"標誌{n}")
            fn = f"{n:03d}-{slug(name)}.png"
            dest = os.path.join(OUT_DIR, fn)
            # 切到說明文字之上（留 2pt 空位），確保答案文字唔會入圖
            x0, y0, x1, y1 = box
            y1 = min(y1, int(cap_y * PX_PER_PT) - 8)
            if y1 - y0 < 40:
                y1 = box[3]
            size = extract(png, (x0, y0, x1, y1), dest)
            ratio = ink_ratio(dest)
            if ratio < 0.05 or ratio > 0.95:
                problems.append((n, fn, f"ink_ratio={ratio:.3f}（可能空白或全黑）"))
            manifest.append({"n": n, "name": name, "file": fn, "bytes": size})
            if make_sheet:
                sheet_rows.append((n, dest))

    manifest.sort(key=lambda r: r["n"])
    json.dump(manifest, open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    total = sum(r["bytes"] for r in manifest)
    print(f"\n共 {len(manifest)} 個標誌, 原始 {total/1024:.0f}KB, base64 約 {total*4/3/1024:.0f}KB")
    missing = [n for n in range(1, 105) if n not in {r['n'] for r in manifest}]
    if missing:
        print(f"⚠️  未抽到：{missing}")
    for n, fn, why in problems:
        print(f"⚠️  {n} {fn}: {why}")
    if not problems and not missing:
        print("✅ 全部標誌抽出並通過非空白檢查")

    if make_sheet:
        from PIL import Image, ImageDraw
        cols = 10
        rows = (len(sheet_rows) + cols - 1) // cols
        cell = 110
        sheet = Image.new("RGB", (cols * cell, rows * (cell + 16)), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        for i, (n, path) in enumerate(sorted(sheet_rows)):
            im = Image.open(path).convert("RGB").resize((cell - 10, cell - 10), Image.LANCZOS)
            x, y = (i % cols) * cell, (i // cols) * (cell + 16)
            sheet.paste(im, (x + 5, y + 2))
            d.text((x + 5, y + cell - 8), str(n), fill=(0, 0, 0))
        sheet.save(os.path.join(CACHE, "contact_sheet.png"))
        print(f"contact sheet → {os.path.join(CACHE, 'contact_sheet.png')}")


if __name__ == "__main__":
    main()
