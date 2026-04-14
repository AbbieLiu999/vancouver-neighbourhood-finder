
"""
analyzer.py
===========

Analysis layer for neighbourhood aggregation and text reporting.

- NeighbourhoodSummary: builds per-neighbourhood raw metrics.
- ReportGenerator: formats rankings and key insights for console output.
"""

from data_loader import (
    ensure_data_files_exist,
    ParkRegistry,
    TransitNetwork,
    NeighbourhoodBoundaries,
)

# Facility types grouped by newcomer profile
PROFILES = {
    "Families": [
        "Playgrounds", "Wading Pool", "Water/Spray Parks", "Swimming Pools",
    ],
    "Dog Lovers": [
        "Dogs Off-Leash Areas",
    ],
    "Sports Players": [
        "Soccer Fields", "Tennis Courts", "Basketball Courts",
        "Baseball Diamonds", "Football Fields", "Rugby Fields",
        "Softball", "Pickleball", "Field Hockey", "Cricket Pitches",
    ],
    "Outdoor Enthusiasts": [
        "Jogging Trails", "Running Tracks", "Skateboard Parks",
        "Disc Golf Courses", "Outdoor Fitness", "Bowling Greens",
        "Golf Courses", "Beaches",
    ],
    "Community Seekers": [
        "Community Centres", "Community Halls", "Field Houses",
        "Food Concessions", "Restaurants", "Picnic Sites",
    ],
}


def build_summary():
    """Load all datasets, build the neighbourhood summary, and return it."""
    ensure_data_files_exist()

    registry = ParkRegistry()
    registry.load_from_csv("data/parks.csv", "data/parks-facilities.csv")

    boundaries = NeighbourhoodBoundaries()
    boundaries.load_from_geojson(
        "data/neighbourhood_boundaries.geojson",
        registry.neighbourhood_name_lookup(),
    )

    network = TransitNetwork()
    network.load_from_csv("data/stops.txt")

    summary = NeighbourhoodSummary(registry, boundaries, network)
    summary.build()
    return summary


# ── NeighbourhoodSummary ──────────────────────────────────────────────────────

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
        self.registry   = registry
        self.boundaries = boundaries
        self.network    = network
        self.data       = {} # neighbourhood name -> summary dict, built by build()

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
                "facility_counts": {}, # facility_type -> count of parks with that type
            }

    def _add_park_count(self):
        """Add park count and total hectares per neighbourhood."""
        for park in self.registry.all_parks():
            neighbourhood_data = self.data[park.neighbourhood]
            neighbourhood_data["park_count"]     += 1
            neighbourhood_data["total_hectares"] += park.hectares

        for neighbourhood_data in self.data.values():
            neighbourhood_data["total_hectares"] = round(neighbourhood_data["total_hectares"], 2)

    def _add_facility_counts(self):
        """Add facility counts per neighbourhood from each park."""
        for park in self.registry.all_parks():
            facility_counts = self.data[park.neighbourhood]["facility_counts"]
            for facility_type in park.facilities:
                facility_counts[facility_type] = facility_counts.get(facility_type, 0) + 1

    def _add_transit_count(self):
        """Fill in transit stop counts for every neighbourhood in the summary.
        
        Uses pre-computed stops_by_neighbourhood mapping from TransitNetwork.
        """
        # Pre-compute neighbourhood assignments once
        if not self.network.stops_by_neighbourhood:
            self.network.assign_to_neighbourhoods(self.boundaries)
        
        # Fill in transit counts from the pre-computed mapping
        for neighbourhood_name in self.data:
            self.data[neighbourhood_name]["transit_count"] = len(
                self.network.stops_by_neighbourhood.get(neighbourhood_name, [])
            )

    def top_by(self, field, n=5, facility_type=None, profile_types=None):
        """
        Return top n (neighbourhood, neighbourhood_data) pairs sorted descending.

        field values:
          "park_count"       - parks
          "total_hectares"   - green space
          "transit_count"    - transit access
          "facility_counts"  - parks with a specific facility_type
                             or total facilities if facility_type is None
                             or grouped facilities if profile_types is provided
        """
        if field == "facility_counts":
            # rank by the total count of parks with any of the given profile types,
            # used to build newcomer profile sections. e.g. top neighbourhoods for
            # families based on playgrounds, wading pools, etc.
            if profile_types:
                def facility_profile_number(neighbourhood_item):
                    _, neighbourhood_data = neighbourhood_item
                    return sum(
                        neighbourhood_data["facility_counts"].get(facility_type, 0)
                        for facility_type in profile_types
                    )

                items = [
                    neighbourhood_item for neighbourhood_item in self.data.items()
                    if facility_profile_number(neighbourhood_item) > 0
                ]
                items.sort(key=facility_profile_number, reverse=True)
                return items[:n]

            # rank by the count of parks with one specific facility type.
            if facility_type:
                def facility_type_number(neighbourhood_item):
                    _, neighbourhood_data = neighbourhood_item
                    return neighbourhood_data["facility_counts"].get(facility_type, 0)

                items = [
                    neighbourhood_item for neighbourhood_item in self.data.items()
                    if facility_type_number(neighbourhood_item) > 0
                ]
                items.sort(key=facility_type_number, reverse=True)
                return items[:n]

            # rank by total count of all facilities.
            def facility_total_number(neighbourhood_item):
                _, neighbourhood_data = neighbourhood_item
                return sum(neighbourhood_data["facility_counts"].values())

            items = list(self.data.items())
            items.sort(key=facility_total_number, reverse=True)
            return items[:n]
        
        # For other fields, rank by the field value directly.   
        items = list(self.data.items())
        items.sort(key=lambda item: item[1][field], reverse=True)
        return items[:n]


# ── ReportGenerator ───────────────────────────────────────────────────────────

class ReportGenerator:
    """
    Prints a text report from a NeighbourhoodSummary, organised by
    newcomer priority so users can skip to what matters to them.

    Attributes
    ----------
    top_n : how many neighbourhoods to show per ranking (default 5)
    """

    DIVIDER = "-" * 62

    def __init__(self, top_n=5):
        """Set report length."""
        self.top_n = top_n

    def print_summary(self, summary):
        """Print the full report."""
        print(self._dataset_summary(summary))
        print(self._section_transit(summary))
        print(self._section_green_space(summary))
        print(self._section_facilities(summary))
        print(self._section_profiles(summary))
        print(self._section_insights(summary))

    # ── private section builders ──────────────────────────────────────────────

    def _dataset_summary(self, summary):
        """Summarise the loaded datasets with basic counts."""
        total_parks = sum(
            neighbourhood_data["park_count"]
            for neighbourhood_data in summary.data.values()
        )
        total_hectares = sum(
            neighbourhood_data["total_hectares"]
            for neighbourhood_data in summary.data.values()
        )

        lines = [
            self.DIVIDER,
            "  DATASET SUMMARY",
            self.DIVIDER,
            f"  Neighbourhoods : {len(summary.data)}",
            f"  Total parks    : {total_parks}",
            f"  Total green    : {total_hectares:.1f} ha",
            f"  Transit stops  : {len(summary.network.stops)}",
        ]
        return "\n".join(lines)

    def _section_transit(self, summary):
        """Build the transit-access ranking section."""
        lines = [
            self.DIVIDER,
            "  IF YOU RELY ON PUBLIC TRANSIT",
            self.DIVIDER,
        ]
        for neighbourhood, neighbourhood_data in summary.top_by("transit_count", self.top_n):
            lines.append(
                f"  {neighbourhood:<30} {neighbourhood_data['transit_count']:>4} stops  "
            )
        return "\n".join(lines)

    def _section_green_space(self, summary):
        """Build the green-space ranking section."""
        lines = [
            self.DIVIDER,
            "  IF YOU LOVE NATURE AND GREEN SPACE",
            self.DIVIDER,
            f"  {'Neighbourhood':<30} {'Parks':>5}  "
            f"{'Total ha':>8}",
            "",
        ]
        for neighbourhood, neighbourhood_data in summary.top_by("total_hectares", self.top_n):
            lines.append(
                f"  {neighbourhood:<30} {neighbourhood_data['park_count']:>5}  "
                f"{neighbourhood_data['total_hectares']:>8.1f}"
            )
        return "\n".join(lines)

    def _section_facilities(self, summary):
        """Build the total-facilities ranking section."""
        lines = [
            self.DIVIDER,
            "  IF YOU WANT THE MOST FACILITIES",
            self.DIVIDER,
            f"  {'Neighbourhood':<30} {'Facilities':>10}",
            "",
        ]
        for neighbourhood, neighbourhood_data in summary.top_by("facility_counts", self.top_n):
            total_facilities = sum(neighbourhood_data["facility_counts"].values())
            lines.append(
                f"  {neighbourhood:<30} {total_facilities:>10}"
            )
        return "\n".join(lines)

    def _section_profiles(self, summary):
        """Build the newcomer profile sections."""
        lines = [self.DIVIDER]

        # For each newcomer profile, rank neighbourhoods by the total count of parks
        # with any of the profile's facility types.
        for profile_name, facility_types in PROFILES.items():
            lines.append(f"  FOR: {profile_name.upper()}")

            top_neighbourhoods = summary.top_by(
                "facility_counts",
                self.top_n,
                profile_types=facility_types,
            )

            if not top_neighbourhoods:
                lines.append("No data found for this profile.")
            else:
                for neighbourhood, neighbourhood_data in top_neighbourhoods:
                    total = sum(
                        neighbourhood_data["facility_counts"].get(facility_type, 0)
                        for facility_type in facility_types
                    )
                    breakdown = "\n ".join(
                        f"      {facility_type:<30}: {summary.data[neighbourhood]['facility_counts'].get(facility_type, 0)}"
                        for facility_type in facility_types
                        if summary.data[neighbourhood]["facility_counts"].get(facility_type, 0) > 0
                    )
                    lines.append(
                        f"  {neighbourhood:<30} total {total}\n" +
                        f" {breakdown}"
                    )

            lines.append(self.DIVIDER)

        return "\n".join(lines)

    def _section_insights(self, summary):
        """Build the key-insights section of the report."""
        lines = [
            self.DIVIDER,
            "  KEY INSIGHTS  ",
            self.DIVIDER,
            self._insight_green_vs_transit(summary),
            "",
            self._insight_worst_facilities(summary),
            "",
            self._insight_dog_lovers(summary),
            "=" * 62,
        ]
        return "\n".join(lines)

    def _insight_green_vs_transit(self, summary):
        """
        There is a trade-off between green space and transit access in Vancouver's neighbourhoods.
        Only visible by joining park size with stop counts.
        """
        greenest_neighbourhood = max(
            summary.data, key=lambda neighbourhood: summary.data[neighbourhood]["total_hectares"]
        )
        greenest_data = summary.data[greenest_neighbourhood]

        best_transit_neighbourhood = max(
            summary.data, key=lambda neighbourhood: summary.data[neighbourhood]["transit_count"]
        )
        best_transit_data = summary.data[best_transit_neighbourhood]

        return (
            f"  INSIGHT 1 - Trade-off Between Green Space and Transit\n"
            f"  Only visible by joining park size with stop counts.\n"
            f"  More green space does not mean better transit access.\n"
            f"  {greenest_neighbourhood} has the most green space ({greenest_data['total_hectares']:.0f} ha)\n"
            f"  but only ({greenest_data['transit_count']}) transit stops.\n"
            f"  {best_transit_neighbourhood} has the most transit stops ({best_transit_data['transit_count']})\n"
            f"  but only ({best_transit_data['total_hectares']:.0f} ha) of green space.\n"
            f"  A newcomer must choose based on what matters most to them."
        )

    def _insight_worst_facilities(self, summary):
        """
        Neighbourhoods that have parks but the fewest total facilities.
        Only visible by joining parks.csv with parks-facilities.csv.
        """
        ranked = sorted(
            summary.data.items(),
            key=lambda item: sum(item[1]["facility_counts"].values())
        )
        bottom3 = ranked[:3]

        lines = ["  INSIGHT 2 - Underserved Neighbourhoods"]
        lines.append("  These neighbourhoods have parks but few facilities.")
        lines.append("  Only visible by joining both park datasets.\n")
        for neighbourhood, neighbourhood_data in bottom3:
            total = sum(neighbourhood_data["facility_counts"].values())
            lines.append(
                f"  {neighbourhood:<30} {neighbourhood_data['park_count']} parks  "
                f"{total:<2} facilities  "
                f"{neighbourhood_data['transit_count']:<2} stops"
            )
        return "\n".join(lines)

    def _insight_dog_lovers(self, summary):
        """
        Best and Worst neighbourhoods for dog owners.
        A warning for dog owners — only visible by joining parks.csv
        with parks-facilities.csv.
        """
        no_dog = [
            (neighbourhood, neighbourhood_data)
            for neighbourhood, neighbourhood_data in summary.data.items()
            if neighbourhood_data["facility_counts"].get("Dogs Off-Leash Areas", 0) == 0
        ]

        has_dog = sorted(
            [
                (neighbourhood, neighbourhood_data)
                for neighbourhood, neighbourhood_data in summary.data.items()
                if neighbourhood_data["facility_counts"].get("Dogs Off-Leash Areas", 0) > 0
            ],
            key=lambda item: (
                item[1]["facility_counts"]["Dogs Off-Leash Areas"],
                item[1]["transit_count"]
            ),
            reverse=True,
        )[:3]

        no_dog_names = ", ".join(neighbourhood for neighbourhood, _ in no_dog)

        lines = ["  INSIGHT 3 - For Dog Lovers"]
        lines.append("  Only visible by joining parks.csv with parks-facilities.csv.\n")
        lines.append(f"  {len(no_dog)} neighbourhoods have parks but no dog")
        lines.append(f"  off-leash areas — avoid these if you have a dog:")
        lines.append(f"  {no_dog_names}\n")
        lines.append("  Best neighbourhoods for dog owners:")
        for neighbourhood, neighbourhood_data in has_dog:
            count = neighbourhood_data["facility_counts"]["Dogs Off-Leash Areas"]
            lines.append(
                f"  {neighbourhood:<30} "
                f"{count} off-leash areas  "
                f"{neighbourhood_data['transit_count']:<3} stops"
            )
        return "\n".join(lines)

    
    