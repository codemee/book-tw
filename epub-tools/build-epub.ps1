# 建置 epub：mdbook build（含 mdbook-epub）→ 後處理
# 用法（在專案根目錄）：pwsh epub-tools/build-epub.ps1
$ErrorActionPreference = 'Stop'

mdbook build
if ($LASTEXITCODE) { throw 'mdbook build 失敗' }

$raw = Get-ChildItem book/epub -Filter *.epub | Select-Object -First 1
if (-not $raw) { throw '找不到 book/epub 底下的 epub，請確認已安裝 mdbook-epub' }

New-Item -ItemType Directory -Force book/epub-final | Out-Null
$out = Join-Path book/epub-final $raw.Name
uv run --with pygments python -I epub-tools/postprocess.py $raw.FullName $out
if ($LASTEXITCODE) { throw '後處理失敗' }

Write-Host "完成：$out"
