"""
parks.py
========
Parks data model and loading layer.

- Park: a single Vancouver park with its facility types
- ParkRegistry: loads parks.csv and parks-facilities.csv, joins them by ParkID
"""

import pandas as pd

from boundaries import _normalize_name


class Park:
    """
    Represents a single park from the Vancouver Parks dataset.

    facilities is a list of facility type strings joined from
    parks-facilities.csv on ParkID, e.g.:
    ["Playgrounds", "Dogs Off-Leash Areas", "Tennis Courts"]
    """

    def __init__(self, park_id, name, neighbourhood, lat, lon,
                 hectares, facilities):
        """Store the park attributes loaded from the CSV files."""
        self.park_id = park_id
        self.name = name
        self.neighbourhood = neighbourhood
        self.lat = lat
        self.lon = lon
        self.hectares = hectares
        self.facilities = facilities   # list of strings

    def has_facility(self, facility_type):
        """Return True if this park has the given facility type."""
        return facility_type in self.facilities


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
        # copy the dataframe to avoid modifying the original
        df = facilities_df.copy()

        # cleaning: drop rows with missing ParkID or FacilityType,
        # strip whitespace, and remove empty types
        df = df.dropna(subset=["ParkID", "FacilityType"])
        df["FacilityType"] = df["FacilityType"].astype(str).str.strip()
        df = df[df["FacilityType"] != ""]

        # group by ParkID and aggregate unique FacilityType values into lists
        result = (
            df.groupby("ParkID")["FacilityType"]
            .unique()
            .apply(list)
            .to_dict()
        )

        return result

    @staticmethod
    def _row_to_park(row, lat, lon, facilities_map):
        """Convert one parks.csv row into a Park object."""
        park_id = row["ParkID"]
        return Park(
            park_id=park_id,
            name=str(row["Name"]).strip(),
            neighbourhood=str(row["NeighbourhoodName"]).strip(),
            lat=lat,
            lon=lon,
            hectares=float(row["Hectare"])
            if pd.notna(row["Hectare"]) else 0.0,
            facilities=facilities_map.get(park_id, []),
        )

    def load_from_csv(self, parks_path, facilities_path):
        """Read and join both CSV files. Create one Park per row.

        Malformed rows are skipped instead of crashing the whole program.
        """
        # Load both CSV files with pandas, skipping bad lines and checking for required columns.
        parks_df = pd.read_csv(parks_path, sep=";", on_bad_lines="skip")
        facilities_df = pd.read_csv(
            facilities_path, sep=";", on_bad_lines="skip")

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

        print(f"  ParkRegistry: loaded {parks_path} ({len(parks_df)} rows)")
        print(f"  ParkRegistry: loaded {facilities_path} ({len(facilities_df)} rows)")

        # Build a ParkID -> facility type list mapping for efficient lookup.
        facilities_map = self._build_facilities_map(facilities_df)
        # For each park row, parse the lat/lon and create a Park object with its facilities.
        skipped = 0
        for _, row in parks_df.iterrows():
            # Basic validation: skip rows with missing critical fields or invalid coordinates.
            if pd.isna(row["ParkID"]) or pd.isna(row["Name"]) or pd.isna(row["NeighbourhoodName"]):
                skipped += 1
                continue
            # Parse lat/lon from the GoogleMapDest field; skip if invalid.
            parsed_coordinates = self._parse_lat_lon(row["GoogleMapDest"])
            if parsed_coordinates is None:
                skipped += 1
                continue

            lat, lon = parsed_coordinates
            # Create a Park object and add it to the registry, 
            # handling any unexpected errors gracefully.
            try:
                self.parks.append(self._row_to_park(
                    row, lat, lon, facilities_map))
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
        # Return a sorted list for consistent ordering.
        return sorted(facility_types)

    def neighbourhood_name_lookup(self):
        """Return normalized neighbourhood name -> parks.csv display name."""
        lookup = {}
        for park in self.parks:
            neighbourhood_key = _normalize_name(park.neighbourhood)
            if neighbourhood_key not in lookup:
                lookup[neighbourhood_key] = park.neighbourhood
        return lookup
