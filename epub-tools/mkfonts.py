"""把內文與程式碼字型子集化成只含書中用到的字元，輸出到 epub-fonts/。

用法：
  uv run --with fonttools python epub-tools/mkfonts.py <書的根目錄> <輸出資料夾> \\
      <NotoSerifTC 可變字型 .ttf> <MapleMono-NF-CN 字型所在資料夾>
"""
import sys, pathlib
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

if len(sys.argv) != 5:
    sys.exit(__doc__)

book = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
noto_vf = sys.argv[3]
maple_dir = pathlib.Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)

chars = set(chr(c) for c in range(0x20, 0x7F))
for p in list(book.glob("src/**/*.md")) + list(book.glob("listings/**/*")):
    if p.is_file() and p.suffix in {".md", ".rs", ".txt", ".toml", ".md"}:
        try:
            chars |= set(p.read_text(encoding="utf-8"))
        except Exception:
            pass
chars -= set("\r\n\t")
# 常用全形標點補齊
chars |= set("，。、；：？！「」『』（）《》〈〉…—～・“”‘’　")
print("characters:", len(chars))

def do_subset(font, name):
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    opts.glyph_names = False
    opts.hinting = False
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)))
    sub.subset(font)
    font.save(out / name)
    print(name, round((out / name).stat().st_size / 1e6, 2), "MB")

# Noto Serif TC：可變字型取出 400 / 700
vf = noto_vf
for w, name in [(400, "NotoSerifTC-Regular.ttf"), (700, "NotoSerifTC-Bold.ttf")]:
    f = TTFont(vf)
    f = instancer.instantiateVariableFont(f, {"wght": w})
    do_subset(f, name)

# Maple Mono NF CN
mdir = maple_dir
for src, name in [("MapleMono-NF-CN-Regular.ttf", "MapleMonoNFCN-Regular.ttf"),
                  ("MapleMono-NF-CN-Bold.ttf", "MapleMonoNFCN-Bold.ttf")]:
    do_subset(TTFont(mdir / src), name)
