# Task 4: Typer CLI Probe Command Report

## Implementation

Added the `llm` Typer command group and `llm probe` command. The command constructs `RealLLMProvider` server-side with `RealLLMProvider.from_env()`, delegates to `probe_real_llm`, and prints only the sanitized `LLMProbeResult` as indented JSON. Successful probes exit `0`; failed probes print their JSON result and exit `1`.

The CLI tests patch `RealLLMProvider.next_action` for the success case, and use the disabled configuration gate for the failure case. No real network request was made. The tests never pass a key as a CLI argument, and both assert the provider token is absent from stdout.

## Exact TDD Evidence

### Cycle 1 RED

```powershell
pytest tests/test_cli.py::test_llm_probe_command_outputs_sanitized_success -v
```

Result: exit code `1`; `1 failed in 0.41s`.

- The test failed with `assert 2 == 0` because the `llm` command group did not exist yet.

### Cycle 1 GREEN

```powershell
pytest tests/test_cli.py::test_llm_probe_command_outputs_sanitized_success -v
```

Result: exit code `0`; `1 passed in 0.41s`.

### Cycle 2 RED

```powershell
pytest tests/test_cli.py::test_llm_probe_command_exits_one_when_disabled -v
```

Result: exit code `1`; `1 failed in 0.43s`.

- The command printed the failed probe result but returned exit code `0`; the test failed with `assert 0 == 1`.

### Cycle 2 GREEN

```powershell
pytest tests/test_cli.py::test_llm_probe_command_exits_one_when_disabled -v
```

Result: exit code `0`; `1 passed in 0.43s`.

## Focused Verification

```powershell
pytest tests/test_llm_probe.py tests/test_cli.py -v
```

Result: exit code `0`; `18 passed in 2.56s`.

## Full Backend Suite

```powershell
pytest -v
```

Result: exit code `0`; `60 passed in 12.64s`.

## Self-Review

- Confirmed the CLI accepts no provider key argument and calls `RealLLMProvider.from_env()` only inside the server-side command implementation.
- Confirmed output is serialized from `LLMProbeResult.model_dump(mode="json")`; raw provider content and credentials are not printed by the CLI.
- Confirmed failed probe results are emitted before `typer.Exit(code=1)`, preserving machine-readable JSON on stdout.
- Confirmed the success test patches `next_action`, so no provider request occurs; the disabled test returns through the probe service gate before any provider call.
- Confirmed `git diff --check` exited `0` with no whitespace errors.
- Confirmed the working diff contains only `src/coding_agent/cli.py`, `tests/test_cli.py`, and this report.

## Concerns

None. This task intentionally wires the reviewed probe service into Typer and does not modify provider or probe-service behavior.

## Commit

```text
feat: expose real llm probe command
```
