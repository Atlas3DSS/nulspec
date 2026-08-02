from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]


def test_primary_runner_never_streams_authoritative_log_to_observer_pipe() -> None:
    runner = (WORKSPACE / "scripts/run_2607_17674_arm.sh").read_text()
    assert 'exec >>"$LOG_ROOT/runner.log" 2>&1' in runner
    assert 'exec > >(tee -a "$LOG_ROOT/runner.log") 2>&1' not in runner


def test_recovery_is_narrow_and_uses_the_unchanged_evaluator() -> None:
    recovery = (WORKSPACE / "scripts/recover_2607_17674_evaluation.sh").read_text()
    assert '!= "141"' in recovery
    assert "observer_output_transport_sigpipe" in recovery
    assert "-m experiments.factorization.evaluate" in recovery
    assert "--config configs/paper/evaluation.json" in recovery
    assert '>>"$LOG_ROOT/evaluation.log" 2>&1' in recovery
    assert (
        "run.failed.json and the truncated first evaluation log remain immutable"
        in recovery
    )
    assert "evaluation-recovery-attempts" in recovery
    assert "--phase start" in recovery
    assert "--phase end" in recovery
