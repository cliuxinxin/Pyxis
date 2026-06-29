from pathlib import Path
from types import SimpleNamespace

from pyxis import cli


def test_doctor_reports_missing_without_secrets(monkeypatch, capsys) -> None:
    for name in cli.REQUIRED_OPENAI_ENV:
        monkeypatch.delenv(name, raising=False)

    code = cli.main(["--env-file", "missing.env", "doctor"])

    captured = capsys.readouterr()
    assert code == 1
    assert "OPENAI_API_KEY: missing" in captured.out
    assert "sk-" not in captured.out


def test_doctor_reads_env_file_without_printing_secret(tmp_path, monkeypatch, capsys) -> None:
    for name in cli.REQUIRED_OPENAI_ENV:
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "OPENAI_BASE_URL=http://localhost\n"
        "OPENAI_API_KEY=secret-value\n"
        "OPENAI_MODEL=test-model\n",
        encoding="utf-8",
    )

    code = cli.main(["--env-file", str(env_file), "doctor"])

    captured = capsys.readouterr()
    assert code == 0
    assert "OPENAI_API_KEY: set" in captured.out
    assert "secret-value" not in captured.out


def test_run_requires_provider_env(monkeypatch, capsys) -> None:
    for name in cli.REQUIRED_OPENAI_ENV:
        monkeypatch.delenv(name, raising=False)

    code = cli.main(["--env-file", "missing.env", "run", "hello"])

    captured = capsys.readouterr()
    assert code == 1
    assert "Missing required environment variable" in captured.err


def test_run_prints_output_and_saves_snapshot(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    class FakeProvider:
        def __init__(self, *, model: str) -> None:
            self.model = model

        def complete(self, request):
            return type("Result", (), {"output": "hello from cli", "raw": None, "metadata": {}})()

    monkeypatch.setattr(cli, "OpenAICompatibleProvider", FakeProvider)
    snapshot_path = tmp_path / "session.json"

    code = cli.main(
        [
            "--env-file",
            "missing.env",
            "run",
            "hello",
            "--save-snapshot",
            str(snapshot_path),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "hello from cli" in captured.out
    assert f"Snapshot saved to {snapshot_path}" in captured.out
    assert Path(snapshot_path).exists()
    assert "secret-value" not in captured.out


def test_run_auto_approves_checkpoint(monkeypatch, capsys) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    checkpoint = SimpleNamespace(id="checkpoint-1")
    tool_result = SimpleNamespace(
        name="write_file",
        output=None,
        requires_confirmation=True,
        checkpoint=checkpoint,
    )
    result = SimpleNamespace(
        output="Confirmation required",
        metadata={"tool_result": tool_result},
    )
    resumed = SimpleNamespace(output="approved output")

    class FakeSession:
        def navigate(self, prompt: str):
            return result

        def approve_checkpoint(self, checkpoint_id: str) -> None:
            assert checkpoint_id == "checkpoint-1"

        def resume_checkpoint(self, checkpoint_id: str):
            assert checkpoint_id == "checkpoint-1"
            return resumed

    class FakePyxis:
        def __init__(self, agent) -> None:
            self.agent = agent

        def session(self):
            return FakeSession()

    class FakeProvider:
        def __init__(self, *, model: str) -> None:
            self.model = model

    monkeypatch.setattr(cli, "OpenAICompatibleProvider", FakeProvider)
    monkeypatch.setattr(cli, "Pyxis", FakePyxis)

    code = cli.main(["--env-file", "missing.env", "run", "hello", "--approve"])

    captured = capsys.readouterr()
    assert code == 0
    assert "Confirmation required" in captured.out
    assert "approved output" in captured.out


def test_run_can_leave_checkpoint_pending(monkeypatch, capsys) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    checkpoint = SimpleNamespace(id="checkpoint-1")
    tool_result = SimpleNamespace(
        name="write_file",
        output=None,
        requires_confirmation=True,
        checkpoint=checkpoint,
    )
    result = SimpleNamespace(
        output="Confirmation required",
        metadata={"tool_result": tool_result},
    )

    class FakeSession:
        def navigate(self, prompt: str):
            return result

    class FakePyxis:
        def __init__(self, agent) -> None:
            self.agent = agent

        def session(self):
            return FakeSession()

    class FakeProvider:
        def __init__(self, *, model: str) -> None:
            self.model = model

    monkeypatch.setattr(cli, "OpenAICompatibleProvider", FakeProvider)
    monkeypatch.setattr(cli, "Pyxis", FakePyxis)

    code = cli.main(["--env-file", "missing.env", "run", "hello"])

    captured = capsys.readouterr()
    assert code == 0
    assert "Checkpoint left pending: checkpoint-1" in captured.out
