"""Curated, editable production blueprints for Fruitful genre starters."""

from __future__ import annotations

from copy import deepcopy

_STYLES = {
    "hip-hop": {
        "aliases": ("hip hop", "boom bap"),
        "tempo": 90,
        "tempo_range": [82, 98],
        "key": "minor or Dorian",
        "roles": ["kick", "snare", "closed hat", "bass", "sample or keys"],
        "structure": ["4-bar intro", "16-bar verse", "8-bar hook", "4-bar turnaround"],
        "production_brief": "Warm drums with swing, a restrained bass line, and a chopped or soulful harmonic bed.",
    },
    "rage-trap": {
        "aliases": ("rage", "opium trap", "dark trap"),
        "tempo": 150,
        "tempo_range": [140, 160],
        "key": "minor, Phrygian color",
        "roles": ["kick", "clap", "closed hat", "open hat", "808", "detuned lead", "atmosphere"],
        "structure": ["4-bar filtered intro", "8-bar hook", "16-bar verse", "8-bar hook variation"],
        "production_brief": "Use a distorted but controlled 808, sparse syncopated kicks, varied hat rolls, and a wide detuned lead. Leave space for vocals.",
    },
    "rnb": {
        "aliases": ("r&b", "rhythm and blues", "contemporary rnb"),
        "tempo": 76,
        "tempo_range": [65, 90],
        "key": "minor with seventh and ninth chords",
        "roles": [
            "kick",
            "snare or clap",
            "soft hat",
            "sub bass",
            "electric piano",
            "pad",
            "vocal texture",
        ],
        "structure": ["8-bar intro", "16-bar verse", "8-bar pre-hook", "8-bar hook"],
        "production_brief": "Prioritize rich voicings, pocket, and negative space. Keep drums soft and the bass supportive rather than busy.",
    },
    "reggae": {
        "aliases": ("dub", "roots reggae"),
        "tempo": 74,
        "tempo_range": [68, 82],
        "key": "major or natural minor",
        "roles": [
            "one-drop kick",
            "rimshot",
            "shaker",
            "round bass",
            "skank guitar or organ",
            "bubble organ",
        ],
        "structure": ["8-bar intro", "16-bar verse", "8-bar chorus", "8-bar dub breakdown"],
        "production_brief": "Put the bass and offbeat chord stab first. Use relaxed one-drop drums and leave room for delay throws.",
    },
    "afrobeat": {
        "aliases": ("afrobeats", "afropop", "afro fusion"),
        "tempo": 108,
        "tempo_range": [98, 116],
        "key": "major or minor pentatonic",
        "roles": [
            "kick",
            "clap",
            "shaker",
            "percussion",
            "sub bass",
            "plucked guitar",
            "keys",
            "lead",
        ],
        "structure": ["8-bar intro", "16-bar verse", "8-bar pre-hook", "8-bar chorus"],
        "production_brief": "Build interlocking percussion before adding melody. Use syncopation, bright plucks, and a buoyant bass groove.",
    },
    "latin": {
        "aliases": ("latin pop", "reggaeton", "dembow"),
        "tempo": 96,
        "tempo_range": [88, 105],
        "key": "minor or major pentatonic",
        "roles": [
            "kick",
            "dembow snare",
            "hat",
            "percussion",
            "sub bass",
            "nylon guitar or pluck",
            "piano",
        ],
        "structure": ["4-bar intro", "8-bar verse", "8-bar pre-hook", "8-bar chorus"],
        "production_brief": "Anchor the groove with a clean dembow rhythm, then add hand percussion and concise melodic hooks.",
    },
    "jazz": {
        "aliases": ("jazz-hop", "jazz hop", "neo soul"),
        "tempo": 118,
        "tempo_range": [90, 150],
        "key": "major or minor with ii-V-I movement",
        "roles": ["ride cymbal", "snare", "upright bass", "piano", "guitar", "horn or sax lead"],
        "structure": ["8-bar head", "16-bar solo section", "8-bar head return"],
        "production_brief": "Use humanized timing, extended chords, walking or pedal bass, and short call-and-response phrases.",
    },
    "rock": {
        "aliases": ("alternative rock", "indie rock", "pop rock"),
        "tempo": 122,
        "tempo_range": [100, 150],
        "key": "minor or Mixolydian",
        "roles": [
            "acoustic or live kick",
            "snare",
            "overheads",
            "bass guitar",
            "rhythm guitar",
            "lead guitar",
            "vocal",
        ],
        "structure": ["4-bar intro", "16-bar verse", "8-bar pre-chorus", "8-bar chorus"],
        "production_brief": "Start with a believable drum and bass pocket. Double rhythm guitars in the chorus and reserve the lead for hooks.",
    },
}


def list_styles() -> list[dict]:
    """Return the available style names and their main production targets."""
    return [
        {"style": style, "tempo": blueprint["tempo"], "roles": list(blueprint["roles"])}
        for style, blueprint in _STYLES.items()
    ]


def get_style(style: str) -> dict:
    """Resolve a user-facing genre label to a complete production blueprint."""
    normalized = " ".join(style.casefold().split())
    for name, blueprint in _STYLES.items():
        if normalized == name or normalized in blueprint["aliases"]:
            result = deepcopy(blueprint)
            result.pop("aliases")
            result["style"] = name
            return result
    available = ", ".join(_STYLES)
    raise ValueError(f"unknown style {style!r}. Available styles: {available}")
