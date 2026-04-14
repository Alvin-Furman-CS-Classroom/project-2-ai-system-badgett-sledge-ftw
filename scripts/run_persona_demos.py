#!/usr/bin/env python3
"""
Run non-interactive recommendation demos for persona fixtures.

Examples:
  python scripts/run_persona_demos.py
  python scripts/run_persona_demos.py --persona persona_05_classical_choral
  python scripts/run_persona_demos.py --seed-count 2 --k 15
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONAS_ROOT = PROJECT_ROOT / "data" / "personas"
QUERY_CLI = PROJECT_ROOT / "src" / "search" / "query_cli.py"
KB_PATH = PROJECT_ROOT / "data" / "knowledge_base.json"


def _persona_dirs() -> list[Path]:
    if not PERSONAS_ROOT.exists():
        return []
    return sorted(
        [
            p
            for p in PERSONAS_ROOT.iterdir()
            if p.is_dir() and p.name.startswith("persona_") and (p / "user_profile.json").exists()
        ]
    )


def _run_for_persona(persona_dir: Path, args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(QUERY_CLI),
        "--kb",
        str(KB_PATH),
        "--persona-dir",
        str(persona_dir),
        "--seed-from-playlist",
        "--seed-count",
        str(args.seed_count),
        "--k",
        str(args.k),
        "--max-degree",
        str(args.max_degree),
        "--algorithm",
        args.algorithm,
        "--once",
    ]
    if args.algorithm == "beam":
        cmd.extend(["--beam-width", str(args.beam_width), "--beam-depth", str(args.beam_depth)])

    print("\n" + "=" * 78, flush=True)
    print(f"Persona demo: {persona_dir.name}", flush=True)
    print("=" * 78, flush=True)
    print("Command:", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=False)
    return proc.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repeatable non-interactive demos for persona fixtures.")
    parser.add_argument("--persona", default=None, help="Run only this persona slug (e.g. persona_01_college_commuter).")
    parser.add_argument("--seed-count", type=int, default=1, help="How many playlist MBIDs to use as seeds per persona.")
    parser.add_argument("--k", type=int, default=10, help="Top-K results from query_cli.")
    parser.add_argument("--max-degree", type=int, default=50, help="Neighbor cap for UCS/Beam.")
    parser.add_argument("--algorithm", choices=["ucs", "beam"], default="ucs", help="Retrieval algorithm.")
    parser.add_argument("--beam-width", type=int, default=10, help="Beam width (beam only).")
    parser.add_argument("--beam-depth", type=int, default=6, help="Beam depth (beam only).")
    args = parser.parse_args()

    personas = _persona_dirs()
    if args.persona:
        personas = [p for p in personas if p.name == args.persona]
        if not personas:
            print(f"Persona not found: {args.persona}")
            sys.exit(1)
    if not personas:
        print(f"No persona fixtures found under: {PERSONAS_ROOT}")
        sys.exit(1)

    failures = 0
    for persona_dir in personas:
        rc = _run_for_persona(persona_dir, args)
        if rc != 0:
            failures += 1

    if failures:
        print(f"\nCompleted with failures: {failures} persona(s) returned non-zero exit codes.")
        sys.exit(1)
    print("\nAll persona demos completed successfully.")


if __name__ == "__main__":
    main()
