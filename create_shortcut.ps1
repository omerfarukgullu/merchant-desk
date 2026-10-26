# Masaustunde IsYonetimSistemi.exe icin bir kisayol olusturur.
# Kullanim: once "python build_exe.py" ile .exe'yi olusturun, sonra bu
# betigi calistirin (ya da yanindaki create_shortcut.bat'a cift tiklayin).

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $repoRoot "dist\IsYonetimSistemi\IsYonetimSistemi.exe"

if (-not (Test-Path $exePath)) {
    Write-Host "HATA: $exePath bulunamadi." -ForegroundColor Red
    Write-Host "Once '.venv\Scripts\python.exe build_exe.py' ile .exe'yi olusturun." -ForegroundColor Red
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Is Yonetim Sistemi.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = Split-Path $exePath -Parent
$shortcut.IconLocation = "$exePath,0"
$shortcut.Description = "Is Yonetim Sistemi"
$shortcut.Save()

Write-Host "Kisayol olusturuldu: $shortcutPath" -ForegroundColor Green
