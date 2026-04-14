"""
text_report.py
==============
Standalone runnable script that prints a formatted text report to the console.

Report includes:
  - A summary of each dataset (record counts, key statistics)
  - At least three meaningful insights drawn from the data
  - At least one insight that connects multiple datasets

Datasets required in data/:
  data/parks.csv
  data/parks-facilities.csv
  data/stops.txt
  data/neighbourhood_boundaries.geojson

See README.md for download instructions.
"""

from analyzer import build_summary, ReportGenerator


def main():
    """Build the summary and print the text report to the console."""
    summary = build_summary()

    report = ReportGenerator()
    report.print_summary(summary)


if __name__ == "__main__":
    main()
