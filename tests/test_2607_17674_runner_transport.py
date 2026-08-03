from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]


def test_primary_runner_never_streams_authoritative_log_to_observer_pipe() -> None:
    runner = (WORKSPACE / "scripts/run_2607_17674_arm.sh").read_text()
    assert 'exec >>"$LOG_ROOT/runner.log" 2>&1' in runner
    assert 'exec > >(tee -a "$LOG_ROOT/runner.log") 2>&1' not in runner


def test_guarded_launcher_uses_detached_service_not_attached_scope() -> None:
    guarded = (WORKSPACE / "scripts/run_guarded_2607_17674_arm.sh").read_text()
    detached = (WORKSPACE / "scripts/launch_detached_2607_17674_arm.sh").read_text()
    assert "launch_detached_2607_17674_arm.sh" in guarded
    assert "--service-type=exec" in detached
    assert "--collect" in detached
    assert "--scope" not in detached
    assert "ATTEMPT_ID" in detached


def test_terminal_success_is_artifact_gated_and_signal_aware() -> None:
    runner = (WORKSPACE / "scripts/run_2607_17674_arm.sh").read_text()
    validator = "validate_2607_17674_attempt_artifacts.py"
    assert runner.index(validator) < runner.index(
        'terminal_manifest="$RUN_ROOT/run.complete.json"'
    )
    assert 'artifact_validation="failed"' in runner
    assert "exit_code=70" in runner
    assert "trap 'handle_signal SIGHUP 129' HUP" in runner
    assert "trap 'handle_signal SIGTERM 143' TERM" in runner


def test_queue_is_target_side_artifact_gated_and_bounded() -> None:
    queue = (WORKSPACE / "scripts/run_2607_17674_detached_queue.sh").read_text()
    launcher = (WORKSPACE / "scripts/launch_detached_2607_17674_queue.sh").read_text()
    assert "--require-terminal" in queue
    assert "MAX_OPERATIONAL_RETRIES" in queue
    assert "arm_fresh_retry" in queue
    assert "protected_unit_restarts" in queue
    assert "stop_experiment_first" in queue
    assert "--service-type=exec" in launcher
    assert "--collect" in launcher
    assert "ssh " not in queue
    assert "ssh " not in launcher


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
