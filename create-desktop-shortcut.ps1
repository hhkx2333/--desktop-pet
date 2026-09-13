$ErrorActionPreference = "Stop"
$appDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $appDirectory "launch-hidden.vbs"

if (-not (Test-Path -LiteralPath $launcherPath)) {
    throw "Missing launcher: $launcherPath"
}

$desktopDirectory = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopDirectory "绘梨衣.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
$shortcut.Arguments = ('"{0}"' -f $launcherPath)
$shortcut.WorkingDirectory = $appDirectory
$shortcut.Description = "打开绘梨衣桌面宠物"
$shortcut.Save()

Write-Host "桌面快捷方式已创建：$shortcutPath"
