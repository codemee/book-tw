"""mdbook-epub 產生 epub 之後的後處理。

用法：python postprocess.py <輸入.epub> <輸出.epub>   （需要 pygments）

- 章節語言標記改為 zh-TW
- 移除原書不合法的 HTML 註解
- Rust 程式碼：移除 mdBook 隱藏行、依語法重新斷行、Pygments 語法上色
- 檔名＋程式碼＋範例說明合成一個區塊；有標題的引用區塊轉成說明框
"""
import html as htmllib
import re
import sys
import zipfile
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reflow import reflow  # noqa: E402
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

src, dst = sys.argv[1], sys.argv[2]

LANG_MAP = {"console": "console", "rust": "rust", "toml": "toml", "powershell": "powershell", "html": "html"}
formatter = HtmlFormatter(nowrap=True)
CODE_RE = re.compile(r'<pre><code class="language-([^"]*)">(.*?)</code></pre>', re.S)


# Noto Serif TC 的全形標點置中。ADE 會把「行內元素之前」那個標點的字寬縮成一半，
# 置中的字形就會和後面的粗體／程式碼重疊；包成 span 並補回半個字寬的 margin。
PUNCT_BEFORE_INLINE_RE = re.compile(r"([，。、；：！？）」』》〉])(?=<(?:code|strong|em|a|b|i)\b)")
LIST_TAG_RE =re.compile(r"<(/?)(ul|ol|li)\b[^>]*>")
BULLETS = ["●", "○", "■"]
# 整個項目只是一句被引號包住的文字時，引號是多餘的（例如 “Desktop Development with C++”）
QUOTED_ITEM_RE = re.compile(r'(<span class="bullet">[^<]</span>)[“"]([^“”"<]*)[”"](</li>)')
EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF]\s?")


def add_bullets(text):
    """無序清單的 <li> 前面加上自繪項目符號（閱讀器內建的圓點太小），巢狀層級換符號。"""
    stack = []

    def repl(m):
        closing, tag = m.group(1), m.group(2)
        if tag in ("ul", "ol"):
            if closing:
                if stack:
                    stack.pop()
            else:
                stack.append(tag)
            return m.group(0)
        if closing or not stack or stack[-1] != "ul":
            return m.group(0)
        level = min(stack.count("ul") - 1, len(BULLETS) - 1)
        return '<li class="bl"><span class="bullet">%s</span>' % BULLETS[level]

    text = LIST_TAG_RE.sub(repl, text)
    return QUOTED_ITEM_RE.sub(r"\1\2\3", text)


TABLE_RE =re.compile(r'<p><span class="caption">(.*?)</span></p>\s*(<table>.*?</table>)', re.S)
NOWRAP_LANGS ={"rust", "toml", "powershell", "cmd", "html"}
NOWRAP_RE = re.compile(r'<pre><code class="language-([^"]*)">')
CALLOUT_RE =re.compile(r"<blockquote>\s*<h([1-6])>(.*?)</h\1>(.*?)</blockquote>", re.S)


# 「檔名 + 程式碼 + 範例說明」合成一個整體；檔名與說明皆為選用，至少要有一個
LISTING_RE = re.compile(
    r'(?:<p><span class="filename">(?P<fn>.*?)</span></p>\s*)?'
    r"(?P<pre><pre>.*?</pre>)"
    r'(?:\s*<p><span class="caption">(?P<cap>.*?)</span></p>)?',
    re.S,
)


def wrap_listing(m):
    fn, cap = m.group("fn"), m.group("cap")
    if fn is None and cap is None:
        return m.group(0)
    parts = ['<div class="listing">']
    if fn is not None:
        parts.append('<div class="listing-filename">%s</div>' % fn)
    parts.append(m.group("pre"))
    if cap is not None:
        parts.append('<div class="listing-caption">%s</div>' % cap)
    parts.append("</div>")
    return "".join(parts)


HIDDEN_STATS = {"lines": 0, "blocks": 0, "emptied": 0}


def strip_hidden(code):
    """移除 mdBook 的隱藏行（"# " 開頭或單獨的 "#"）；"##" 開頭則還原成字面的 "#"。"""
    out, removed = [], 0
    for line in code.split("\n"):
        s = line.lstrip()
        if s == "#" or s.startswith("# "):
            removed += 1
            continue
        if s.startswith("##"):
            line = line.replace("##", "#", 1)
        out.append(line)
    if not removed:
        return code
    # 隱藏行拿掉後，連續空行縮成一行，並去掉頭尾空行
    cleaned = []
    for line in out:
        if line.strip() == "" and cleaned and cleaned[-1].strip() == "":
            continue
        cleaned.append(line)
    while cleaned and cleaned[0].strip() == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1].strip() == "":
        cleaned.pop()
    HIDDEN_STATS["lines"] += removed
    HIDDEN_STATS["blocks"] += 1
    if not cleaned:
        HIDDEN_STATS["emptied"] += 1
    return "\n".join(cleaned) + "\n"


def color_block(m):
    lang = m.group(1).split(",")[0]
    name = LANG_MAP.get(lang)
    if not name:
        return m.group(0)
    try:
        lexer = get_lexer_by_name(name)
    except ClassNotFound:
        return m.group(0)
    code = htmllib.unescape(m.group(2))
    if lang == "rust":
        code = strip_hidden(code)
    code = reflow(code, lang)
    out =highlight(code, lexer, formatter).rstrip("\n") + "\n"
    return '<pre><code class="language-%s">%s</code></pre>' % (m.group(1), out)


def token_css():
    rules = []
    for line in HtmlFormatter(style="default").get_style_defs("pre code").splitlines():
        if re.match(r"^pre code \.\w+", line) and ".hll" not in line and ".err" not in line:
            rules.append(line)
    return "\n/* 語法上色 */\n" + "\n".join(rules) + "\n"


with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
    names = ["mimetype"] + [n for n in zin.namelist() if n != "mimetype"]
    for n in names:
        data = zin.read(n)
        if n == "mimetype":
            zout.writestr(n, data, compress_type=zipfile.ZIP_STORED)
            continue
        if n.endswith((".html", ".xhtml")):
            text = data.decode("utf-8").replace('xml:lang="en" lang="en"', 'xml:lang="zh-TW" lang="zh-TW"')
            # 原書的 HTML 註解含有 "--release" 等字串，不是合法 XML 註解，直接移除
            text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
            # 以標題開頭的 blockquote 轉成「標題條 + 內容」的說明框
            text = CALLOUT_RE.sub(
                lambda m: '<div class="callout"><div class="callout-title">%s</div><div class="callout-body">%s</div></div>'
                % (m.group(2), m.group(3)),
                text,
            )
            # emoji 在多數閱讀器的內嵌字型中沒有字形，會變成空白，直接移除
            text = EMOJI_RE.sub("", text)
            text = PUNCT_BEFORE_INLINE_RE.sub(r'<span class="pn">\1</span>', text)
            text = add_bullets(text)
            text = CODE_RE.sub(color_block, text)
            # 程式碼（非終端輸出）不自動折行，避免折行後與語法混淆
            text = NOWRAP_RE.sub(
                lambda m: '<pre><code class="language-%s code-nowrap">' % m.group(1)
                if m.group(1).split(",")[0] in NOWRAP_LANGS
                else m.group(0),
                text,
            )
            text = LISTING_RE.sub(wrap_listing, text)
            # 「表格標題 + 表格」合成一個整體，標題條樣式與程式碼區塊相同
            text = TABLE_RE.sub(
                lambda m: '<div class="tablebox"><div class="tablebox-title">%s</div>%s</div>'
                % (m.group(1), m.group(2)),
                text,
            )
            # 圖片的說明（不屬於程式碼區塊、表格者）改成置中的說明列
            text = re.sub(
                r'<p><span class="caption">(.*?)</span></p>',
                r'<div class="caption-line">\1</div>',
                text,
                flags=re.S,
            )
            data = text.encode("utf-8")
        elif n.endswith("stylesheet.css"):
            data = (data.decode("utf-8") + token_css()).encode("utf-8")
        zout.writestr(n, data, compress_type=zipfile.ZIP_DEFLATED)

print('hidden lines removed:', HIDDEN_STATS)
