# PowerShell Script to set up Interactive Projector Client/Standalone as a Windows Startup Task
# Run as Administrator

param (
    [string]$Mode = "client", # "client" or "standalone"
    [string]$PythonPath = "python.exe",
    [string]$RepoPath = "$PSScriptRoot\.."
)

$TaskName = "InteractiveProjector_$Mode"
$ScriptFile = if ($Mode -eq "client") { "$RepoPath\src\client.py" } else { "$RepoPath\src\main.py" }

Write-Host "Setting up Task Scheduler entry for $TaskName..." -ForegroundColor Green

$Action = New-ScheduledTaskAction -Execute$PythonPath -Argument "`"$ScriptFile`"" -WorkingDirectory $RepoPath
$Trigger = New-ScheduledTaskTrigger -AtLogOn$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0

Register-ScheduledTask -TaskName $TaskName -Action$Action -Trigger $Trigger -Settings$Settings -Description "Runs Interactive Projector automatically upon user login." -Force

Write-Host "Task $TaskName successfully registered! It will run automatically at logon." -ForegroundColor Yellow