"""
boundaries.py
=============
Neighbourhood boundary data model and loading layer.

- Neighbourhood: a single Vancouver neighbourhood with its boundary polygon
- NeighbourhoodBoundaries: loads and manages neighbourhood polygons
"""

import json
import re

from shapely.geometry import Point, shape


def _normalize_name(name):
    """Return a lowercase comparison key with punctuation collapsed to spaces."""
    text = re.sub(r"[^0-9A-Za-z]+", " ", str(name).strip().lower())
    return re.sub(r"\s+", " ", text).strip()


class Neighbourhood:
    """
    Represents a single Vancouver neighbourhood with its boundary polygon.
    The polygon is a shapely geometry object used for point-in-polygon checks.
    """

    def __init__(self, name, polygon):
        """Store the neighbourhood name and boundary polygon."""
        self.name = name
        self.polygon = polygon

    def contains(self, lat, lon):
        """Return True if (lat, lon) falls inside this neighbourhood."""
        # shapely's Point uses (lon, lat) order, which is the opposite of our convention.
        return self.polygon.contains(Point(lon, lat))


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
                # Extract the raw name of the neighbourhood from the feature properties, 
                # normalize it, and look up the display name from parks.csv if available.
                raw_name = feature["properties"]["name"]
                if neighbourhood_name_lookup is not None:
                    name = neighbourhood_name_lookup.get(
                        _normalize_name(raw_name),
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

        print(
            f"  NeighbourhoodBoundaries: loaded {boundaries_path} "
            f"({len(self.neighbourhoods)} neighbourhoods), {skipped} skipped")
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
