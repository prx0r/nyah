#!/usr/bin/env python3
"""pipeline/product_wire.py — generic adapter to expose products as API endpoints.

Usage:
  python3 pipeline/product_wire.py --test translation_proof
  python3 pipeline/product_wire.py --list
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PRODUCTS_DIR = Path("/root/patalacheckpoints/pipeline/products")
sys.path.insert(0, str(PRODUCTS_DIR.parent))


def import_product(name: str):
    engine_path = PRODUCTS_DIR / name / "engine.py"
    if not engine_path.exists():
        raise FileNotFoundError(f"product not found: {name}")
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"product_{name}", engine_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wire_translation_proof(source: str, candidate: str) -> dict:
    from products.translation_proof.engine import translation_proof
    passage = {"source": {"text": source}, "l2_text": candidate, "l200": {}}
    result = translation_proof(passage)
    checks = result.get("audit_vector", {})
    gate = result.get("publication_gate", {})
    blocking = gate.get("blocking_dimensions", [])
    return {"product": "translation_proof", "checks": checks,
            "blocking": blocking, "gate": gate.get("decision", "BLOCKED" if blocking else "PASS"),
            "content_hash": result.get("content_hash", "")}


def wire_translation_studio(text: str, layer: str = "L2") -> dict:
    mod = import_product("translation_studio")
    funcs = [f for f in dir(mod) if not f.startswith("_") and callable(getattr(mod, f, None))]
    return {"product": "translation_studio", "layer": layer, "functions": funcs[:10]}


def wire_benchmark(n: int = 5) -> dict:
    mod = import_product("benchmark")
    funcs = [f for f in dir(mod) if not f.startswith("_") and callable(getattr(mod, f, None))]
    return {"product": "benchmark", "functions": funcs[:10]}


def wire_claim(source: str, passage_text: str) -> dict:
    mod = import_product("claim")
    funcs = [f for f in dir(mod) if not f.startswith("_") and callable(getattr(mod, f, None))]
    return {"product": "claim", "functions": funcs[:10]}


def wire_argument(source: str, passage_text: str) -> dict:
    mod = import_product("argument")
    funcs = [f for f in dir(mod) if not f.startswith("_") and callable(getattr(mod, f, None))]
    return {"product": "argument", "functions": funcs[:10]}


def wire_crux(pos_a: str, pos_b: str) -> dict:
    mod = import_product("crux")
    funcs = [f for f in dir(mod) if not f.startswith("_") and callable(getattr(mod, f, None))]
    return {"product": "crux", "functions": funcs[:10]}


def wire_comparison(a: str, b: str) -> dict:
    mod = import_product("comparison")
    funcs = [f for f in dir(mod) if not f.startswith("_") and callable(getattr(mod, f, None))]
    return {"product": "comparison", "functions": funcs[:10]}


def wire_research_packet(query: str) -> dict:
    mod = import_product("research_packet")
    funcs = [f for f in dir(mod) if not f.startswith("_") and callable(getattr(mod, f, None))]
    return {"product": "research_packet", "functions": funcs[:10]}


def wire_context_bundle(query: str, budget: int = 8000) -> dict:
    mod = import_product("context_bundle")
    funcs = [f for f in dir(mod) if not f.startswith("_") and callable(getattr(mod, f, None))]
    return {"product": "context_bundle", "functions": funcs[:10]}


PRODUCTS = {
    "translation_proof": {"wire": wire_translation_proof, "inputs": ["source", "candidate"]},
    "translation_studio": {"wire": wire_translation_studio, "inputs": ["text", "layer"]},
    "benchmark": {"wire": wire_benchmark, "inputs": ["n"]},
    "claim": {"wire": wire_claim, "inputs": ["source", "passage_text"]},
    "argument": {"wire": wire_argument, "inputs": ["source", "passage_text"]},
    "crux": {"wire": wire_crux, "inputs": ["pos_a", "pos_b"]},
    "comparison": {"wire": wire_comparison, "inputs": ["a", "b"]},
    "research_packet": {"wire": wire_research_packet, "inputs": ["query"]},
    "context_bundle": {"wire": wire_context_bundle, "inputs": ["query", "budget"]},
}


def call_product(name: str, **kwargs) -> dict:
    if name not in PRODUCTS:
        return {"error": f"unknown product: {name}", "available": list(PRODUCTS.keys())}
    try:
        start = time.time()
        result = PRODUCTS[name]["wire"](**kwargs)
        result["duration_s"] = round(time.time() - start, 3)
        return result
    except Exception as e:
        return {"error": str(e), "product": name}


def wire_product(name: str) -> bool:
    try:
        import_product(name)
        return True
    except Exception:
        return False


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default="")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for name, info in PRODUCTS.items():
            print(f"  {name:25} inputs: {info['inputs']}")
        return 0
    if a.test:
        try:
            import_product(a.test)
            print(f"  {a.test}: importable, wireable={wire_product(a.test)}")
        except Exception as e:
            print(f"  {a.test}: FAILED ({e})")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
