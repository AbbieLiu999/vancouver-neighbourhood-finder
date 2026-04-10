# Design Document — Vancouver Neighbourhood Finder for Newcomers

## Overview

This project combines four open datasets to help newcomers compare Vancouver
neighbourhoods by practical needs: transit access, total green space, and
park facilities (dog off-leash, family, sports, outdoors, and community).

The current implementation intentionally uses raw counts and raw area totals.
No custom weighted score is used.


## Data Sources Used

1) parks.csv
2) parks-facilities.csv
3) stops.txt (GTFS)
4) neighbourhood_boundaries.geojson


## Current Architecture

models.py
        - Park
        - TransitStop
        - Neighbourhood

data_loader.py
        - ensure_data_files_exist()
        - load_core_data()
        - ParkRegistry
        - TransitNetwork
        - NeighbourhoodBoundaries

analyzer.py
        - PROFILES
        - build_summary()
        - NeighbourhoodSummary
        - ReportGenerator

visualizer.py
        - Visualizer

main.py
        - main() (runs full pipeline)

text_report.py
        - main() (prints text report only)


## Runtime Flow

1) main.py calls build_summary() from analyzer.py
2) build_summary() loads datasets and builds NeighbourhoodSummary
3) ReportGenerator prints the console report
4) Visualizer writes 3 PNG charts and map.html


## Class Responsibilities (Current)

### Park (models.py)
Represents a single park record with ID, name, neighbourhood, coordinates,
hectares, and facilities.

Method:
- has_facility(facility_type)


### TransitStop (models.py)
Represents one stop with ID, name, and coordinates.


### Neighbourhood (models.py)
Represents one boundary polygon.

Method:
- contains(lat, lon)


### ParkRegistry (data_loader.py)
Loads parks + facilities CSV, joins via ParkID, and exposes park queries.

Methods:
- load_from_csv(parks_path, facilities_path)
- all_parks()
- parks_with_facility(facility_type)
- all_facility_types()


### TransitNetwork (data_loader.py)
Loads all transit stops from GTFS stops.txt without filtering.
Neighbourhood assignment is performed on-demand by analyzer.py.

Attributes:
- stops: list of all TransitStop objects
- stops_by_neighbourhood: dict mapping neighbourhood name -> list of TransitStop

Methods:
- load_from_csv(stops_path)
- assign_to_neighbourhoods(boundaries)  [called by NeighbourhoodSummary]


### NeighbourhoodBoundaries (data_loader.py)
Loads GeoJSON polygons and resolves which neighbourhood contains a point.

Methods:
- load_from_geojson(boundaries_path)
- neighbourhood_of(lat, lon)


### NeighbourhoodSummary (analyzer.py)
Aggregates park/facility/transit data into one dict per neighbourhood.
Builds neighbourhood summary by joining four data sources.

Per-neighbourhood fields (current):
- park_count
- total_hectares
- transit_stops
- facility_counts

Methods:
- build()  [runs all aggregation steps]
- top_by(field, n=5, facility_type=None, facility_types=None)
- _init_neighbourhoods()
- _add_park_counts()
- _add_facility_counts()
- _add_transit_counts()  [triggers assign_to_neighbourhoods() on first call]


### ReportGenerator (analyzer.py)
Formats and prints report sections for transit, green space, profile
facility counts, and key insights.

Main method:
- print_summary(summary)


### Visualizer (visualizer.py)
Writes three matplotlib charts and one folium map.

Methods:
- chart_green_vs_transit()
- chart_most_facilities()
- chart_dog_lovers()
- save_map()


## Current Output Files

- charts/c1_green_transit.png
- charts/c2_facility_mix.png
- charts/c3_dog_transit.png
- map.html


## Design Notes

- **Data loading:** data_loader loads all raw data without filtering.
- **Filtering:** analyzer.py filters transit stops by neighbourhood boundary.
- **Performance:** Transit stops are assigned once (in assign_to_neighbourhoods)
  and cached in stops_by_neighbourhood for reuse.
- **Point-in-polygon:** Uses shapely geometry for accurate neighbourhood assignment.
- **Map layers:** One emoji per facility category in layer control (not per type).
- **Transit visualization:** Circle markers on map; stops filtered to Vancouver only.
- **Park visualization:** Circle markers sized by hectares; base layer always shown.
