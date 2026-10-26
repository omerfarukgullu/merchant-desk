# Hatirlatici uygulamasini (IsYonetimHatirlatici.exe) Windows baslangicina
# ekler - boylece bilgisayar acilista arka planda otomatik calismaya baslar.
# Kaldirmak icin: shell:startup klasorunu acip kisayolu silin.
#
# Kullanim: once "python build_tray_exe.py" ile .exe'yi olusturun, sonra bu
# betigi calistirin (ya da yanindaki create_startup_shortcut.bat'a cift
# tiklayin).

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $repoRoot "dist\IsYonetimHatirlatici\IsYonetimHatirlatici.exe"

if (-not (Test-Path $exePath)) {
    Write-Host "HATA: $exePath bulunamadi." -ForegroundColor Red
    Write-Host "Once '.venv\Scripts\python.exe build_tray_exe.py' ile .exe'yi olusturun." -ForegroundColor Red
    exit 1
}

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "Is Yonetim Hatirlatici.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = Split-Path $exePath -Parent
$shortcut.IconLocation = "$exePath,0"
$shortcut.Description = "Is Yonetim Sistemi - arka plan hatirlatici"
$shortcut.Save()

Write-Host "Baslangic kisayolu olusturuldu: $shortcutPath" -ForegroundColor Green
Write-Host "Bilgisayar her acildiginda hatirlatici arka planda otomatik baslayacak." -ForegroundColor Green
Write-Host "Simdi hemen baslatmak icin: dist\IsYonetimHatirlatici\IsYonetimHatirlatici.exe" -ForegroundColor Cyan
