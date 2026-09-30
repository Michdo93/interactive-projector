# Registers the Interactive Projector as a Windows logon task (runs in the user's desktop session,
# which is required for mouse control and the calibration window).
# Run PowerShell as Administrator.

param (
    [ValidateSet("client", "standalone", "standalone_v1")]
    [string]$Mode = "client",
    [string]$PythonPath = "python.exe",
    [string]$RepoPath = (Resolve-Path "$PSScriptRoot\..").Path
)

$TaskName = "InteractiveProjector_$Mode"
$ScriptFile = switch ($Mode) {
    "client"        { "$RepoPath\src\client.py" }
    "standalone"    { "$RepoPath\src\main.py" }
    "standalone_v1" { "$RepoPath\src\main_v1.py" }
}

Write-Host "Setting up Task Scheduler entry for $TaskName..." -ForegroundColor Green

$Action    = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptFile`"" -WorkingDirectory $RepoPath
$Trigger   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                 -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal `
    -Settings $Settings -Description "Runs Interactive Projector ($Mode) automatically upon user logon." -Force

Write-Host "Task $TaskName successfully registered! It will run automatically at logon." -ForegroundColor Yellow
