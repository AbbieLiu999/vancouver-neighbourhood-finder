"""
Vancouver Neighbourhood Finder — For Newcomers
==============================================

Combines four open datasets to help newcomers choose which Vancouver
neighbourhood to live in based on what matters most to them.

Before running, download the data files and place them in data/:

  1. Vancouver Parks
     https://opendata.vancouver.ca/explore/dataset/parks/export/
     -> save as data/parks.csv

  2. Vancouver Parks Facilities
     https://opendata.vancouver.ca/explore/dataset/parks-facilities/export/
     -> save as data/parks-facilities.csv

  3. TransLink GTFS stops
     https://www.translink.ca/about-us/doing-business-with-translink/
     app-developer-resources/gtfs/gtfs-data
     -> download zip, open it, copy stops.txt -> save as data/stops.txt

  4. Vancouver Local Area Boundary
     https://opendata.vancouver.ca/explore/dataset/local-area-boundary/export/
     -> save as data/neighbourhood_boundaries.geojson

Then run:
    python main.py
"""

from summary_builder import build_summary
from report_generator import ReportGenerator
from visualizer import Visualizer

DIVISION = "=" * 62


def main():
    """Run the full analysis pipeline and generate the report, charts, and map."""
    print("\n" + DIVISION)
    print("  Vancouver Neighbourhood Finder — For Newcomers")
    print(DIVISION + "\n")

    # ── 1. Load data and build summary ─────────────────────────────
    print("Loading data ...\n")
    summary = build_summary()

    # ── 2. Print report ───────────────────────────────────────────
    report = ReportGenerator()
    report.print_summary(summary)

    # ── 3. Save charts ────────────────────────────────────────────
    print("\nGenerating charts ...\n")
    viz = Visualizer(summary)
    viz.chart_green_vs_transit()              # c1_green_transit.png
    viz.chart_most_facilities()               # c2_facility_mix.png
    viz.chart_dog_lovers()                    # c3_dog_transit.png

    # ── 4. Save map ───────────────────────────────────────────────
    print("\nBuilding map ...\n")
    viz.save_map()                            # map.html

    print(DIVISION)
    print("  Done!")
    print("  Charts  ->  charts/  (3 x PNG)")
    print("  Map     ->  map.html  (deploy to GitHub Pages)")
    print(DIVISION + "\n")


if __name__ == "__main__":
    main()
