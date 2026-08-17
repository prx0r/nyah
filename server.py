#!/usr/bin/env python3
"""server.py — FastAPI server exposing all product engines.

Usage:
  python3 server.py
  curl -X POST http://localhost:8900/audit -d '{"source":"namah shivaya","candidate":"Homage to Shiva"}'
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(Path("/root/patalacheckpoints/pipeline")))

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    app = FastAPI(title="Pāṭala Products API", version="0.1.0")
except ImportError:
    print("FastAPI not installed. Install with: pip install fastapi uvicorn")
    sys.exit(1)


# ── Models ──────────────────────────────────────────────────────────────────

class TranslationProofRequest(BaseModel):
    source: str
    candidate: str

class ClaimRequest(BaseModel):
    source: str
    passage_text: str

class ArgumentRequest(BaseModel):
    source: str
    passage_text: str

class CruxRequest(BaseModel):
    pos_a: str
    pos_b: str

class ComparisonRequest(BaseModel):
    a: str
    b: str

class ResearchPacketRequest(BaseModel):
    query: str

class ContextBundleRequest(BaseModel):
    query: str
    budget: int = 8000

class BenchmarkRequest(BaseModel):
    n: int = 5


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    from product_wire import PRODUCTS
    return {"status": "ok", "products": len(PRODUCTS), "backend": "products"}


@app.post("/audit")
def audit(req: TranslationProofRequest):
    from product_wire import wire_translation_proof
    start = time.time()
    result = wire_translation_proof(req.source, req.candidate)
    result["duration_s"] = round(time.time() - start, 3)
    return result


@app.post("/claim")
def claim_endpoint(req: ClaimRequest):
    from product_wire import wire_claim
    start = time.time()
    result = wire_claim(req.source, req.passage_text)
    result["duration_s"] = round(time.time() - start, 3)
    return result


@app.post("/crux")
def crux_endpoint(req: CruxRequest):
    from product_wire import wire_crux
    start = time.time()
    result = wire_crux(req.pos_a, req.pos_b)
    result["duration_s"] = round(time.time() - start, 3)
    return result


@app.post("/comparison")
def comparison_endpoint(req: ComparisonRequest):
    from product_wire import wire_comparison
    start = time.time()
    result = wire_comparison(req.a, req.b)
    result["duration_s"] = round(time.time() - start, 3)
    return result


@app.post("/research")
def research_endpoint(req: ResearchPacketRequest):
    from product_wire import wire_research_packet
    start = time.time()
    result = wire_research_packet(req.query)
    result["duration_s"] = round(time.time() - start, 3)
    return result


@app.post("/context")
def context_endpoint(req: ContextBundleRequest):
    from product_wire import wire_context_bundle
    start = time.time()
    result = wire_context_bundle(req.query, req.budget)
    result["duration_s"] = round(time.time() - start, 3)
    return result


@app.post("/bench")
def bench_endpoint(req: BenchmarkRequest):
    from product_wire import wire_benchmark
    start = time.time()
    result = wire_benchmark(req.n)
    result["duration_s"] = round(time.time() - start, 3)
    return result


@app.get("/products")
def list_products():
    from product_wire import PRODUCTS
    return {name: info["inputs"] for name, info in PRODUCTS.items()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8900)
