from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "workshop").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError("Repository root not found")


REPO_ROOT = _repo_root()
SERVICE_PATH = (
    REPO_ROOT
    / "workshop"
    / "materials"
    / "part-00-fundamental"
    / "02-prompt-quality"
    / "llm_judge_service.py"
)


def _load_service(env_overrides: dict[str, str] | None = None):
    env_patch = env_overrides or {}
    with patch.dict("os.environ", env_patch, clear=False):
        spec = importlib.util.spec_from_file_location("llm_judge_service", SERVICE_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load judge service module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def service():
    return _load_service()


# ── Backend detection ──────────────────────────────────────────────


def test_default_backend_is_codex(service):
    assert service.JUDGE_BACKEND == "codex"


def test_backend_from_env():
    mod = _load_service({"JUDGE_BACKEND": "claude-code"})
    assert mod.JUDGE_BACKEND == "claude-code"


def test_backend_label_codex(service):
    with patch.object(service, "JUDGE_BACKEND", "codex"):
        assert service._get_backend_label() == "Codex"


def test_backend_label_claude_code(service):
    with patch.object(service, "JUDGE_BACKEND", "claude-code"):
        assert service._get_backend_label() == "Claude Code"


# ── _build_judge_prompt ────────────────────────────────────────────


def test_build_judge_prompt_contains_skill_and_payload(service):
    payload = {"stage": "generic", "prompt_text": "test prompt"}
    skill_text = "## Fake Skill\nDo something."
    result = service._build_judge_prompt(payload, skill_text)

    assert "=== SKILL: prompt-contract-judge ===" in result
    assert "## Fake Skill" in result
    assert "=== END SKILL ===" in result
    assert '"stage": "generic"' in result
    assert '"prompt_text": "test prompt"' in result
    assert "Return only JSON matching the provided output schema." in result
    assert service.RUBRIC_PROMPT in result


# ── _build_codex_command ───────────────────────────────────────────


def test_build_codex_command_structure(service):
    schema_p = Path("/tmp/schema.json")
    output_p = Path("/tmp/output.json")
    cmd, out_file = service._build_codex_command(
        "test prompt", "gpt-5.3-codex", "medium", schema_p, output_p
    )

    assert cmd[0] == "codex"
    assert "exec" in cmd
    assert "--output-schema" in cmd
    assert str(schema_p) in cmd
    assert "-o" in cmd
    assert str(output_p) in cmd
    assert "--model" in cmd
    assert "gpt-5.3-codex" in cmd
    assert "-c" in cmd
    assert "model_reasoning_effort=medium" in cmd
    assert cmd[-1] == "test prompt"
    assert out_file == output_p


# ── _build_claude_code_command ─────────────────────────────────────


def test_build_claude_code_command_structure(service):
    schema_p = Path("/tmp/schema.json")
    output_p = Path("/tmp/output.json")
    cmd, out_file = service._build_claude_code_command(
        "test prompt", "claude-sonnet-4-6", "high", schema_p, output_p
    )

    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert "--output-format" in cmd
    assert "json" in cmd
    assert "--model" in cmd
    assert "claude-sonnet-4-6" in cmd
    assert "--max-turns" in cmd
    assert "1" in cmd
    assert out_file is None

    prompt_idx = cmd.index("-p") + 1
    full_prompt = cmd[prompt_idx]
    assert "test prompt" in full_prompt
    assert "Thinking effort:" not in full_prompt
    assert "IMPORTANT: Return ONLY valid JSON" in full_prompt
    assert "--json-schema" not in cmd


# ── Shared helpers ─────────────────────────────────────────────────


def _make_judge_response() -> dict:
    return {
        "completeness": 75,
        "ambiguity_risk": 30,
        "verification_readiness": 60,
        "rework_risk": 25,
        "summary": "Solid prompt with minor gaps.",
        "parameter_effects": ["strictness raised threshold"],
        "coverage": {
            "goal_clarity": True,
            "allowed_context": True,
            "forbidden_context": False,
            "output_schema": True,
            "acceptance_checks": True,
            "failure_handling": False,
        },
        "blocking_issues": ["Missing forbidden context boundary"],
        "improvement_actions": ["Add explicit forbidden-context section"],
        "evidence": [{"finding": "No exclusion", "excerpt": "..."}],
        "confidence": "medium",
    }


def _make_judge_request(service):
    return service.JudgeRequest(
        stage="generic",
        mode="single",
        specificity_bias=50,
        thinking_effort="medium",
        strictness="standard",
        evidence_depth="standard",
        prompt_text="Goal: implement a feature. Allowed context: src/. Output: JSON.",
        requirements=service.ChecklistCoverage(
            goal_clarity=True,
            allowed_context=True,
            forbidden_context=False,
            output_schema=True,
            acceptance_checks=True,
            failure_handling=False,
        ),
    )


# ── CLAUDE_MODEL_TIERS ─────────────────────────────────────────────


def test_claude_model_tiers_has_all_levels(service):
    assert service.CLAUDE_MODEL_TIERS["low"] == "claude-haiku-4-5-20251001"
    assert service.CLAUDE_MODEL_TIERS["medium"] == "claude-sonnet-4-6"
    assert service.CLAUDE_MODEL_TIERS["high"] == "claude-opus-4-6"


def test_claude_code_model_resolved_from_thinking_effort(service):
    judge_output = _make_judge_response()
    envelope = {"type": "result", "result": json.dumps(judge_output)}

    captured_cmd = []

    def fake_subprocess_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps(envelope)
        result.stderr = ""
        return result

    with (
        patch.object(service, "JUDGE_BACKEND", "claude-code"),
        patch("subprocess.run", side_effect=fake_subprocess_run),
        patch.dict("os.environ", {}, clear=False),
    ):
        import os

        os.environ.pop("CLAUDE_CODE_JUDGE_MODEL", None)
        request = service.JudgeRequest(
            stage="generic",
            mode="single",
            specificity_bias=50,
            thinking_effort="high",
            strictness="standard",
            evidence_depth="standard",
            prompt_text="Goal: implement feature. Allowed context: src/.",
            requirements=service.ChecklistCoverage(
                goal_clarity=True,
                allowed_context=True,
                forbidden_context=False,
                output_schema=True,
                acceptance_checks=True,
                failure_handling=False,
            ),
        )
        service.run_judge(request)

    model_idx = captured_cmd.index("--model") + 1
    assert captured_cmd[model_idx] == "claude-opus-4-6"


def test_claude_code_env_var_overrides_tier(service):
    judge_output = _make_judge_response()
    envelope = {"type": "result", "result": json.dumps(judge_output)}

    captured_cmd = []

    def fake_subprocess_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps(envelope)
        result.stderr = ""
        return result

    with (
        patch.object(service, "JUDGE_BACKEND", "claude-code"),
        patch("subprocess.run", side_effect=fake_subprocess_run),
        patch.dict(
            "os.environ",
            {"CLAUDE_CODE_JUDGE_MODEL": "claude-custom-model"},
            clear=False,
        ),
    ):
        request = _make_judge_request(service)
        service.run_judge(request)

    model_idx = captured_cmd.index("--model") + 1
    assert captured_cmd[model_idx] == "claude-custom-model"


# ── _extract_claude_code_json ──────────────────────────────────────


def test_extract_result_dict(service):
    raw = json.dumps(
        {
            "type": "result",
            "result": {"completeness": 80, "summary": "good"},
            "session_id": "abc",
        }
    )
    parsed = service._extract_claude_code_json(raw)
    assert parsed["completeness"] == 80
    assert parsed["summary"] == "good"


def test_extract_result_json_string(service):
    raw = json.dumps(
        {
            "type": "result",
            "result": '{"completeness": 90, "summary": "great"}',
        }
    )
    parsed = service._extract_claude_code_json(raw)
    assert parsed["completeness"] == 90


def test_extract_result_markdown_fenced_json(service):
    raw = json.dumps(
        {
            "type": "result",
            "result": '```json\n{"completeness": 85, "summary": "nice"}\n```',
        }
    )
    parsed = service._extract_claude_code_json(raw)
    assert parsed["completeness"] == 85


def test_extract_passthrough_no_envelope(service):
    raw = json.dumps({"completeness": 60, "summary": "bare"})
    parsed = service._extract_claude_code_json(raw)
    assert parsed["completeness"] == 60


# ── Env var precedence ─────────────────────────────────────────────


def test_timeout_prefers_judge_timeout_sec():
    _load_service({"JUDGE_TIMEOUT_SEC": "300", "CODEX_JUDGE_TIMEOUT_SEC": "120"})
    import os

    with patch.dict(
        os.environ,
        {"JUDGE_TIMEOUT_SEC": "300", "CODEX_JUDGE_TIMEOUT_SEC": "120"},
    ):
        timeout = int(
            os.environ.get(
                "JUDGE_TIMEOUT_SEC",
                os.environ.get("CODEX_JUDGE_TIMEOUT_SEC", "240"),
            )
        )
    assert timeout == 300


def test_timeout_falls_back_to_codex_timeout():
    import os

    with patch.dict(
        os.environ,
        {"CODEX_JUDGE_TIMEOUT_SEC": "180"},
        clear=False,
    ):
        env = os.environ.copy()
        env.pop("JUDGE_TIMEOUT_SEC", None)
        timeout = int(
            env.get(
                "JUDGE_TIMEOUT_SEC",
                env.get("CODEX_JUDGE_TIMEOUT_SEC", "240"),
            )
        )
    assert timeout == 180


def test_timeout_falls_back_to_default():
    import os

    with patch.dict(os.environ, {}, clear=True):
        timeout = int(
            os.environ.get(
                "JUDGE_TIMEOUT_SEC",
                os.environ.get("CODEX_JUDGE_TIMEOUT_SEC", "240"),
            )
        )
    assert timeout == 240


# ── Integration: mocked subprocess for Codex backend ──────────────


def test_integration_codex_backend(service):
    judge_output = _make_judge_response()

    def fake_subprocess_run(cmd, **kwargs):
        output_path = None
        for i, arg in enumerate(cmd):
            if arg == "-o" and i + 1 < len(cmd):
                output_path = Path(cmd[i + 1])
                break
        if output_path is not None:
            output_path.write_text(json.dumps(judge_output), encoding="utf-8")
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with (
        patch.object(service, "JUDGE_BACKEND", "codex"),
        patch("subprocess.run", side_effect=fake_subprocess_run),
    ):
        request = _make_judge_request(service)
        response = service.run_judge(request)

    assert response.completeness == 75
    assert response.summary == "Solid prompt with minor gaps."
    assert response.confidence == "medium"


def test_integration_claude_code_backend(service):
    judge_output = _make_judge_response()
    envelope = {
        "type": "result",
        "result": json.dumps(judge_output),
        "session_id": "test-123",
    }

    def fake_subprocess_run(cmd, **kwargs):
        assert cmd[0] == "claude"
        assert "cwd" in kwargs
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps(envelope)
        result.stderr = ""
        return result

    with (
        patch.object(service, "JUDGE_BACKEND", "claude-code"),
        patch("subprocess.run", side_effect=fake_subprocess_run),
    ):
        request = _make_judge_request(service)
        response = service.run_judge(request)

    assert response.completeness == 75
    assert response.summary == "Solid prompt with minor gaps."
    assert response.confidence == "medium"
