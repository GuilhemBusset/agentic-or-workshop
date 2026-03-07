# Participant Exercise: Context, Agents, and Value

## Duration
- 20-25 minutes (solo or pairs)

## Objective
Apply the Part 00 concepts to your own optimization workflow and identify concrete changes for your next project iteration.

## Activity 1: Context Window Experiments (8 minutes)
Start with `00-llm-architecture-primer.html` for a quick architecture comparison, then use `context-window-lab.html` and run the scenarios below.

### Scenario A
- Set low-to-moderate context size.
- Increase signal-to-noise.
- Keep conflicts near zero.

Record:
- quality trend,
- risk trend,
- cost/latency trend.

### Scenario B
- Increase context size substantially.
- Hold relevance roughly constant.
- Add distractors.

Record:
- where quality plateaus,
- where costs rise faster than quality.

### Scenario C
- Keep facts constant.
- Switch recency from front-loaded to mixed.

Record:
- what changed in simulated quality/risk,
- one implication for prompt/document ordering in your own workflow.

## Activity 2: Agent Workflow Mapping (7 minutes)
Pick one current coding task in your research pipeline.

Fill the mini-canvas:
- `Plan`: What is the exact goal, constraint set, and acceptance criteria?
- `Act`: What files/tools should an agent touch?
- `Observe`: What evidence will prove correctness?
- `Revise`: What triggers a re-plan or human intervention?

Boundary checklist:
- allowed files,
- disallowed files,
- allowed commands,
- required tests.

## Activity 3: Paradigm Shift Reflection (7-10 minutes)
For your current project, answer each prompt in 2-3 sentences.

1. Where are you still spending effort as if code generation were the bottleneck?
2. What one quality gate would most improve reliability of your model outputs?
3. What one change would improve decision impact (not just code quality)?

## Reflection Rubric (Self-check)
Rate each item from 1 (unclear) to 3 (clear and actionable).

- I can explain context-window diminishing returns from my own experiment results.
- I can define concrete agent boundaries for one real task.
- I can separate code quality improvements from solution-impact improvements.
- I can state one immediate change to my research workflow.

## Deliverable
Submit a one-page note with:
- one screenshot or summary from Activity 1,
- your Plan/Act/Observe/Revise mini-canvas from Activity 2,
- top two actions from Activity 3 to apply in your next sprint.
