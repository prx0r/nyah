#!/usr/bin/env python3
"""pipeline/worker_pool.py — worker type registry + task assignment logic.

Defines the worker types available to nyah, their capabilities, and how tasks are assigned.
Workers are abstract — they represent a capability (discovery, resolution, fetching, etc.),
not a specific process. The actual execution happens via hermes subagents or direct calls.

Usage:
  python3 pipeline/worker_pool.py --status
  python3 pipeline/worker_pool.py --demo
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class WorkerType:
    """A registered worker type."""
    name: str
    description: str
    capabilities: list[str]  # task types this worker can handle
    max_concurrency: int = 1
    current_load: int = 0
    status: str = "AVAILABLE"  # AVAILABLE, BUSY, OFFLINE

    @property
    def available(self) -> bool:
        return self.status == "AVAILABLE" and self.current_load < self.max_concurrency

    def assign(self) -> bool:
        if not self.available:
            return False
        self.current_load += 1
        if self.current_load >= self.max_concurrency:
            self.status = "BUSY"
        return True

    def release(self) -> None:
        self.current_load = max(0, self.current_load - 1)
        if self.status == "BUSY" and self.current_load < self.max_concurrency:
            self.status = "AVAILABLE"


# The default worker pool
DEFAULT_WORKERS = [
    WorkerType("discovery", "Finds new sources via adapter sweeps, protocol probing, and graph expansion",
               ["FIND_SOURCE", "FIND_ETEXT", "FIND_EDITION"], max_concurrency=2),
    WorkerType("resolver", "Resolves identity conflicts and rights questions",
               ["RESOLVE_IDENTITY", "RESOLVE_RIGHTS"], max_concurrency=1),
    WorkerType("fetcher", "Fetches resources from providers and runs OCR",
               ["FETCH_RESOURCE", "OCR_RESOURCE"], max_concurrency=2),
    WorkerType("normalizer", "Normalizes raw text into clean e-texts",
               ["NORMALIZE_ETEXT"], max_concurrency=2),
    WorkerType("searcher", "Searches for translations across providers",
               ["SEARCH_TRANSLATION"], max_concurrency=2),
    WorkerType("translator", "Runs the Factory translation pipeline",
               ["TRANSLATE"], max_concurrency=1),
    WorkerType("aligner", "Aligns translations to source passages",
               ["ANCHOR_TRANSLATION"], max_concurrency=2),
]


class WorkerPool:
    """Registry of available worker types."""

    def __init__(self, workers: list[WorkerType] | None = None):
        self.workers = {w.name: w for w in (workers or DEFAULT_WORKERS)}

    def get_worker_for_task(self, task_type: str) -> WorkerType | None:
        """Find an available worker that can handle this task type."""
        for w in self.workers.values():
            if task_type in w.capabilities and w.available:
                return w
        return None

    def assign_task(self, task_type: str) -> tuple[WorkerType, bool] | None:
        """Try to assign a task to an available worker. Returns (worker, success)."""
        w = self.get_worker_for_task(task_type)
        if w is None:
            return None
        success = w.assign()
        return (w, success)

    def status(self) -> dict:
        """Return pool status summary."""
        return {
            "total_workers": len(self.workers),
            "available": sum(1 for w in self.workers.values() if w.available),
            "busy": sum(1 for w in self.workers.values() if w.status == "BUSY"),
            "offline": sum(1 for w in self.workers.values() if w.status == "OFFLINE"),
            "workers": {
                name: {
                    "status": w.status,
                    "load": f"{w.current_load}/{w.max_concurrency}",
                    "capabilities": w.capabilities,
                }
                for name, w in self.workers.items()
            },
        }

    def print_status(self) -> None:
        """Print human-readable status."""
        st = self.status()
        print(f"=== WORKER POOL ({st['total_workers']} workers) ===")
        print(f"  available: {st['available']}  busy: {st['busy']}  offline: {st['offline']}")
        print()
        for name, info in st["workers"].items():
            marker = "●" if info["status"] == "AVAILABLE" else "○" if info["status"] == "BUSY" else "✕"
            caps = ", ".join(info["capabilities"])
            print(f"  {marker} {name:15} {info['load']:5}  [{caps}]")


def demo() -> None:
    """Demo worker pool operations."""
    pool = WorkerPool()

    print("=== INITIAL STATUS ===")
    pool.print_status()

    print("\n=== ASSIGNING TASKS ===")
    test_tasks = ["FIND_SOURCE", "TRANSLATE", "RESOLVE_IDENTITY", "FIND_SOURCE", "FETCH_RESOURCE"]
    for tt in test_tasks:
        result = pool.assign_task(tt)
        if result:
            w, ok = result
            print(f"  {tt:22} → {w.name} ({'OK' if ok else 'FAIL'})")
        else:
            print(f"  {tt:22} → NO WORKER AVAILABLE")

    print("\n=== AFTER ASSIGNMENTS ===")
    pool.print_status()

    print("\n=== RELEASING WORKERS ===")
    pool.workers["discovery"].release()
    pool.workers["translator"].release()
    print("  released discovery + translator")
    print()
    pool.print_status()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
        return 0
    if a.status:
        pool = WorkerPool()
        pool.print_status()
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
