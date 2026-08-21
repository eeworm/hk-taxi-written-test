#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Driwe 溫習指南構建腳本（公開版）
將 notes/ exams/ curriculum/ 下所有 markdown 筆記整合成
單一自包含 index.html（內嵌 CSS/JS/交通標誌圖片，完全離線可用）。

用法：python3 build-html.py
改完任何 .md 筆記後重跑一次即可。

依賴：pip install markdown
"""
import datetime
import os
import re
import sys
from urllib.parse import quote

import markdown

ROOT = os.path.dirname(os.path.abspath(__file__))
SIGNS_ROOT = os.path.join(ROOT, "assets", "signs")
SIGNS_REDRAWN = os.path.join(SIGNS_ROOT, "redrawn")
OUT_PATH = os.path.join(ROOT, "index.html")

# ---------------------------------------------------------------------------
# 1. 來源檔案（固定順序）
# ---------------------------------------------------------------------------
FILES = [
    "notes/lesson-01-exam-overview.md",
    "notes/lesson-02-licensing.md",
    "notes/lesson-03-fleet-demirit.md",
    "notes/lesson-04-fare-taximeter.md",
    "notes/lesson-05-passenger-service.md",
    "notes/lesson-06-driver-conduct.md",
    "notes/lesson-07-hk-island-locations.md",
    "notes/lesson-08-kowloon-locations.md",
    "notes/lesson-09-nt-islands-locations.md",
    "notes/lesson-10-route-planning.md",
    "notes/lesson-13-traffic-lights.md",
    "notes/lesson-14-speed-parking.md",
    "notes/lesson-15-safe-driving.md",
    "notes/lesson-16-accidents-demerit.md",
    "notes/lesson-17-trunk-roads.md",
    "notes/lesson-18-signs-classification.md",
    "notes/official-place-route-bank.md",
    "notes/location-reference-handbook.md",
    "exams/real-exam-questions-reference.md",
    "exams/route-and-location-drill.md",
    "exams/deep-dive-practice.md",
    "exams/quiz-bank-mc.md",
    "curriculum/course-plan.md",
]

# 側邊欄分組（預設按資料夾；呢度只覆寫例外）
GROUP_OVERRIDE = {
    "notes/location-reference-handbook.md": "參考手冊",
    "notes/official-place-route-bank.md": "官方題庫",
}

# ---------------------------------------------------------------------------
# 2. 標誌圖鑑（lesson-18 注入）— (檔案, 說明, badge, 鏡像)
#    官方 PNG 由運輸署《道路使用者守則》PDF 抽取；SVG 為 Commons/重繪圖。
# ---------------------------------------------------------------------------
GALLERY = [
    ("警告標誌", "🔺 三角形・紅邊 — 預告前方有危險", [
        ("official-warn-bend-left.png", "前面左彎", None, False),
        ("official-warn-bend-left.png", "前面右彎（鏡像）", None, True),
        ("official-warn-road-narrows.png", "前面道路兩邊收窄", None, False),
        ("official-warn-narrows-right.png", "前面道路右邊收窄", None, False),
        ("official-warn-roundabout.png", "前面有迴旋處", None, False),
        ("official-warn-school.png", "前面有兒童", None, False),
        ("official-warn-traffic-light.png", "前面有交通燈號", None, False),
        ("official-warn-giveway-ahead.png", "前面有讓路/停車標誌（預告牌）", None, False),
    ]),
    ("禁制標誌", "⭕ 圓形・紅邊 — 唔准做", [
        ("official-prohib-no-parking.png", "不准泊車", None, False),
        ("official-prohib-no-stopping.png", "不准停車", None, False),
        ("official-prohib-no-entry.png", "所有車輛不准駛入", None, False),
        ("official-prohib-no-uturn.png", "不准掉頭", None, False),
        ("official-prohib-speed-50.png", "車速限制", None, False),
        ("official-prohib-no-horn.png", "禁止響號", None, False),
    ]),
    ("指示標誌", "🔵 圓形藍底 / 藍長方 — 必須做", [
        ("official-mand-ahead-only.png", "只准向前駛", None, False),
        ("official-mand-turn-left.png", "左轉（符號方向相反則右轉）", None, False),
        ("official-mand-one-way.png", "單程行車", None, False),
    ]),
    ("指示標誌（必考陷阱！）", "⚠️ 形狀呃人——功能上係指令你讓路/停車，屬指示標誌", [
        ("official-give-way.png", "讓路（倒三角）", "必考陷阱", False),
        ("official-stop-sign.png", "停車（八角形）", "必考陷阱", False),
    ]),
    ("資訊標誌", "⬜ 長方形 — 提供資料", [
        ("official-info-parking-p.png", "泊車處（P）", None, False),
        ("info-parking-direction.svg", "泊車處方向", None, False),
        ("official-info-tunnel.png", "隧道區起點", None, False),
        ("official-info-taxi-stand.png", "的士站", None, False),
    ]),
]

# 其他注入點：(檔案, 標題文字子串, 模式 after-heading | before-next-heading, HTML)
INJECT = [
    ("notes/lesson-13-traffic-lights.md", "基本三色燈號", "after-heading",
     '<div class="injected pictogram-row"><div class="pictogram"><img src="assets/signs/traffic-light.svg" alt="三色交通燈（綠燈亮起）"></div>'
     '<p class="pictogram-note">🟢 綠燈：可通行（轉綠先確認安全）・🟡 黃燈：如能安全停車須停・🔴 紅燈：必須停定</p></div>'),
    ("notes/lesson-14-speed-parking.md", "停車及泊車三大層級", "after-heading",
     '<div class="injected pictogram-row"><div class="pictogram"><img src="assets/signs/official-prohib-no-parking.png" alt="不准泊車"><span>不准泊車</span></div>'
     '<div class="pictogram"><img src="assets/signs/official-prohib-no-stopping.png" alt="不准停車"><span>不准停車</span></div>'
     '<p class="pictogram-note">🚨 記法：一條斜線＝不准泊車（P 被刪）；交叉＝不准停車（連停都唔得，更嚴格）</p></div>'),
]

# ---------------------------------------------------------------------------
# 3. 工具函數
# ---------------------------------------------------------------------------
def find_sign(name):
    """先搵 assets/signs/，再搵 redrawn/。"""
    for base in (SIGNS_ROOT, SIGNS_REDRAWN):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(name)


def sanitize_svg(src, alt=""):
    """消毒下載/手繪 SVG：移除 prolog/註解/編輯器 metadata，補 viewBox，加 class。"""
    src = re.sub(r"<\?xml[^>]*\?>", "", src)
    src = re.sub(r"<!--.*?-->", "", src, flags=re.DOTALL)
    src = re.sub(r"<sodipodi:namedview[^>]*/>", "", src, flags=re.DOTALL)
    src = re.sub(r"<metadata>.*?</metadata>", "", src, flags=re.DOTALL)
    src = re.sub(r"\s+(?:inkscape|sodipodi|xml:space|enable-background|version)="
                 r'"[^"]*"', "", src)
    m = re.search(r"<svg[^>]*>", src)
    if not m:
        raise ValueError("no <svg> tag found")
    svg_tag = m.group(0)
    if "viewBox=" not in svg_tag:
        w = re.search(r'width="([\d.]+)"', svg_tag)
        h = re.search(r'height="([\d.]+)"', svg_tag)
        if w and h:
            svg_tag = svg_tag.replace(">", f' viewBox="0 0 {w.group(1)} {h.group(1)}">', 1)
    svg_tag = re.sub(r'\s+width="[^"]*"', "", svg_tag)
    svg_tag = re.sub(r'\s+height="[^"]*"', "", svg_tag)
    if 'class="' in svg_tag:
        svg_tag = svg_tag.replace('class="', 'class="sign ')
    else:
        svg_tag = svg_tag.replace(">", ' class="sign">', 1)
    if alt:
        svg_tag = svg_tag.replace(">", f' role="img" aria-label="{alt}">', 1)
    src = src[: m.start()] + svg_tag + src[m.end():]
    return src.strip()


def inline_imgs(html):
    """內嵌標誌圖：SVG → 消毒後 inline；PNG → base64 data URI。支援 mirror class。"""
    def repl(m):
        src, alt, mirror_cls = m.group(1), m.group(2), m.group(3) or ""
        name = src.rsplit("/", 1)[-1]
        try:
            path = find_sign(name)
        except FileNotFoundError:
            print(f"  !! 標誌檔案缺失：{name}", file=sys.stderr)
            return m.group(0)
        if name.endswith(".svg"):
            with open(path, encoding="utf-8", errors="ignore") as f:
                return sanitize_svg(f.read(), alt)
        import base64
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        extra = ' mirror' if mirror_cls else ''
        return (f'<img class="sign{extra}" src="data:image/png;base64,{b64}" '
                f'alt="{alt}">')
    return re.sub(
        r'<img\s+src="(assets/signs/[^"]+)"\s+alt="([^"]*)"(\sclass="mirror")?\s*/?>',
        repl, html)


def enhance_bank(html, path):
    """官方題庫：地點名→地圖連結；路線表加「地圖」掣（撳一下開Google Maps modal）。"""
    if path != "notes/official-place-route-bank.md":
        return html

    def map_link(name):
        q = name + " 香港"
        return (f'<a class="map-link" href="https://www.google.com/maps/search/?api=1&query={quote(q)}" '
                f'data-q="{q}" title="喺地圖顯示位置">{name}</a>')

    # 1) 路線表頭加一欄
    html = re.sub(r"<th>最直接可行的路線</th>",
                  "<th>最直接可行的路線</th><th>地圖</th>", html, count=1)
    # 2) 路線行（4格）：起點/目的地變連結＋加地圖掣
    def route_row(m):
        a, num, s, d, r = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        btn = (f'<td><button class="route-map" data-from="{s} 香港" data-to="{d} 香港" '
               f'title="顯示起點至目的地路線">🗺️ 地圖</button></td>')
        return f"<td{a}>{num}</td><td>{map_link(s)}</td><td>{map_link(d)}</td><td>{r}</td>{btn}"
    html = re.sub(r"<td([^>]*)>(\d+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>",
                  route_row, html)
    # 3) 地方行（3格）：地方名變連結
    def place_row(m):
        a1, num, name, a2, loc = m.groups()
        return f"<td{a1}>{num}</td><td>{map_link(name)}</td><td{a2}>{loc}</td>"
    html = re.sub(r"<td([^>]*)>(\d+)</td>\s*<td>([^<]+)</td>\s*<td([^>]*)>([^<]+)</td>",
                  place_row, html)
    return html


def wrap_tables(html):
    return re.sub(r"(<table>.*?</table>)",
                  r'<div class="table-wrap">\1</div>', html, flags=re.DOTALL)


def style_callouts(html):
    """按開頭 emoji 為 blockquote 加上顏色 class。"""
    def repl(m):
        emoji, rest = m.group(1), m.group(2)
        cls = {"🚨": "red", "⚠️": "amber", "🧠": "blue", "🔑": "blue",
               "✅": "green", "📌": "green"}.get(emoji, "red")
        return f'<blockquote class="callout callout-{cls}"><p>{emoji} {rest}</p>'
    return re.sub(r"<blockquote>\s*<p>(🚨|⚠️|🧠|🔑|✅|📌)\s*(.*?)</p>",
                  repl, html, flags=re.DOTALL)


def file_eyebrow(path, title):
    """側邊欄 mono 標籤：課程用 L-XX，其他用短標籤。"""
    m = re.search(r"第(\d+)課", title)
    if m:
        return f"L-{int(m.group(1)):02d}"
    name = os.path.basename(path)
    labels = {
        "location-reference-handbook.md": "手冊",
        "official-place-route-bank.md": "255+18",
        "real-exam-questions-reference.md": "題庫",
        "route-and-location-drill.md": "路線",
        "deep-dive-practice.md": "練習",
        "course-plan.md": "計劃",
    }
    return labels.get(name, name[:6])


HEADING_RE = re.compile(r"<(h[1-4])>(.*?)</\1>", re.DOTALL)


def convert_file(idx, path):
    """轉換單一檔案 → dict(title, eyebrow, html, toc_entries)。"""
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        text = f.read()
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list", "md_in_html"],
        output_format="html5",
    )

    # 分割成 headings / body 段落
    parts = HEADING_RE.split(body)  # [body, tag, text, body, tag, text, ...]
    items = []  # ("h", level, text) 或 ("b", html)
    if parts[0].strip():
        items.append(("b", parts[0]))
    for i in range(1, len(parts), 3):
        items.append(("h", parts[i], parts[i + 1]))
        if i + 2 < len(parts) and parts[i + 2].strip():
            items.append(("b", parts[i + 2]))

    # 指派穩定 id + 收集 TOC
    toc, out, seq, title, first_h1_done = [], [], 0, "", False
    for it in items:
        if it[0] == "h":
            _, level, text = it
            seq += 1
            hid = f"l{idx}-s{seq}"
            if level == "h1":
                title = re.sub(r"<[^>]+>", "", text).strip()
            out.append(f'<{level} id="{hid}">{text}</{level}>')
            if level in ("h2", "h3"):
                toc.append((level, re.sub(r"<[^>]+>", "", text).strip(), hid, False))
        else:
            out.append(it[1])
    html = "\n".join(out)

    # 注入點（anchor 標題 → 前後插入）
    for path_cfg, anchor, mode, inject_html in INJECT:
        if path_cfg != path:
            continue
        anchor_re = re.compile(
            rf'(<h[1-4] id="l{idx}-s\d+">([^<]*?){re.escape(anchor)}[^<]*?</h[1-4]>)')
        m = anchor_re.search(html)
        if not m:
            print(f"  !! 注入錨點搵唔到：{path} :: {anchor}", file=sys.stderr)
            continue
        if mode == "after-heading":
            html = html.replace(m.group(1), m.group(1) + "\n" + inject_html, 1)
        else:  # before-next-heading：插喺下一節之前
            nxt = re.search(r'<h[1-4] id=', html[m.end():])
            pos = m.end() + nxt.start() if nxt else len(html)
            html = html[:pos] + "\n" + inject_html + "\n" + html[pos:]

    # lesson-18：圖鑑注入（喺「記憶口訣」一節之後）
    if path == "notes/lesson-18-signs-classification.md":
        gallery = build_gallery()
        anchor_re = re.compile(
            rf'(<h[1-4] id="l{idx}-s\d+">([^<]*?)記憶口訣[^<]*?</h[1-4]>)')
        m = anchor_re.search(html)
        if m:
            nxt = re.search(r'<h[1-4] id=', html[m.end():])
            pos = m.end() + nxt.start() if nxt else len(html)
            html = html[:pos] + "\n" + gallery + "\n" + html[pos:]

    return {
        "path": path,
        "title": title,
        "eyebrow": file_eyebrow(path, title),
        "html": html,
        "toc": toc,
    }


def parse_bank_md():
    """由 notes/official-place-route-bank.md 嘅表格解析題庫 → 互動模擬試數據。"""
    import json
    path = os.path.join(ROOT, "notes", "official-place-route-bank.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    places, routes = [], []
    cur_cat = ""
    for line in text.splitlines():
        m = re.match(r"###\s+(.+?)（編號", line)
        if m:
            cur_cat = m.group(1).strip()
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 4 and cells[0].isdigit() and int(cells[0]) >= 256:
            routes.append({"n": int(cells[0]), "s": cells[1], "d": cells[2], "r": cells[3]})
        elif len(cells) == 3 and cells[0].isdigit() and int(cells[0]) < 256:
            places.append({"n": int(cells[0]), "name": cells[1], "loc": cells[2], "cat": cur_cat})
    return places, routes


def parse_mc_bank():
    """解析 exams/quiz-bank-mc.md → 服務知識/道路守則選擇題。"""
    path = os.path.join(ROOT, "exams", "quiz-bank-mc.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    part, cat, q, partA, partB = "", "", None, [], []
    for line in text.splitlines():
        m = re.match(r"##\s+(.+)", line)
        if m:
            part = "A" if "甲部" in m.group(1) else "B" if "乙部" in m.group(1) else part
            continue
        m = re.match(r"###\s+(.+)", line)
        if m:
            cat = m.group(1).strip()
            continue
        m = re.match(r"Q:\s*(.+)", line)
        if m:
            q = {"q": m.group(1).strip(), "cat": cat, "opts": []}
            continue
        m = re.match(r"O:\s*(.+)", line)
        if m and q is not None:
            for opt in m.group(1).split("|"):
                ok = opt.strip().startswith("**")
                q["opts"].append({"t": opt.strip().strip("*"), "ok": ok})
            (partA if part == "A" else partB).append(q)
            q = None
    return partA, partB


def render_mc_card():
    """選擇題庫卡片：Q/O 格式渲染為易讀樣式（正確答案打✓）。"""
    partA, partB = parse_mc_bank()
    out = [
        '<blockquote class="callout callout-blue"><p>🧠 呢份係互動模擬試嘅服務知識＋道路守則題庫。'
        '答案已用 <strong>粗體✓</strong> 標示——溫習時遮住答案試答，再喺模擬試測試自己。</p></blockquote>',
    ]
    for title, items in (("一、的士及網約車營運（甲部）", partA),
                         ("二、道路使用者守則（乙部）", partB)):
        out.append(f"<h2>{title}</h2>")
        cur = None
        for q in items:
            if q["cat"] != cur:
                cur = q["cat"]
                out.append(f"<h3>{cur}</h3>")
            out.append(f'<div class="mc-q"><p class="mc-text">{q["q"]}</p><ul class="mc-opts">')
            for o in q["opts"]:
                cls = ' class="ok"' if o["ok"] else ""
                out.append(f"<li{cls}>{o['t']}</li>")
            out.append("</ul></div>")
    return "\n".join(out)


def build_quiz(places, routes):
    """互動模擬試：HTML卡片＋內嵌題庫JSON。"""
    import json
    cats = []
    for p in places:
        if p["cat"] and p["cat"] not in cats:
            cats.append(p["cat"])
    mc_a, mc_b = parse_mc_bank()
    mc_cats = list(dict.fromkeys(q["cat"] for q in mc_a + mc_b))
    bank = json.dumps({"places": places, "routes": routes, "cats": cats,
                       "mcA": mc_a, "mcB": mc_b, "mcCats": mc_cats},
                      ensure_ascii=False)
    cat_opts = "".join(f'<option value="{c}">{c}</option>' for c in cats)
    mccat_opts = "".join(f'<option value="{c}">{c}</option>' for c in mc_cats)
    return f"""
<section class="quiz-wrap">
  <div class="lesson" id="quiz-sec">
    <div class="lesson-content">
      <h2 id="quiz-title">📝 互動模擬試 — 官方題庫＋全範圍</h2>
      <p class="quiz-sub">地方255・路線18・服務知識{len(mc_a)}・道路守則{len(mc_b)} ・撳答案即知對錯・錯題可以重溫</p>
      <div class="quiz-controls">
        <label>範圍
          <select id="quiz-mode">
            <option value="place">地方題（255）</option>
            <option value="route">路線題（18）</option>
            <option value="mca">服務知識・甲部（{len(mc_a)}）</option>
            <option value="mcb">道路守則・乙部（{len(mc_b)}）</option>
            <option value="mixed">混合模擬（20）</option>
          </select>
        </label>
        <label>分類
          <select id="quiz-cat"><option value="">全部</option></select>
        </label>
        <label>次序
          <select id="quiz-order">
            <option value="order">順序</option>
            <option value="random" selected>隨機</option>
          </select>
        </label>
        <label class="quiz-newfirst"><input type="checkbox" id="quiz-wrong-first" checked> 曾答錯優先</label>
        <label class="quiz-newfirst"><input type="checkbox" id="quiz-new-first" checked> 未答過優先</label>
        <span class="quiz-seen-count" id="quiz-seen-count"></span>
        <label>每次
          <select id="quiz-n">
            <option>10</option>
            <option selected>50</option>
            <option>100</option>
            <option value="0">全部</option>
          </select>
          <span>題</span>
        </label>
        <button id="quiz-start">▶ 開始</button>
        <button id="quiz-reset">↺ 重設</button>
      </div>
      <div class="quiz-status" id="quiz-status"></div>
      <div class="quiz-body" id="quiz-body"><p class="quiz-idle">撳「▶ 開始」出題～</p></div>
      <div class="quiz-wrong" id="quiz-wrong"></div>
    </div>
  </div>
</section>
<script id="quiz-bank" type="application/json">{bank}</script>"""


def build_gallery():
    """lesson-18 標誌圖鑑 HTML（先放 img 佔位，稍後統一內嵌）。"""
    parts = ['<div class="injected sign-gallery">',
             '<h3 class="gallery-title">🚦 標誌圖鑑 — 一次過睇晒四大分類</h3>',
             '<p class="gallery-sub">黃金原則：<strong>功能決定分類，唔係形狀決定！</strong></p>']
    for group, sub, signs in GALLERY:
        parts.append(f'<div class="gallery-group"><h4 class="gallery-group-title">{sub}</h4>'
                     f'<div class="sign-grid">')
        for name, caption, badge, mirror in signs:
            badge_html = (f'<span class="sign-badge">{badge}</span>'
                          if badge else "")
            mirror_html = ' class="mirror"' if mirror else ""
            parts.append(f'<figure class="sign-card">{badge_html}'
                         f'<img src="assets/signs/{name}" alt="{caption}"{mirror_html}>'
                         f'<figcaption>{caption}</figcaption></figure>')
        parts.append("</div></div>")
    parts.append("</div>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 4. CSS / JS（內嵌）
# ---------------------------------------------------------------------------
CSS = """
/* ==== Driwe 溫習指南 — 設計系統 ==== */
:root {
  --ink: #12233B;
  --ink-2: #1A3050;
  --paper: #F4F1EA;
  --card: #FFFFFF;
  --text: #1E2430;
  --text-soft: #5C6675;
  --line: #E3DFD5;
  --red: #C8102E;
  --red-soft: #FBF1F0;
  --blue: #0057B8;
  --blue-soft: #EFF4FA;
  --amber: #F7A800;
  --amber-soft: #FBF6EA;
  --green: #1E7A46;
  --green-soft: #EFF6F1;
  --mono: ui-monospace, "SF Mono", "Cascadia Mono", Consolas, "Noto Sans Mono CJK TC", monospace;
  --sans: "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", "Segoe UI", sans-serif;
  --shadow: 0 1px 3px rgba(18,35,59,.08), 0 8px 24px rgba(18,35,59,.06);
}
[data-theme="dark"] {
  --paper: #10151C;
  --card: #18202B;
  --text: #E8E4DA;
  --text-soft: #97A0AC;
  --line: #2A3442;
  --red-soft: rgba(200,16,46,.14);
  --blue-soft: rgba(0,87,184,.16);
  --amber-soft: rgba(247,168,0,.13);
  --green-soft: rgba(30,122,70,.16);
  --shadow: 0 1px 3px rgba(0,0,0,.4);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--sans);
  background: var(--paper);
  color: var(--text);
  line-height: 1.7;
}
button { font-family: var(--sans); }

/* ==== 版面 ==== */
.layout { display: grid; grid-template-columns: 300px 1fr; min-height: 100vh; }

/* ==== 側邊欄 ==== */
.sidebar {
  background: var(--ink);
  color: #E8E4DA;
  position: sticky; top: 0; height: 100vh;
  display: flex; flex-direction: column;
  overflow-y: auto;
  padding: 20px 14px 32px;
}
.brand { display: flex; align-items: center; gap: 12px; padding: 4px 6px 18px; }
.taxi-badge {
  background: #fff; color: var(--red);
  font-weight: 800; font-size: 1.05rem; letter-spacing: .06em;
  padding: 5px 10px; border-radius: 9px;
  box-shadow: 0 0 18px rgba(200,16,46,.55);
  flex: none;
}
.brand-text strong { display: block; font-size: 1.02rem; color: #fff; letter-spacing: .02em; }
.brand-text small { color: #8FA0B8; font-size: .72rem; }
.sidebar .search {
  width: 100%; padding: 9px 12px; border-radius: 8px; border: 1px solid #2C4268;
  background: #0D1B2E; color: #fff; font-size: .88rem; margin-bottom: 14px;
}
.sidebar .search::placeholder { color: #6E8199; }
.sidebar .search:focus { outline: 2px solid var(--red); border-color: transparent; }
.toc { flex: 1; }
.toc-group {
  font-size: .68rem; color: #6E8199; letter-spacing: .14em;
  padding: 10px 8px 4px; font-family: var(--mono);
}
.toc details { margin-bottom: 6px; }
.toc summary {
  cursor: pointer; list-style: none; padding: 7px 8px; border-radius: 7px;
  font-size: .86rem; display: flex; align-items: baseline; gap: 8px; color: #D7DEE8;
}
.toc summary::-webkit-details-marker { display: none; }
.toc summary:hover { background: var(--ink-2); color: #fff; }
.toc summary .eyebrow {
  font-family: var(--mono); font-size: .68rem; color: #FF8B93;
  background: rgba(200,16,46,.22); padding: 1px 6px; border-radius: 4px; flex: none;
}
.toc details[open] > summary { background: var(--ink-2); color: #fff; }
.toc ul { list-style: none; margin: 2px 0 8px; padding-left: 18px; }
.toc li a {
  display: block; padding: 3px 8px; border-radius: 5px;
  color: #9FB1C9; text-decoration: none; font-size: .8rem;
}
.toc li a:hover, .toc li a.active { color: #fff; background: rgba(255,255,255,.08); }
.toc li a.sub { padding-left: 16px; font-size: .76rem; }
.sidebar-foot {
  margin-top: 14px; padding-top: 12px; border-top: 1px solid #2C4268;
  font-size: .68rem; color: #6E8199; font-family: var(--mono);
}

/* ==== 主區 ==== */
.main { min-width: 0; }
.topbar {
  position: sticky; top: 0; z-index: 40;
  display: none; align-items: center; gap: 10px;
  background: var(--ink); color: #fff; padding: 10px 14px;
}
.hamburger {
  background: none; border: 1px solid #2C4268; color: #fff; border-radius: 6px;
  font-size: 1.1rem; padding: 2px 9px; cursor: pointer;
}
.toolbar { display: flex; gap: 8px; justify-content: flex-end; padding: 12px 22px; }
.toolbar button {
  background: var(--card); border: 1px solid var(--line); color: var(--text);
  border-radius: 7px; padding: 5px 12px; font-size: .8rem; cursor: pointer;
}
.toolbar button:hover { border-color: var(--red); color: var(--red); }

/* ==== 歡迎橫幅（公開版） ==== */
.hero { padding: 26px 22px 8px; }
.welcome {
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  box-shadow: var(--shadow); overflow: hidden; max-width: 860px; margin: 0 auto;
  text-align: center; padding: 26px 18px 22px;
}
.welcome-title { font-size: 1.28rem; font-weight: 700; line-height: 1.5; }
.welcome-title .taxi { color: var(--red); }
.welcome-sub {
  margin-top: 8px; font-family: var(--mono); font-size: .78rem; color: var(--text-soft);
}
.welcome-greet {
  margin-top: 16px; display: inline-block;
  background: var(--blue-soft); color: var(--blue);
  border: 1px solid rgba(0,87,184,.25); border-radius: 999px;
  padding: 7px 20px; font-weight: 600; font-size: .92rem;
}

/* ==== 課程卡片 ==== */
.lessons { padding: 18px 22px 60px; }
.lesson {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  box-shadow: var(--shadow); margin: 0 auto 18px; max-width: 860px;
}
.lesson > summary {
  cursor: pointer; list-style: none; display: flex; align-items: center; gap: 12px;
  padding: 14px 20px;
}
.lesson > summary::-webkit-details-marker { display: none; }
.lesson > summary .eyebrow {
  font-family: var(--mono); font-size: .72rem; color: var(--red);
  background: var(--red-soft); border: 1px solid rgba(200,16,46,.25);
  padding: 2px 8px; border-radius: 5px; flex: none;
}
.lesson > summary h1 { font-size: 1.06rem; margin: 0; font-weight: 700; flex: 1; }
.lesson > summary .chev { color: var(--text-soft); transition: transform .18s; }
.lesson[open] > summary .chev { transform: rotate(90deg); }
.lesson[open] > summary { border-bottom: 1px solid var(--line); }
.lesson-content { padding: 20px 24px 26px; }

/* ==== 內文 ==== */
.lesson-content h1 { font-size: 1.2rem; margin: .2em 0 .8em; }
.lesson-content h2 {
  font-size: 1.05rem; margin: 1.6em 0 .7em; padding-left: 12px;
  border-left: 4px solid var(--red); border-bottom: 1px solid var(--line); padding-bottom: 5px;
}
.lesson-content h3 {
  font-size: .95rem; margin: 1.4em 0 .5em; padding-left: 10px; border-left: 3px solid var(--blue);
}
.lesson-content h4 { font-size: .88rem; margin: 1.2em 0 .4em; color: var(--text-soft); }
.lesson-content p { margin: .55em 0; }
.lesson-content ul, .lesson-content ol { margin: .5em 0; padding-left: 1.5em; }
.lesson-content li { margin: .22em 0; }
.lesson-content a { color: var(--blue); }
.lesson-content code {
  font-family: var(--mono); font-size: .82em;
  background: rgba(18,35,59,.07); border-radius: 4px; padding: 1px 6px;
}
[data-theme="dark"] .lesson-content code { background: rgba(255,255,255,.09); }
.lesson-content pre {
  background: #F0EDE4; border: 1px solid var(--line); border-radius: 8px;
  padding: 12px 14px; overflow-x: auto;
}
[data-theme="dark"] .lesson-content pre { background: #0D1420; }
.lesson-content pre code { background: none; padding: 0; }
.lesson-content hr { border: none; border-top: 1px solid var(--line); margin: 1.4em 0; }

/* ==== 表格（收費卡風格） ==== */
.table-wrap { overflow-x: auto; margin: .9em 0; border: 1px solid var(--line); border-radius: 8px; }
.table-wrap table { border-collapse: collapse; width: 100%; min-width: 460px; font-size: .85rem; }
.table-wrap th {
  background: var(--ink); color: #fff; text-align: left; font-weight: 600;
  padding: 7px 12px; white-space: nowrap;
}
[data-theme="dark"] .table-wrap th { background: var(--ink-2); }
.table-wrap td { padding: 6px 12px; border-top: 1px solid var(--line); vertical-align: top; }
.table-wrap tbody tr:nth-child(even) { background: rgba(18,35,59,.03); }
[data-theme="dark"] .table-wrap tbody tr:nth-child(even) { background: rgba(255,255,255,.03); }
.table-wrap td:first-child { font-weight: 600; }

/* ==== Callout ==== */
.lesson-content blockquote {
  margin: .9em 0; padding: 10px 14px; border-radius: 8px; border-left: 4px solid var(--red);
  background: var(--red-soft);
}
.lesson-content blockquote p { margin: 0; }
.lesson-content blockquote.callout-blue { border-left-color: var(--blue); background: var(--blue-soft); }
.lesson-content blockquote.callout-amber { border-left-color: var(--amber); background: var(--amber-soft); }
.lesson-content blockquote.callout-green { border-left-color: var(--green); background: var(--green-soft); }

/* ==== 標誌圖鑑 ==== */
.sign-gallery { margin-top: 1.8em; border-top: 2px dashed var(--line); padding-top: 1.2em; }
.gallery-title { border-left: 4px solid var(--red); padding-left: 12px; }
.gallery-sub { color: var(--text-soft); font-size: .88rem; }
.gallery-group { margin: 1.2em 0; }
.gallery-group-title { font-size: .86rem; color: var(--text-soft); margin: 0 0 .6em; }
.sign-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(128px, 1fr)); gap: 10px;
}
.sign-card {
  position: relative; margin: 0; background: var(--card);
  border: 1px solid var(--line); border-radius: 10px; padding: 12px 8px 8px;
  text-align: center; transition: transform .15s, box-shadow .15s;
}
.sign-card:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.sign-card img, .sign-card svg { width: 84px; height: 84px; display: block; margin: 0 auto 6px; object-fit: contain; }
.sign-card img.mirror, .pictogram img.mirror { transform: scaleX(-1); }
.sign-card figcaption { font-size: .74rem; color: var(--text-soft); line-height: 1.35; }
.sign-badge {
  position: absolute; top: 6px; right: 6px; background: var(--red); color: #fff;
  font-size: .62rem; padding: 1px 7px; border-radius: 9px; font-weight: 700;
}
.pictogram-row {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  background: var(--blue-soft); border: 1px solid rgba(0,87,184,.18);
  border-radius: 10px; padding: 12px 16px; margin: .9em 0;
}
.pictogram { text-align: center; }
.pictogram img, .pictogram svg { width: 62px; height: 62px; display: block; margin: 0 auto 4px; }
.pictogram span { font-size: .72rem; color: var(--text-soft); }
.pictogram-note { font-size: .84rem; margin: 0; flex: 1; min-width: 200px; }

/* ==== 選擇題庫卡片 ==== */
.mc-q {
  margin: .8em 0; padding: 10px 14px; border-radius: 9px;
  border: 1px solid var(--line); border-left: 3px solid var(--blue);
}
.mc-text { font-weight: 700; margin: 0 0 .4em; }
.mc-opts { list-style: none; margin: 0; padding: 0; }
.mc-opts li { padding: 2px 0 2px 22px; position: relative; }
.mc-opts li::before { content: "○"; position: absolute; left: 2px; color: var(--text-soft); }
.mc-opts li.ok { color: var(--green); font-weight: 700; }
.mc-opts li.ok::before { content: "✔"; color: var(--green); }

.sidebar-quick {
  display: block; margin: 0 0 12px; padding: 9px 12px; border-radius: 8px;
  background: rgba(200,16,46,.16); border: 1px dashed rgba(255,139,147,.4);
  color: #FFC9CE; text-decoration: none; font-size: .85rem; font-weight: 600;
  text-align: center; letter-spacing: .02em;
}
.sidebar-quick:hover { background: rgba(200,16,46,.3); color: #fff; }

/* ==== 互動模擬試 ==== */
.quiz-wrap { padding: 0 22px 10px; }
.quiz-wrap .lesson { margin: 0 auto 18px; }
.quiz-sub { color: var(--text-soft); font-size: .85rem; }
.quiz-controls {
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
  margin: .9em 0; padding: 12px 14px; background: var(--blue-soft);
  border: 1px solid rgba(0,87,184,.15); border-radius: 10px;
}
.quiz-controls label {
  font-size: .78rem; color: var(--text-soft); display: flex;
  align-items: center; gap: 6px;
}
.quiz-controls select {
  font-family: var(--sans); font-size: .82rem; padding: 5px 8px;
  border: 1px solid var(--line); border-radius: 7px; background: var(--card); color: var(--text);
}
.quiz-controls button {
  font-family: var(--sans); font-size: .84rem; cursor: pointer;
  background: var(--red); color: #fff; border: none; border-radius: 7px; padding: 6px 16px;
  font-weight: 700;
}
.quiz-controls button:hover { filter: brightness(1.12); }
.quiz-controls button#quiz-reset { background: var(--card); color: var(--text-soft); border: 1px solid var(--line); font-weight: 400; }
.quiz-controls .quiz-newfirst { cursor: pointer; user-select: none; white-space: nowrap; }
.quiz-controls .quiz-newfirst input { accent-color: var(--red); }
.quiz-seen-count { font-family: var(--mono); font-size: .72rem; color: var(--text-soft); background: var(--card); border: 1px solid var(--line); padding: 4px 9px; border-radius: 7px; }
.quiz-status { font-family: var(--mono); font-size: .8rem; color: var(--text-soft); margin: .8em 0 .4em; min-height: 1.2em; }
.quiz-idle { color: var(--text-soft); text-align: center; padding: 30px 0; }
.quiz-q {
  font-size: 1.02rem; font-weight: 700; margin: .4em 0 .8em; line-height: 1.6;
}
.quiz-q .q-tag {
  font-family: var(--mono); font-size: .68rem; color: var(--red); font-weight: 700;
  background: var(--red-soft); border: 1px solid rgba(200,16,46,.25);
  padding: 1px 8px; border-radius: 5px; margin-right: 8px; vertical-align: 2px;
}
.quiz-options { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
@media (max-width: 640px) { .quiz-options { grid-template-columns: 1fr; } }
.quiz-opt {
  font-family: var(--sans); font-size: .9rem; text-align: left; cursor: pointer;
  background: var(--card); border: 1.5px solid var(--line); border-radius: 9px;
  padding: 10px 14px; color: var(--text); line-height: 1.5;
  transition: border-color .12s, transform .12s;
}
.quiz-opt:hover:not(:disabled) { border-color: var(--blue); transform: translateY(-1px); }
.quiz-opt:disabled { cursor: default; }
.quiz-opt.correct { border-color: var(--green); background: var(--green-soft); font-weight: 700; }
.quiz-opt.wrong { border-color: var(--red); background: var(--red-soft); }
.quiz-opt .opt-tag {
  font-family: var(--mono); font-size: .7rem; color: var(--text-soft); margin-right: 8px;
}
.quiz-feedback { margin: .9em 0; font-size: .9rem; min-height: 1.4em; }
.quiz-feedback.ok { color: var(--green); font-weight: 700; }
.quiz-feedback.no { color: var(--red); font-weight: 700; }
.quiz-next {
  font-family: var(--sans); font-size: .88rem; cursor: pointer;
  background: var(--ink); color: #fff; border: none; border-radius: 8px; padding: 8px 22px;
}
.quiz-next:hover { background: var(--red); }
.quiz-end { text-align: center; padding: 26px 0; }
.quiz-end .score-big { font-family: var(--mono); font-size: 2.2rem; font-weight: 700; color: var(--red); }
.quiz-end p { color: var(--text-soft); margin: .3em 0; }
.quiz-wrong { margin-top: 1.2em; }
.quiz-wrong h4 { font-size: .85rem; color: var(--text-soft); margin: 0 0 .5em; }
.quiz-wrong ul { list-style: none; padding: 0; margin: 0; }
.quiz-wrong li {
  font-size: .8rem; padding: 7px 10px; margin: 4px 0; border-radius: 7px;
  background: var(--red-soft); border: 1px solid rgba(200,16,46,.15); line-height: 1.6;
}
.quiz-wrong li b { color: var(--red); }

/* ==== 官方文件下載 ==== */
.downloads { padding: 0 22px 10px; }
.downloads-card { margin: 0 auto 18px; }
.download-list { list-style: none; padding: 0; margin: .6em 0; }
.download-list li {
  display: flex; justify-content: space-between; gap: 10px;
  padding: 9px 0; border-bottom: 1px dashed var(--line);
}
.download-list li:last-child { border-bottom: none; }
.download-list a { color: var(--blue); text-decoration: none; font-weight: 600; }
.download-list a:hover { color: var(--red); }
.download-list span {
  color: var(--text-soft); font-family: var(--mono); font-size: .75rem; white-space: nowrap;
}
.dl-note { font-size: .8rem; color: var(--text-soft); margin: .4em 0 0; }

/* ==== 地圖連結 & modal ==== */
.lesson-content .map-link {
  color: inherit; cursor: pointer;
  border-bottom: 1px dashed var(--blue); text-decoration: none;
  transition: color .15s, border-color .15s;
}
.lesson-content .map-link:hover { color: var(--red); border-bottom-color: var(--red); }
.route-map {
  font-family: var(--mono); font-size: .74rem; cursor: pointer;
  background: var(--blue-soft); color: var(--blue);
  border: 1px solid rgba(0,87,184,.25); border-radius: 6px; padding: 2px 8px;
  white-space: nowrap;
}
.route-map:hover { background: var(--blue); color: #fff; }
.map-modal { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; }
.map-modal[hidden] { display: none; }
.map-modal-backdrop { position: absolute; inset: 0; background: rgba(10,16,26,.6); }
.map-modal-card {
  position: relative; width: min(760px, 94vw); background: var(--card);
  border-radius: 14px; box-shadow: 0 24px 60px rgba(0,0,0,.45); overflow: hidden;
  display: flex; flex-direction: column;
}
.map-modal-head {
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
  padding: 10px 16px; border-bottom: 1px solid var(--line); flex-wrap: wrap;
}
.map-modal-head .title { font-weight: 700; font-size: .92rem; }
.map-modal-actions { display: flex; align-items: center; gap: 12px; }
.map-modal-actions a { color: var(--blue); font-size: .78rem; }
.map-modal-actions button {
  background: none; border: 1px solid var(--line); color: var(--text-soft);
  border-radius: 7px; padding: 2px 9px; cursor: pointer; font-size: .9rem;
}
.map-modal-actions button:hover { color: var(--red); border-color: var(--red); }
.map-modal-frame { width: 100%; height: 62vh; border: none; background: var(--paper); }

/* ==== 其他 ==== */
.no-results {
  display: none; text-align: center; color: var(--text-soft);
  padding: 40px 0; font-size: .95rem;
}
.back-top {
  position: fixed; right: 22px; bottom: 22px; z-index: 30;
  background: var(--red); color: #fff; border: none; border-radius: 50%;
  width: 42px; height: 42px; font-size: 1.1rem; cursor: pointer;
  box-shadow: 0 4px 14px rgba(200,16,46,.4); display: none;
}
.hidden { display: none !important; }
.footer {
  text-align: center; padding: 10px 0 36px; color: var(--text-soft);
  font-family: var(--mono); font-size: .7rem;
}

/* ==== 流動版 ==== */
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0; z-index: 50; width: 280px;
    transform: translateX(-100%); transition: transform .22s;
  }
  .sidebar.open { transform: translateX(0); }
  .topbar { display: flex; }
  .overlay {
    position: fixed; inset: 0; background: rgba(10,16,26,.55); z-index: 45; display: none;
  }
  .overlay.show { display: block; }
  .hero { padding-top: 14px; }
  .welcome { padding: 20px 14px 18px; }
  .lessons { padding: 12px 10px 60px; }
  .lesson-content { padding: 14px 14px 20px; }
}

/* ==== 列印 ==== */
@media print {
  .sidebar, .topbar, .toolbar, .back-top, .footer { display: none !important; }
  .layout { grid-template-columns: 1fr; }
  .lesson { box-shadow: none; border: 1px solid #ccc; page-break-inside: avoid; }
  .lesson > summary { border-bottom: 1px solid #ccc; }
  .lesson-content { padding: 10px 12px; }
  .table-wrap { overflow: visible; }
  .table-wrap th { background: #eee !important; color: #000 !important; }
  body { background: #fff; }
}
"""

JS = """
(function () {
  "use strict";
  var root = document.documentElement;

  /* ---- 深淺模式 ---- */
  function applyTheme(t) {
    root.setAttribute("data-theme", t);
    localStorage.setItem("driwe-theme", t);
    document.getElementById("theme-btn").textContent = (t === "dark") ? "☀️ 淺色" : "🌙 深色";
  }
  var saved = localStorage.getItem("driwe-theme");
  applyTheme(saved || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  document.getElementById("theme-btn").addEventListener("click", function () {
    applyTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
  });

  /* ---- 側邊欄（流動版） ---- */
  var sidebar = document.getElementById("sidebar");
  var overlay = document.getElementById("overlay");
  function closeSidebar() { sidebar.classList.remove("open"); overlay.classList.remove("show"); }
  document.getElementById("hamburger").addEventListener("click", function () {
    sidebar.classList.toggle("open"); overlay.classList.toggle("show");
  });
  overlay.addEventListener("click", closeSidebar);
  sidebar.addEventListener("click", function (e) {
    if (e.target.tagName === "A") closeSidebar();
  });

  /* ---- 全部展開/收合 ---- */
  var lessons = document.querySelectorAll(".lesson");
  document.getElementById("btn-open-all").addEventListener("click", function () {
    lessons.forEach(function (l) { l.open = true; });
  });
  document.getElementById("btn-close-all").addEventListener("click", function () {
    lessons.forEach(function (l) { l.open = false; });
  });

  /* ---- 搜尋 ---- */
  var search = document.getElementById("search");
  var tocLinks = document.querySelectorAll(".toc li a");
  var noResults = document.getElementById("no-results");
  search.addEventListener("input", function () {
    var q = search.value.trim().toLowerCase();
    var visible = 0;
    lessons.forEach(function (lesson) {
      var match = !q || lesson.textContent.toLowerCase().indexOf(q) !== -1;
      lesson.classList.toggle("hidden", !match);
      if (match && q) lesson.open = true;
      if (match) visible++;
    });
    tocLinks.forEach(function (a) {
      a.classList.toggle("hidden", q && a.textContent.toLowerCase().indexOf(q) === -1);
    });
    noResults.style.display = (q && visible === 0) ? "block" : "none";
  });

  /* ---- TOC 高亮（scrollspy） ---- */
  var heads = document.querySelectorAll(".lesson-content h2, .lesson-content h3");
  var map = {};
  tocLinks.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
  var spy = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      var a = map[en.target.id];
      if (a && en.isIntersecting) {
        tocLinks.forEach(function (x) { x.classList.remove("active"); });
        a.classList.add("active");
      }
    });
  }, { rootMargin: "0px 0px -70% 0px" });
  heads.forEach(function (h) { spy.observe(h); });

  /* ---- 回到頂部 ---- */
  var backTop = document.getElementById("back-top");
  window.addEventListener("scroll", function () {
    backTop.style.display = (window.scrollY > 600) ? "block" : "none";
  }, { passive: true });
  backTop.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  /* ---- 地圖 modal ---- */
  var mapModal = document.getElementById("map-modal");
  var mapFrame = document.getElementById("map-modal-frame");
  var mapTitle = document.getElementById("map-modal-title");
  var mapExt = document.getElementById("map-modal-ext");
  function closeMap() { mapModal.hidden = true; mapFrame.src = "about:blank"; }
  document.getElementById("map-modal-close").addEventListener("click", closeMap);
  document.getElementById("map-modal-backdrop").addEventListener("click", closeMap);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !mapModal.hidden) closeMap();
  });
  function showPlace(q, label) {
    mapTitle.textContent = "📍 " + label;
    mapFrame.src = "https://maps.google.com/maps?q=" + encodeURIComponent(q) + "&output=embed&hl=zh-TW&z=15";
    mapExt.href = "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(q);
    mapModal.hidden = false;
  }
  function showRoute(from, to) {
    mapTitle.textContent = "🚕 " + from + " → " + to;
    mapFrame.src = "https://maps.google.com/maps?saddr=" + encodeURIComponent(from) +
                   "&daddr=" + encodeURIComponent(to) + "&output=embed&hl=zh-TW";
    mapExt.href = "https://www.google.com/maps/dir/?api=1&origin=" + encodeURIComponent(from) +
                  "&destination=" + encodeURIComponent(to);
    mapModal.hidden = false;
  }
  document.addEventListener("click", function (e) {
    var link = e.target.closest(".map-link");
    if (link) {
      e.preventDefault();
      showPlace(link.dataset.q, link.textContent.trim());
      return;
    }
    var btn = e.target.closest(".route-map");
    if (btn) {
      e.preventDefault();
      showRoute(btn.dataset.from, btn.dataset.to);
    }
  });

  /* ---- 互動模擬試 ---- */
  (function () {
    var bank = JSON.parse(document.getElementById("quiz-bank").textContent);
    var qzBody = document.getElementById("quiz-body");
    var qzStatus = document.getElementById("quiz-status");
    var qzWrong = document.getElementById("quiz-wrong");
    var modeSel = document.getElementById("quiz-mode");
    var catSel = document.getElementById("quiz-cat");
    var orderSel = document.getElementById("quiz-order");
    var nSel = document.getElementById("quiz-n");
    var newFirstSel = document.getElementById("quiz-new-first");
    var wrongFirstSel = document.getElementById("quiz-wrong-first");
    var seenCountEl = document.getElementById("quiz-seen-count");
    var st = { questions: [], i: 0, correct: 0, wrong: [] };

    function esc(s) {
      return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
    function shuffle(arr) {
      var a = arr.slice();
      for (var i = a.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var t = a[i]; a[i] = a[j]; a[j] = t;
      }
      return a;
    }
    function uniq(arr) {
      var seen = {};
      return arr.filter(function (v) {
        if (seen[v]) return false;
        seen[v] = true; return true;
      });
    }
    /* 未答過／曾答錯優先：答題狀態記喺 localStorage（1=答啱過 2=答錯過，答啱後解除答錯標記），抽題時按優先排序 */
    var SEEN_KEY = "driwe-quiz-seen";
    var NEWFIRST_KEY = "driwe-quiz-newfirst";
    var WRONGFIRST_KEY = "driwe-quiz-wrongfirst";
    function loadSeen() {
      try { return JSON.parse(localStorage.getItem(SEEN_KEY)) || {}; }
      catch (e) { return {}; }
    }
    function saveSeen(s) { localStorage.setItem(SEEN_KEY, JSON.stringify(s)); }
    function qKey(q) {
      if (q.type === "place") return "p:" + q.n;
      if (q.type === "route") return "r:" + q.n;
      return "m:" + q.q;
    }
    function placeQ(p) { return { type: "place", q: p.name, a: p.loc, tag: p.cat, n: p.n }; }
    function routeQ(r) { return { type: "route", q: r.s + " → " + r.d, a: r.r, tag: "路線", n: r.n }; }
    function mcQ(m) {
      var ok = null;
      m.opts.forEach(function (o) { if (o.ok) ok = o.t; });
      return { type: "mc", q: m.q, a: ok, tag: m.cat, opts: m.opts.map(function (o) { return o.t; }) };
    }

    function fillCats() {
      var mode = modeSel.value;
      var list = [];
      if (mode === "place") list = bank.cats;
      else if (mode === "mca") list = bank.mcA.map(function (m) { return m.cat; });
      else if (mode === "mcb") list = bank.mcB.map(function (m) { return m.cat; });
      catSel.innerHTML = '<option value="">全部</option>' + uniq(list).map(function (c) {
        return '<option value="' + esc(c) + '">' + esc(c) + "</option>";
      }).join("");
      catSel.style.display = (mode === "route" || mode === "mixed") ? "none" : "";
    }

    function buildPool() {
      var mode = modeSel.value, cat = catSel.value, qs = [];
      if (mode === "place") {
        bank.places.forEach(function (p) {
          if (!cat || p.cat === cat) qs.push(placeQ(p));
        });
      } else if (mode === "route") {
        bank.routes.forEach(function (r) { qs.push(routeQ(r)); });
      } else if (mode === "mca") {
        bank.mcA.forEach(function (m) {
          if (!cat || m.cat === cat) qs.push(mcQ(m));
        });
      } else if (mode === "mcb") {
        bank.mcB.forEach(function (m) {
          if (!cat || m.cat === cat) qs.push(mcQ(m));
        });
      } else {
        shuffle(bank.mcA).slice(0, 8).forEach(function (m) { qs.push(mcQ(m)); });
        shuffle(bank.places).slice(0, 6).forEach(function (p) { qs.push(placeQ(p)); });
        shuffle(bank.routes).slice(0, 1).forEach(function (r) { qs.push(routeQ(r)); });
        shuffle(bank.mcB).slice(0, 5).forEach(function (m) { qs.push(mcQ(m)); });
        qs = shuffle(qs);
      }
      if (orderSel.value === "random" && mode !== "mixed") qs = shuffle(qs);
      return qs;
    }

    function buildQuestions() {
      var qs = buildPool();
      if (newFirstSel.checked || wrongFirstSel.checked) {
        var seen = loadSeen();
        var groups = [[], [], []];
        qs.forEach(function (q) {
          var s = seen[qKey(q)];
          var isW = s === 2, isU = !s;
          var r;
          if (newFirstSel.checked && wrongFirstSel.checked) r = isW ? 0 : isU ? 1 : 2;
          else if (wrongFirstSel.checked) r = isW ? 0 : 1;
          else r = isU ? 0 : 1;
          groups[r].push(q);
        });
        qs = groups[0].concat(groups[1], groups[2]);
      }
      var n = parseInt(nSel.value, 10);
      if (n > 0 && qs.length > n) qs = qs.slice(0, n);
      return qs;
    }

    function updateSeenCount() {
      var seen = loadSeen();
      var pool = buildPool();
      var unseen = pool.filter(function (q) { return !seen[qKey(q)]; }).length;
      var wrong = pool.filter(function (q) { return seen[qKey(q)] === 2; }).length;
      seenCountEl.textContent = pool.length
        ? "曾答錯 " + wrong + " ・ 未答過 " + unseen + " / " + pool.length
        : "";
    }

    function start() {
      st.questions = buildQuestions();
      if (!st.questions.length) {
        qzBody.innerHTML = '<p class="quiz-idle">呢個分類暫時冇題目～</p>';
        qzStatus.textContent = "";
        return;
      }
      st.i = 0; st.correct = 0; st.wrong = [];
      qzWrong.innerHTML = "";
      render();
    }

    function render() {
      var q = st.questions[st.i];
      var pool, opts;
      if (q.type === "place") {
        pool = uniq(bank.places.map(function (p) { return p.loc; })).filter(function (l) { return l !== q.a; });
        opts = shuffle([q.a].concat(shuffle(pool).slice(0, 3)));
      } else if (q.type === "mc") {
        opts = shuffle(q.opts.slice());
      } else {
        pool = uniq(bank.routes.map(function (r) { return r.r; })).filter(function (r) { return r !== q.a; });
        opts = shuffle([q.a].concat(shuffle(pool).slice(0, 2)));
      }
      qzStatus.textContent = "第 " + (st.i + 1) + " / " + st.questions.length +
        " 題 ・ 答對 " + st.correct + " ・ 答錯 " + st.wrong.length;
      var qtext = q.type === "route" ? "「" + esc(q.q) + "」最直接可行嘅路線係？"
                 : q.type === "place" ? "「" + esc(q.q) + "」喺邊度？"
                 : esc(q.q);
      qzBody.innerHTML =
        '<p class="quiz-q"><span class="q-tag">' + esc(q.tag) + "</span>" + qtext + "</p>" +
        '<div class="quiz-options">' + opts.map(function (o, i) {
          return '<button class="quiz-opt" data-v="' + esc(o) + '"><span class="opt-tag">' +
                 String.fromCharCode(65 + i) + "</span>" + esc(o) + "</button>";
        }).join("") + "</div>" +
        '<p class="quiz-feedback" id="qz-fb"></p>' +
        '<button class="quiz-next" id="qz-next" hidden>下一題 ▶</button>';
      qzBody.querySelectorAll(".quiz-opt").forEach(function (b) {
        b.addEventListener("click", function () { answer(b); });
      });
      document.getElementById("qz-next").addEventListener("click", next);
    }

    function answer(btn) {
      var q = st.questions[st.i];
      var picked = btn.dataset.v;
      var seen = loadSeen();
      seen[qKey(q)] = picked === q.a ? 1 : 2;
      saveSeen(seen);
      updateSeenCount();
      var fb = document.getElementById("qz-fb");
      qzBody.querySelectorAll(".quiz-opt").forEach(function (b) {
        b.disabled = true;
        if (b.dataset.v === q.a) b.classList.add("correct");
        else if (b === btn) b.classList.add("wrong");
      });
      if (picked === q.a) {
        st.correct++;
        fb.textContent = "✅ 啱！";
        fb.className = "quiz-feedback ok";
      } else {
        st.wrong.push({ q: q.q, a: q.a, picked: picked });
        fb.textContent = "❌ 錯！正確答案：" + q.a;
        fb.className = "quiz-feedback no";
      }
      qzStatus.textContent = "第 " + (st.i + 1) + " / " + st.questions.length +
        " 題 ・ 答對 " + st.correct + " ・ 答錯 " + st.wrong.length;
      document.getElementById("qz-next").hidden = false;
    }

    function next() {
      st.i++;
      if (st.i >= st.questions.length) { end(); return; }
      render();
    }

    function end() {
      var pct = Math.round(st.correct * 100 / st.questions.length);
      qzStatus.textContent = "完成！";
      qzBody.innerHTML = '<div class="quiz-end"><div class="score-big">' + pct + "%</div>" +
        "<p>答對 " + st.correct + " / " + st.questions.length + " 題</p>" +
        '<button class="quiz-next" id="qz-again">↺ 再來一次</button></div>';
      document.getElementById("qz-again").addEventListener("click", start);
      if (st.wrong.length) {
        qzWrong.innerHTML = "<h4>❌ 錯題重溫（" + st.wrong.length + "題）</h4><ul>" +
          st.wrong.map(function (w) {
            return "<li>" + esc(w.q) + " → 正確：<b>" + esc(w.a) + "</b>（你答：" + esc(w.picked) + "）</li>";
          }).join("") + "</ul>";
      } else {
        qzWrong.innerHTML = "";
      }
    }

    document.getElementById("quiz-start").addEventListener("click", start);
    document.getElementById("quiz-reset").addEventListener("click", function () {
      st.questions = []; st.i = 0; st.correct = 0; st.wrong = [];
      qzBody.innerHTML = '<p class="quiz-idle">撳「▶ 開始」出題～</p>';
      qzStatus.textContent = "↺ 已重設（連「答過」紀錄一併清除）";
      qzWrong.innerHTML = "";
      localStorage.removeItem(SEEN_KEY);
      updateSeenCount();
    });
    modeSel.addEventListener("change", function () { fillCats(); updateSeenCount(); });
    catSel.addEventListener("change", updateSeenCount);
    newFirstSel.addEventListener("change", function () {
      localStorage.setItem(NEWFIRST_KEY, newFirstSel.checked ? "1" : "0");
    });
    if (localStorage.getItem(NEWFIRST_KEY) === "0") newFirstSel.checked = false;
    wrongFirstSel.addEventListener("change", function () {
      localStorage.setItem(WRONGFIRST_KEY, wrongFirstSel.checked ? "1" : "0");
    });
    if (localStorage.getItem(WRONGFIRST_KEY) === "0") wrongFirstSel.checked = false;
    fillCats();
    updateSeenCount();
  })();

  /* ---- 列印前自動展開 ---- */
  window.addEventListener("beforeprint", function () {
    lessons.forEach(function (l) { l.open = true; });
  });
})();
"""

# ---------------------------------------------------------------------------
# 5. 組裝
# ---------------------------------------------------------------------------
def build():
    t0 = datetime.datetime.now()
    docs, toc_groups = [], {}
    for idx, path in enumerate(FILES, 1):
        doc = convert_file(idx, path)
        docs.append((idx, path, doc))
        group = GROUP_OVERRIDE.get(path) or {
            "notes": "課程", "exams": "練習"}.get(path.split("/")[0], "課程計劃")
        toc_groups.setdefault(group, []).append((idx, doc))

    # 側邊欄 TOC
    toc_parts = []
    for group, entries in toc_groups.items():
        toc_parts.append(f'<div class="toc-group">{group}</div>')
        for idx, doc in entries:
            toc_parts.append('<details>')
            toc_parts.append(
                f'<summary><span class="eyebrow">{doc["eyebrow"]}</span>'
                f'<span>{doc["title"]}</span></summary>')
            if doc["toc"]:
                toc_parts.append("<ul>")
                for level, text, hid, priv in doc["toc"]:
                    cls = ' class="sub"' if level == "h3" else ""
                    toc_parts.append(f'<li{cls}><a href="#{hid}">{text}</a></li>')
                toc_parts.append("</ul>")
            toc_parts.append("</details>")
    toc_html = "\n".join(toc_parts)

    # 課程區
    lesson_parts = []
    for idx, path, doc in docs:
        if path == "exams/quiz-bank-mc.md":
            body = render_mc_card()
        else:
            body = doc["html"]
            body = wrap_tables(body)
            body = style_callouts(body)
            body = inline_imgs(body)
            body = enhance_bank(body, path)
        lesson_parts.append(
            f'<details class="lesson" id="l{idx}">'
            f'<summary><span class="eyebrow">{doc["eyebrow"]}</span>'
            f'<h1>{doc["title"]}</h1><span class="chev">▶</span></summary>'
            f'<div class="lesson-content">{body}</div></details>')
    lessons_html = "\n".join(lesson_parts)

    n_signs = (lessons_html.count("<svg")
               + lessons_html.count("data:image/png;base64,"))
    stamp = t0.strftime("%Y-%m-%d %H:%M")
    places, routes = parse_bank_md()
    quiz_html = build_quiz(places, routes)

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Driwe 溫習指南 — 的士及網約車綜合筆試</title>
<style>{CSS}</style>
</head>
<body>
<div class="overlay" id="overlay"></div>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="brand">
      <span class="taxi-badge">的士</span>
      <span class="brand-text"><strong>Driwe 溫習指南</strong>
      <small>的士及網約車綜合筆試</small></span>
    </div>
    <input class="search" id="search" type="search" placeholder="🔍 搜尋筆記內容…" aria-label="搜尋">
    <a class="sidebar-quick" href="#quiz-sec">📝 互動模擬試</a>
    <nav class="toc">{toc_html}</nav>
    <div class="sidebar-foot">💪 祝大家考試成功，一take過！</div>
  </aside>
  <div class="main">
    <div class="topbar">
      <button class="hamburger" id="hamburger" aria-label="開啟目錄">☰</button>
      <strong>Driwe 溫習指南</strong>
    </div>
    <div class="toolbar">
      <button id="btn-open-all">全部展開</button>
      <button id="btn-close-all">全部收合</button>
      <button id="theme-btn">🌙 深色</button>
    </div>
    <section class="hero">
      <div class="welcome">
        <div class="welcome-title">🚕 的士及網約車綜合筆試 <span class="taxi">免費溫習平台</span></div>
        <div class="welcome-sub">甲部 ≥25/30 ・ 乙部 ≥30/35 ・ 65題 ・ 45分鐘（電腦化選擇題）</div>
        <div class="welcome-greet">🎉 祝大家考試成功，一take過！</div>
      </div>
    </section>
    <div class="lessons">
{lessons_html}
      <div class="no-results" id="no-results">😕 搵唔到「<span id="no-results-q"></span>」，試下其他關鍵字啦～</div>
    </div>
{quiz_html}
    <section class="downloads">
      <div class="lesson downloads-card">
        <div class="lesson-content">
          <h2 id="dl-sec">📥 官方文件（運輸署網站）</h2>
          <ul class="download-list">
            <li><a href="https://www.td.gov.hk/filemanager/tc/content_5405/New%20Combined%20Written%20Test%20Booklet_C.pdf" target="_blank" rel="noopener">📕 合併筆試試題小冊子（地方＋路線官方題庫出處）</a><span>PDF ↗</span></li>
            <li><a href="https://www.td.gov.hk/filemanager/tc/content_5405/Guide%20to%20Taxi%20and%20Ride-hailing%20Vehicle%20Combined%20Written%20Test_TC_clean_r_20260803_r2_20260806.pdf" target="_blank" rel="noopener">📋 考試指引（含模擬試題）</a><span>PDF ↗</span></li>
            <li><a href="https://www.td.gov.hk/filemanager/tc/content_172/road_users_code_2020_chi.pdf" target="_blank" rel="noopener">📘 道路使用者守則 2020（交通標誌官方圖源）</a><span>PDF ↗</span></li>
            <li><a href="https://www.td.gov.hk/tc/public_services/licences_and_permits/driving_test/tarhvcwt/index.html" target="_blank" rel="noopener">🏛 運輸署官方專頁 — 的士及出租汽車合併筆試</a><span>網頁 ↗</span></li>
          </ul>
          <p class="dl-note">💡 以上文件版權屬運輸署所有，全部連結至官方網站；如連結失效，請到運輸署專頁搜尋下載。</p>
        </div>
      </div>
    </section>
    <div class="footer">
      <p>⚠️ 本網站為非官方溫習平台，內容僅供參考，一切以運輸署官方公布為準。</p>
      <p>📷 交通標誌圖片版權屬香港特別行政區政府運輸署所有。部分題目來源已於內文註明。</p>
      <p>📚 筆記及程式碼以 <a href="https://github.com/eeworm/hk-taxi-written-test/blob/main/LICENSE" target="_blank" rel="noopener">CC BY-NC-SA 4.0</a> 授權共享（圖片除外）。</p>
      <p>🎉 祝大家考試成功，一take過！</p>
      <p>由 build-html.py 生成・{stamp}・{len(FILES)} 個檔案・{n_signs} 個標誌內嵌・完全離線</p>
    </div>
  </div>
</div>
<button class="back-top" id="back-top" aria-label="回到頂部">↑</button>
<div class="map-modal" id="map-modal" hidden>
  <div class="map-modal-backdrop" id="map-modal-backdrop"></div>
  <div class="map-modal-card">
    <div class="map-modal-head">
      <span class="title" id="map-modal-title">地圖</span>
      <div class="map-modal-actions">
        <a id="map-modal-ext" href="#" target="_blank" rel="noopener">喺Google Maps開啟 ↗</a>
        <button id="map-modal-close" aria-label="關閉地圖">✕</button>
      </div>
    </div>
    <iframe class="map-modal-frame" id="map-modal-frame" src="about:blank"
            loading="lazy" title="Google地圖"></iframe>
  </div>
</div>
<script>{JS}</script>
</body>
</html>"""

    # no-results 關鍵字回顯
    html = html.replace(
        "😕 搵唔到「<span id=\"no-results-q\"></span>」",
        "😕 搵唔到相關內容")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(OUT_PATH)
    print(f"✅ 生成完成：{OUT_PATH}")
    print(f"   檔案數：{len(FILES)} ・ 標誌內嵌：{n_signs} ・ 大小：{size:,} bytes")
    return html


if __name__ == "__main__":
    build()
