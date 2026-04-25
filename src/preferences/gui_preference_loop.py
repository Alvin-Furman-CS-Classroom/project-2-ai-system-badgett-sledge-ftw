#!/usr/bin/env python3
"""
Tkinter GUI for Module 2 preference survey + song ratings loop.

This keeps the same underlying logic and outputs as the CLI loop:
- data/user_profile.json
- data/user_ratings.json
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_base_wrapper import KnowledgeBase
from preferences.ratings import Rating, UserRatings, refine_weights_from_ratings
from preferences.rules import build_rules, get_default_weights
from preferences.sampling import sample_next_batch, sample_songs
from preferences.scorer import PreferenceScorer
from preferences.survey import collect_survey_from_dict, genre_to_display_name, save_profile


REFINEMENT_ALPHA_LOOP = 0.15


class PreferenceGuiApp:
    """Simple two-step GUI: survey form then song ratings."""

    def __init__(
        self,
        root: tk.Tk,
        kb_path: str = "data/knowledge_base.json",
        batch_size: int = 5,
        max_rounds: int = 3,
    ) -> None:
        self.root = root
        self.root.title("Module 2 Preferences GUI")
        self.root.geometry("900x700")

        self.kb = KnowledgeBase(kb_path)
        self.batch_size = batch_size
        self.max_rounds = max_rounds

        self.kb_genres = sorted(list(self.kb.get_all_genres()))
        self.kb_moods = sorted(list(self.kb.get_all_moods()))
        self.genre_display_to_codes: Dict[str, List[str]] = self._build_genre_display_map(self.kb_genres)
        self.genre_display_options = sorted(self.genre_display_to_codes.keys())

        self.profile = None
        self.rules = []
        self.weights: Dict[str, float] = {}
        self.scorer: Optional[PreferenceScorer] = None

        self.ratings = UserRatings()
        self.already_rated: List[str] = []
        self.current_round = 1
        self.current_batch: List[str] = []
        self.current_song_index = 0

        self.container = ttk.Frame(self.root, padding=12)
        self.container.pack(fill=tk.BOTH, expand=True)

        self._build_survey_screen()

    def _clear_container(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def _build_survey_screen(self) -> None:
        self._clear_container()

        header = ttk.Label(
            self.container,
            text="Music Preference Survey",
            font=("Helvetica", 16, "bold"),
        )
        header.pack(anchor=tk.W, pady=(0, 10))

        top = ttk.Frame(self.container)
        top.pack(fill=tk.BOTH, expand=True)

        genres_frame = ttk.LabelFrame(top, text="Genres (multi-select, optional)", padding=8)
        genres_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.genres_listbox = tk.Listbox(genres_frame, selectmode=tk.MULTIPLE, exportselection=False)
        genres_scroll = ttk.Scrollbar(genres_frame, orient=tk.VERTICAL, command=self.genres_listbox.yview)
        self.genres_listbox.config(yscrollcommand=genres_scroll.set)
        for genre in self.genre_display_options:
            self.genres_listbox.insert(tk.END, genre)
        self.genres_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        genres_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        moods_frame = ttk.LabelFrame(top, text="Moods (multi-select, optional)", padding=8)
        moods_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.moods_listbox = tk.Listbox(moods_frame, selectmode=tk.MULTIPLE, exportselection=False)
        moods_scroll = ttk.Scrollbar(moods_frame, orient=tk.VERTICAL, command=self.moods_listbox.yview)
        self.moods_listbox.config(yscrollcommand=moods_scroll.set)
        for mood in self.kb_moods:
            self.moods_listbox.insert(tk.END, mood)
        self.moods_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        moods_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.danceable_var = tk.StringVar(value="any")
        self.voice_var = tk.StringVar(value="any")
        self.timbre_var = tk.StringVar(value="any")
        self.loudness_var = tk.StringVar(value="any")

        options = ttk.Frame(self.container)
        options.pack(fill=tk.X, pady=(10, 0))

        self._add_radio_group(
            options,
            "Danceability",
            self.danceable_var,
            [("Danceable", "danceable"), ("Not danceable/chill", "not_danceable"), ("Any", "any")],
        ).pack(fill=tk.X, pady=4)

        self._add_radio_group(
            options,
            "Vocals vs Instrumental",
            self.voice_var,
            [("Vocals", "voice"), ("Instrumental", "instrumental"), ("Any", "any")],
        ).pack(fill=tk.X, pady=4)

        self._add_radio_group(
            options,
            "Timbre",
            self.timbre_var,
            [("Bright", "bright"), ("Dark", "dark"), ("Any", "any")],
        ).pack(fill=tk.X, pady=4)

        loudness_row = ttk.Frame(options)
        loudness_row.pack(fill=tk.X, pady=4)
        ttk.Label(loudness_row, text="Loudness").pack(side=tk.LEFT)
        loudness_menu = ttk.Combobox(
            loudness_row,
            textvariable=self.loudness_var,
            state="readonly",
            values=["quiet", "moderate", "loud", "any"],
            width=14,
        )
        loudness_menu.pack(side=tk.LEFT, padx=8)

        submit = ttk.Button(self.container, text="Save Survey and Start Ratings", command=self._submit_survey)
        submit.pack(anchor=tk.E, pady=(12, 0))

    def _add_radio_group(
        self,
        parent: ttk.Frame,
        title: str,
        variable: tk.StringVar,
        values: List[tuple],
    ) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text=title, padding=8)
        for text, value in values:
            ttk.Radiobutton(frame, text=text, value=value, variable=variable).pack(side=tk.LEFT, padx=8)
        return frame

    def _selected_from_listbox(self, listbox: tk.Listbox) -> List[str]:
        return [listbox.get(i) for i in listbox.curselection()]

    def _build_genre_display_map(self, kb_genres: List[str]) -> Dict[str, List[str]]:
        """Map one human-readable genre label to one or more KB genre codes."""
        display_to_codes: Dict[str, List[str]] = {}
        for code in kb_genres:
            display = genre_to_display_name(code)
            if display not in display_to_codes:
                display_to_codes[display] = []
            if code not in display_to_codes[display]:
                display_to_codes[display].append(code)
        return display_to_codes

    def _submit_survey(self) -> None:
        selected_genre_labels = self._selected_from_listbox(self.genres_listbox)
        expanded_genres: List[str] = []
        seen_genres = set()
        for label in selected_genre_labels:
            for code in self.genre_display_to_codes.get(label, []):
                if code not in seen_genres:
                    expanded_genres.append(code)
                    seen_genres.add(code)

        answers = {
            "genres": expanded_genres,
            "moods": self._selected_from_listbox(self.moods_listbox),
            "danceable": self.danceable_var.get(),
            "voice_instrumental": self.voice_var.get(),
            "timbre": self.timbre_var.get(),
            "loudness": self.loudness_var.get(),
        }

        try:
            self.profile = collect_survey_from_dict(answers, self.kb_genres, self.kb_moods)
            save_profile(self.profile)
        except Exception as err:
            messagebox.showerror("Survey Error", f"Could not save survey: {err}")
            return

        self.rules = build_rules(self.profile)
        self.weights = get_default_weights(self.rules)
        self.scorer = PreferenceScorer(self.rules, self.weights)

        self.current_round = 1
        self.already_rated = []
        self.ratings = UserRatings()
        self._load_batch()

    def _load_batch(self) -> None:
        if self.current_round == 1:
            if self.rules:
                self.current_batch = sample_songs(self.kb, n=self.batch_size, method="score_based", scorer=self.scorer)
            else:
                self.current_batch = sample_songs(self.kb, n=self.batch_size, method="stratified")
        else:
            self.current_batch = sample_next_batch(self.kb, self.batch_size, self.scorer, self.already_rated)

        if not self.current_batch:
            self._finish_flow()
            return

        self.current_song_index = 0
        self._build_rating_screen()
        self._render_current_song()

    def _build_rating_screen(self) -> None:
        self._clear_container()

        self.round_label = ttk.Label(self.container, text="", font=("Helvetica", 14, "bold"))
        self.round_label.pack(anchor=tk.W)

        self.song_info = tk.Text(self.container, height=12, wrap=tk.WORD)
        self.song_info.pack(fill=tk.X, pady=(8, 8))
        self.song_info.config(state=tk.DISABLED)

        buttons = ttk.Frame(self.container)
        buttons.pack(fill=tk.X)

        ttk.Button(buttons, text="1 - Dislike", command=lambda: self._rate_current_song(Rating.DISLIKE)).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(buttons, text="2 - Neutral", command=lambda: self._rate_current_song(Rating.NEUTRAL)).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(buttons, text="3 - Like", command=lambda: self._rate_current_song(Rating.LIKE)).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(
            buttons,
            text="4 - Really Like",
            command=lambda: self._rate_current_song(Rating.REALLY_LIKE),
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(self.container, text="Finish Early", command=self._finish_flow).pack(anchor=tk.E, pady=(12, 0))

    def _render_current_song(self) -> None:
        total = len(self.current_batch)
        idx = self.current_song_index
        mbid = self.current_batch[idx]
        song = self.kb.get_song(mbid) or {}

        lines = [
            f"Round {self.current_round}/{self.max_rounds} - Song {idx + 1}/{total}",
            "",
            f"Track:  {song.get('track', 'Unknown')}",
            f"Album:  {song.get('album', 'Unknown')}",
            f"Artist: {song.get('artist', 'Unknown')}",
        ]

        self.round_label.config(text=f"Rate this song ({idx + 1}/{total})")
        self.song_info.config(state=tk.NORMAL)
        self.song_info.delete("1.0", tk.END)
        self.song_info.insert("1.0", "\n".join(lines))
        self.song_info.config(state=tk.DISABLED)

    def _rate_current_song(self, rating: Rating) -> None:
        mbid = self.current_batch[self.current_song_index]
        self.ratings.add_rating(mbid, rating)
        self.already_rated.append(mbid)

        self.current_song_index += 1
        if self.current_song_index < len(self.current_batch):
            self._render_current_song()
            return

        if self.rules:
            self.weights = refine_weights_from_ratings(
                self.kb,
                self.rules,
                self.weights,
                self.ratings,
                alpha=REFINEMENT_ALPHA_LOOP,
            )
            self.scorer = PreferenceScorer(self.rules, self.weights)

        next_round = self.current_round + 1
        if next_round > self.max_rounds:
            self._finish_flow()
            return

        # Match CLI behavior where users opt in to each additional batch.
        continue_next = messagebox.askyesno(
            "Continue to Next Batch?",
            (
                f"You have completed round {self.current_round}.\n\n"
                f"Start round {next_round} of {self.max_rounds} "
                f"({self.batch_size} more songs)?"
            ),
        )
        if not continue_next:
            self._finish_flow()
            return

        self.current_round = next_round
        self._load_batch()

    def _finish_flow(self) -> None:
        try:
            self.ratings.save("data/user_ratings.json")
        except Exception as err:
            messagebox.showerror("Save Error", f"Could not save ratings: {err}")
            return

        self._clear_container()
        ttk.Label(
            self.container,
            text="Preference collection complete.",
            font=("Helvetica", 16, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(
            self.container,
            text=(
                "Saved files:\n"
                "- data/user_profile.json\n"
                "- data/user_ratings.json\n\n"
                "You can now run:\n"
                "python3 src/search/query_cli.py --kb data/knowledge_base.json "
                "--profile data/user_profile.json --ratings data/user_ratings.json --use-ratings"
            ),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)
        ttk.Button(self.container, text="Close", command=self.root.destroy).pack(anchor=tk.E, pady=(12, 0))


def main() -> None:
    root = tk.Tk()
    try:
        app = PreferenceGuiApp(root)
    except FileNotFoundError:
        messagebox.showerror("Missing KB", "Could not find data/knowledge_base.json. Run from project root.")
        root.destroy()
        return

    root.mainloop()


if __name__ == "__main__":
    main()
