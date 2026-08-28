#!/usr/bin/env python3
"""
build_fonts.py — 把中文字型切成小塊，讓瀏覽器只下載頁面用得到的部分。

用法：
    pip install fonttools brotli
    python3 build_fonts.py

它會做的事：
  1. 讀取 index.html，抓出頁面上所有文字
  2. 把「已經用到的字」做成第 0 塊（最優先載入，很小）
  3. 剩下的字依編碼順序切成多塊
  4. 每塊輸出成 .woff2，並產生 fonts/fonts.css

之後你在 HTML 加新文字，如果那些字不在第 0 塊裡，
瀏覽器會自動去抓對應的那一塊，不用重跑這個腳本。
內容大改（或字型改版）時再重跑一次，第 0 塊會重新最佳化。
"""

import os
import re
import subprocess
from html.parser import HTMLParser

# ---------- 設定 ----------
HTML_FILE = "index.html"
OUT_DIR = "fonts"
CHUNK_SIZE = 600          # 每一塊放幾個字，數字越小檔案越碎但下載越精準

FONTS = [
    {
        "file": "fontwork/Iansui-Regular.ttf",
        "family": "Iansui",
        "slug": "iansui",
        "priority": "all",          # 內文字型：整頁的字都優先
    },
    {
        "file": "fontwork/ChenYuluoyan-2.0-Thin.ttf",
        "family": "ChenYuluoyan",
        "slug": "chenyuluoyan",
        "priority": "quote",        # 引言字型：只有引言的字優先
    },
]


# ---------- 從 HTML 抓文字 ----------
class TextGrabber(HTMLParser):
    def __init__(self):
        super().__init__()
        self.all_text = []
        self.quote_text = []
        self.depth_quote = 0
        self.quote_tags = []
        self.skip = 0

    # 這些 class 在 style.css 裡被指定成手寫體，
    # 改 CSS 的字型歸屬時記得同步更新這份清單。
    QUOTE_CLASSES = {
        "quote-font", "pull-quote", "panel-quote",
        "hero-quote", "card-text",
    }

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        classes = set(d.get("class", "").split())
        if tag == "blockquote" or (classes & self.QUOTE_CLASSES):
            self.depth_quote += 1
            self.quote_tags.append(tag)
        else:
            self.quote_tags.append(None)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        # 依開啟順序回退，才不會被巢狀標籤弄亂
        while self.quote_tags:
            opened = self.quote_tags.pop()
            if opened == tag:
                if self.depth_quote:
                    self.depth_quote -= 1
                break
            if opened is None:
                break

    def handle_data(self, data):
        if self.skip:
            return
        self.all_text.append(data)
        if self.depth_quote:
            self.quote_text.append(data)


def read_page_text(path):
    with open(path, encoding="utf-8") as fh:
        g = TextGrabber()
        g.feed(fh.read())
    clean = lambda parts: set(re.sub(r"\s", "", "".join(parts)))
    return clean(g.all_text), clean(g.quote_text)


# ---------- 把碼位壓成 unicode-range ----------
def to_unicode_range(codepoints):
    cps = sorted(codepoints)
    parts, start, prev = [], cps[0], cps[0]
    for cp in cps[1:]:
        if cp == prev + 1:
            prev = cp
            continue
        parts.append(f"U+{start:X}" if start == prev else f"U+{start:X}-{prev:X}")
        start = prev = cp
    parts.append(f"U+{start:X}" if start == prev else f"U+{start:X}-{prev:X}")
    return ", ".join(parts)


# ---------- 主流程 ----------
def main():
    from fontTools.ttLib import TTFont

    os.makedirs(OUT_DIR, exist_ok=True)
    all_text, quote_text = read_page_text(HTML_FILE)
    print(f"頁面共用到 {len(all_text)} 個不同的字元（引言 {len(quote_text)} 個）\n")

    css_blocks = []

    for spec in FONTS:
        font = TTFont(spec["file"], lazy=True)
        available = set(font.getBestCmap().keys())
        font.close()

        wanted = all_text if spec["priority"] == "all" else quote_text
        first = sorted({ord(c) for c in wanted} & available)
        rest = sorted(available - set(first))

        chunks = [first] + [rest[i:i + CHUNK_SIZE]
                            for i in range(0, len(rest), CHUNK_SIZE)]
        chunks = [c for c in chunks if c]

        print(f"{spec['family']}：{len(available)} 字 → {len(chunks)} 塊")

        for i, cps in enumerate(chunks):
            name = f"{spec['slug']}-{i}.woff2"
            out = os.path.join(OUT_DIR, name)
            subprocess.run([
                "pyftsubset", spec["file"],
                "--unicodes=" + ",".join(f"U+{c:X}" for c in cps),
                "--flavor=woff2",
                "--layout-features=",
                "--no-hinting",
                "--desubroutinize",
                "--output-file=" + out,
            ], check=True, stderr=subprocess.DEVNULL)

            kb = os.path.getsize(out) / 1024
            tag = "（頁面用字）" if i == 0 else ""
            print(f"    {name:28s} {kb:7.1f} KB  {len(cps):5d} 字 {tag}")

            css_blocks.append(
                "@font-face {\n"
                f'  font-family: "{spec["family"]}";\n'
                "  font-style: normal;\n"
                "  font-weight: 400;\n"
                "  font-display: swap;\n"
                f'  src: url("{name}") format("woff2");\n'
                f"  unicode-range: {to_unicode_range(cps)};\n"
                "}\n"
            )
        print()

    header = (
        "/* 由 build_fonts.py 自動產生，請勿手動編輯。\n"
        "   芫荽 Iansui — ButTaiwan，SIL OFL 1.1\n"
        "   辰宇落雁體 ChenYuluoyan — 王立宇、劉韋辰，SIL OFL 1.1 */\n\n"
    )
    with open(os.path.join(OUT_DIR, "fonts.css"), "w", encoding="utf-8") as fh:
        fh.write(header + "\n".join(css_blocks))

    total = sum(os.path.getsize(os.path.join(OUT_DIR, f))
                for f in os.listdir(OUT_DIR) if f.endswith(".woff2"))
    first_load = sum(os.path.getsize(os.path.join(OUT_DIR, f"{s['slug']}-0.woff2"))
                     for s in FONTS)
    print(f"全部切片共 {total/1024/1024:.1f} MB")
    print(f"但首次開頁只會下載 {first_load/1024:.0f} KB")


if __name__ == "__main__":
    main()
