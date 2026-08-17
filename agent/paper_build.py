#!/usr/bin/env python3
"""agent/paper_build.py — the NUMBER-INJECT paper build (bulletproof anti-drift).

Stolen mechanism (verified: AI-Scientist number-inject templating + CI-compiled PDF): the paper's headline
numbers and tables are BUILD OUTPUTS of the content-addressed run records — never hand-typed prose. So the
PDF cannot state a number that isn't in the log. This script:

  1. Reads the content-addressed runs (run_recorder) + the experiment registry.
  2. Injects the real numbers into a .tex template (placeholders).
  3. Compiles to PDF (if pdflatex is available) — a "one command produces the paper" gate.

Usage:
  python3 agent/paper_build.py                 # inject numbers from runs + registry, write .tex
  python3 agent/paper_build.py --out docs/     # write into a docs dir
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
TEMPLATE = ROOT / "agent" / "paper_template.tex"
OUT = ROOT / "docs"


def _registry_rows():
    reg = ROOT / "data" / "corpus" / "registries" / "experiments.jsonl"
    rows = []
    if reg.exists():
        for line in open(reg):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "avg_chrF" in r:
                rows.append(r)
    return rows


def _runs():
    from run_recorder import RunRecorder
    return RunRecorder().all()


def build(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = _registry_rows()
    runs = _runs()

    # build the metrics table from the real logs
    table_rows = "\n".join(
        f"    {r['experiment_id'][-12:]} & {r['avg_chrF']:.3f} & {r['avg_bleu1']:.3f} & "
        f"{str(r.get('avg_semantic','—'))} \\\\" for r in rows
    ) or "    — & — & — & — \\\\"
    n_runs = len(runs)
    n_exp = len(rows)
    sigs = ", ".join(r["run_signature"][:12] for r in runs[:5]) or "—"
    assert_cites = "; ".join(
        f"{r['nanopublication']['assertion']} (run {r['run_signature'][:12]})" for r in runs[:3]
    ) or "—"

    subs = {
        "@N_RUNS@": str(n_runs),
        "@N_EXP@": str(n_exp),
        "@RUN_SIGNATURES@": sigs,
        "@METRIC_TABLE@": table_rows,
        "@ASSERTION_CITATIONS@": assert_cites,
        "@DATE@": "2026",
    }
    tex = TEMPLATE.read_text() if TEMPLATE.exists() else _default_template()
    for k, v in subs.items():
        tex = tex.replace(k, v)
    out_file = out_dir / "sanskrit-benchmark-report.tex"
    out_file.write_text(tex)
    print(f"✓ injected numbers into {out_file} ({n_runs} runs, {n_exp} experiments)")

    # compile to PDF if available (the one-command gate)
    try:
        subprocess.run(["pdflatex", "-interaction=nonstopmode", str(out_file.name)],
                       cwd=out_dir, capture_output=True, text=True, timeout=120)
        pdf = out_dir / "sanskrit-benchmark-report.pdf"
        if pdf.exists():
            print(f"✓ compiled PDF: {pdf}")
        else:
            print("  (pdflatex ran but no PDF — check template)")
    except FileNotFoundError:
        print("  (pdflatex not installed — .tex written, PDF requires pdflatex/typst)")
    return 0


def _default_template() -> str:
    return r"""\documentclass{article}
\usepackage{booktabs}
\begin{document}
\title{Sanskrit Benchmark — Verified Result Report}
\author{sanskritbenchy}
\date{@DATE@}
\maketitle
\section{Runs}
Content-addressed runs: @N_RUNS@ (signatures: @RUN_SIGNATURES@)
\section{Experiments}
\begin{tabular}{lrrr}\toprule
Exp & chrF & bleu & semantic \\\midrule
@METRIC_TABLE@
\bottomrule\end{tabular}
\section{Verified assertions}
@ASSERTION_CITATIONS@
\end{document}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    return build(Path(args.out))


if __name__ == "__main__":
    sys.exit(main())
