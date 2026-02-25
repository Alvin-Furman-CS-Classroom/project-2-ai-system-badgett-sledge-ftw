"""
Survey Schema for Module 2: Rule-Based Preference Encoding

Defines survey questions that map to knowledge base facts.
Collects user preferences and converts them into a PreferenceProfile.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class LoudnessLevel(Enum):
    """Volume level descriptions mapped to dB ranges."""
    QUIET = (-15.0, -12.0)  # Quiet/Soft
    MODERATE = (-12.0, -8.0)  # Moderate/Normal
    LOUD = (-8.0, -5.0)  # Loud/Energetic
    ANY = None  # No preference


@dataclass
class SurveyQuestion:
    """Represents a single survey question."""
    question_id: str
    prompt: str
    question_type: str  # 'multi_select', 'single_choice', 'loudness'
    options: Optional[List[str]] = None
    kb_fact: Optional[str] = None  # Maps to KB fact type (e.g., 'has_genre')
    required: bool = True


@dataclass
class PreferenceProfile:
    """Structured representation of user preferences from survey."""
    preferred_genres: List[str]
    preferred_moods: List[str]
    danceable: Optional[str]  # 'danceable', 'not_danceable', or None (any)
    voice_instrumental: Optional[str]  # 'voice', 'instrumental', or None (any)
    timbre: Optional[str]  # 'bright', 'dark', or None (any)
    loudness_min: Optional[float]  # dB, or None if no preference
    loudness_max: Optional[float]  # dB, or None if no preference
    
    def has_loudness_preference(self) -> bool:
        """Check if user specified a loudness preference."""
        return self.loudness_min is not None and self.loudness_max is not None


# Map KB genre codes (as stored in knowledge base) to full display names for the survey.
# Used so Question 1 lists full names and accepts either full name or code from the user.
GENRE_DISPLAY_NAMES = {
    "alternative": "Alternative",
    "ambient": "Ambient",
    "blu": "Blues",
    "blues": "Blues",
    "cla": "Classical",
    "cou": "Country",
    "dan": "Dance",
    "dis": "Disco",
    "dnb": "Drum and Bass",
    "electronic": "Electronic",
    "folkcountry": "Folk / Country",
    "hip": "Hip-Hop",
    "house": "House",
    "jaz": "Jazz",
    "jazz": "Jazz",
    "met": "Metal",
    "pop": "Pop",
    "raphiphop": "Rap / Hip-Hop",
    "reg": "Reggae",
    "rhy": "Rhythm & Blues",
    "roc": "Rock",
    "rock": "Rock",
    "spe": "Speech / Spoken Word",
    "techno": "Techno",
    "trance": "Trance",
}


def genre_to_display_name(kb_genre: str) -> str:
    """Return full display name for a KB genre code; fallback to title-case if unknown."""
    key = kb_genre.lower().strip() if kb_genre else ""
    return GENRE_DISPLAY_NAMES.get(key, kb_genre.title() if key else kb_genre)


def display_name_to_genre_code(display_or_code: str, kb_genres: Optional[List[str]] = None) -> Optional[str]:
    """
    Map user input (full name or KB code) to the KB genre code for storage.
    If kb_genres is provided, only return a code that exists in the KB.
    When multiple codes share a display name (e.g. blu/blues -> Blues), prefer the one in kb_genres.
    """
    s = (display_or_code or "").strip().lower()
    if not s:
        return None
    kb_set = {g.lower(): g for g in (kb_genres or [])}
    # All codes that match this input (by display name or by code)
    candidates = []
    for code, display in GENRE_DISPLAY_NAMES.items():
        if display.lower() == s or code.lower() == s:
            candidates.append(code)
    if not candidates and s:
        candidates = [s]
    # Prefer a candidate that exists in the KB
    if kb_genres:
        for c in candidates:
            if c.lower() in kb_set:
                return kb_set[c.lower()]
        return None
    return candidates[0] if candidates else None


class SurveySchema:
    """Defines the survey questions and their structure."""
    
    QUESTIONS = [
        SurveyQuestion(
            question_id="genres",
            prompt="Which genres do you enjoy? (Select all that apply, or leave empty for no preference)",
            question_type="multi_select",
            kb_fact="has_genre",
            required=False
        ),
        SurveyQuestion(
            question_id="moods",
            prompt="What moods do you prefer in music? (Select all that apply, or leave empty for no preference)",
            question_type="multi_select",
            kb_fact="has_mood",
            required=False
        ),
        SurveyQuestion(
            question_id="danceable",
            prompt="Do you prefer music you can dance to?",
            question_type="single_choice",
            options=["danceable", "not_danceable", "any"],
            kb_fact="has_danceable",
            required=False
        ),
        SurveyQuestion(
            question_id="voice_instrumental",
            prompt="Do you prefer songs with vocals or instrumental music?",
            question_type="single_choice",
            options=["voice", "instrumental", "any"],
            kb_fact="has_voice_instrumental",
            required=False
        ),
        SurveyQuestion(
            question_id="timbre",
            prompt="Do you prefer bright or dark-sounding music?",
            question_type="single_choice",
            options=["bright", "dark", "any"],
            kb_fact="has_timbre",
            required=False
        ),
        SurveyQuestion(
            question_id="loudness",
            prompt="What volume level do you prefer?",
            question_type="loudness",
            options=["quiet", "moderate", "loud", "any"],
            kb_fact="has_loudness",
            required=False
        ),
    ]
    
    @staticmethod
    def get_question_by_id(question_id: str) -> Optional[SurveyQuestion]:
        """Get a question by its ID."""
        for q in SurveySchema.QUESTIONS:
            if q.question_id == question_id:
                return q
        return None
    
    @staticmethod
    def map_loudness_choice(choice: str) -> Optional[tuple]:
        """
        Map user-friendly loudness choice to dB range.
        
        Args:
            choice: User's choice ('quiet', 'moderate', 'loud', 'any')
            
        Returns:
            Tuple of (min_db, max_db) or None if 'any'
        """
        choice_lower = choice.lower().strip()
        if choice_lower == "quiet":
            return LoudnessLevel.QUIET.value
        elif choice_lower == "moderate":
            return LoudnessLevel.MODERATE.value
        elif choice_lower == "loud":
            return LoudnessLevel.LOUD.value
        elif choice_lower == "any":
            return None
        else:
            raise ValueError(f"Invalid loudness choice: {choice}. Must be 'quiet', 'moderate', 'loud', or 'any'")


def collect_survey_from_dict(answers: Dict[str, Any], kb_genres: Optional[List[str]] = None, 
                             kb_moods: Optional[List[str]] = None) -> PreferenceProfile:
    """
    Build a PreferenceProfile from a dictionary of answers.
    
    Args:
        answers: Dictionary with question_id -> answer(s)
                 - 'genres': List[str] or empty list
                 - 'moods': List[str] or empty list
                 - 'danceable': 'danceable', 'not_danceable', or 'any'
                 - 'voice_instrumental': 'voice', 'instrumental', or 'any'
                 - 'timbre': 'bright', 'dark', or 'any'
                 - 'loudness': 'quiet', 'moderate', 'loud', or 'any'
        kb_genres: Optional list of valid genres from KB (for validation)
        kb_moods: Optional list of valid moods from KB (for validation)
        
    Returns:
        PreferenceProfile object
        
    Raises:
        ValueError: If answers are invalid or missing required fields
    """
    # Extract answers with defaults
    preferred_genres = answers.get("genres", [])
    if not isinstance(preferred_genres, list):
        preferred_genres = [preferred_genres] if preferred_genres else []
    
    preferred_moods = answers.get("moods", [])
    if not isinstance(preferred_moods, list):
        preferred_moods = [preferred_moods] if preferred_moods else []
    
    danceable = answers.get("danceable", "any")
    if danceable == "any":
        danceable = None
    
    voice_instrumental = answers.get("voice_instrumental", "any")
    if voice_instrumental == "any":
        voice_instrumental = None
    
    timbre = answers.get("timbre", "any")
    if timbre == "any":
        timbre = None
    
    # Handle loudness
    loudness_choice = answers.get("loudness", "any")
    loudness_range = SurveySchema.map_loudness_choice(loudness_choice)
    loudness_min, loudness_max = loudness_range if loudness_range else (None, None)
    
    # Validate single-choice answers
    valid_danceable = ["danceable", "not_danceable"]
    valid_voice_instrumental = ["voice", "instrumental"]
    valid_timbre = ["bright", "dark"]
    
    if danceable and danceable not in valid_danceable:
        raise ValueError(f"Invalid danceable value: {danceable}. Must be one of {valid_danceable}")
    
    if voice_instrumental and voice_instrumental not in valid_voice_instrumental:
        raise ValueError(f"Invalid voice_instrumental value: {voice_instrumental}. Must be one of {valid_voice_instrumental}")
    
    if timbre and timbre not in valid_timbre:
        raise ValueError(f"Invalid timbre value: {timbre}. Must be one of {valid_timbre}")
    
    # Optional: validate genres/moods against KB if provided
    if kb_genres:
        invalid_genres = [g for g in preferred_genres if g.lower() not in [kg.lower() for kg in kb_genres]]
        if invalid_genres:
            raise ValueError(f"Invalid genres: {invalid_genres}. Valid genres: {kb_genres[:10]}...")
    
    if kb_moods:
        invalid_moods = [m for m in preferred_moods if m.lower() not in [km.lower() for km in kb_moods]]
        if invalid_moods:
            raise ValueError(f"Invalid moods: {invalid_moods}. Valid moods: {kb_moods[:10]}...")
    
    return PreferenceProfile(
        preferred_genres=preferred_genres,
        preferred_moods=preferred_moods,
        danceable=danceable,
        voice_instrumental=voice_instrumental,
        timbre=timbre,
        loudness_min=loudness_min,
        loudness_max=loudness_max
    )


def collect_survey_cli(kb_genres: Optional[List[str]] = None, kb_moods: Optional[List[str]] = None) -> PreferenceProfile:
    """
    Collect survey answers via command-line interface.
    
    Args:
        kb_genres: Optional list of valid genres from KB (for display/validation)
        kb_moods: Optional list of valid moods from KB (for display/validation)
        
    Returns:
        PreferenceProfile object
    """
    answers = {}
    
    print("\n" + "=" * 70)
    print("  MUSIC PREFERENCE SURVEY")
    print("=" * 70 + "\n")
    
    # Question 1: Genres (multi-select) — list all KB genres by full name, no truncation
    print("Question 1: Which genres do you enjoy?")
    if kb_genres:
        # Show all available genres using full display names, sorted by display name
        sorted_by_display = sorted(
            kb_genres,
            key=lambda g: genre_to_display_name(g)
        )
        display_list = [genre_to_display_name(g) for g in sorted_by_display]
        print("Available genres (all):")
        print("  " + ", ".join(display_list))
        print("(Enter genre names separated by commas, or press Enter for no preference)")
    else:
        print("(Enter genre names separated by commas, or press Enter for no preference)")
    
    genres_input = input("Your answer: ").strip()
    if genres_input:
        # Parse tokens; map full names or codes to KB codes for storage
        raw_tokens = [t.strip() for t in genres_input.split(",") if t.strip()]
        answers["genres"] = []
        seen_lower = set()
        for token in raw_tokens:
            code = display_name_to_genre_code(token, kb_genres)
            if code and code.lower() not in seen_lower:
                seen_lower.add(code.lower())
                answers["genres"].append(code)
    else:
        answers["genres"] = []
    
    # Question 2: Moods (multi-select)
    print("\nQuestion 2: What moods do you prefer in music?")
    if kb_moods:
        print(f"Available moods: {', '.join(sorted(kb_moods))}")
        print("(Enter mood names separated by commas, or press Enter for no preference)")
    else:
        print("(Enter mood names separated by commas, or press Enter for no preference)")
    
    moods_input = input("Your answer: ").strip()
    if moods_input:
        answers["moods"] = [m.strip() for m in moods_input.split(",") if m.strip()]
    else:
        answers["moods"] = []
    
    # Question 3: Danceability
    print("\nQuestion 3: Do you prefer music you can dance to?")
    print("Options: [1] Yes, I prefer danceable music")
    print("         [2] No, I prefer non-danceable/chill music")
    print("         [3] I don't have a preference")
    danceable_input = input("Your choice (1-3): ").strip()
    danceable_map = {"1": "danceable", "2": "not_danceable", "3": "any"}
    answers["danceable"] = danceable_map.get(danceable_input, "any")
    
    # Question 4: Voice vs Instrumental
    print("\nQuestion 4: Do you prefer songs with vocals or instrumental music?")
    print("Options: [1] I prefer songs with vocals")
    print("         [2] I prefer instrumental music")
    print("         [3] I don't have a preference")
    vi_input = input("Your choice (1-3): ").strip()
    vi_map = {"1": "voice", "2": "instrumental", "3": "any"}
    answers["voice_instrumental"] = vi_map.get(vi_input, "any")
    
    # Question 5: Timbre
    print("\nQuestion 5: Do you prefer bright or dark-sounding music?")
    print("Options: [1] I prefer bright-sounding music")
    print("         [2] I prefer dark-sounding music")
    print("         [3] I don't have a preference")
    timbre_input = input("Your choice (1-3): ").strip()
    timbre_map = {"1": "bright", "2": "dark", "3": "any"}
    answers["timbre"] = timbre_map.get(timbre_input, "any")
    
    # Question 6: Loudness (Option 1: Volume Level Descriptions)
    print("\nQuestion 6: What volume level do you prefer?")
    print("Options: [1] Quiet/Soft")
    print("         [2] Moderate/Normal")
    print("         [3] Loud/Energetic")
    print("         [4] I don't have a preference")
    loudness_input = input("Your choice (1-4): ").strip()
    loudness_map = {"1": "quiet", "2": "moderate", "3": "loud", "4": "any"}
    answers["loudness"] = loudness_map.get(loudness_input, "any")
    
    print("\n" + "=" * 70)
    print("  Survey Complete!")
    print("=" * 70 + "\n")
    
    return collect_survey_from_dict(answers, kb_genres, kb_moods)


if __name__ == "__main__":
    # Example usage
    print("Survey Schema Test")
    print("\nExample: Creating a profile from a dictionary")
    
    example_answers = {
        "genres": ["rock", "electronic"],
        "moods": ["happy", "party"],
        "danceable": "danceable",
        "voice_instrumental": "voice",
        "timbre": "bright",
        "loudness": "moderate"
    }
    
    profile = collect_survey_from_dict(example_answers)
    print(f"\nProfile created:")
    print(f"  Genres: {profile.preferred_genres}")
    print(f"  Moods: {profile.preferred_moods}")
    print(f"  Danceable: {profile.danceable}")
    print(f"  Voice/Instrumental: {profile.voice_instrumental}")
    print(f"  Timbre: {profile.timbre}")
    print(f"  Loudness range: {profile.loudness_min} to {profile.loudness_max} dB")
    
    print("\nTo run interactive CLI survey, call:")
    print("  from src.preferences.survey import collect_survey_cli")
    print("  profile = collect_survey_cli(kb_genres, kb_moods)")
