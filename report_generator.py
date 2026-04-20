"""
report_generator.py
===================
Text reporting layer for neighbourhood analysis output.
"""

from profiles import FACILITY_PROFILES


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
        for neighbourhood, neighbourhood_data in summary.top_by_field("transit_count", self.top_n):
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
            f"  {'Neighbourhood':<30} {'Parks':>5}  {'Total ha':>8}",
            "",
        ]
        for neighbourhood, neighbourhood_data in summary.top_by_field("total_hectares", self.top_n):
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
        for neighbourhood, neighbourhood_data in summary.top_by_field("facility_counts", self.top_n):
            total_facilities = sum(neighbourhood_data["facility_counts"].values())
            lines.append(
                f"  {neighbourhood:<30} {total_facilities:>10}"
            )
        return "\n".join(lines)

    def _section_profiles(self, summary):
        """Build the newcomer profile sections."""
        lines = [self.DIVIDER]

        for profile_name, facility_types in FACILITY_PROFILES.items():
            lines.append(f"  FOR: {profile_name.upper()}")

            top_neighbourhoods = summary.top_by_profile(
                facility_types,
                self.top_n
            )

            if not top_neighbourhoods:
                lines.append("No data found for this profile.")
            else:
                for neighbourhood, neighbourhood_data in top_neighbourhoods:
                    total = sum(
                        neighbourhood_data["facility_counts"].get(
                            facility_type, 0)
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
        if not summary.data:
            return "  INSIGHT 1 - No data available."

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
        if not summary.data:
            return "  INSIGHT 2 - No data available."

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
        if not summary.data:
            return "  INSIGHT 3 - No data available."

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
        lines.append(
            "  Only visible by joining parks.csv with parks-facilities.csv.\n")
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
