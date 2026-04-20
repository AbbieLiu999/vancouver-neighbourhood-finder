"""
summary_builder.py
==================
Dataset-loading orchestration for neighbourhood summary construction.
"""

import os

from parks import ParkRegistry
from transit import TransitNetwork
from boundaries import NeighbourhoodBoundaries
from summary import NeighbourhoodSummary


# Data file paths (single source of truth)
PARKS_CSV = "data/parks.csv"
PARKS_FACILITIES_CSV = "data/parks-facilities.csv"
STOPS_TXT = "data/stops.txt"
NEIGHBOURHOOD_BOUNDARIES_GEOJSON = "data/neighbourhood_boundaries.geojson"

REQUIRED_DATA_FILES = {
    PARKS_CSV: (
        "Vancouver Parks CSV\n"
        "  https://opendata.vancouver.ca/explore/dataset/parks/export/"
    ),
    PARKS_FACILITIES_CSV: (
        "Vancouver Parks Facilities CSV\n"
        "  https://opendata.vancouver.ca/explore/dataset/parks-facilities/export/"
    ),
    STOPS_TXT: (
        "TransLink GTFS stops.txt\n"
        "  https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources/gtfs/gtfs-data"
        "  (download the zip, open it, copy stops.txt)"
    ),
    NEIGHBOURHOOD_BOUNDARIES_GEOJSON: (
        "Vancouver Local Area Boundary GeoJSON\n"
        "  https://opendata.vancouver.ca/explore/dataset/local-area-boundary/export/"
    ),
}


def ensure_data_files_exist():
    """Check all required files exist; print instructions and exit if not."""
    missing_files = {
        file_path: instructions
        for file_path, instructions in REQUIRED_DATA_FILES.items()
        if not os.path.exists(file_path)
    }

    if missing_files:
        print("\n  Some data files are missing.\n")
        for file_path, instructions in missing_files.items():
            print(f"  MISSING: {file_path}")
            print(f"  Download: {instructions}\n")
        print("  Then run this program again.\n")
        raise SystemExit(1)


def build_summary():
    """Load all datasets, build the neighbourhood summary, and return it."""
    ensure_data_files_exist()

    registry = ParkRegistry()
    registry.load_from_csv(PARKS_CSV, PARKS_FACILITIES_CSV)

    boundaries = NeighbourhoodBoundaries()
    boundaries.load_from_geojson(
        NEIGHBOURHOOD_BOUNDARIES_GEOJSON,
        registry.neighbourhood_name_lookup(),
    )

    network = TransitNetwork()
    network.load_from_csv(STOPS_TXT)
    network.assign_to_neighbourhoods(boundaries)

    summary = NeighbourhoodSummary(registry, boundaries, network)
    summary.build()
    return summary
