# 馬開腹手術支援アプリ ランチャー
# Streamlit と cloudflared(HTTPS トンネル) を起動し、スマホ用のURLとQRを表示する。
# このウィンドウを開いている間、アプリは動き続ける。終了は Enter キー。

$ErrorActionPreference = "Stop"
$proj = $PSScriptRoot
Set-Location $proj

# --- cloudflared の場所を探す ---
$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cf) {
  $cf = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "cloudflared*.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $cf) { Write-Host "cloudflared が見つかりません。`nwinget install Cloudflare.cloudflared を実行してください。" -ForegroundColor Red; Read-Host "Enterで終了"; exit 1 }

$log = Join-Path $env:TEMP "equine_app"
New-Item -ItemType Directory -Force -Path $log | Out-Null
$cfOut = Join-Path $log "cf.out"
$cfErr = Join-Path $log "cf.err"
Remove-Item $cfOut,$cfErr -ErrorAction SilentlyContinue

Write-Host "`n[1/3] Streamlit を起動中..." -ForegroundColor Cyan
$st = Start-Process -FilePath "python" `
  -ArgumentList "-m","streamlit","run","app.py","--server.port","8501","--server.headless","true","--server.address","0.0.0.0" `
  -WorkingDirectory $proj -WindowStyle Hidden -PassThru

# 8501 が立ち上がるまで待つ
$ok = $false
for ($i=0; $i -lt 30; $i++) {
  if (Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue) { $ok = $true; break }
  Start-Sleep -Seconds 1
}
if (-not $ok) { Write-Host "Streamlit の起動に失敗しました。" -ForegroundColor Red; Read-Host "Enterで終了"; exit 1 }
Write-Host "    OK (http://localhost:8501)" -ForegroundColor Green

Write-Host "[2/3] HTTPS トンネルを起動中..." -ForegroundColor Cyan
$cfp = Start-Process -FilePath $cf `
  -ArgumentList "tunnel","--url","http://localhost:8501","--no-autoupdate" `
  -RedirectStandardOutput $cfOut -RedirectStandardError $cfErr -WindowStyle Hidden -PassThru

# トンネルURLを取得
$url = $null
for ($i=0; $i -lt 40; $i++) {
  Start-Sleep -Seconds 1
  $m = Select-String -Path $cfErr,$cfOut -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($m) { $url = [regex]::Match($m.Line, "https://[a-z0-9-]+\.trycloudflare\.com").Value; break }
}
if (-not $url) { Write-Host "トンネルURLの取得に失敗しました。" -ForegroundColor Red; Stop-Process -Id $st.Id -Force -ErrorAction SilentlyContinue; Read-Host "Enterで終了"; exit 1 }
Write-Host "    OK" -ForegroundColor Green

# --- QRコード画像を生成して開く ---
Write-Host "[3/3] QRコードを生成中..." -ForegroundColor Cyan
$qrPath = Join-Path $log "qr.png"
$pyCode = @"
import qrcode
img = qrcode.make('$url')
img.save(r'$qrPath')
"@
$pyCode | python - 2>$null
if (Test-Path $qrPath) { Start-Process $qrPath }

Write-Host "`n============================================================" -ForegroundColor Yellow
Write-Host "  スマホでこのURLを開いてください (QR画像も開きました):" -ForegroundColor Yellow
Write-Host "  $url" -ForegroundColor White
Write-Host "============================================================`n" -ForegroundColor Yellow
Write-Host "・スマホのカメラでQRを読む、またはURLを直接入力"
Write-Host "・アプリ → 撮影&色解析 → 『背面カメラで撮影』を選択"
Write-Host "・このウィンドウを閉じる/Enterを押すとアプリは停止します`n" -ForegroundColor DarkGray

Read-Host "終了するには Enter を押してください"

# --- 後始末 ---
Write-Host "停止中..." -ForegroundColor Cyan
Stop-Process -Id $cfp.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $st.Id  -Force -ErrorAction SilentlyContinue
Write-Host "停止しました。"
