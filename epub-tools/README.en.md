**English** | [繁體中文](README.md)

# epub Build Tools

This folder holds the epub output support added in this fork of [rust-tw/book-tw](https://github.com/rust-tw/book-tw).
Forked from: <https://github.com/rust-tw/book-tw> (the Traditional Chinese edition of *The Rust Programming Language*).

## What was added

- `book.toml` gains `[output.epub]`, and the obsolete `author` key is renamed to `authors` (newer mdBook rejects `author`).
- `epub.css`: Chinese body font, code font, heading hierarchy, paragraph spacing, callout boxes and listing blocks.
- `epub-fonts/`: body (Noto Serif TC) and code (Maple Mono NF CN) fonts, subset to only the characters used in the book and embedded in the epub.
- `epub-tools/postprocess.py`: post-processing after the epub is generated (language tags, syntax highlighting, hidden-line removal, syntax-aware re-wrapping of over-wide code, merging listings and callouts).
- `epub-tools/reflow.py`: the re-wrapping logic for code and comments.
- `epub-tools/mkfonts.py`: the font subsetting script that produces `epub-fonts/`.

## Requirements

- A Rust toolchain (use stable; this project's `rust-toolchain` pins 1.65, which is too old to build current mdBook)
- `mdbook` and `mdbook-epub`:
  ```bash
  cargo +stable install mdbook mdbook-epub
  ```
- [uv](https://docs.astral.sh/uv/) (runs the Python scripts and installs `pygments` automatically)

## Build

From the project root:

```powershell
pwsh epub-tools/build-epub.ps1
```

The result is in `book/epub-final/`. `book/epub/` contains the unprocessed version.

## Regenerating the fonts

After changing fonts or the book content, subset them again:

```bash
uv run --with fonttools python epub-tools/mkfonts.py . epub-fonts <NotoSerifTC variable font.ttf> <folder containing MapleMono-NF-CN>
```

## Known limitations

- Tested in Adobe Digital Editions; other readers may look different.
- A few very long strings (for example a single `format!("…")`) cannot be wrapped and slightly overflow the code block.
- mdBook hidden lines (starting with `# `) are removed from code blocks, so some examples are shown as fragments.

## Font licenses

Noto Serif TC and Maple Mono are both licensed under the SIL Open Font License 1.1, which allows subsetting and embedding.
