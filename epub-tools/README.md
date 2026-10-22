[English](README.en.md) | **繁體中文**

# epub 建置工具

本資料夾是 [rust-tw/book-tw](https://github.com/rust-tw/book-tw) 的 fork 所加入的 epub 輸出功能。
Fork 來源：<https://github.com/rust-tw/book-tw>（《Rust 程式設計語言》繁體中文版）。

## 做了什麼

- `book.toml` 新增 `[output.epub]`，並將過時的 `author` 改為 `authors`（新版 mdBook 不再接受 `author`）。
- `epub.css`：中文內文字型、程式碼字型、標題層級、段落間距、說明框與範例區塊樣式。
- `epub-fonts/`：內文（Noto Serif TC）與程式碼（Maple Mono NF CN）字型，已子集化成只含書中用到的字元，直接嵌入 epub。
- `epub-tools/postprocess.py`：epub 產生後的後處理（語言標記、語法上色、隱藏行移除、過寬程式碼依語法重新斷行、範例區塊與說明框合併）。
- `epub-tools/reflow.py`：程式碼與註解的重新斷行邏輯。
- `epub-tools/mkfonts.py`：產生 `epub-fonts/` 的字型子集化腳本。

## 需求

- Rust 工具鏈（請使用 stable；本專案的 `rust-toolchain` 鎖定 1.65，太舊，無法編譯新版 mdBook）
- `mdbook` 與 `mdbook-epub`：
  ```bash
  cargo +stable install mdbook mdbook-epub
  ```
- [uv](https://docs.astral.sh/uv/)（執行 Python 腳本，並自動安裝 `pygments`）

## 建置

在專案根目錄執行：

```powershell
pwsh epub-tools/build-epub.ps1
```

成品會在 `book/epub-final/` 底下。`book/epub/` 內是未經後處理的版本。

## 重新產生字型

更換字型或書的內容變動後，可重新子集化：

```bash
uv run --with fonttools python epub-tools/mkfonts.py . epub-fonts <NotoSerifTC 可變字型.ttf> <MapleMono-NF-CN 所在資料夾>
```

## 已知限制

- 在 Adobe Digital Editions 測試過；其他閱讀器的外觀可能不同。
- 少數很長的字串（例如單一 `format!("…")`）無法斷行，會略超出程式碼區塊。
- 程式碼區塊中 mdBook 的隱藏行（`# ` 開頭）會被移除，部分範例因此只剩片段。

## 字型授權

Noto Serif TC 與 Maple Mono 皆以 SIL Open Font License 1.1 授權，允許子集化與嵌入。
