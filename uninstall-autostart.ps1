$taskName = "EriiDesktopPet"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -ne $task) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "已取消绘梨衣的开机自启动。"
} else {
    Write-Host "未找到绘梨衣的开机自启动任务。"
}
