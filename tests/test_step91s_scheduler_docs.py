from pathlib import Path


def test_scheduler_instructions_are_exact_and_isolated() -> None:
    text = Path("docs/step91s_totals_task_scheduler.md").read_text(encoding="utf-8")
    assert r"C:\Users\grego\Desktop\ProjectGridiron\.venv\Scripts\pythonw.exe" in text
    assert r"C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex\scripts\gridiron_totals_collector.py" in text
    assert r"C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex" in text
    assert "Project Gridiron Totals Collector" in text
    assert "New-ScheduledTaskTrigger" in text and "-Once" in text
    assert "-RepetitionInterval" in text and "New-TimeSpan -Minutes 15" in text
    assert "-RepetitionDuration" in text and "New-TimeSpan -Days 3650" in text
    assert "IgnoreNew" in text
    assert "WakeToRun" in text and "StartWhenAvailable" in text
    assert "AllowStartIfOnBatteries" in text and "DontStopIfGoingOnBatteries" in text
    assert "LogonType Interactive" in text
    assert "RunLevel Limited" in text
    assert "GRIDIRON_ODDS_API_KEY" in text
    assert "apiKey=" not in text
    assert "gridiron_market_collector.py" not in text
    assert ".Repetition.Interval" not in text
    assert ".Repetition.Duration" not in text
