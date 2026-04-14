# Design Document — Vancouver Neighbourhood Finder for Newcomers

## Overview

This project combines four open datasets to help newcomers compare Vancouver neighbourhoods by practical needs: transit access, total green space, and park facilities (dog off-leash, family, sports, outdoors, and community).


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
        - ParkRegistry
        - TransitNetwork
        - NeighbourhoodBoundaries

analyzer.py
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


## Class Responsibilities

Class descriptions below follow the same order as classes appear in the source files.

### Park (models.py)
`Park` models one record from the parks dataset and is responsible for storing park-level information in a clean, reusable object. Its key attributes are `park_id`, `name`, `neighbourhood`, `lat`, `lon`, `hectares`, and `facilities`. Its key method is `has_facility(facility_type)`, which supports higher-level filtering and map layer logic without duplicating facility-check code elsewhere.

### TransitStop (models.py)
`TransitStop` models one GTFS stop and is responsible for representing stop identity and location only. Its key attributes are `stop_id`, `name`, `lat`, and `lon`. It intentionally has no complex methods because its role is to act as a simple entity that can be loaded, assigned to neighbourhoods, counted, and visualized by other classes.

### Neighbourhood (models.py)
`Neighbourhood` models one boundary polygon and is responsible for geometric containment checks. Its key attributes are `name` and `polygon`. Its key method is `contains(lat, lon)`, which performs the point-in-polygon test used to determine whether transit stops belong to a specific Vancouver neighbourhood.

### ParkRegistry (data_loader.py)
`ParkRegistry` is responsible for loading and joining `parks.csv` with `parks-facilities.csv` and exposing park-level query helpers. Its key attribute is `parks` (a list of `Park` objects). Its key methods are `load_from_csv(parks_path, facilities_path)`, `all_parks()`, `parks_with_facility(facility_type)`, and `all_facility_types()`, plus internal helpers used for coordinate parsing and row-to-object conversion.

### TransitNetwork (data_loader.py)
`TransitNetwork` is responsible for loading transit stop records, applying an initial Metro Vancouver bounding-box filter at load time, and preparing reusable neighbourhood assignments. Its key attributes are `stops` (filtered loaded `TransitStop` objects) and `stops_by_neighbourhood` (a cached mapping for fast counting and mapping). Its key methods are `load_from_csv(stops_path)` and `assign_to_neighbourhoods(boundaries)`, where assignment is computed once and reused by analysis and visualization.

### NeighbourhoodBoundaries (data_loader.py)
`NeighbourhoodBoundaries` is responsible for loading GeoJSON boundary shapes and resolving neighbourhood membership for coordinates. Its key attribute is `neighbourhoods` (a list of `Neighbourhood` objects). Its key methods are `load_from_geojson(boundaries_path, neighbourhood_name_lookup=None)` for ingesting polygons and `neighbourhood_of(lat, lon)` for returning the matching neighbourhood name.

### NeighbourhoodSummary (analyzer.py)
`NeighbourhoodSummary` is the core analysis class, responsible for joining parks, facilities, transit stops, and boundaries into one per-neighbourhood summary table. Its key attributes are `registry`, `boundaries`, `network`, and `data`, where each neighbourhood row stores `park_count`, `total_hectares`, `transit_count`, and `facility_counts`. Its key public methods are `build()` (pipeline entry) and `top_by(...)` (ranking helper for ranking/report sections).

### ReportGenerator (analyzer.py)
`ReportGenerator` is responsible for transforming summary data into a human-readable console report focused on newcomer decision-making. Its key attribute is `top_n` (how many neighbourhoods to show per ranking section). Its key method is `print_summary(summary)`, which orchestrates dataset summary, transit/green/facility rankings, profile-based sections, and cross-dataset insights.

### Visualizer (visualizer.py)
`Visualizer` is responsible for producing all visual outputs from a built summary object. Its key attributes are `summary`, `charts_dir`, `COLORS`, and `MAP_LAYERS`. Its key methods are `chart_green_vs_transit()`, `chart_most_facilities()`, `chart_dog_lovers()`, and `save_map()`, which together generate the three required static charts and the interactive folium map.

## Class Interaction Overview

The interaction flow is linear and layered: `main.py` triggers `build_summary()`, which uses data-loading classes (`ParkRegistry`, `TransitNetwork`, and `NeighbourhoodBoundaries`) to create domain objects (`Park`, `TransitStop`, `Neighbourhood`). `NeighbourhoodSummary` then joins these datasets into neighbourhood-level metrics. From that shared summary, `ReportGenerator` produces the text report and `Visualizer` produces charts and map output. This keeps each class focused on one responsibility while allowing all outputs to be generated from a single, consistent summary state.


## Current Output Files

- charts/c1_green_transit.png
- charts/c2_facility_mix.png
- charts/c3_dog_transit.png
- map.html


## Design Notes

- **Data loading:** data_loader.py loads datasets and applies Metro Vancouver bounding-box filtering to transit stops.
- **Robustness:** loaders now fail gracefully: malformed transit rows, park rows, facility rows, and GeoJSON features are skipped; missing required columns in CSVs or invalid GeoJSON structure trigger clear error messages.
- **Filtering:** analyzer.py performs neighbourhood-level assignment/counting using boundary geometry.
- **Performance:** Transit stops are assigned once (in assign_to_neighbourhoods) and cached in stops_by_neighbourhood for reuse.
- **Point-in-polygon:** Uses shapely geometry for accurate neighbourhood assignment.
- **Map layers:** One emoji per facility category in layer control (not per type).
- **Transit visualization:** Circle markers on map; uses stops assigned to Vancouver neighbourhoods.
- **Park visualization:** Circle markers sized by hectares; base layer always shown.
