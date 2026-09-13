# Step 91S totals Task Scheduler preparation

This prepares a second, independent task. It does not alter or restart the existing moneyline task. Run these commands manually only after explicit production-activation approval.

```powershell
$action = New-ScheduledTaskAction `
  -Execute 'C:\Users\grego\Desktop\ProjectGridiron\.venv\Scripts\python.exe' `
  -Argument '"C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex\scripts\gridiron_totals_collector.py"' `
  -WorkingDirectory 'C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex'

$trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date).Date
$trigger.Repetition.Interval = 'PT15M'
$trigger.Repetition.Duration = 'P1D'

$settings = New-ScheduledTaskSettingsSet `
  -MultipleInstances IgnoreNew `
  -WakeToRun `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries

$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType Interactive `
  -RunLevel Limited

Register-ScheduledTask `
  -TaskName 'Project Gridiron Totals Collector' `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal
```

The task inherits `GRIDIRON_ODDS_API_KEY` from the interactive user environment. No credential belongs in the command, task definition, repository, or logs. Validate local state before activation with:

```powershell
python scripts/gridiron_totals_health.py
python scripts/gridiron_totals_collector.py --dry-run
```

Step 91R remains non-prospective observational collection. Do not backfill completed games or passed targets.
