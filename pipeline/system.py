#!/usr/bin/env python3
"""pipeline/system.py — the MODULAR SYSTEM contract (compose agentic-infra instances).

Each agentic-infra instance is a SYSTEM with a ROLE. This kernel makes systems modular + composable:

  - `System` declares: name, role, `produces` (outputs), `consumes` (inputs), `gate` (the deterministic
    "is it real" check), and the checkpoints it owns.
  - `systems.json` (data/systems.json) declares the whole organism: multiple systems + their handoffs
    (which system's output feeds which system's input).
  - The coordinator (`compose`) checks the handoffs resolve (A.produces ⊇ B.consumes) and is acyclic, so
    the organism is a well-formed DAG of systems.

Deterministic + stdlib. Usage:
  python3 pipeline/system.py --register --name ingest --role "find+normalize" --produces verses --consumes sources --gate "test -f data/corpus.json"
  python3 pipeline/system.py --compose data/systems.json     # verify the handoffs + acyclicity
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSTEMS = ROOT / "data" / "systems.json"


@dataclass
class System:
    """A modular system with a role + an explicit interface (inputs/outputs + a gate)."""
    name: str
    role: str
    produces: list = field(default_factory=list)   # artifact types this system outputs
    consumes: list = field(default_factory=list)   # artifact types this system needs as input
    gate: str = "true"                             # the deterministic "is it real" check
    depends_on: list = field(default_factory=list)  # which systems must run first

    def to_dict(self) -> dict:
        return {"name": self.name, "role": self.role, "produces": self.produces,
                "consumes": self.consumes, "gate": self.gate, "depends_on": self.depends_on}

    @classmethod
    def from_dict(cls, d: dict) -> "System":
        return cls(d["name"], d.get("role", ""), d.get("produces", []), d.get("consumes", []),
                   d.get("gate", "true"), d.get("depends_on", []))


def _load() -> dict:
    if SYSTEMS.exists():
        return json.loads(SYSTEMS.read_text())
    return {"schema": "agentic-infra.systems.v1", "systems": {}}


def _save(d: dict) -> None:
    SYSTEMS.parent.mkdir(parents=True, exist_ok=True)
    SYSTEMS.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def register(name: str, role: str, produces: list, consumes: list, gate: str, depends_on: list) -> None:
    d = _load()
    d["systems"][name] = System(name, role, produces, consumes, gate, depends_on).to_dict()
    _save(d)
    print(f"registered system '{name}': {role} (produces {produces}, consumes {consumes}, gate '{gate}')")


def compose(spec_path: str) -> int:
    """Verify a multi-system organism: handoffs resolve + the dependency graph is acyclic."""
    spec = json.loads(Path(spec_path).read_text())
    systems = spec.get("systems", {})
    if not systems:
        print("no systems in spec"); return 1
    # 1. every dependency (depends_on) exists
    for name, s in systems.items():
        for dep in s.get("depends_on", []):
            if dep not in systems:
                print(f"✗ system '{name}' depends on unknown system '{dep}'"); return 1
    # 2. every 'consumes' artifact is produced by a dependency (handoff resolves) — EXCEPT the root
    #    system(s) (no depends_on), which legitimately consume external input.
    for name, s in systems.items():
        deps = s.get("depends_on", [])
        if not deps:
            continue  # root system: consumes external artifacts, no upstream to resolve against
        for art in s.get("consumes", []):
            produced = [d for d in deps if art in systems[d].get("produces", [])]
            if not produced:
                print(f"✗ system '{name}' consumes '{art}' but no dependency produces it"); return 1
    # 3. acyclicity (topological check on depends_on)
    degree = {n: len(s.get("depends_on", [])) for n, s in systems.items()}
    order = []
    ready = [n for n, deg in degree.items() if deg == 0]
    while ready:
        n = ready.pop(); order.append(n)
        for m, s in systems.items():
            if n in s.get("depends_on", []) and m not in order:
                degree[m] -= 1
                if degree[m] == 0:
                    ready.append(m)
    if len(order) != len(systems):
        print(f"✗ dependency cycle detected (only {len(order)}/{len(systems)} ordered)")
        return 1
    print(f"✓ ORGANISM VALID: {len(systems)} systems, acyclic, handoffs resolve. Order: {' → '.join(order)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--name", default="")
    ap.add_argument("--role", default="")
    ap.add_argument("--produces", default="")
    ap.add_argument("--consumes", default="")
    ap.add_argument("--gate", default="true")
    ap.add_argument("--depends", default="")
    ap.add_argument("--compose", default="")
    a = ap.parse_args()
    if a.register:
        register(a.name, a.role, [x for x in a.produces.split(",") if x],
                 [x for x in a.consumes.split(",") if x], a.gate,
                 [x for x in a.depends.split(",") if x])
        return 0
    if a.compose:
        return compose(a.compose)
    ap.print_help(); return 0


if __name__ == "__main__":
    sys.exit(main())
