#!/usr/bin/env python3
"""Import a typed classification-accuracy handoff into the public site.

The research handoff remains immutable. This importer resolves only the
website-compatibility gate, validates the source at an exact Git revision, and
copies a small allowlist of explicitly declared public artifacts.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from import_publication import (
    HEX64,
    PRIVATE_TEXT,
    STUDY_ID,
    ImportError,
    atomic_write,
    load_bundle,
    safe_relative,
    sha256,
    verify_public_value,
)


HANDOFF_SCHEMA = "nulspec-classification-accuracy-study-handoff-v1"
SITE_SCHEMA = "nulspec-classification-accuracy-site-v1"
TECHNICAL_GATE = "blocked_pending_typed_accuracy_frontend"
METRIC_SCHEMA = "sprkd_trial_accuracy_v1"
FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
ROUTE_COMPONENT = re.compile(r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$")

# Site roles are intentionally narrower than the handoff's declaration. The
# importer never walks the study directory and never copies undeclared files.
PUBLIC_ARTIFACTS = {
    "one_page_explainer": ("result_summary", "result-summary.md"),
    "full_report": ("full_report", "full-report.md"),
    "machine_primary": ("machine_analysis", "machine-analysis.json"),
    "primary_figure": ("primary_figure", "primary-accuracy-by-seed.png"),
    "frozen_primary_protocol": ("frozen_primary_protocol", "primary-protocol.md"),
    "extension_roadmap": ("extension_roadmap", "extension-roadmap.md"),
    "typed_frontend_contract": ("frontend_handoff", "frontend-handoff.md"),
    "upstream_issue_audit": ("upstream_audit", "upstream-audit.md"),
    "posthoc_register": ("posthoc_register", "posthoc-register.md"),
    "loss_contract_human_table": (
        "posthoc_loss_contract",
        "posthoc-loss-contract.md",
    ),
    "executed_code_identity": ("executed_code_manifest", "executed-code.json"),
    "final_peer_review_protocol": (
        "peer_review_protocol",
        "peer-review-protocol.md",
    ),
}

OPTIONAL_REVIEW_ARTIFACTS = {
    "final_peer_review_result": ("peer_review_result", "peer-review-result.json"),
    "final_peer_review_human_record": (
        "peer_review_summary",
        "peer-review-summary.md",
    ),
    "final_peer_review_action_closure": (
        "peer_review_action_closure",
        "peer-review-action-closure.json",
    ),
}


def git(repository: Path, *arguments: str, binary: bool = False) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError):
            detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise ImportError(f"Git source validation failed: {detail or exc}") from exc
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ImportError(f"{label} must be an object")
    return value


def validate_handoff(
    bundle: dict[str, Any], require_release_authorized: bool
) -> tuple[str, list[dict[str, Any]], dict[str, Any], str]:
    if bundle.get("schema_version") != HANDOFF_SCHEMA:
        raise ImportError(f"schema_version must be {HANDOFF_SCHEMA}")

    status = require_object(bundle.get("publication_status"), "publication_status")
    if status.get("canonical_site_import") != TECHNICAL_GATE:
        raise ImportError(
            "handoff must carry the typed-frontend compatibility gate; "
            "scientific or operational blockers cannot be resolved by this importer"
        )

    study = require_object(bundle.get("study"), "study")
    study_id = study.get("id")
    if not isinstance(study_id, str) or not STUDY_ID.fullmatch(study_id):
        raise ImportError("study.id must contain at least three digits")
    if not re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}v[0-9]+", study.get("arxiv_id", "")):
        raise ImportError("study.arxiv_id must be a versioned arXiv identifier")
    if study.get("arxiv_url") != f"https://arxiv.org/abs/{study['arxiv_id']}":
        raise ImportError("study.arxiv_url is not canonical")

    classification = require_object(bundle.get("classification"), "classification")
    if classification.get("replication_outcome") != "not_replicated":
        raise ImportError("replication outcome is not the frozen not_replicated result")
    if classification.get("underlying_method_claim") != "inconclusive":
        raise ImportError("underlying method assessment is not the frozen inconclusive result")
    if not isinstance(classification.get("rationale"), str) or not classification["rationale"].strip():
        raise ImportError("classification rationale is missing")

    metrics_schema = require_object(bundle.get("metrics_schema"), "metrics_schema")
    if (
        metrics_schema.get("id") != METRIC_SCHEMA
        or metrics_schema.get("primary_unit") != "percent_accuracy"
        or metrics_schema.get("primary_estimator")
        != "final_sample_weighted_full_validation_accuracy"
        or metrics_schema.get("not_prompt_bootstrap") is not True
        or metrics_schema.get("not_equivalence_test") is not True
    ):
        raise ImportError("classification-accuracy metric contract is malformed")

    primary = require_object(bundle.get("primary"), "primary")
    metrics = require_object(primary.get("metrics"), "primary.metrics")
    runs = primary.get("runs")
    if not isinstance(runs, list) or len(runs) != 5:
        raise ImportError("primary.runs must contain five frozen training seeds")
    if not isinstance(primary.get("comparisons"), dict):
        raise ImportError("primary.comparisons is missing")

    required_metrics = {
        "control_student",
        "control_teacher",
        "exact_public_response_kd",
        "exact_public_sprkd",
        "paper_intent_response_kd",
        "paper_intent_sprkd",
        "weak_teacher",
    }
    if not required_metrics.issubset(metrics):
        raise ImportError("primary.metrics is missing required accuracy series")
    for key in required_metrics:
        observed = require_object(metrics[key].get("observed"), f"primary.metrics.{key}.observed")
        values = observed.get("per_seed")
        interval = observed.get("descriptive_t95_interval")
        if (
            observed.get("unit") != "percent_accuracy"
            or observed.get("estimator")
            != "final_sample_weighted_full_validation_accuracy"
            or observed.get("n_training_seeds") != 5
            or not isinstance(values, list)
            or len(values) != 5
            or not all(finite_number(value) for value in values)
            or not finite_number(observed.get("mean"))
            or not finite_number(observed.get("sample_sd"))
            or not isinstance(interval, list)
            or len(interval) != 2
            or not all(finite_number(value) for value in interval)
        ):
            raise ImportError(f"invalid accuracy aggregate for {key}")

    routes = require_object(bundle.get("routes"), "routes")
    if routes.get("study") != f"/studies/{study_id}":
        raise ImportError("canonical study route is malformed")
    declared_routes = routes.get("arms")
    if not isinstance(declared_routes, list) or len(declared_routes) != len(runs):
        raise ImportError("canonical arm routes do not match frozen runs")

    seen_ids: set[str] = set()
    seen_seeds: set[int] = set()
    for run in runs:
        run = require_object(run, "primary run")
        run_id = run.get("run_id")
        seed = run.get("seed")
        if (
            not isinstance(run_id, str)
            or not ROUTE_COMPONENT.fullmatch(run_id)
            or run_id in seen_ids
            or not isinstance(seed, int)
            or isinstance(seed, bool)
            or seed in seen_seeds
            or run_id != f"seed-{seed}"
            or run.get("route") != f"/studies/{study_id}/arms/{run_id}"
            or run["route"] not in declared_routes
        ):
            raise ImportError(f"invalid or duplicate frozen run: {run_id}")
        seen_ids.add(run_id)
        seen_seeds.add(seed)
        integrity = require_object(run.get("integrity"), f"{run_id}.integrity")
        if integrity.get("status") != "passed":
            raise ImportError(f"nonterminal or invalid run: {run_id}")
        for digest_key in (
            "complete_sha256",
            "config_sha256",
            "predictions_sha256",
            "split_indices_sha256",
            "validation_indices_sha256",
        ):
            if not isinstance(integrity.get(digest_key), str) or not HEX64.fullmatch(
                integrity[digest_key]
            ):
                raise ImportError(f"invalid {digest_key} for {run_id}")
        if not isinstance(run.get("models"), dict) or not isinstance(run.get("comparisons"), dict):
            raise ImportError(f"run evidence is incomplete: {run_id}")
    if seen_seeds != set(range(5)):
        raise ImportError("frozen seed set must be exactly 0 through 4")

    extension = require_object(bundle.get("extension_vote"), "extension_vote")
    choices = extension.get("choices")
    if (
        extension.get("button_label") != "Vote to extend this paper"
        or not isinstance(extension.get("question"), str)
        or not isinstance(choices, list)
        or len(choices) != 6
        or extension.get("effect")
        != "Schedules new evidence and never rewrites the frozen result."
    ):
        raise ImportError("extension vote contract is missing or malformed")
    choice_ids = [choice.get("id") for choice in choices if isinstance(choice, dict)]
    if len(choice_ids) != 6 or len(set(choice_ids)) != 6:
        raise ImportError("extension vote choices are invalid or duplicated")

    diagnostics = require_object(bundle.get("diagnostics"), "diagnostics")
    for required in (
        "preregistered_extensions",
        "common_probe_hessian",
        "posthoc_stability",
        "posthoc_loss_contract",
    ):
        if required not in diagnostics:
            raise ImportError(f"diagnostic section is missing: {required}")

    review = require_object(bundle.get("final_peer_review"), "final_peer_review")
    if (
        review.get("protocol") != "nulspec-fable-one-shot-final-gate-v1"
        or review.get("protocol_document") != "FABLE_REVIEW_PROTOCOL.md"
        or review.get("reviewer") != "Fable"
        or review.get("single_invocation") is not True
        or review.get("resubmission_allowed") is not False
        or review.get("author_email_human_approval_required") is not True
    ):
        raise ImportError("one-shot final peer-review contract is malformed")
    release_gate = require_object(status.get("research_release_gate"), "research_release_gate")
    for key in (
        "status",
        "publication_authorized",
        "author_email_eligible_for_human_approval",
        "author_email_dispatch_authorized",
        "author_email_human_approval_required",
        "author_email_approval_status",
        "human_review_required",
        "action_closure_required",
    ):
        if review.get(key) != release_gate.get(key):
            raise ImportError(f"final peer review disagrees with publication gate at {key}")

    authorized_statuses = {
        "approved",
        "approved_after_three_action_closure",
    }
    if require_release_authorized:
        if (
            review.get("publication_authorized") is not True
            or review.get("status") not in authorized_statuses
            or review.get("author_email_eligible_for_human_approval") is not True
            or review.get("human_review_required") is not False
            or review.get("action_closure_required") is not False
        ):
            raise ImportError(
                "research release gate is not authorized: "
                + str(review.get("status") or "unknown")
            )
        if review.get("author_email_dispatch_authorized") is True:
            if review.get("author_email_approval_status") != "approved_for_exact_draft_once":
                raise ImportError("author-email dispatch lacks exact-draft human approval")
        elif review.get("author_email_approval_status") != "pending_final_human_approval":
            raise ImportError("author-email approval state is inconsistent after peer review")
    elif review.get("publication_authorized") not in {True, False}:
        raise ImportError("final peer-review publication state is not Boolean")

    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list):
        raise ImportError("artifacts must be an array")
    declared_roles = {
        item.get("role") for item in artifacts if isinstance(item, dict)
    }
    missing_roles = set(PUBLIC_ARTIFACTS) - declared_roles
    if missing_roles:
        raise ImportError(
            "handoff is missing required declared artifacts: "
            + ", ".join(sorted(missing_roles))
        )
    draft = next(
        (
            item
            for item in artifacts
            if isinstance(item, dict) and item.get("role") == "unsent_author_email_draft"
        ),
        None,
    )
    if not isinstance(draft, dict) or not isinstance(draft.get("sha256"), str):
        raise ImportError("exact author-email draft digest is missing")
    if not HEX64.fullmatch(draft["sha256"]):
        raise ImportError("exact author-email draft digest is malformed")
    if require_release_authorized:
        required_review_roles = {
            "final_peer_review_result",
            "final_peer_review_human_record",
        }
        if review.get("status") == "approved_after_three_action_closure":
            required_review_roles.add("final_peer_review_action_closure")
        missing_review_roles = required_review_roles - declared_roles
        if missing_review_roles:
            raise ImportError(
                "authorized release is missing peer-review artifacts: "
                + ", ".join(sorted(missing_review_roles))
            )
    return study_id, artifacts, review, draft["sha256"]


def media_type(path: str) -> str:
    value, _ = mimetypes.guess_type(path)
    if value:
        return value
    if path.endswith("Dockerfile"):
        return "text/plain"
    return "application/octet-stream"


def import_accuracy_publication(
    handoff_path: Path,
    source_root: Path,
    site_root: Path,
    evidence_revision: str,
    check_only: bool = False,
) -> None:
    if not FULL_GIT_SHA.fullmatch(evidence_revision):
        raise ImportError("evidence revision must be a full 40-character Git SHA")

    handoff, raw_handoff = load_bundle(handoff_path)
    verify_public_value(handoff)
    study_id, declared_artifacts, final_review, author_email_sha256 = validate_handoff(
        handoff, require_release_authorized=not check_only
    )

    repository_root = Path(str(git(source_root, "rev-parse", "--show-toplevel"))).resolve()
    try:
        handoff_relative = handoff_path.resolve().relative_to(repository_root).as_posix()
    except ValueError as exc:
        raise ImportError("handoff is outside the source repository") from exc
    safe_relative(handoff_relative, "handoff path")
    committed_handoff = git(
        repository_root,
        "show",
        f"{evidence_revision}:{handoff_relative}",
        binary=True,
    )
    if committed_handoff != raw_handoff:
        raise ImportError("handoff bytes do not match the exact evidence revision")
    generated_at = str(
        git(repository_root, "show", "-s", "--format=%cI", evidence_revision)
    )

    declared_by_role: dict[str, dict[str, Any]] = {}
    for item in declared_artifacts:
        item = require_object(item, "artifact entry")
        role = item.get("role")
        if not isinstance(role, str) or role in declared_by_role:
            raise ImportError(f"missing or duplicate declared artifact role: {role}")
        declared_by_role[role] = item

    public_root = (site_root / "public").resolve()
    source_root = source_root.resolve()
    staged: list[tuple[Path, bytes]] = []
    public_artifacts: list[dict[str, Any]] = []
    artifact_selection = dict(PUBLIC_ARTIFACTS)
    artifact_selection.update(
        {
            role: projection
            for role, projection in OPTIONAL_REVIEW_ARTIFACTS.items()
            if role in declared_by_role
        }
    )
    artifact_contents: dict[str, bytes] = {}
    for declared_role, (site_role, filename) in artifact_selection.items():
        item = declared_by_role[declared_role]
        source_relative = safe_relative(item.get("path", ""), "artifact path")
        source = (source_root / Path(*source_relative.parts)).resolve()
        if source_root not in source.parents or not source.is_file():
            raise ImportError(f"declared artifact is unavailable: {source_relative}")
        content = source.read_bytes()
        expected_bytes = item.get("bytes")
        expected_digest = item.get("sha256")
        if not isinstance(expected_bytes, int) or expected_bytes != len(content):
            raise ImportError(f"artifact byte count mismatch: {source_relative}")
        if not isinstance(expected_digest, str) or not HEX64.fullmatch(expected_digest):
            raise ImportError(f"invalid artifact digest: {source_relative}")
        if sha256(content) != expected_digest:
            raise ImportError(f"artifact digest mismatch: {source_relative}")
        artifact_contents[declared_role] = content
        detected_type = media_type(str(source_relative))
        if (
            detected_type.startswith("text/")
            or detected_type in {"application/json", "application/yaml"}
        ) and PRIVATE_TEXT.search(content.decode("utf-8", errors="replace")):
            raise ImportError(f"private or unrelated text in {source_relative}")

        public_path = f"studies/{study_id}/artifacts/{filename}"
        destination = (public_root / public_path).resolve()
        if public_root not in destination.parents:
            raise ImportError(f"artifact destination escaped public root: {public_path}")
        staged.append((destination, content))
        public_artifacts.append(
            {
                "role": site_role,
                "path": str(source_relative),
                "public_path": public_path,
                "media_type": detected_type,
                "sha256": expected_digest,
                "byte_count": expected_bytes,
            }
        )

    if final_review.get("publication_authorized") is True:
        try:
            review_result = json.loads(artifact_contents["final_peer_review_result"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise ImportError("authorized peer-review result is unavailable or invalid") from exc
        if (
            review_result.get("single_invocation") is not True
            or review_result.get("resubmission_allowed") is not False
            or not isinstance(review_result.get("decision"), dict)
            or review_result["decision"].get("verdict") not in {"PASS", "FAIL"}
            or not isinstance(review_result.get("packet"), dict)
            or review_result["decision"].get("reviewed_packet_sha256")
            != review_result["packet"].get("sha256")
        ):
            raise ImportError("authorized peer-review result violates the one-shot contract")
        if final_review.get("status") == "approved":
            if review_result["decision"].get("verdict") != "PASS":
                raise ImportError("approved peer-review gate is not backed by PASS")
            for key in (
                "status",
                "publication_authorized",
                "author_email_eligible_for_human_approval",
                "author_email_dispatch_authorized",
                "author_email_human_approval_required",
                "author_email_approval_status",
                "human_review_required",
                "action_closure_required",
            ):
                if review_result.get("gate", {}).get(key) != final_review.get(key):
                    raise ImportError(
                        f"peer-review result disagrees with release gate at {key}"
                    )
        elif final_review.get("status") == "approved_after_three_action_closure":
            if review_result["decision"].get("verdict") != "FAIL":
                raise ImportError("three-action closure is not backed by FAIL")
            try:
                closure = json.loads(
                    artifact_contents["final_peer_review_action_closure"]
                )
            except (KeyError, json.JSONDecodeError) as exc:
                raise ImportError("three-action closure is unavailable or invalid") from exc
            actions = closure.get("actions")
            if (
                closure.get("no_resubmission_performed") is not True
                or not isinstance(actions, list)
                or [action.get("id") for action in actions] != ["F1", "F2", "F3"]
                or any(action.get("status") != "RESOLVED" for action in actions)
            ):
                raise ImportError("three-action closure does not close exact F1/F2/F3")

    if check_only:
        print(
            "NULSPEC_ACCURACY_HANDOFF_COMPATIBLE "
            f"study={study_id} runs={len(handoff['primary']['runs'])} "
            f"release_gate={final_review.get('status')}"
        )
        return

    runs = handoff["primary"]["runs"]
    site_bundle = {
        "schema_version": SITE_SCHEMA,
        "publication_status": "ready",
        "generated_at_utc": generated_at,
        "source": {
            "repository": "https://github.com/Atlas3DSS/nulspec",
            "evidence_revision": evidence_revision,
            "handoff_path": handoff_relative,
            "handoff_sha256": sha256(raw_handoff),
            "handoff_schema_version": HANDOFF_SCHEMA,
            "source_publication_status": TECHNICAL_GATE,
            "declared_artifact_count": len(declared_artifacts),
        },
        "study": handoff["study"],
        "metrics_schema": handoff["metrics_schema"],
        "classification": handoff["classification"],
        "paper_reported_accuracy": handoff["paper_reported_accuracy"],
        "primary": handoff["primary"],
        "diagnostics": handoff["diagnostics"],
        "compute": handoff["compute"],
        "artifacts": public_artifacts,
        "routes": handoff["routes"],
        "extension_vote": handoff["extension_vote"],
        "final_peer_review": final_review,
        "author_email": {
            "draft_sha256": author_email_sha256,
            "public_draft": False,
            "eligible_for_human_approval": final_review[
                "author_email_eligible_for_human_approval"
            ],
            "dispatch_authorized": final_review[
                "author_email_dispatch_authorized"
            ],
            "human_approval_required": final_review[
                "author_email_human_approval_required"
            ],
            "approval_status": final_review["author_email_approval_status"],
        },
        "completion": {
            "registered_runs": len(runs),
            "terminal_runs": len(runs),
            "claim_ready_runs": len(runs),
            "gates": {
                "analysis_complete": True,
                "scientific_review_complete": True,
                "artifact_audit_complete": True,
                "public_export_hygiene_complete": True,
                "typed_accuracy_frontend_complete": True,
            },
        },
        "frozen_primary_result": {
            "registered_runs": len(runs),
            "claim_ready_runs": len(runs),
            "may_be_rewritten_by_extension": False,
        },
    }
    verify_public_value(site_bundle)
    bundle_bytes = (json.dumps(site_bundle, indent=2, sort_keys=True) + "\n").encode()

    for destination, content in staged:
        atomic_write(destination, content)
    destination = site_root / "site-data" / "publications" / f"study-{study_id}.json"
    atomic_write(destination, bundle_bytes)
    print(
        "NULSPEC_ACCURACY_PUBLICATION_IMPORTED "
        f"study={study_id} runs={len(runs)} bundle_sha256={sha256(bundle_bytes)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--site-root", type=Path, default=Path.cwd())
    parser.add_argument("--evidence-revision", required=True)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate typed compatibility without resolving a pending research gate",
    )
    args = parser.parse_args()
    try:
        import_accuracy_publication(
            args.handoff.resolve(),
            args.source_root.resolve(),
            args.site_root.resolve(),
            args.evidence_revision,
            args.check_only,
        )
    except (ImportError, OSError, TypeError, KeyError, ValueError) as exc:
        print(f"NULSPEC_ACCURACY_IMPORT_FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
