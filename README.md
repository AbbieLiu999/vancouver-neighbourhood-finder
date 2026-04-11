# Vancouver Neighbourhood Finder — For Newcomers

A Python data analysis program that combines four open Vancouver datasets
to help newcomers choose which neighbourhood to live in based on what
matters most to them — transit access, green space, dog parks, playgrounds,
or sports facilities.

---

## What the program produces

| Output | File | Description |
|---|---|---|
| Text report | printed to console | Dataset summaries, rankings, and insights |
| Chart 1 | `charts/c1_green_transit.png` | Green space vs transit access by neighbourhood |
| Chart 2 | `charts/c2_facility_mix.png` | Facility breakdown by neighbourhood (most-served at top) |
| Chart 3 | `charts/c3_dog_transit.png` | Dog off-leash areas vs transit by neighbourhood |
| Map | `map.html` | Interactive folium map with toggleable layers |

---

## Datasets

### 1. Vancouver Parks
- **Source:** City of Vancouver Open Data Portal
- **URL:** https://opendata.vancouver.ca/explore/dataset/parks/export/
- **Download:** Click Export → CSV → Save as `data/parks.csv`
- **Licence:** Open Government Licence – Vancouver

### 2. Vancouver Parks Facilities
- **Source:** City of Vancouver Open Data Portal
- **URL:** https://opendata.vancouver.ca/explore/dataset/parks-facilities/export/
- **Download:** Click Export → CSV → Save as `data/parks-facilities.csv`
- **Licence:** Open Government Licence – Vancouver

### 3. TransLink Stops
- **Source:** TransLink Developer Resources
- **URL:** https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources/gtfs/gtfs-data
- **Download:** Click "GTFS Static Data" → download zip → open zip → copy `stops.txt` → save as `data/stops.txt`
- **Licence:** TransLink Open Data Terms of Use

### 4. Vancouver Local Area Boundary
- **Source:** City of Vancouver Open Data Portal
- **URL:** https://opendata.vancouver.ca/explore/dataset/local-area-boundary/export/
- **Download:** Click Export → GeoJSON → Save as `data/neighbourhood_boundaries.geojson`
- **Licence:** Open Government Licence – Vancouver
- **Purpose:** Provides exact polygon boundaries for Vancouver's 22 neighbourhoods, used to assign each transit stop to its correct neighbourhood via point-in-polygon geometry

---

## Setup

### 1. Place data files

Create a `data/` folder in the same directory as the Python files:

```
data/
  parks.csv
  parks-facilities.csv
  stops.txt
  neighbourhood_boundaries.geojson
```

### 2. Install required libraries

All imported libraries are required for the full program (`main.py`).
If any are missing (including `folium`), Python will raise an import error.

```bash
python -m pip install pandas matplotlib folium shapely
```

### 3. Run the text report only

```bash
python text_report.py
```

### 4. Run the full program (text report + charts + map)

```bash
python main.py
```

---

## Project Links

- **GitHub Repository:** https://github.com/<your-username>/<your-repo>
- **GitHub Pages Map:** https://abbieliu999.github.io/vancouver-neighbourhood-finder/
> Replace the placeholders above with your actual links before submission.

---

## Project structure

```
main.py              Entry point — runs full analysis, charts, and map
text_report.py       Prints text report to console
models.py            Park, TransitStop, Neighbourhood  (domain objects)
data_loader.py       ParkRegistry, TransitNetwork, NeighbourhoodBoundaries
analyzer.py          NeighbourhoodSummary, ReportGenerator  (analysis)
visualizer.py        Visualizer  (charts + interactive map)
design.md            Class design written before coding
README.md            This file
data/                Downloaded datasets (not included in repo)
charts/              Generated PNG charts (created on first run)
map.html             Generated interactive map
```

---

## Libraries

| Library | Purpose |
|---|---|
| `pandas` | Reading and joining CSV files |
| `matplotlib` | Saving PNG charts |
| `folium` | Interactive map with toggleable facility layers |
| `shapely` | Point-in-polygon geometry for assigning stops to neighbourhoods |

---

## Known limitations

- **Transit stop assignment** — transit stops are assigned to
  neighbourhoods using exact point-in-polygon geometry from the
  Vancouver Local Area Boundary dataset. Stops that fall outside
  all 22 neighbourhood boundaries (e.g. in industrial areas or
  on the boundary line) are not counted.

- **Park coordinates** — `GoogleMapDest` in parks.csv points to the
  park's navigation destination, which is close to the entrance for
  most parks. For very large parks the coordinate may be closer to the
  centre than the entrance.

- **Facility data** — `parks-facilities.csv` lists facilities recorded
  by the City of Vancouver Parks Board. Some parks may have unlisted
  or outdated facility records.

---

## AI Assistance

AI tools were used as auxiliary support, not as a primary authoring mechanism.
Scope of AI usage:
- Identifying potential bugs and edge cases
- Suggesting and validating fixes during refactoring
- Assisting with README structure, clarity, and formatting
- Improving grammar and phrasing

All core project decisions and implementations were completed independently, including:
- Problem framing and dataset selection
- System architecture and class design
- Aggregation and ranking methodology
- Insight design and interpretation
- Visualization goals and interaction design
