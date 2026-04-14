
"""
models.py
=========
Domain objects — pure data classes with no loading or analysis logic.

  Park          - a single Vancouver park with its facility types
  TransitStop   - a single TransLink bus or rail stop
  Neighbourhood - a single Vancouver neighbourhood with its boundary polygon
"""

from shapely.geometry import Point

# ── Park ──────────────────────────────────────────────────────────────

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
        self.park_id       = park_id
        self.name          = name
        self.neighbourhood = neighbourhood
        self.lat           = lat
        self.lon           = lon
        self.hectares      = hectares
        self.facilities    = facilities   # list of strings

    def has_facility(self, facility_type):
        """Return True if this park has the given facility type."""
        return facility_type in self.facilities

# ── TransitStop ──────────────────────────────────────────────────────────────

class TransitStop:
    """Represents a single TransLink bus or rail stop."""

    def __init__(self, stop_id, name, lat, lon):
        """Store the transit stop attributes loaded from stops.txt."""
        self.stop_id = stop_id
        self.name    = name
        self.lat     = lat
        self.lon     = lon

# ── Neighbourhood ──────────────────────────────────────────────────────────────

class Neighbourhood:
    """
    Represents a single Vancouver neighbourhood with its boundary polygon.
    The polygon is a shapely geometry object used for point-in-polygon checks.
    """

    def __init__(self, name, polygon):
        """Store the neighbourhood name and boundary polygon."""
        self.name    = name
        self.polygon = polygon

    def contains(self, lat, lon):
        """Return True if (lat, lon) falls inside this neighbourhood."""
        return self.polygon.contains(Point(lon, lat))
