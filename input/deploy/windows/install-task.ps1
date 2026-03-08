$ErrorActionPreference = "Stop"

$TaskName = "eastmoney-yw"
$ProjectRoot = "C:\Users\moyueheng\.openclaw\workspace\input"
$ScriptPath = Join-Path $ProjectRoot "scripts\run-eastmoney-yw.bat"

$Action = New-ScheduledTaskAction -Execute $ScriptPath
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force
