$ErrorActionPreference = "Stop"
$taskName = "EriiDesktopPet"
$appDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $appDirectory "launch-hidden.vbs"

if (-not (Test-Path -LiteralPath $launcherPath)) {
    throw "Missing launcher: $launcherPath"
}

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument ('"{0}"' -f $launcherPath)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Start 绘梨衣 desktop pet when this user signs in." -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "绘梨衣已设置为开机自启动，并已启动。"
