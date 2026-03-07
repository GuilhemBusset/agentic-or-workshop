# Coding Agents Explainer

## Why This Matters for OR Research
Coding agents accelerate implementation, but they do not replace scientific reasoning. In optimization work, value comes from correct models, validated assumptions, and decision impact. The agent is a force multiplier when the workflow is explicit and test-driven.

## 1) What Is an Agent?
An agent is a goal-directed system that can take actions in an environment, observe outcomes, and adapt its next action.

Core properties:
- Goal: a target state or deliverable.
- Policy/plan: a strategy for deciding next actions.
- Tools: mechanisms to act (files, shell, APIs, editors, tests).
- Feedback loop: observation of results from the environment.
- Stop condition: done, blocked, or needs human input.

Practical distinction:
- Chat assistant: mostly returns text.
- Agent: executes actions, inspects results, and iterates until completion criteria are met.

## 2) What Is a Coding Agent?
A coding agent is an agent specialized for software tasks in a real repository and runtime.

Examples include Codex and Claude Code. In practice, both operate as workflow engines around the same loop:
- understand task and constraints,
- read relevant code and docs,
- propose and apply edits,
- run checks (tests/lint/type checks),
- revise until acceptance criteria pass.

## 3) How Coding Agents Work (General Loop)
1. Task intake
- Parse objective, constraints, and acceptance criteria.

2. Context gathering
- Read only task-relevant files and infer current architecture.

3. Planning
- Build a short execution plan with concrete edit and verification steps.

4. Acting
- Modify code/docs/config, run commands, and generate artifacts.

5. Observation
- Inspect test output, runtime behavior, error logs, and diff quality.

6. Revision
- Update assumptions, patch failures, and close edge cases.

7. Handoff
- Provide changed files, verification evidence, remaining risks, and next steps.

## 4) Reliability Controls (Non-Negotiable)
Coding-agent quality is mostly determined by workflow guardrails, not by model confidence.

Controls that matter most:
- Boundary controls: allowed files, commands, network, and approval rules.
- Context controls: minimum relevant context, explicit assumptions, no hidden dependencies.
- Contract controls: required outputs, path contracts, schema/types, behavior expectations.
- Verification controls: tests, lint, type checks, scenario checks.
- Traceability controls: plan, diffs, command evidence, unresolved risks.

## 5) Codex and Claude Code Through the Same Lens
This is a workflow comparison frame, not a benchmark claim.

Codex-style workflow strengths:
- Strong repo + terminal execution loop.
- Effective for implementation-heavy tasks with clear gates.
- Good momentum on iterative fix-verify cycles.

Claude Code-style workflow strengths:
- Strong synthesis of broad context and design alternatives.
- Useful for architecture framing and documentation-heavy tasks.
- Good at turning vague intent into structured tasks.

Common failure modes for both:
- Overconfident assumptions when requirements are underspecified.
- Missing edge cases without explicit tests.
- Drifting scope when context boundaries are unclear.

Guardrails for both:
- Define objective and acceptance criteria first.
- Restrict editable surface area.
- Require runnable verification before completion.
- Ask for explicit uncertainty and open questions.