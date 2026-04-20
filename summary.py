"""
summary.py
==========
Neighbourhood aggregation model.

- NeighbourhoodSummary: aggregate park, facility, and transit metrics.
"""


class NeighbourhoodSummary:
    """
    Joins parks, facilities, and transit stops into one summary per
    neighbourhood. Summary rows are initialized from neighbourhood
    boundaries, then parks, facilities, and transit are layered in.
    This is the analytical core — the data that none of the three
    source files can provide alone.

    self.data maps neighbourhood name to:
      park_count       int    number of parks
      total_hectares   float  total green space in ha
      transit_count    int    number of transit stops
      facility_counts  dict   facility_type -> count of parks with that type

    Attributes
    ----------
    registry   : ParkRegistry
    boundaries : NeighbourhoodBoundaries
    network    : TransitNetwork
    data       : dict (populated by build())
    """

    def __init__(self, registry, boundaries, network):
        """Store the loaded datasets and prepare an empty summary map."""
        self.registry = registry
        self.boundaries = boundaries
        self.network = network
        self.data = {}  # neighbourhood name -> summary dict, built by build()

    def build(self):
        """Aggregate all datasets into self.data."""
        print("  Building neighbourhood summary ...")

        self._init_neighbourhoods()
        self._add_park_count()
        self._add_facility_counts()
        self._add_transit_count()

        print(f"  Done — {len(self.data)} neighbourhoods.\n")

    def _init_neighbourhoods(self):
        """Initialize empty summary rows for all neighbourhood boundaries."""
        for neighbourhood in self.boundaries.neighbourhoods:
            self.data[neighbourhood.name] = {
                "park_count":      0,
                "total_hectares":  0.0,
                "transit_count":   0,
                "facility_counts": {},
            }

    def _add_park_count(self):
        """Add park count and total hectares per neighbourhood.

        Parks whose neighbourhood name doesn't match any boundary in the
        GeoJSON (typos, renamed areas, regional parks like Stanley Park)
        are skipped and reported as a warning.
        """
        unknown = 0
        for park in self.registry.all_parks():
            if park.neighbourhood not in self.data:
                unknown += 1
                continue
            neighbourhood_data = self.data[park.neighbourhood]
            neighbourhood_data["park_count"] += 1
            neighbourhood_data["total_hectares"] += park.hectares

        for neighbourhood_data in self.data.values():
            neighbourhood_data["total_hectares"] = round(
                neighbourhood_data["total_hectares"], 2)

        if unknown:
            print(
                f"  Warning: {unknown} parks had neighbourhoods not in boundary file")

    def _add_facility_counts(self):
        """Add facility counts per neighbourhood from each park."""
        for park in self.registry.all_parks():
            if park.neighbourhood not in self.data:
                continue

            facility_counts = self.data[park.neighbourhood]["facility_counts"]
            for facility_type in park.facilities:
                facility_counts[facility_type] = facility_counts.get(
                    facility_type, 0) + 1

    def _add_transit_count(self):
        """Fill in transit stop counts for every neighbourhood in the summary.

        Relies on stops_by_neighbourhood being pre-populated by
        TransitNetwork.assign_to_neighbourhoods (called in build_summary).
        """
        for neighbourhood_name in self.data:
            self.data[neighbourhood_name]["transit_count"] = len(
                self.network.stops_by_neighbourhood.get(neighbourhood_name, [])
            )

    def top_by_field(self, field, n=5):
        """
        Return top n (neighbourhood, neighbourhood_data) pairs ranked by a
        direct summary field, sorted descending.

        field values:
          "park_count"      - parks
          "total_hectares"  - green space
          "transit_count"   - transit access
          "facility_counts" - total count across all facility types
        """
        if field == "facility_counts":
            def key(item):
                return sum(item[1]["facility_counts"].values())
        else:
            def key(item):
                return item[1][field]

        items = list(self.data.items())
        items.sort(key=key, reverse=True)
        return items[:n]

    def top_by_facility(self, facility_type, n=5):
        """
        Return top n neighbourhoods ranked by count of parks with a specific
        facility type. Neighbourhoods with zero are excluded so rankings
        don't get padded with ties on zero.
        """
        def count(item):
            return item[1]["facility_counts"].get(facility_type, 0)

        items = [item for item in self.data.items() if count(item) > 0]
        items.sort(key=count, reverse=True)
        return items[:n]

    def top_by_profile(self, facility_types, n=5):
        """
        Return top n neighbourhoods ranked by the total count of parks with
        any facility type in facility_types.
        Neighbourhoods with zero matching facilities are excluded.
        """
        def total(item):
            return sum(
                item[1]["facility_counts"].get(facility_type, 0)
                for facility_type in facility_types
            )

        items = [item for item in self.data.items() if total(item) > 0]
        items.sort(key=total, reverse=True)
        return items[:n]
