#!/usr/bin/env python3
"""agent/memory.py — the deterministic temporal memory (DML, adopted from the RKA replay repo).

The agent's persistent, auditable memory of its decisions. Uses the Deterministic Memory Layer (DML) —
an event-sourced memory substrate (event log = truth, state = derived projection). Every agent decision
(what hypothesis was tried, what the metric was, what was kept/discarded) is an auditable event with
provenance + drift tracking. This is the anti-regression memory: the agent "remembers" past results across
sessions, so it doesn't re-hallucinate or re-litigate decisions.

Adopted from fuck-off/ecosystem/replay/deterministic-memory-layer (pure Python, event-sourced, stdlib).

Usage:
  from agent.memory import LabMemory
  mem = LabMemory()
  mem.record(step="hypothesis", key="compound-hint", metric=0.8, decision="keep")
  mem.search("compound")          # find past decisions about compounds
  mem.history("compound-hint")    # the full event history for one key
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# DML lives in the fuck-off ecosystem clone
_DML = Path("/root/fuck-off/ecosystem/replay/deterministic-memory-layer")
if _DML.exists() and str(_DML) not in sys.path:
    sys.path.insert(0, str(_DML))

MEM_DB = ROOT / "data" / "lab-memory.db"


class LabMemory:
    """The lab's deterministic temporal memory (wraps DML)."""

    def __init__(self, db: Path = MEM_DB):
        from dml.events import EventStore
        from dml.memory_api import MemoryAPI
        self.store = EventStore(str(db))
        self.api = MemoryAPI(self.store)

    def record(self, *, step: str, key: str, value: str = "", metric: float | None = None,
               decision: str = "observed") -> int:
        """Record one agent decision as an auditable memory event.

        confidence = the metric (how confident/valid the result was), correlation_id = the step,
        so the full provenance (which step, what metric) is stored with each fact.
        """
        return self.api.add_fact(key, value=str(value),
                                 confidence=float(metric) if metric is not None else 1.0,
                                 correlation_id=f"{step}:{decision}")

    def search(self, query: str) -> list:
        """Find past decisions matching a query (the anti-regression memory)."""
        try:
            return self.api.search(query)
        except Exception:
            return []

    def history(self, key: str) -> list:
        """The full auditable event history for one key."""
        try:
            return self.api.get_fact_history(key)
        except Exception:
            return []

    def trace(self, key: str) -> list:
        """The provenance chain for a fact (how it came to be)."""
        try:
            return self.api.trace_provenance(key)
        except Exception:
            return []

    def drift(self, seq1: int, seq2: int) -> dict:
        """Measure memory drift between two states (did a decision change over time?)."""
        try:
            return self.api.measure_drift(seq1, seq2).to_dict()
        except Exception:
            return {}


if __name__ == "__main__":
    mem = LabMemory()
    print("=== lab memory (deterministic, event-sourced) ===")
    mem.record(step="hypothesis", key="compound-hint",
               value="Decompose compounds first", metric=0.82, decision="keep")
    mem.record(step="hypothesis", key="terms-hint",
               value="Keep terms transliterated", metric=0.79, decision="keep")
    print("  recorded 2 decisions")
    print("  search 'compound':", len(mem.search("compound")), "hit(s)")
    print("  history 'compound-hint':", len(mem.history("compound-hint")), "event(s)")
