# Design Document — Vancouver Neighbourhood Finder for Newcomers

## Overview

This project combines four open datasets to help newcomers compare Vancouver neighbourhoods by practical needs: transit access, total green space, and park facilities (dog off-leash, family, sports, outdoors, and community).

The codebase is organised by responsibility: resource-specific modules handle data objects and loading, `summary.py` handles aggregation, `report_generator.py` handles text output, and `visualizer.py` handles charts and map generation through mixins.


## Data Sources Used

1) parks.csv
2) parks-facilities.csv
3) stops.txt (GTFS)
4) neighbourhood_boundaries.geojson


## Current Architecture

parks.py
        - Park
        - ParkRegistry

transit.py
        - TransitStop
        - TransitNetwork

boundaries.py
        - Neighbourhood
        - NeighbourhoodBoundaries

summary_builder.py
        - ensure_data_files_exist
        - build_summary

summary.py
        - NeighbourhoodSummary

profiles.py
        - _FACILITY_CATEGORIES (internal single source of truth)
        - FACILITY_PROFILES (derived; newcomer-facing profiles for text reports)
        - MAP_LAYER_FACILITIES (derived; map visualization layers)

report_generator.py
        - ReportGenerator (imports FACILITY_PROFILES from profiles.py)

chart_visualizer.py
        - ChartVisualizerMixin

map_visualizer.py
        - MapVisualizerMixin

visualizer.py
        - Visualizer facade (single public visualization API)

main.py
        - main() (runs full pipeline)

text_report.py
        - main() (prints text report only)


## Runtime Flow

1) main.py calls build_summary() from summary_builder.py
2) build_summary() loads datasets via parks/transit/boundaries modules and builds NeighbourhoodSummary
3) ReportGenerator prints the console report
4) Visualizer writes 3 PNG charts and map.html


## Class Responsibilities

Class descriptions below follow the same order as classes appear in the source files.

### Park (parks.py)
`Park` models one record from the parks dataset and is responsible for storing park-level information in a clean, reusable object. Its key attributes are `park_id`, `name`, `neighbourhood`, `lat`, `lon`, `hectares`, and `facilities`. Its key method is `has_facility(facility_type)`, which supports higher-level filtering and map layer logic without duplicating facility-check code elsewhere.

### TransitStop (transit.py)
`TransitStop` models one GTFS stop and is responsible for representing stop identity and location only. Its key attributes are `stop_id`, `name`, `lat`, and `lon`. It intentionally has no complex methods because its role is to act as a simple entity that can be loaded, assigned to neighbourhoods, counted, and visualized by other classes.

### Neighbourhood (boundaries.py)
`Neighbourhood` models one boundary polygon and is responsible for geometric containment checks. Its key attributes are `name` and `polygon`. Its key method is `contains(lat, lon)`, which performs the point-in-polygon test used to determine whether transit stops belong to a specific Vancouver neighbourhood.

### ParkRegistry (parks.py)
`ParkRegistry` is responsible for loading and joining `parks.csv` with `parks-facilities.csv` and exposing park-level query helpers. Its key attribute is `parks` (a list of `Park` objects). Its key methods are `load_from_csv(parks_path, facilities_path)`, `all_parks()`, `parks_with_facility(facility_type)`, and `all_facility_types()`, plus internal helpers used for coordinate parsing and row-to-object conversion.

### TransitNetwork (transit.py)
`TransitNetwork` is responsible for loading transit stop records, applying an initial Metro Vancouver bounding-box filter at load time, and preparing reusable neighbourhood assignments. Its key attributes are `stops` (filtered loaded `TransitStop` objects) and `stops_by_neighbourhood` (a cached mapping for fast counting and mapping). Its key methods are `load_from_csv(stops_path)` and `assign_to_neighbourhoods(boundaries)`, where assignment is computed once and reused by analysis and visualization.

### NeighbourhoodBoundaries (boundaries.py)
`NeighbourhoodBoundaries` is responsible for loading GeoJSON boundary shapes and resolving neighbourhood membership for coordinates. Its key attribute is `neighbourhoods` (a list of `Neighbourhood` objects). Its key methods are `load_from_geojson(boundaries_path, neighbourhood_name_lookup=None)` for ingesting polygons and `neighbourhood_of(lat, lon)` for returning the matching neighbourhood name.

### NeighbourhoodSummary (summary.py)
`NeighbourhoodSummary` is the core analysis class, responsible for joining parks, facilities, transit stops, and boundaries into one per-neighbourhood summary table. Its key attributes are `registry`, `boundaries`, `network`, and `data`, where each neighbourhood row stores `park_count`, `total_hectares`, `transit_count`, and `facility_counts`. Its key public methods are `build()`, `top_by_field(...)`, `top_by_facility(...)`, and `top_by_profile(...)`.

### ReportGenerator (report_generator.py)
`ReportGenerator` is responsible for transforming summary data into a human-readable console report focused on newcomer decision-making. Its key attribute is `top_n` (how many neighbourhoods to show per ranking section). Its key method is `print_summary(summary)`, which orchestrates dataset summary, transit/green/facility rankings, profile-based sections, and cross-dataset insights.

### ChartVisualizerMixin (chart_visualizer.py)
`ChartVisualizerMixin` is responsible for all matplotlib chart generation from the built summary object. It contains chart-specific helpers and methods `chart_green_vs_transit()`, `chart_most_facilities()`, and `chart_dog_lovers()`.

### MapVisualizerMixin (map_visualizer.py)
`MapVisualizerMixin` is responsible for all folium map-generation internals, including base park markers, category facility layers, and transit stop layer assembly.

### Visualizer (visualizer.py)
`Visualizer` is a facade that composes `ChartVisualizerMixin` and `MapVisualizerMixin` into one public API. It exposes chart and map outputs while centralizing shared configuration (`COLORS`) and importing `MAP_LAYER_FACILITIES` from `profiles.py` to maintain a single source of truth for facility categorization. It preserves backward compatibility through its own `MAP_LAYERS` attribute, which wraps the imported facilities.

## Class Interaction Overview

The interaction flow is linear and layered: `main.py` triggers `build_summary()` from `summary_builder.py`, which uses resource-specific data modules (`parks.py`, `transit.py`, and `boundaries.py`) to create domain objects (`Park`, `TransitStop`, `Neighbourhood`). `NeighbourhoodSummary` then joins these datasets into neighbourhood-level metrics. From that shared summary, `ReportGenerator` produces the text report and `Visualizer` facade delegates output generation to chart/map mixins. This keeps each class focused on one responsibility while allowing all outputs to be generated from a single, consistent summary state.


## Current Output Files

- charts/c1_green_transit.png
- charts/c2_facility_mix.png
- charts/c3_dog_transit.png
- map.html


## Design Notes

- **Facility categorization (DRY):** All facility type definitions are centralized in `profiles.py` via `_FACILITY_CATEGORIES` (internal single source of truth). Two derived dictionaries (`FACILITY_PROFILES` for text reports, `MAP_LAYER_FACILITIES` for map visualization) are generated from this central definition. Updating a facility list in `_FACILITY_CATEGORIES` automatically keeps both outputs in sync.
- **Data loading:** `summary_builder.py` orchestrates loading; `parks.py`, `transit.py`, and `boundaries.py` load their own datasets. Metro Vancouver bounding-box filtering for transit remains in `TransitNetwork`.
- **Robustness:** loaders now fail gracefully: malformed transit rows, park rows, facility rows, and GeoJSON features are skipped; missing required columns in CSVs or invalid GeoJSON structure trigger clear error messages.
- **Filtering:** neighbourhood-level assignment/counting is performed by `TransitNetwork.assign_to_neighbourhoods(...)` and then consumed by `NeighbourhoodSummary`.
- **Performance:** Transit stops are assigned once (in assign_to_neighbourhoods) and cached in stops_by_neighbourhood for reuse.
- **Point-in-polygon:** Uses shapely geometry for accurate neighbourhood assignment.
- **Map layers:** One emoji per facility category in layer control (not per type).
- **Transit visualization:** Circle markers on map; uses stops assigned to Vancouver neighbourhoods.
- **Park visualization:** Circle markers sized by hectares; base layer always shown.
