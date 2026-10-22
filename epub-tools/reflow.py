"""依語法把過寬的 Rust / TOML 程式碼行重新斷行。

- 整行註解：依寬度拆成多行相同前綴的註解（中文可在字間斷行，並避免行首出現標點）。
- 行尾註解：移到該行上方，成為獨立的註解行。
- 程式碼：在字串之外的逗號後、方法鏈的「.」前、&& / || / + 前、「= 」後斷行，
  續行多縮排 4 個空格。找不到合適斷點（例如單一長字串）就維持原樣。
"""
import re
import unicodedata

LIMIT = 76
CLOSERS = set("，。、；：？！）」』》〉”’,.;:?!)]}")
OPENERS = set("（「『《〈“‘([{")


def width(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def is_cjk(c):
    return unicodedata.east_asian_width(c) in "WF"


def find_comment(s, marker="//"):
    """回傳字串、字元常值之外第一個註解起點；沒有則 None。"""
    i, n = 0, len(s)
    in_str = False
    while i < n:
        c = s[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "'":
                if i + 2 < n and s[i + 2] == "'":
                    i += 3
                    continue
                if i + 3 < n and s[i + 1] == "\\" and s[i + 3] == "'":
                    i += 4
                    continue
            elif s.startswith(marker, i):
                return i
        i += 1
    return None


def wrap_text(text, avail):
    """把一段（可含中英文）文字切成每行寬度不超過 avail 的多行。"""
    text = text.strip()
    lines = []
    while width(text) > avail:
        best = None
        w = 0
        cands = []  # (位置, 斷點前寬度)
        for i in range(1, len(text)):
            w += 2 if is_cjk(text[i - 1]) else 1
            if w > avail:
                break
            prev, cur = text[i - 1], text[i]
            if cur in CLOSERS or prev in OPENERS:
                ok = False
            else:
                ok = prev == " " or is_cjk(prev) or is_cjk(cur)
            if ok:
                best = i
                cands.append((i, w))
        # 最後一行太短（孤字）時，改斷在接近中間處，讓兩行長度平均
        total = width(text)
        if best is not None and total <= 2 * avail and total - cands[-1][1] < 12:
            best = min(cands, key=lambda c: abs(c[1] - total / 2))[0]
        if best is None:
            # 沒有合適斷點：用寬度硬切（至少前進一個字元）
            w, best = 0, 1
            for i in range(1, len(text)):
                w += 2 if is_cjk(text[i - 1]) else 1
                if w > avail:
                    break
                best = i
        lines.append(text[:best].rstrip())
        text = text[best:].lstrip()
    if text:
        lines.append(text)
    return lines


def comment_lines(indent, hp, marker_text, body):
    """marker_text 例如 '// '、'/// '、'# '；body 為註解內文。"""
    prefix = hp + indent + marker_text
    avail = max(LIMIT - width(prefix), 20)
    return [prefix + chunk for chunk in wrap_text(body, avail)]


def break_candidates(s):
    """回傳可斷行的位置（斷在該位置之前），略過字串內部。"""
    cands = []
    i, n = 0, len(s)
    in_str = False
    while i < n:
        c = s[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
        elif c == "'":
            if i + 2 < n and s[i + 2] == "'":
                i += 3
                continue
            if i + 3 < n and s[i + 1] == "\\" and s[i + 3] == "'":
                i += 4
                continue
        elif c == "," and i + 1 < n and s[i + 1] == " ":
            cands.append(i + 2)
        elif c == "." and i > 0 and s[i - 1] in ")]}" and i + 1 < n and (s[i + 1].isalpha() or s[i + 1] == "_"):
            cands.append(i)
        elif c == " " and (s.startswith(" && ", i) or s.startswith(" || ", i) or s.startswith(" + ", i)):
            cands.append(i + 1)
        elif c == "=" and i + 1 < n and s[i + 1] == " " and i > 0 and s[i - 1] == " ":
            cands.append(i + 2)
        i += 1
    return cands


def reflow_code(hp, indent, text):
    cont = indent + "    "
    out = []
    cur = text
    first = True
    while True:
        lead = indent if first else cont
        line = hp + lead + cur
        if width(line) <= LIMIT:
            out.append(line)
            break
        cands = [c for c in break_candidates(cur) if 0 < c < len(cur) and cur[:c].strip()]
        fit = [c for c in cands if width(hp + lead + cur[:c].rstrip()) <= LIMIT]
        if fit:
            c = max(fit)
        elif cands:
            c = min(cands)
            if c >= len(cur) or not cur[c:].strip():
                out.append(line)
                break
        else:
            out.append(line)
            break
        out.append(hp + lead + cur[:c].rstrip())
        cur = cur[c:].lstrip()
        first = False
    return out


def reflow_line(line, lang):
    if width(line) <= LIMIT:
        return [line]
    hp = "# " if lang == "rust" and line.startswith("# ") else ""
    body = line[len(hp):]
    stripped = body.lstrip(" ")
    indent = body[: len(body) - len(stripped)]
    marker = "#" if lang == "toml" else "//"

    c = find_comment(body, marker)
    if c is not None and c == len(indent):
        m = re.match(r"(//[/!]?|#) ?", stripped) if lang == "toml" else re.match(r"//[/!]? ?", stripped)
        mt = stripped[: m.end()]
        if not mt.endswith(" "):
            mt += " "
        return comment_lines(indent, hp, mt, stripped[m.end():])
    if lang == "toml":
        return [line]
    if c is not None:
        code = body[:c].rstrip()
        m = re.match(r"//[/!]? ?", body[c:])
        mt = body[c : c + m.end()]
        if not mt.endswith(" "):
            mt += " "
        out = comment_lines(indent, hp, mt, body[c + m.end():])
        out += reflow_code(hp, indent, code.lstrip(" "))
        return out
    return reflow_code(hp, indent, stripped)


def reflow(code, lang):
    if lang not in ("rust", "toml"):
        return code
    out = []
    for line in code.split("\n"):
        out.extend(reflow_line(line, lang))
    return "\n".join(out)
