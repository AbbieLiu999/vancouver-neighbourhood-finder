"""
data_loader.py
==============

Data-loading layer for local CSV/GeoJSON sources.

- ParkRegistry: loads parks and facilities, and joins them by ParkID.
- TransitNetwork: loads GTFS stops and assigns stops to neighbourhoods.
- NeighbourhoodBoundaries: loads polygons and resolves point-in-neighbourhood.
"""

import os
import pandas as pd
import json
import re
from shapely.geometry import shape

from models import Park, TransitStop, Neighbourhood


def _normalize_name(name):
    """Return a lowercase comparison key with punctuation collapsed to spaces."""
    text = re.sub(r"[^0-9A-Za-z]+", " ", str(name).strip().lower())
    return re.sub(r"\s+", " ", text).strip()


REQUIRED_DATA_FILES = {
    "data/parks.csv": (
        "Vancouver Parks CSV\n"
        "  https://opendata.vancouver.ca/explore/dataset/parks/export/"
    ),
    "data/parks-facilities.csv": (
        "Vancouver Parks Facilities CSV\n"
        "  https://opendata.vancouver.ca/explore/dataset/parks-facilities/export/"
    ),
    "data/stops.txt": (
        "TransLink GTFS stops.txt\n"
        "  https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources/gtfs/gtfs-data"
        "  (download the zip, open it, copy stops.txt)"
    ),
    "data/neighbourhood_boundaries.geojson": (
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


def load_core_data():
    """Load datasets and return registry, boundaries, and network objects."""
    registry = ParkRegistry()
    registry.load_from_csv("data/parks.csv", "data/parks-facilities.csv")

    boundaries = NeighbourhoodBoundaries()
    boundaries.load_from_geojson(
        "data/neighbourhood_boundaries.geojson",
        registry.neighbourhood_name_lookup(),
    )

    network = TransitNetwork()
    network.load_from_csv("data/stops.txt")

    return registry, boundaries, network


# ── ParkRegistry ──────────────────────────────────────────────────────────────

class ParkRegistry:
    """
    Loads parks.csv and parks-facilities.csv and stores them as Park objects.

    The two files are joined on ParkID so every Park knows its facility types.
    This join is what makes the cross-dataset analysis possible — facility
    types only exist in parks-facilities.csv, while neighbourhood names only
    exist in parks.csv.

    Attributes
    ----------
    parks : list of Park objects
    """

    def __init__(self):
        """Create an empty park registry."""
        self.parks = []

    # Helper methods for loading and joining the two CSV files into Park objects
    @staticmethod
    def _parse_lat_lon(google_map_dest):
        """Parse a "lat, lon" string into floats, or return None if invalid."""
        try:
            lat_str, lon_str = str(google_map_dest).split(",")
            return float(lat_str.strip()), float(lon_str.strip())
        except Exception:
            return None

    @staticmethod
    def _build_facilities_map(facilities_df):
        """Build a ParkID-to-facility list mapping from the facilities table."""
        facilities_map = {}
        for _, row in facilities_df.iterrows():
            park_id = row["ParkID"]
            facility_type = str(row["FacilityType"]).strip()
            if park_id not in facilities_map:
                facilities_map[park_id] = []
            if facility_type not in facilities_map[park_id]:
                facilities_map[park_id].append(facility_type)
        return facilities_map

    @staticmethod
    def _row_to_park(row, lat, lon, facilities_map):
        """Convert one parks.csv row into a Park object."""
        park_id = row["ParkID"]
        return Park(
            park_id       = park_id,
            name          = str(row["Name"]).strip(),
            neighbourhood = str(row["NeighbourhoodName"]).strip(),
            lat           = lat,
            lon           = lon,
            hectares      = float(row["Hectare"])
                            if pd.notna(row["Hectare"]) else 0.0,
            facilities    = facilities_map.get(park_id, []),
        )

    def load_from_csv(self, parks_path, facilities_path):
        """Read and join both CSV files. Create one Park per row."""

        parks_df = pd.read_csv(parks_path, sep=";", on_bad_lines="skip")
        facilities_df = pd.read_csv(facilities_path, sep=";", on_bad_lines="skip")
        print(f"  Loaded {parks_path}            ({len(parks_df)} rows)")
        print(f"  Loaded {facilities_path}  ({len(facilities_df)} rows)")

        facilities_map = self._build_facilities_map(facilities_df)
        # For each park row, parse the lat/lon and create a Park object with its facilities.
        skipped = 0
        for _, row in parks_df.iterrows():
            parsed_coordinates = self._parse_lat_lon(row["GoogleMapDest"])
            if parsed_coordinates is None:
                skipped += 1
                continue

            lat, lon = parsed_coordinates
            self.parks.append(self._row_to_park(row, lat, lon, facilities_map))

        print(f"  ParkRegistry: {len(self.parks)} parks loaded, "
              f"{skipped} skipped\n")

    def all_parks(self):
        """Return all Park objects."""
        return self.parks

    def parks_with_facility(self, facility_type):
        """Return all parks that have the given facility type."""
        return [park for park in self.parks if park.has_facility(facility_type)]

    def all_facility_types(self):
        """Return a sorted list of all unique facility types across all parks."""
        facility_types = set()
        for park in self.parks:
            for facility_type in park.facilities:
                facility_types.add(facility_type)
        return sorted(facility_types)

    def neighbourhood_name_lookup(self):
        """Return normalized neighbourhood name -> parks.csv display name."""
        lookup = {}
        for park in self.parks:
            neighbourhood_key = _normalize_name(park.neighbourhood)
            if neighbourhood_key not in lookup:
                lookup[neighbourhood_key] = park.neighbourhood
        return lookup
    

# ── TransitNetwork ────────────────────────────────────────────────────────────

class TransitNetwork:
    """
    Loads stops.txt and stores TransitStop objects.
    Performs no filtering — returns all stops as loaded.
    Filtering by neighbourhood is handled by NeighbourhoodSummary using boundaries.

    Attributes
    ----------
    stops               : list of TransitStop objects
    stops_by_neighbourhood : dict mapping neighbourhood name -> list of TransitStop
    """

    def __init__(self):
        """Create an empty transit network."""
        self.stops = []
        self.stops_by_neighbourhood = {}

    def load_from_csv(self, stops_path):
        """
        Read stops.txt and load all transit stops without filtering.
        All stops are loaded — filtering by neighbourhood is handled
        by NeighbourhoodSummary in analyzer.py.
        """
        stops_df = pd.read_csv(stops_path)

        for _, row in stops_df.iterrows():
            stop = TransitStop(
                stop_id = str(row["stop_id"]),
                name    = str(row["stop_name"]),
                lat     = float(row["stop_lat"]),
                lon     = float(row["stop_lon"]),
            )
            self.stops.append(stop)

        print(f"  TransitNetwork: {len(self.stops)} stops loaded\n")

    def assign_to_neighbourhoods(self, boundaries):
        """
        Pre-compute neighbourhood assignments for all stops.
        Builds stops_by_neighbourhood dict once instead of point-in-polygon
        checking repeatedly for each neighbourhood.
        """
        for stop in self.stops:
            neighbourhood_name = boundaries.neighbourhood_of(stop.lat, stop.lon)
            if neighbourhood_name:
                if neighbourhood_name not in self.stops_by_neighbourhood:
                    self.stops_by_neighbourhood[neighbourhood_name] = []
                self.stops_by_neighbourhood[neighbourhood_name].append(stop)


# ── NeighbourhoodBoundaries ───────────────────────────────────────────────────

class NeighbourhoodBoundaries:
    """
    Loads Vancouver neighbourhood boundary polygons from GeoJSON
    and stores them as Neighbourhood objects.

    Answers which neighbourhood a given lat/lon point belongs to
    using exact point-in-polygon geometry.

    Neighbourhood names from other sources are matched with normalized
    keys, then converted back to the parks.csv display name for storage.

    Attributes
    ----------
    neighbourhoods : list of Neighbourhood objects
    """

    def __init__(self):
        """Create an empty neighbourhood boundary container."""
        self.neighbourhoods = []

    def load_from_geojson(self, boundaries_path, parks_neighbourhood_lookup=None):
        """
        Read the local area boundary GeoJSON file and create one
        Neighbourhood object per feature.

        If parks_neighbourhood_lookup is provided, each boundary name is
        normalized and mapped to the parks.csv display name when available.
        """
        with open(boundaries_path) as geojson_file:
            geojson_data = json.load(geojson_file)

        for feature in geojson_data["features"]:
            raw_name = feature["properties"]["name"]
            if parks_neighbourhood_lookup is not None:
                # Normalize the raw name and look it up in the parks_neighbourhood_lookup
                # Return the mapped name if found, otherwise return the raw name.
                name = parks_neighbourhood_lookup.get(
                    _normalize_name(raw_name),
                    raw_name,
                )
            else:
                name = raw_name
            polygon = shape(feature["geometry"])
            self.neighbourhoods.append(Neighbourhood(name, polygon))

        print(f"  Loaded {boundaries_path}  ({len(self.neighbourhoods)} neighbourhoods)\n")

    def neighbourhood_of(self, lat, lon):
        """
        Return the neighbourhood name containing (lat, lon),
        or None if the point falls outside all boundaries.
        """
        for neighbourhood in self.neighbourhoods:
            if neighbourhood.contains(lat, lon):
                return neighbourhood.name
        return None

 
