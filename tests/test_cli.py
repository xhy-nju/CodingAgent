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
