from __future__ import annotations

from scripts import gridiron_settlement


def test_validate_missing_ledgers_is_read_only(tmp_path, capsys) -> None:
    path = tmp_path / "executions.jsonl"
    assert gridiron_settlement.main(["validate-executions", "--executions", str(path)]) == 0
    assert '"execution_count":0' in capsys.readouterr().out
    assert not path.exists()


def test_show_close_with_no_history_is_null(tmp_path, capsys) -> None:
    path = tmp_path / "history.jsonl"
    assert gridiron_settlement.main(["show-close", "--game", "missing", "--history", str(path)]) == 0
    assert capsys.readouterr().out.strip() == "null"
    assert not path.exists()
