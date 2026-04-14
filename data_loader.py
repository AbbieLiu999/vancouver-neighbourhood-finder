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

    REQUIRED_PARK_COLUMNS = {
        "ParkID", "Name", "NeighbourhoodName", "GoogleMapDest", "Hectare"
    }
    REQUIRED_FACILITY_COLUMNS = {"ParkID", "FacilityType"}

    def __init__(self):
        """Create an empty park registry."""
        self.parks = []

    # Helper methods for loading and joining the two CSV files into Park objects
    @staticmethod
    def _normalize_name(name):
        """Return a lowercase comparison key with punctuation collapsed to spaces."""
        text = re.sub(r"[^0-9A-Za-z]+", " ", str(name).strip().lower())
        return re.sub(r"\s+", " ", text).strip()

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
            raw_facility_type = row["FacilityType"]
            if pd.isna(park_id) or pd.isna(raw_facility_type):
                continue
            
            facility_type = str(raw_facility_type).strip()
            if not facility_type:
                continue
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
        """Read and join both CSV files. Create one Park per row.

        Malformed rows are skipped instead of crashing the whole program.
        """

        parks_df = pd.read_csv(parks_path, sep=";", on_bad_lines="skip")
        facilities_df = pd.read_csv(facilities_path, sep=";", on_bad_lines="skip")

        missing_columns_by_file = {
            "parks.csv": self.REQUIRED_PARK_COLUMNS - set(parks_df.columns),
            "parks-facilities.csv": self.REQUIRED_FACILITY_COLUMNS - set(facilities_df.columns),
        }
        if any(missing_columns_by_file.values()):
            print("\n  Required columns are missing from input park files.\n")

            for file_name, missing_columns in missing_columns_by_file.items():
                if not missing_columns:
                    continue
                print(f"  {file_name} missing columns:")
                for column_name in sorted(missing_columns):
                    print(f"  - {column_name}")

            print("\n  Please download valid files and try again.\n")
            raise SystemExit(1)

        print(f"  Loaded {parks_path}            ({len(parks_df)} rows)")
        print(f"  Loaded {facilities_path}  ({len(facilities_df)} rows)")

        # Build a ParkID -> facility type list mapping for efficient lookup.
        facilities_map = self._build_facilities_map(facilities_df)
        # For each park row, parse the lat/lon and create a Park object with its facilities.
        skipped = 0
        for _, row in parks_df.iterrows():
            if pd.isna(row["ParkID"]) or pd.isna(row["Name"]) or pd.isna(row["NeighbourhoodName"]):
                skipped += 1
                continue

            parsed_coordinates = self._parse_lat_lon(row["GoogleMapDest"])
            if parsed_coordinates is None:
                skipped += 1
                continue

            lat, lon = parsed_coordinates
            try:
                self.parks.append(self._row_to_park(row, lat, lon, facilities_map))
            except (TypeError, ValueError):
                skipped += 1

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
            neighbourhood_key = self._normalize_name(park.neighbourhood)
            if neighbourhood_key not in lookup:
                lookup[neighbourhood_key] = park.neighbourhood
        return lookup
    

# ── TransitNetwork ────────────────────────────────────────────────────────────

class TransitNetwork:
    """
    Loads stops.txt and stores TransitStop objects.
    Performs Metro Vancouver filtering and returns only local stops.
    Filtering by neighbourhood is handled by NeighbourhoodSummary using boundaries.

    Attributes
    ----------
    stops               : list of TransitStop objects
    stops_by_neighbourhood : dict mapping neighbourhood name -> list of TransitStop
    """

    METRO_MIN_LAT = 49.0
    METRO_MAX_LAT = 49.5
    METRO_MIN_LON = -123.3
    METRO_MAX_LON = -122.5
    REQUIRED_STOP_COLUMNS = {"stop_id", "stop_name", "stop_lat", "stop_lon"}

    def __init__(self):
        """Create an empty transit network."""
        self.stops = []
        self.stops_by_neighbourhood = {}

    @staticmethod
    def _filter_metro_vancouver_stops(stops_df):
        """Keep only stops inside the Metro Vancouver bounding box."""
        return stops_df[
            (stops_df["stop_lat"] >= TransitNetwork.METRO_MIN_LAT) &
            (stops_df["stop_lat"] <= TransitNetwork.METRO_MAX_LAT) &
            (stops_df["stop_lon"] >= TransitNetwork.METRO_MIN_LON) &
            (stops_df["stop_lon"] <= TransitNetwork.METRO_MAX_LON)
        ].reset_index(drop=True)

    def load_from_csv(self, stops_path):
        """
        Read stops.txt, filter to Metro Vancouver, and load transit stops.
        Further neighbourhood-level assignment is handled by
        NeighbourhoodSummary in analyzer.py.

        Malformed rows are skipped instead of crashing the whole program.
        """
        stops_df = pd.read_csv(stops_path, on_bad_lines="skip")

        missing_columns = self.REQUIRED_STOP_COLUMNS - set(stops_df.columns)
        if missing_columns:
            print("\n  stops.txt is missing required columns:\n")
            for column_name in sorted(missing_columns):
                print(f"  - {column_name}")
            print("\n  Please download a valid GTFS stops.txt and try again.\n")
            raise SystemExit(1)

        stops_df = self._filter_metro_vancouver_stops(stops_df)

        skipped = 0
        for _, row in stops_df.iterrows():
            try:
                stop = TransitStop(
                    stop_id = str(row["stop_id"]),
                    name    = str(row["stop_name"]),
                    lat     = float(row["stop_lat"]),
                    lon     = float(row["stop_lon"]),
                )
                self.stops.append(stop)
            except (TypeError, ValueError):
                skipped += 1

        print(f"  TransitNetwork: {len(self.stops)} stops loaded")
        if skipped > 0:
            print(f"  TransitNetwork: {skipped} malformed stop rows skipped")
        print()

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

    def load_from_geojson(self, boundaries_path, neighbourhood_name_lookup=None):
        """
        Read the local area boundary GeoJSON file and create one
        Neighbourhood object per feature.

        If neighbourhood_name_lookup is provided, each boundary name is
        normalized and mapped to the parks.csv display name when available.
        Malformed features are skipped.
        """
        try:
            with open(boundaries_path) as geojson_file:
                geojson_data = json.load(geojson_file)
        except (OSError, json.JSONDecodeError) as e:
            print("\n  Failed to read a valid neighbourhood GeoJSON file.")
            print(f"  File: {boundaries_path}")
            print(f"  Error: {e}")
            print("  Please download the file again and retry.\n")
            raise SystemExit(1)

        features = geojson_data.get("features", [])
        if not isinstance(features, list):
            print("\n  Invalid neighbourhood GeoJSON: 'features' must be a list.\n")
            raise SystemExit(1)

        skipped = 0
        for feature in features:
            try:
                raw_name = feature["properties"]["name"]
                if neighbourhood_name_lookup is not None:
                    name = neighbourhood_name_lookup.get(
                        ParkRegistry._normalize_name(raw_name),
                        raw_name,
                    )
                else:
                    name = raw_name

                polygon = shape(feature["geometry"])
                if polygon.is_empty:
                    skipped += 1
                    continue

                self.neighbourhoods.append(Neighbourhood(name, polygon))
            except (KeyError, TypeError, ValueError):
                skipped += 1

        print(f"  Loaded {boundaries_path}  ({len(self.neighbourhoods)} neighbourhoods)")
        if skipped > 0:
            print(f"  NeighbourhoodBoundaries: {skipped} malformed features skipped")
        print()

    def neighbourhood_of(self, lat, lon):
        """
        Return the neighbourhood name containing (lat, lon),
        or None if the point falls outside all boundaries.
        """
        for neighbourhood in self.neighbourhoods:
            if neighbourhood.contains(lat, lon):
                return neighbourhood.name
        return None

 
