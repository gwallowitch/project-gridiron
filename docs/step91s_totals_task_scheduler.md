# Step 91S totals Task Scheduler preparation

This prepares a second, independent task. It does not alter or restart the existing moneyline task. Run these commands manually only after explicit production-activation approval.

```powershell
$action = New-ScheduledTaskAction `
  -Execute 'C:\Users\grego\Desktop\ProjectGridiron\.venv\Scripts\pythonw.exe' `
  -Argument '"C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex\scripts\gridiron_totals_collector.py"' `
  -WorkingDirectory 'C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex'

$trigger = New-ScheduledTaskTrigger `
  -Once `
  -At (Get-Date).AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes 15) `
  -RepetitionDuration (New-TimeSpan -Days 3650)

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

The task repeats every 15 minutes. The 3,650-day repetition duration is an operational approximation of indefinite recurrence that uses parameters supported by the verified Windows host. `pythonw.exe` intentionally launches the collector without a visible console window.

Interactive logon is intentional because collection uses the signed-in user's existing operational environment and network context. The task inherits `GRIDIRON_ODDS_API_KEY` from that environment; no credential belongs in the command, task definition, repository, or logs. The user should remain signed in. A locked session is acceptable, but signing out or shutting down prevents execution. Sleep/wake execution still depends on Windows and hardware wake behavior.

A scheduler invocation does not imply a provider request. Step 91R first validates retained state and target-window eligibility, and requests the provider only when one exact target is eligible. Validate local state before activation with:

```powershell
python scripts/gridiron_totals_health.py
python scripts/gridiron_totals_collector.py --dry-run
```

Step 91R remains non-prospective observational collection. Do not backfill completed games or passed targets.
