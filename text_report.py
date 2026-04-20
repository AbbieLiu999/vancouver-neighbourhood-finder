"""
text_report.py
==============
Standalone runnable script that prints a formatted text report to the console.

Datasets required in data/:
  data/parks.csv
  data/parks-facilities.csv
  data/stops.txt
  data/neighbourhood_boundaries.geojson

See README.md for download instructions.
"""

from summary_builder import build_summary
from report_generator import ReportGenerator


def main():
    """Build the summary and print the text report to the console."""
    summary = build_summary()

    report = ReportGenerator()
    report.print_summary(summary)


if __name__ == "__main__":
    main()
