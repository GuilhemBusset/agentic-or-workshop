from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class ChecklistCoverage(BaseModel):
    goal_clarity: bool
    allowed_context: bool
    forbidden_context: bool
    output_schema: bool
    acceptance_checks: bool
    failure_handling: bool


class EvidenceItem(BaseModel):
    finding: str
    excerpt: str


class JudgeResponse(BaseModel):
    completeness: int = Field(ge=0, le=100)
    ambiguity_risk: int = Field(ge=0, le=100)
    verification_readiness: int = Field(ge=0, le=100)
    rework_risk: int = Field(ge=0, le=100)
    summary: str
    parameter_effects: list[str]
    coverage: ChecklistCoverage
    blocking_issues: list[str]
    improvement_actions: list[str]
    evidence: list[EvidenceItem]
    confidence: Literal["low", "medium", "high"]


class JudgeRequest(BaseModel):
    stage: Literal["generic", "lp", "mip"]
    mode: Literal["single", "team", "review"]
    specificity_bias: int = Field(ge=0, le=100)
    thinking_effort: Literal["low", "medium", "high"]
    strictness: Literal["relaxed", "standard", "strict"]
    evidence_depth: Literal["minimal", "standard", "detailed"]
    prompt_text: str = Field(min_length=8)
    requirements: ChecklistCoverage


ChecklistCoverage.model_rebuild()
EvidenceItem.model_rebuild()
JudgeResponse.model_rebuild()
JudgeRequest.model_rebuild()


JUDGE_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "completeness",
        "ambiguity_risk",
        "verification_readiness",
        "rework_risk",
        "summary",
        "parameter_effects",
        "coverage",
        "blocking_issues",
        "improvement_actions",
        "evidence",
        "confidence",
    ],
    "properties": {
        "completeness": {"type": "integer", "minimum": 0, "maximum": 100},
        "ambiguity_risk": {"type": "integer", "minimum": 0, "maximum": 100},
        "verification_readiness": {"type": "integer", "minimum": 0, "maximum": 100},
        "rework_risk": {"type": "integer", "minimum": 0, "maximum": 100},
        "summary": {"type": "string"},
        "parameter_effects": {"type": "array", "items": {"type": "string"}},
        "coverage": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "goal_clarity",
                "allowed_context",
                "forbidden_context",
                "output_schema",
                "acceptance_checks",
                "failure_handling",
            ],
            "properties": {
                "goal_clarity": {"type": "boolean"},
                "allowed_context": {"type": "boolean"},
                "forbidden_context": {"type": "boolean"},
                "output_schema": {"type": "boolean"},
                "acceptance_checks": {"type": "boolean"},
                "failure_handling": {"type": "boolean"},
            },
        },
        "blocking_issues": {"type": "array", "items": {"type": "string"}},
        "improvement_actions": {"type": "array", "items": {"type": "string"}},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["finding", "excerpt"],
                "properties": {
                    "finding": {"type": "string"},
                    "excerpt": {"type": "string"},
                },
            },
        },
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
}


RUBRIC_PROMPT = """
You are a strict prompt-contract judge for optimization workshop artifacts.

Evaluate ONE prompt and return only JSON matching the required schema.

Interpretation rules:
- stage can be generic, lp, or mip.
- mode can be single, team, or review.
- strictness controls grading severity.
- specificity_bias is a user-selected bias: higher values mean stricter expectations for explicitness.
- requirements booleans indicate what the user currently expects to be present.
- evidence_depth controls how many evidence items to include:
  - minimal: 1-2
  - standard: 3-5
  - detailed: 6-8

Scoring intent:
- completeness: explicit objective, scope, constraints, deliverables, domain framing.
- ambiguity_risk: penalize vague adjectives (best/practical/nice/quick), missing metric definitions, unclear scope.
- verification_readiness: presence of acceptance checks, testability, reproducibility cues.
- rework_risk: high when completeness/verification is weak or ambiguity is high.

Coverage booleans reflect whether each contract element appears in the prompt text.

Blocking issues:
- Add issues when requirements demand an element but the prompt does not provide it.
- Keep each issue concise and actionable.

parameter_effects:
- Explain how strictness, specificity_bias, stage, and mode influenced the score.

summary:
- 1-2 sentence concise diagnosis.
""".strip()


LAB_DIR = Path(__file__).resolve().parent
REPO_ROOT = LAB_DIR.parents[3]
SKILL_PATH = LAB_DIR / "skills/prompt-contract-judge/SKILL.md"

JUDGE_BACKEND = os.environ.get("JUDGE_BACKEND", "codex")

CLAUDE_MODEL_TIERS: dict[str, str] = {
    "low": "claude-haiku-4-5-20251001",
    "medium": "claude-sonnet-4-6",
    "high": "claude-opus-4-6",
}

app = FastAPI(title="Explorer Prompt Contract Judge", version="0.4.0")
app.add_middleware(
    cast(Any, CORSMiddleware),
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_judge_prompt(evaluation_payload: dict[str, object], skill_text: str) -> str:
    return (
        "Use the following skill to perform the judgment.\n"
        "Follow its output contract and judging rules exactly.\n\n"
        "=== SKILL: prompt-contract-judge ===\n"
        f"{skill_text}\n"
        "=== END SKILL ===\n\n"
        f"{RUBRIC_PROMPT}\n\n"
        "Evaluate this payload:\n"
        f"{json.dumps(evaluation_payload, indent=2)}\n\n"
        "Return only JSON matching the provided output schema."
    )


def _build_codex_command(
    prompt: str,
    model: str,
    thinking_effort: str,
    schema_path: Path,
    output_path: Path,
) -> tuple[list[str], Path | None]:
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--cd",
        str(REPO_ROOT),
        "--color",
        "never",
        "--model",
        model,
        "-c",
        f"model_reasoning_effort={thinking_effort}",
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        prompt,
    ]
    return cmd, output_path


def _build_claude_code_command(
    prompt: str,
    model: str,
    thinking_effort: str,
    schema_path: Path,
    output_path: Path,
) -> tuple[list[str], None]:
    schema_text = json.dumps(JUDGE_SCHEMA, indent=2)
    full_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: Return ONLY valid JSON matching this exact schema "
        "(no markdown fences, no extra text):\n"
        f"{schema_text}"
    )
    cmd = [
        "claude",
        "-p",
        full_prompt,
        "--output-format",
        "json",
        "--model",
        model,
        "--max-turns",
        "1",
    ]
    return cmd, None


_JSON_FENCE_RE = None


def _strip_markdown_json(text: str) -> str:
    global _JSON_FENCE_RE  # noqa: PLW0603
    if _JSON_FENCE_RE is None:
        import re

        _JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    m = _JSON_FENCE_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def _extract_claude_code_json(raw: str) -> dict[str, object]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        return parsed
    # --output-format json envelope: {"type":"result", "result":"...", ...}
    if "result" in parsed:
        inner = parsed["result"]
        if isinstance(inner, dict):
            return inner
        if isinstance(inner, str):
            cleaned = _strip_markdown_json(inner)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
    return parsed


def _get_backend_label() -> str:
    return "Claude Code" if JUDGE_BACKEND == "claude-code" else "Codex"


def run_judge(payload: JudgeRequest) -> JudgeResponse:
    if not SKILL_PATH.exists():
        raise HTTPException(
            status_code=500, detail=f"Skill file not found: {SKILL_PATH}"
        )

    skill_text = SKILL_PATH.read_text(encoding="utf-8")
    evaluation_payload = {
        "stage": payload.stage,
        "mode": payload.mode,
        "specificity_bias": payload.specificity_bias,
        "strictness": payload.strictness,
        "evidence_depth": payload.evidence_depth,
        "requirements": payload.requirements.model_dump(),
        "prompt_text": payload.prompt_text,
    }

    prompt = _build_judge_prompt(evaluation_payload, skill_text)

    timeout_sec = int(
        os.environ.get(
            "JUDGE_TIMEOUT_SEC",
            os.environ.get("CODEX_JUDGE_TIMEOUT_SEC", "240"),
        )
    )

    backend = JUDGE_BACKEND
    label = _get_backend_label()

    if backend == "claude-code":
        model = os.environ.get(
            "CLAUDE_CODE_JUDGE_MODEL",
            CLAUDE_MODEL_TIERS.get(payload.thinking_effort, "claude-sonnet-4-6"),
        )
    else:
        model = os.environ.get("CODEX_JUDGE_MODEL", "gpt-5.3-codex")

    try:
        with tempfile.TemporaryDirectory(prefix="judge-") as tmp:
            schema_path = Path(tmp) / "judge_schema.json"
            output_path = Path(tmp) / "judge_output.json"
            schema_path.write_text(json.dumps(JUDGE_SCHEMA, indent=2), encoding="utf-8")

            if backend == "claude-code":
                cmd, out_file = _build_claude_code_command(
                    prompt, model, payload.thinking_effort, schema_path, output_path
                )
            else:
                cmd, out_file = _build_codex_command(
                    prompt, model, payload.thinking_effort, schema_path, output_path
                )

            run_kwargs: dict[str, Any] = {
                "capture_output": True,
                "text": True,
                "check": False,
                "timeout": timeout_sec,
            }
            if backend == "claude-code":
                run_kwargs["cwd"] = str(REPO_ROOT)

            run = subprocess.run(cmd, **run_kwargs)

            if run.returncode != 0:
                stderr_tail = "\n".join(run.stderr.strip().splitlines()[-8:])
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"{label} judge failed. "
                        f"Ensure {label} CLI is installed and logged in. "
                        f"details: {stderr_tail or 'no stderr'}"
                    ),
                )

            if out_file is not None:
                if not out_file.exists():
                    raise HTTPException(
                        status_code=502,
                        detail=f"{label} judge succeeded but produced no output file",
                    )
                output_text = out_file.read_text(encoding="utf-8").strip()
            else:
                output_text = run.stdout.strip()

            if not output_text:
                raise HTTPException(
                    status_code=502,
                    detail=f"{label} judge returned empty output",
                )

            if backend == "claude-code":
                parsed = _extract_claude_code_json(output_text)
            else:
                parsed = json.loads(output_text)

            return JudgeResponse.model_validate(parsed)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                f"{label} judge timed out after {timeout_sec}s. "
                "Increase JUDGE_TIMEOUT_SEC for slower networks."
            ),
        ) from exc
    except FileNotFoundError as exc:
        cli_name = "claude" if backend == "claude-code" else "codex"
        raise HTTPException(
            status_code=500,
            detail=f"{cli_name} CLI not found in PATH",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"{label} output was not valid JSON: {exc}",
        ) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "backend": JUDGE_BACKEND}


@app.post("/judge", response_model=JudgeResponse)
def judge(payload: JudgeRequest) -> JudgeResponse:
    return run_judge(payload)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("JUDGE_HOST", "127.0.0.1")
    port = int(os.environ.get("JUDGE_PORT", "8008"))
    uvicorn.run(app, host=host, port=port)
