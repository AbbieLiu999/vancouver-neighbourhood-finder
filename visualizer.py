"""
visualizer.py
=============
One class that produces all charts and the interactive map.
Outputs:
    charts/c1_green_transit.png             (matplotlib)
    charts/c2_facility_mix.png              (matplotlib)
    charts/c3_dog_transit.png               (matplotlib)
    map.html                                         (folium interactive)

The map has one toggleable layer per facility type, each with an emoji
icon. Users tick what matters to them — dog parks, playgrounds, sports
fields, transit stops — and the map updates instantly.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import folium


class Visualizer:
    """
    Saves all output files from a built NeighbourhoodSummary.

    Attributes
    ----------
    summary    : the built NeighbourhoodSummary
    charts_dir : folder where chart files are written
    COLORS     : shared color palette
    MAP_LAYERS : category-to-facility map layer configuration
    """

    COLORS = {
        "figure_bg":   "#fdfdfd",
        "axes_bg":     "#f4f4f4",
        "text_color":  "#1a1a2e",
        "chart1_scatter_cmap": "turbo",
        "chart1_median_x": "#ff9f1c",
        "chart1_median_y": "#9b5de5",
        "chart3_dog_bar": "#ff7f50",
        "chart3_transit_bar": "#339af0",
        "map_transit_stop": "#339af0",
    }

    # Map layers: one emoji per category, not per individual facility type.
    # Each category groups related facility types together.
    # Clicking a marker shows the exact facilities inside that park.
    MAP_LAYERS = {
        "🐕 Dog Off-Leash": {
            "types":  ["Dogs Off-Leash Areas"],
        },
        "🛝 Family": {
            "types":  ["Playgrounds", "Wading Pool",
                       "Water/Spray Parks", "Swimming Pools"],
        },
        "⚽ Sports": {
            "types":  ["Soccer Fields", "Tennis Courts", "Basketball Courts",
                       "Baseball Diamonds", "Softball", "Football Fields",
                       "Rugby Fields", "Pickleball", "Field Hockey",
                       "Cricket Pitches", "Ultimate Fields", "Ball Hockey",
                       "Lighted Fields", "Lacrosse Boxes",
                       "Outdoor Roller Hockey Rinks", "Rinks",
                       "Bowling Greens", "Golf Courses",
                       "Skateboard Parks", "Disc Golf Courses"],
        },
        "🏃 Outdoors": {
            "types":  ["Jogging Trails", "Running Tracks",
                       "Beaches", "Outdoor Fitness"],
        },
        "🏛️ Community": {
            "types":  ["Community Centres", "Community Halls",
                       "Field Houses", "Picnic Sites",
                       "Restaurants", "Food Concessions"],
        },
        "🚌 Transit Stops": {
            "types":  [],          # handled separately
        },
    }

    def __init__(self, summary, charts_dir="charts"):
        """Store the summary and create the chart output directory."""
        self.summary    = summary
        self.charts_dir = charts_dir
        os.makedirs(charts_dir, exist_ok=True)

    def _apply_chart_style(self, ax, grid_axis="y"):
        """Apply a shared visual style across matplotlib charts."""
        ax.set_facecolor(self.COLORS["axes_bg"])
        ax.tick_params(colors=self.COLORS["text_color"], labelsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis=grid_axis, linestyle="--", alpha=0.22)
        ax.set_axisbelow(True)

    def _set_chart_title(self, ax, title):
        """Set a consistent chart title."""
        ax.set_title(
            title,
            fontsize=14,
            fontweight="bold",
            color=self.COLORS["text_color"],
            pad=18,
        )

    # ── Chart 1 — Green Space vs Transit scatter ──────────────────────────────
    # Insight 1: the fundamental trade-off every newcomer faces

    def chart_green_vs_transit(self):
        """
        Scatter plot: total hectares vs transit stops per neighbourhood.
        Shows the green space vs transit trade-off visually.
        """
        out = os.path.join(self.charts_dir, "c1_green_transit.png")

        neighbourhood_names = list(self.summary.data.keys())
        total_hectares_list = [
            self.summary.data[neighbourhood]["total_hectares"]
            for neighbourhood in neighbourhood_names
        ]
        transit_stops_list = [
            self.summary.data[neighbourhood]["transit_stops"]
            for neighbourhood in neighbourhood_names
        ]

        fig, ax = plt.subplots(figsize=(11, 8),
                       facecolor=self.COLORS["figure_bg"])
        self._apply_chart_style(ax, grid_axis="both")

        scatter = ax.scatter(
            total_hectares_list,
            transit_stops_list,
            c=transit_stops_list,
            cmap=self.COLORS["chart1_scatter_cmap"],
            s=95,
            alpha=0.9,
            edgecolors="white",
            linewidths=0.6,
        )

        cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
        cbar.set_label("Transit stops", fontsize=10, color=self.COLORS["text_color"])
        cbar.ax.tick_params(labelsize=8)

        # label every dot
        for x, y, neighbourhood_name in zip(
            total_hectares_list, transit_stops_list, neighbourhood_names
        ):
            ax.annotate(neighbourhood_name, (x, y),
                        fontsize=7.5, color=self.COLORS["text_color"],
                        textcoords="offset points", xytext=(6, 3))

        # median reference lines
        median_hectares = sorted(total_hectares_list)[len(total_hectares_list) // 2]
        median_transit_stops = sorted(transit_stops_list)[len(transit_stops_list) // 2]
        ax.axvline(median_hectares, color=self.COLORS["chart1_median_x"], linestyle="--",
                   alpha=0.5, lw=1)
        ax.axhline(median_transit_stops, color=self.COLORS["chart1_median_y"], linestyle="--",
                   alpha=0.5, lw=1)

        ax.set_xlabel("Total Green Space (ha)",
                      fontsize=11, color=self.COLORS["text_color"])
        ax.set_ylabel("Transit Stops",
                      fontsize=11, color=self.COLORS["text_color"])
        self._set_chart_title(
            ax,
            "Green vs Go: Vancouver Neighbourhood Trade-offs",
        )
        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved {out}")

    # ── Chart 2 — Facility breakdown stacked bar ───────────────────────────────
    # Insight 2: underserved neighbourhoods — each facility type its own colour

    def chart_most_facilities(self):
        """
        Stacked horizontal bar: all neighbourhoods ranked by total facilities,
        each facility type shown in a different colour.
        Most-served neighbourhoods appear at the top.
        """
        out = os.path.join(self.charts_dir, "c2_facility_mix.png")

        # get all facility types that appear in the data
        facility_types = self.summary.registry.all_facility_types()

        # sort neighbourhoods by total facilities ascending.
        # barh renders categories bottom-to-top, so this places most-served at top.
        sorted_neighbourhoods = sorted(
            self.summary.data.keys(),
            key=lambda nb: sum(
                self.summary.data[nb]["facility_counts"].values()
            )
        )

        # build a color map — one color per facility type
        cmap = plt.get_cmap("tab20")
        facility_colors = {
            facility_type: cmap(i / len(facility_types))
            for i, facility_type in enumerate(facility_types)
        }

        fig, ax = plt.subplots(
            figsize=(12, max(6, len(sorted_neighbourhoods) * 0.45)),
            facecolor=self.COLORS["figure_bg"]
        )
        self._apply_chart_style(ax, grid_axis="x")
        # build the stacked bars iteratively, one facility type at a time
        left_counts = np.zeros(len(sorted_neighbourhoods))
        for facility_type in facility_types:
            values = [
                self.summary.data[neighbourhood]["facility_counts"].get(facility_type, 0)
                for neighbourhood in sorted_neighbourhoods
            ]
            if sum(values) == 0:
                continue
            ax.barh(sorted_neighbourhoods, values, left=left_counts,
                    color=facility_colors[facility_type],
                    label=facility_type, edgecolor="white", height=0.7)
            left_counts += np.array(values)

        ax.set_xlabel("Number of Parks with Each Facility Type",
                      fontsize=11, color=self.COLORS["text_color"])
        self._set_chart_title(
            ax,
            "Facility Mix Across Vancouver Neighbourhoods",
        )
        ax.legend(fontsize=7, loc="lower right",
                  ncol=2, framealpha=0.8)
        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved {out}")

    # ── Chart 3 — Dog lovers: off-leash areas + transit ───────────────────────
    # Insight 3: best and worst neighbourhoods for dog owners

    def chart_dog_lovers(self):
        """
        Horizontal lollipop chart: dog off-leash area count and transit
        stops per neighbourhood. Shows which neighbourhoods are best for
        dog owners who rely on transit.
        """
        out = os.path.join(self.charts_dir, "c3_dog_transit.png")

        # sort by dog off-leash count first, then transit stops (both descending)
        sorted_neighbourhoods = sorted(
            self.summary.data.keys(),
            key=lambda neighbourhood: (
                self.summary.data[neighbourhood]["facility_counts"].get("Dogs Off-Leash Areas", 0),
                self.summary.data[neighbourhood]["transit_stops"],
            ),
            reverse=True,
        )

        dog_off_leash_counts = [
            self.summary.data[neighbourhood]["facility_counts"]
                        .get("Dogs Off-Leash Areas", 0)
            for neighbourhood in sorted_neighbourhoods
        ]
        transit_stop_counts = [
            self.summary.data[neighbourhood]["transit_stops"]
            for neighbourhood in sorted_neighbourhoods
        ]

        # normalise stops to same scale as dog counts for readability
        max_dog_count = max(dog_off_leash_counts) if max(dog_off_leash_counts) > 0 else 1
        max_transit_stops = max(transit_stop_counts) if max(transit_stop_counts) > 0 else 1
        scale = max_dog_count / max_transit_stops

        y_positions = np.arange(len(sorted_neighbourhoods))
        offset = 0.16

        fig, ax = plt.subplots(figsize=(13, 7),
                       facecolor=self.COLORS["figure_bg"])
        self._apply_chart_style(ax, grid_axis="x")

        dog_y = y_positions - offset
        transit_y = y_positions + offset

        scaled_transit = [s * scale for s in transit_stop_counts]

        # Dog off-leash lollipops
        ax.hlines(dog_y, 0, dog_off_leash_counts,
              color=self.COLORS["chart3_dog_bar"], linewidth=3.0, alpha=0.75)
        ax.scatter(dog_off_leash_counts, dog_y,
               s=90, color=self.COLORS["chart3_dog_bar"],
               edgecolors="white", linewidths=0.8,
               label="Dog Off-Leash Areas", zorder=3)

        # Transit lollipops
        ax.hlines(transit_y, 0, scaled_transit,
              color=self.COLORS["chart3_transit_bar"], linewidth=3.0, alpha=0.75)
        ax.scatter(scaled_transit, transit_y,
               s=90, color=self.COLORS["chart3_transit_bar"],
               edgecolors="white", linewidths=0.8,
               label="Transit Stops (scaled)", zorder=3)

        ax.set_yticks(y_positions)
        ax.set_yticklabels(sorted_neighbourhoods, fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlabel("Dog Off-Leash Areas", fontsize=11, color=self.COLORS["text_color"])
        dog_ticks = np.arange(0, max_dog_count + 1, 1)
        ax.set_xticks(dog_ticks)
        ax.set_xlim(0, max_dog_count + 0.2)

        # Use rounded integer ticks on the transit axis (e.g., 0, 50, 100, 150, 200).
        if max_transit_stops <= 20:
            transit_step = 5
        elif max_transit_stops <= 60:
            transit_step = 10
        elif max_transit_stops <= 120:
            transit_step = 20
        elif max_transit_stops <= 250:
            transit_step = 50
        else:
            transit_step = 100

        transit_max_rounded = int(np.ceil(max_transit_stops / transit_step) * transit_step)
        transit_ticks = np.arange(0, transit_max_rounded + 1, transit_step)
        x_max = max(max_dog_count, transit_max_rounded * scale)
        ax.set_xlim(0, x_max + 0.2)

        # Add a second x-axis for raw transit-stop scale.
        ax_top = ax.twiny()
        ax_top.set_xlim(ax.get_xlim())
        ax_top.set_xticks([tick * scale for tick in transit_ticks])
        ax_top.set_xticklabels([str(int(tick)) for tick in transit_ticks])
        ax_top.set_xlabel("Transit Stops", fontsize=11, color=self.COLORS["text_color"])
        ax_top.tick_params(axis="x", colors=self.COLORS["text_color"])

        self._set_chart_title(
            ax,
            "Dog Parks + Transit, Side by Side",
        )
        ax.legend(loc="lower right", fontsize=9, frameon=True, framealpha=0.95)
        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved {out}")

    # ── Folium map ────────────────────────────────────────────────────────────

    def save_map(self):
        """
        Interactive folium map with 7 toggleable layers:
          🌲 All Parks       — grey circles, always on
          🐕 Dog Off-Leash   — parks with dog off-leash areas
          🛝 Family          — parks with playgrounds / pools / spray parks
          ⚽ Sports          — parks with any sports facility
          🏃 Outdoors        — parks with trails / beaches / fitness
          🏛️ Community       — parks with community centres / picnic sites
          🚌 Transit Stops   — TransLink stop locations

        Each marker shows one emoji for the category. Clicking it opens
        a popup listing the exact facilities that park has.
        Multiple layers can be active at once.
        """
        out = "map.html"

        m = folium.Map(
            location=[49.248, -123.117],
            zoom_start=12,
            tiles="CartoDB positron",
            control_scale=True,   # shows a distance scale bar (km/miles)
        )

        # ── Base layer: all parks as sized grey circles ───────────
        base_layer = folium.FeatureGroup(name="🌲 All Parks", show=True)
        for park in self.summary.registry.all_parks():
            neighbourhood_data = self.summary.data.get(park.neighbourhood, {})
            neighbourhood_transit_stops = neighbourhood_data.get("transit_stops", 0)
            neighbourhood_total_hectares = neighbourhood_data.get("total_hectares", 0.0)
            facilities_list = ", ".join(park.facilities) if park.facilities else "No recorded facilities"

            popup_text = (
                f"{park.name}<br>"
                f"Neighbourhood: {park.neighbourhood}<br>"
                f"Area: {park.hectares:.1f} ha<br>"
                f"Facilities: {len(park.facilities)}<br>"
                f"{facilities_list}<br>"
                f"Transit stops nearby: {neighbourhood_transit_stops}<br>"
                f"Total green space: {neighbourhood_total_hectares:.1f} ha"
            )
            folium.CircleMarker(
                location=[park.lat, park.lon],
                radius=max(4, min(12, 3 + park.hectares / 5)),
                color="#888888",
                weight=1,
                fill=True,
                fill_color="#cccccc",
                fill_opacity=0.5,
                popup=folium.Popup(popup_text, max_width=280),
                tooltip=f"🌲 {park.name}  |  {park.neighbourhood}",
            ).add_to(base_layer)
        base_layer.add_to(m)

        # ── One layer per category ────────────────────────────────
        for layer_name, layer_config in self.MAP_LAYERS.items():
            if layer_name == "🚌 Transit Stops":
                continue    # handled separately below

            emoji = layer_name.split()[0]
            facility_types = layer_config["types"]
            layer = folium.FeatureGroup(name=layer_name, show=False)

            # collect parks that have at least one facility in this category
            seen_park_ids = set()
            for facility_type in facility_types:
                for park in self.summary.registry.parks_with_facility(facility_type):
                    if park.park_id in seen_park_ids:
                        continue
                    seen_park_ids.add(park.park_id)

                    # list only the facilities in this category that the park has
                    matching_facilities = [f for f in park.facilities if f in facility_types]
                    matching_facilities_text = ", ".join(matching_facilities)
                    popup_text = (
                        f"{emoji} {park.name}<br>"
                        f"Neighbourhood: {park.neighbourhood}<br>"
                        f"Area: {park.hectares:.1f} ha<br>"
                        f"{layer_name.split(' ', 1)[1]} facilities: {matching_facilities_text}"
                    )
                    emoji_icon = folium.DivIcon(
                        html=f'<div style="font-size:20px;text-align:center;line-height:1">{emoji}</div>',
                        icon_size=(24,24),
                        icon_anchor=(12,12),
                    )
                    folium.Marker(
                        location=[park.lat, park.lon],
                        icon=emoji_icon,
                        popup=folium.Popup(popup_text, max_width=260),
                        tooltip=(
                            f"{emoji} {park.name}  |  "
                            f"{matching_facilities_text}"
                        ),
                    ).add_to(layer)

            layer.add_to(m)

        # ── Transit stops layer — only stops inside Vancouver ─────
        # Get all stops that have been assigned to a Vancouver neighbourhood
        # (Metro Vancouver stops outside the city are not in stops_by_neighbourhood)
        stop_layer = folium.FeatureGroup(name="🚌 Transit Stops", show=False)
        transit_stops = [
            stop
            for stops_list in self.summary.network.stops_by_neighbourhood.values()
            for stop in stops_list
        ]
        for transit_stop in transit_stops:
            folium.CircleMarker(
                location=[transit_stop.lat, transit_stop.lon],
                radius=3,
                color=self.COLORS["map_transit_stop"],
                fill=True,
                fill_color=self.COLORS["map_transit_stop"],
                fill_opacity=0.65,
                weight=0,
                tooltip=transit_stop.name,
            ).add_to(stop_layer)
        stop_layer.add_to(m)

        # ── Layer control ────────────────────────────────────────
        folium.LayerControl(collapsed=False).add_to(m)

        m.save(out)
        print(f"  Saved {out}")
