import json

from typer.testing import CliRunner

from intake_engine.cli.main import app

runner = CliRunner()


def test_batch_processes_multiple_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    for i in range(1, 4):
        (folder / f"file{i}.csv").write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(folder)])

    assert result.exit_code == 0, result.output
    assert "Processed 3/3" in result.output


def test_batch_skips_bad_file_and_continues(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "good.csv").write_text("name,score\nAlice,90\n")
    (folder / "corrupt.xlsx").write_bytes(b"this is not a valid xlsx")  # will raise on load

    result = runner.invoke(app, ["run", str(folder)])

    assert result.exit_code == 0, result.output
    assert "Processed 1/2" in result.output
    assert "corrupt.xlsx" in result.output  # appears in Failed list


def test_batch_creates_summary_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "a.csv").write_text("name,score\nAlice,90\nBob,80\n")
    (folder / "b.csv").write_text("name,score\nCharlie,70\nCharlie,70\n")  # 1 dupe

    result = runner.invoke(app, ["run", str(folder)])
    assert result.exit_code == 0, result.output

    summary_path = tmp_path / "outputs" / "run_summary.json"
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text())
    assert summary["files_found"] == 2
    assert summary["files_processed"] == 2
    assert summary["files_failed"] == 0
    assert summary["rows_loaded_total"] == 4
    assert summary["rows_output_total"] == 3   # 1 dupe removed from b.csv
    assert summary["duplicates_removed_total"] == 1
    assert set(summary["file_names_processed"]) == {"a.csv", "b.csv"}
