from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "workshop").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError("Repository root not found")


ROOT = _repo_root()
HTML_PATH = ROOT / Path(
    "workshop/materials/part-01-explorer-paradigm/02-visual-explorer/00-visual-explorer-live-lab.html"
)


def _run_node(snippet: str) -> dict:
    script = f"""
const fs = require('node:fs');
const vm = require('node:vm');

const htmlPath = {json.dumps(str(HTML_PATH.resolve()))};
const html = fs.readFileSync(htmlPath, 'utf8');
const matches = [...html.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)];
if (matches.length === 0) throw new Error('No script tag found in explorer html');
let src = matches[matches.length - 1][1];
src = src.replace(/init\\(\\)\\.catch\\([\\s\\S]*?\\);\\s*$/m, '');

globalThis.window = {{ location: {{ search: '' }}, innerWidth: 1280 }};
vm.runInThisContext(src, {{ filename: 'visual_explorer_inline.js' }});

{snippet}
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_core_required_tables_and_removed_legacy_controls() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")

    required_match = re.search(
        r"const\s+REQUIRED_TABLES\s*=\s*\[(.*?)\];",
        html,
        flags=re.DOTALL,
    )
    assert required_match is not None
    required = re.findall(r"'([^']+\.csv)'", required_match.group(1))
    assert required == [
        "depots.csv",
        "towns.csv",
        "arcs.csv",
        "scenarios.csv",
        "scenario_demands.csv",
    ]

    assert 'id="designSelect"' not in html
    assert 'id="seedReplay"' not in html


def test_build_data_and_validate_data_in_node_vm() -> None:
    result = _run_node(
        """
const data = buildData();
const issues = validateData(data);
console.log(JSON.stringify({
  depots: data.depots.length,
  towns: data.towns.length,
  arcs: data.arcs.length,
  scenarios: data.scenarios.length,
  scenarioDemands: data.scenarioDemands.length,
  issueCount: issues.length,
  badCount: issues.filter((x) => x.level === 'bad').length,
  hasScenarioById: data.scenarioById instanceof Map,
}));
"""
    )

    assert result["depots"] == 6
    assert result["towns"] == 12
    assert result["arcs"] == 72
    assert result["scenarios"] == 8
    assert result["scenarioDemands"] == 96
    assert result["badCount"] == 0
    assert result["hasScenarioById"] is True


def test_flow_and_metric_invariants_in_node_vm() -> None:
    result = _run_node(
        """
const data = buildData();
const state = {
  scenarioId: 'S01',
  timelineIndex: 0,
  timelineStep: TIMELINE_STEPS[0].id,
  allowShortages: false,
  penaltyP: 60,
  criticalBoost: 0.15,
  flowThreshold: 0,
  capacityFactor: 1,
  languageMode: 'plain',
};
const run = computeFlowsHeuristic(data, state);
const metrics = computeMetrics(data, state, run.flowByArc, run.unmetByTown);
const issues = validateState(data, state, run.flowByArc, run.unmetByTown, metrics);

let maxDemandResidual = 0;
for (const town of data.towns) {
  const tid = String(town.town_id);
  const demand = Number(metrics.demandByTown.get(tid) ?? town.base_demand ?? 0);
  let inbound = 0;
  for (const [pair, flow] of run.flowByArc.entries()) {
    if (pair.endsWith('|' + tid)) inbound += flow;
  }
  const unmet = Number(run.unmetByTown.get(tid) ?? 0);
  maxDemandResidual = Math.max(maxDemandResidual, Math.abs(inbound + unmet - demand));
}

let maxCapExcess = 0;
for (const depot of data.depots) {
  const did = String(depot.depot_id);
  const flow = Number(metrics.flowByDepot.get(did) ?? 0);
  const cap = Number(depot.capacity) * state.capacityFactor;
  maxCapExcess = Math.max(maxCapExcess, flow - cap);
}

console.log(JSON.stringify({
  flowArcCount: run.flowByArc.size,
  totalUnmet: metrics.totalUnmet,
  maxDemandResidual,
  maxCapExcess,
  stateBadCount: issues.filter((x) => x.level === 'bad').length,
}));
"""
    )

    assert result["flowArcCount"] > 0
    assert result["maxDemandResidual"] <= 1e-6
    assert result["maxCapExcess"] <= 1e-6
    assert result["stateBadCount"] == 0
