"""
transit.py
==========
Transit data model and loading layer.

- TransitStop: a single TransLink bus or rail stop
- TransitNetwork: loads stops.txt and manages transit stop collection
"""

import pandas as pd


class TransitStop:
    """Represents a single TransLink bus or rail stop."""

    def __init__(self, stop_id, name, lat, lon):
        """Store the transit stop attributes loaded from stops.txt."""
        self.stop_id = stop_id
        self.name = name
        self.lat = lat
        self.lon = lon


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
        NeighbourhoodSummary in summary.py.

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
        # Filter to Metro Vancouver stops before processing to save time and memory.
        stops_df = self._filter_metro_vancouver_stops(stops_df)

        skipped = 0
        for _, row in stops_df.iterrows():
            try:
                stop = TransitStop(
                    stop_id=str(row["stop_id"]),
                    name=str(row["stop_name"]),
                    lat=float(row["stop_lat"]),
                    lon=float(row["stop_lon"]),
                )
                self.stops.append(stop)
            except (TypeError, ValueError):
                skipped += 1

        print(f"  TransitNetwork: loaded {stops_path} ({len(self.stops)} stops), "
              f"{skipped} skipped")
        print()

    def assign_to_neighbourhoods(self, boundaries):
        """
        Pre-compute neighbourhood assignments for all stops.
        Builds stops_by_neighbourhood dict once instead of point-in-polygon
        checking repeatedly for each neighbourhood.
        """
        for stop in self.stops:
            neighbourhood_name = boundaries.neighbourhood_of(
                stop.lat, stop.lon)
            if neighbourhood_name:
                if neighbourhood_name not in self.stops_by_neighbourhood:
                    self.stops_by_neighbourhood[neighbourhood_name] = []
                self.stops_by_neighbourhood[neighbourhood_name].append(stop)
