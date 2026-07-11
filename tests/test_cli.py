import json

from typer.testing import CliRunner

from coding_agent.cli import app
from coding_agent.credentials import CredentialService
from coding_agent.llm import RealLLMProvider


class FakeKeyring:
    def __init__(self) -> None:
        self.token: str | None = None

    def get_password(self, service: str, username: str) -> str | None:
        return self.token

    def set_password(self, service: str, username: str, token: str) -> None:
        self.token = token

    def delete_password(self, service: str, username: str) -> None:
        if self.token is None:
            from keyring.errors import PasswordDeleteError

            raise PasswordDeleteError("credential not found")
        self.token = None


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
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
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


def test_hidden_credential_commands_set_update_and_clear(monkeypatch) -> None:
    service = CredentialService(keyring_backend=FakeKeyring())
    monkeypatch.setattr("coding_agent.cli._credential_service", lambda: service)
    runner = CliRunner()

    commands = runner.invoke(app, ["credentials", "--help"])
    set_result = runner.invoke(app, ["credentials", "set"], input="first-token\nfirst-token\n")
    update_result = runner.invoke(app, ["credentials", "update"], input="second-token\nsecond-token\n")
    clear_result = runner.invoke(app, ["credentials", "clear"])

    assert commands.exit_code == 0
    assert "set" not in commands.stdout
    assert "update" not in commands.stdout
    assert "clear" not in commands.stdout
    assert set_result.exit_code == 0
    assert update_result.exit_code == 0
    assert clear_result.exit_code == 0
    assert service.resolve().configured is False
    assert "removed" in clear_result.stdout.lower()
    assert "environment" in clear_result.stdout.lower()
    assert "docker secret" in clear_result.stdout.lower()


def test_llm_probe_command_outputs_sanitized_success(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "provider-token-for-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setattr(
        RealLLMProvider,
        "next_action",
        lambda self, context: json.dumps(
            {
                "kind": "final",
                "args": {},
                "reason": "real llm probe",
                "expectation": "stop",
            }
        ),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["llm", "probe"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["ok"] is True
    assert body["protocol_valid"] is True
    assert body["action_kind"] == "final"
    assert body["model"] == "demo-model"
    assert "provider-token-for-test" not in result.stdout


def test_llm_probe_command_exits_one_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "provider-token-for-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
    monkeypatch.setenv("ENABLE_REAL_LLM", "false")
    runner = CliRunner()

    result = runner.invoke(app, ["llm", "probe"])

    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert body["ok"] is False
    assert body["error_code"] == "real_llm_disabled"
    assert "provider-token-for-test" not in result.stdout
