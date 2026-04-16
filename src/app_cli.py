#!/usr/bin/env python3
"""
Unified wizard-style CLI for the curated music recommendation system.

This entrypoint is meant to show how the modules fit together:

- Module 2: interactive survey + ratings loop to build preferences
- Module 4: optional ML training from playlists + ratings
- Module 3 (+4): interactive query over the knowledge base
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def _print_banner(title: str) -> None:
    bar = "=" * 70
    print(f"\n{bar}\n  {title}\n{bar}\n")


def _kb_exists() -> bool:
    kb_path = DATA_DIR / "knowledge_base.json"
    if not kb_path.exists():
        print(
            f"\n[!] Expected knowledge base at {kb_path}, but it was not found.\n"
            "    Run from the project root after building the KB."
        )
        return False
    return True


def _prompt_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        try:
            ans = input(prompt + suffix).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return default
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please answer y or n.")


def run_preferences_wizard() -> None:
    """
    Wrap the Module 2 hill-climbing preference loop.
    """
    from knowledge_base_wrapper import KnowledgeBase  # lazy import for faster startup
    from preferences.run_preference_loop import main as preference_loop_main

    _print_banner("MODULE 2: PREFERENCE SURVEY + RATINGS LOOP")

    if not _kb_exists():
        return

    kb_path = DATA_DIR / "knowledge_base.json"
    try:
        kb = KnowledgeBase(str(kb_path))
    except FileNotFoundError:
        # Redundant with _kb_exists but keeps messaging local.
        print(f"Could not load knowledge base from {kb_path}.")
        return

    print(f"Loaded knowledge base with {len(kb.songs)} songs.")
    print(
        "\nThis step will:\n"
        "- Ask a short survey about genres and moods you like.\n"
        "- Show you small batches of songs to rate.\n"
        "- Refine a rule-based preference model from your ratings.\n"
        "- Save `data/user_profile.json` and `data/user_ratings.json` for later steps.\n"
    )

    # The preference loop handles all interaction; we just call into it.
    preference_loop_main(
        batch_size=5,
        max_rounds=3,
        kb_path=str(kb_path),
    )


def _convert_simple_playlist_to_user_playlists(src_path: Path, dest_path: Path) -> None:
    """
    Convert a simple playlist JSON of the form:
        { "name": "...", "mbids": ["..."] }
    into the standard Module 4 schema:
        { "playlists": [ { "name": "...", "mbids": ["..."] } ] }
    """
    import json

    with src_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    name = data.get("name") or "user_playlist"
    mbids = data.get("mbids") or []
    wrapped = {"playlists": [{"name": name, "mbids": mbids}]}

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("w", encoding="utf-8") as f:
        json.dump(wrapped, f, indent=2)

    print(f"\nWrote normalized playlists file to {dest_path} (from {src_path}).")


def ensure_playlists_file_interactive() -> Optional[Path]:
    """
    Guide the user to provide a playlists file for Module 4 training.

    Returns the path to `user_playlists.json` (or equivalent) or None if the
    user chooses to skip ML training.
    """
    import json

    default_standard = DATA_DIR / "user_playlists.json"
    default_simple = DATA_DIR / "playlists" / "user_playlist_v1.json"

    print(
        "\nModule 4 uses playlists as positive training examples.\n"
        "You can either:\n"
        "  1) Point at an existing `user_playlists.json` in the documented schema, or\n"
        "  2) Convert a simple playlist file like `data/playlists/user_playlist_v1.json`.\n"
    )

    if default_standard.exists():
        print(f"Found existing playlists file at {default_standard}.")
        try:
            with default_standard.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict) and isinstance(payload.get("playlists"), list):
                if not _prompt_yes_no("Use this existing playlists file?", default=True):
                    pass
                else:
                    return default_standard
        except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError):
            print("Existing playlists file could not be parsed; you may choose another.")

    print("Playlist options:")
    print("  [1] Use / convert from a simple playlist file (v1 format).")
    print("  [2] Point at an existing user_playlists.json.")
    print("  [3] Skip playlists / ML training for now.")

    while True:
        choice = input("Choose an option [1-3]: ").strip()
        if choice not in ("1", "2", "3"):
            print("Please enter 1, 2, or 3.")
            continue

        if choice == "3":
            return None

        if choice == "1":
            path_str = input(
                f"Path to simple playlist JSON "
                f"(default: {default_simple}): "
            ).strip()
            if not path_str:
                path = default_simple
            else:
                path = Path(path_str)
            if not path.exists():
                print(f"File {path} not found.")
                continue
            dest = default_standard
            if dest.exists():
                if not _prompt_yes_no(
                    f"{dest} already exists. Overwrite with converted playlist?", default=False
                ):
                    continue
            try:
                _convert_simple_playlist_to_user_playlists(path, dest)
            except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:  # pragma: no cover - defensive
                print(f"Failed to convert playlist: {e}")
                continue
            return dest

        if choice == "2":
            path_str = input(
                f"Path to user_playlists.json "
                f"(default: {default_standard}): "
            ).strip()
            if not path_str:
                path = default_standard
            else:
                path = Path(path_str)
            if not path.exists():
                print(f"File {path} not found.")
                continue
            return path


def run_ml_training_wizard(playlists_path: Optional[Path]) -> None:
    """
    Run Module 4 offline training using the provided playlists (if any)
    and any existing ratings.
    """
    from ml.train_module4 import train_module4_scorer

    _print_banner("MODULE 4: OFFLINE ML TRAINING FROM PLAYLISTS + RATINGS")

    if not _kb_exists():
        return

    if playlists_path is None:
        print(
            "No playlists file provided; Module 4 training will have only ratings (if any).\n"
            "You can still run this step, but it may produce weak or empty models.\n"
        )

    kb_path = DATA_DIR / "knowledge_base.json"
    ratings_path = DATA_DIR / "user_ratings.json"
    scorer_artifact = DATA_DIR / "module4_scorer.json"
    reranker_artifact = DATA_DIR / "module4_reranker.json"

    if scorer_artifact.exists() or reranker_artifact.exists():
        if not _prompt_yes_no(
            "Existing Module 4 artifacts detected. Overwrite with new training?", default=False
        ):
            print("Keeping existing artifacts; skipping training.")
            return

    playlists_arg = playlists_path if playlists_path is not None else DATA_DIR / "user_playlists.json"

    train_module4_scorer(
        kb_path=str(kb_path),
        playlists_path=str(playlists_arg),
        ratings_path=str(ratings_path),
        artifact_path=str(scorer_artifact),
        reranker_artifact_path=str(reranker_artifact),
    )


def _artifacts_exist() -> tuple[bool, bool]:
    scorer_artifact = DATA_DIR / "module4_scorer.json"
    reranker_artifact = DATA_DIR / "module4_reranker.json"
    return scorer_artifact.exists(), reranker_artifact.exists()


def run_query_wizard() -> None:
    """
    Run the interactive query CLI (Module 3, optionally enhanced with Module 4).
    """
    import search.query_cli as query_cli

    _print_banner("MODULE 3 + 4: INTERACTIVE QUERY OVER KNOWLEDGE BASE")

    if not _kb_exists():
        return

    kb_path = DATA_DIR / "knowledge_base.json"
    profile_path = DATA_DIR / "user_profile.json"
    ratings_path = DATA_DIR / "user_ratings.json"
    scorer_artifact = DATA_DIR / "module4_scorer.json"
    reranker_artifact = DATA_DIR / "module4_reranker.json"

    use_ratings = ratings_path.exists()
    has_scorer, has_reranker = _artifacts_exist()

    print("This step uses:")
    print(f"- KB: {kb_path}")
    print(f"- Profile: {profile_path} (expected from Module 2)")
    if use_ratings:
        print(f"- Ratings: {ratings_path}")
    else:
        print("- Ratings: none found (rule weights will not be refined from ratings).")
    if has_scorer:
        print(f"- Module 4 scorer artifact: {scorer_artifact}")
    else:
        print("- Module 4 scorer artifact: not found (rule-based scorer only).")
    if has_reranker:
        print(f"- Module 4 reranker artifact: {reranker_artifact}")
    else:
        print("- Module 4 reranker artifact: not found (no ML reranking).")

    argv = ["query_cli.py", "--kb", str(kb_path), "--profile", str(profile_path)]
    if use_ratings:
        argv.extend(["--ratings", str(ratings_path), "--use-ratings"])
    if has_scorer:
        argv.extend(["--use-ml-scorer", "--ml-scorer-artifact", str(scorer_artifact)])
    if has_reranker:
        argv.extend(["--use-ml-reranker", "--ml-reranker-artifact", str(reranker_artifact)])

    # Preserve and restore sys.argv so this can be called from the main wizard.
    old_argv = sys.argv[:]
    try:
        sys.argv = argv
        query_cli.main()
    finally:
        sys.argv = old_argv


def _run_full_pipeline() -> None:
    run_preferences_wizard()
    if _prompt_yes_no("\nEnable / retrain the Module 4 ML layer now?", default=True):
        playlists_path = ensure_playlists_file_interactive()
        run_ml_training_wizard(playlists_path)
    run_query_wizard()


def _run_ml_only() -> None:
    playlists_path = ensure_playlists_file_interactive()
    run_ml_training_wizard(playlists_path)


def _execute_menu_choice(choice: str) -> bool:
    """
    Execute one main-menu action.

    Returns:
        True to keep showing the menu, False to exit.
    """
    if choice == "5":
        print("Goodbye.")
        return False

    if choice == "1":
        _run_full_pipeline()
    elif choice == "2":
        run_preferences_wizard()
    elif choice == "3":
        _run_ml_only()
    elif choice == "4":
        run_query_wizard()

    print("\nReturning to main menu.\n")
    return True


def main_menu() -> None:
    _print_banner("CURATED MUSIC RECOMMENDATION SYSTEM - UNIFIED CLI")
    print(
        "This wizard can walk you through the full pipeline or let you\n"
        "run individual steps:\n"
        "  1) Full pipeline: preferences → ML training → query\n"
        "  2) Preferences only (Module 2)\n"
        "  3) ML training only (Module 4)\n"
        "  4) Query only (Modules 3–4)\n"
        "  5) Exit\n"
    )

    while True:
        choice = input("Choose an option [1-5]: ").strip()
        if choice not in {"1", "2", "3", "4", "5"}:
            print("Please enter a number between 1 and 5.")
            continue

        if not _execute_menu_choice(choice):
            return


if __name__ == "__main__":
    main_menu()

