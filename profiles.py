"""
profiles.py
===========
Facility category definitions for reports and visualization.

Centralizes newcomer profile definitions: facility types grouped by user needs
(families, dog lovers, sports players, outdoor enthusiasts, community seekers).
Both text reports and map layers derive from this single source.
"""


# Central facility category definitions (single source of truth)
_FACILITY_CATEGORIES = {
    "dog": {
        "text_label": "Dog Lovers",
        "map_emoji": "🐕",
        "map_label": "Dog Off-Leash",
        "facilities": [
            "Dogs Off-Leash Areas",
        ],
    },
    "families": {
        "text_label": "Families",
        "map_emoji": "🛝",
        "map_label": "Family",
        "facilities": [
            "Playgrounds", "Wading Pool", "Water/Spray Parks", "Swimming Pools",
        ],
    },
    "sports": {
        "text_label": "Sports Players",
        "map_emoji": "⚽",
        "map_label": "Sports",
        "facilities": [
            "Soccer Fields", "Tennis Courts", "Basketball Courts",
            "Baseball Diamonds", "Softball", "Football Fields",
            "Rugby Fields", "Pickleball", "Field Hockey",
            "Cricket Pitches", "Ultimate Fields", "Ball Hockey",
            "Lighted Fields", "Lacrosse Boxes",
            "Outdoor Roller Hockey Rinks", "Rinks",
            "Bowling Greens", "Golf Courses",
            "Skateboard Parks", "Disc Golf Courses",
        ],
    },
    "outdoors": {
        "text_label": "Outdoor Enthusiasts",
        "map_emoji": "🏃",
        "map_label": "Outdoors",
        "facilities": [
            "Jogging Trails", "Running Tracks", "Beaches", "Outdoor Fitness",
        ],
    },
    "community": {
        "text_label": "Community Seekers",
        "map_emoji": "🏛️",
        "map_label": "Community",
        "facilities": [
            "Community Centres", "Community Halls", "Field Houses",
            "Picnic Sites", "Restaurants", "Food Concessions",
        ],
    },
}

# Derived dictionaries for reports and visualization (single update point)
FACILITY_PROFILES = {
    cat["text_label"]: cat["facilities"]
    for cat in _FACILITY_CATEGORIES.values()
}

MAP_LAYER_FACILITIES = {
    f"{cat['map_emoji']} {cat['map_label']}": cat["facilities"]
    for cat in _FACILITY_CATEGORIES.values()
}
MAP_LAYER_FACILITIES["🚌 Transit Stops"] = []
