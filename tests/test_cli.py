import json

from typer.testing import CliRunner

from coding_agent.cli import app


def test_demo_dangerous_action_outputs_blocked_status() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["demo", "dangerous-action"])

    assert result.exit_code == 1
    assert "guardrail_blocked" in result.stdout


def test_demo_bugfix_outputs_succeeded_status() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["demo", "bugfix"])

    assert result.exit_code == 0
    assert "succeeded" in result.stdout


def test_credentials_status_outputs_environment_state(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "provider-token-for-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    runner = CliRunner()

    result = runner.invoke(app, ["credentials", "status"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body == {
        "provider": "openai-compatible",
        "configured": True,
        "source": "environment",
        "base_url": "https://example.test/v1",
        "model": "demo-model",
        "real_enabled": True,
    }
    assert "provider-token-for-test" not in result.stdout
