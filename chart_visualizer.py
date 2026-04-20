"""
chart_visualizer.py
===================
Chart rendering mixin for Visualizer.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

import matplotlib
matplotlib.use("Agg")


class ChartVisualizerMixin:
    """Chart-related helpers and rendering methods."""

    # ── Shared chart helpers ────────────────────────────────────────────────

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

    def _make_chart_axes(self, figsize, grid_axis):
        """Create a styled matplotlib figure/axes pair."""
        fig, ax = plt.subplots(figsize=figsize,
                               facecolor=self.COLORS["figure_bg"])
        self._apply_chart_style(ax, grid_axis=grid_axis)
        return fig, ax

    @staticmethod
    def _save_chart(fig, output_path):
        """Save and close a matplotlib figure with consistent settings."""
        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved {output_path}")

    @staticmethod
    def _median(values):
        """Return the middle value from a sequence."""
        sorted_values = sorted(values)
        return sorted_values[len(sorted_values) // 2]

    @staticmethod
    def _choose_transit_tick_step(max_transit_stops):
        """Choose a readable top-axis tick step for transit stops."""
        if max_transit_stops <= 20:
            return 5
        if max_transit_stops <= 60:
            return 10
        if max_transit_stops <= 120:
            return 20
        if max_transit_stops <= 250:
            return 50
        return 100

    # ── Chart-specific data helpers ─────────────────────────────────────────

    def _get_chart1_data(self):
        """Return chart 1 neighbourhood labels and axis series."""
        neighbourhood_names = list(self.summary.data.keys())
        total_hectares = [
            self.summary.data[neighbourhood]["total_hectares"]
            for neighbourhood in neighbourhood_names
        ]
        transformed_hectares = np.log1p(total_hectares)
        transit_stops = [
            self.summary.data[neighbourhood]["transit_count"]
            for neighbourhood in neighbourhood_names
        ]
        return neighbourhood_names, transformed_hectares, transit_stops

    def _add_chart1_labels(self, ax, x_values, y_values, labels):
        """Place text labels for chart 1 scatter points with small offsets."""
        y_span = max(y_values) - min(y_values) if y_values else 1
        x_span = max(x_values) - min(x_values) if len(x_values) else 1
        y_offset = max(y_span * 0.02, 0.25)
        x_offset = max(x_span * 0.01, 0.05)

        for index, (x_value, y_value, label) in enumerate(zip(x_values, y_values, labels)):
            direction = 1 if (index % 2 == 0) else -1
            ax.text(
                x_value + x_offset,
                y_value + direction * y_offset,
                label,
                fontsize=7.5,
                color=self.COLORS["text_color"],
            )

    def _get_neighbourhoods_sorted_by_total_facilities(self):
        """Return neighbourhoods sorted by total facility counts ascending."""
        return sorted(
            self.summary.data.keys(),
            key=lambda neighbourhood: sum(
                self.summary.data[neighbourhood]["facility_counts"].values()
            ),
        )

    def _get_ranked_dog_transit_data(self):
        """Return sorted neighbourhoods with dog counts and transit counts."""
        sorted_neighbourhoods = sorted(
            self.summary.data.keys(),
            key=lambda neighbourhood: (
                self.summary.data[neighbourhood]["facility_counts"].get(
                    "Dogs Off-Leash Areas", 0
                ),
                self.summary.data[neighbourhood]["transit_count"],
            ),
            reverse=True,
        )

        dog_off_leash_counts = [
            self.summary.data[neighbourhood]["facility_counts"].get(
                "Dogs Off-Leash Areas", 0
            )
            for neighbourhood in sorted_neighbourhoods
        ]
        transit_stop_counts = [
            self.summary.data[neighbourhood]["transit_count"]
            for neighbourhood in sorted_neighbourhoods
        ]
        return sorted_neighbourhoods, dog_off_leash_counts, transit_stop_counts

    # ── Chart 1 — Green Space vs Transit scatter ──────────────────────────────

    def chart_green_vs_transit(self):
        """
        Scatter plot: total hectares vs transit stops per neighbourhood.
        Shows the green space vs transit trade-off visually.
        """
        out = os.path.join(self.charts_dir, "c1_green_transit.png")

        neighbourhood_names, transformed_hectares, transit_stops_list = self._get_chart1_data()

        fig, ax = self._make_chart_axes(figsize=(11, 10), grid_axis="both")

        ax.scatter(
            transformed_hectares,
            transit_stops_list,
            color=self.COLORS["chart3_transit_bar"],
            s=95,
            alpha=0.9,
            edgecolors="white",
            linewidths=0.6,
        )

        self._add_chart1_labels(
            ax,
            transformed_hectares,
            transit_stops_list,
            neighbourhood_names,
        )

        median_hectares = self._median(transformed_hectares)
        median_transit_stops = self._median(transit_stops_list)
        ax.axvline(median_hectares, color=self.COLORS["chart1_median_x"], linestyle="--",
                   alpha=0.5, lw=1)
        ax.axhline(median_transit_stops, color=self.COLORS["chart1_median_y"], linestyle="--",
                   alpha=0.5, lw=1)

        ax.set_xlabel("Total Green Space (log1p ha)",
                      fontsize=11, color=self.COLORS["text_color"])
        ax.set_ylabel("Transit Stops",
                      fontsize=11, color=self.COLORS["text_color"])
        self._set_chart_title(
            ax,
            "Green vs Go: Vancouver Neighbourhood Trade-offs",
        )
        self._save_chart(fig, out)

    # ── Chart 2 — Facility breakdown stacked bar ───────────────────────────────

    def chart_most_facilities(self):
        """
        Stacked horizontal bar: all neighbourhoods ranked by total facilities,
        each facility type shown in a different colour.
        Most-served neighbourhoods appear at the top.
        """
        out = os.path.join(self.charts_dir, "c2_facility_mix.png")

        facility_types = self.summary.registry.all_facility_types()
        sorted_neighbourhoods = self._get_neighbourhoods_sorted_by_total_facilities()

        cmap = plt.get_cmap("tab20")
        facility_colors = {
            facility_type: cmap(i / len(facility_types))
            for i, facility_type in enumerate(facility_types)
        }

        fig, ax = self._make_chart_axes(
            figsize=(12, max(6, len(sorted_neighbourhoods) * 0.45)),
            grid_axis="x",
        )

        left_counts = np.zeros(len(sorted_neighbourhoods))
        for facility_type in facility_types:
            values = [
                self.summary.data[neighbourhood]["facility_counts"].get(
                    facility_type, 0)
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
        self._save_chart(fig, out)

    # ── Chart 3 — Dog lovers: off-leash areas + transit ───────────────────────

    def chart_dog_lovers(self):
        """
        Grouped horizontal bar chart with dual x-axes:
        bottom axis shows dog off-leash counts, top axis shows transit stops.
        """
        out = os.path.join(self.charts_dir, "c3_dog_transit.png")

        sorted_neighbourhoods, dog_off_leash_counts, transit_stop_counts = (
            self._get_ranked_dog_transit_data()
        )

        max_dog_count = max(dog_off_leash_counts) if max(dog_off_leash_counts) > 0 else 1
        max_transit_stops = max(transit_stop_counts) if max(transit_stop_counts) > 0 else 1
        scale = max_dog_count / max_transit_stops

        y_positions = np.arange(len(sorted_neighbourhoods))
        bar_height = 0.38

        fig, ax = self._make_chart_axes(figsize=(13, 8), grid_axis="x")

        scaled_transit = [value * scale for value in transit_stop_counts]

        ax.barh(
            y_positions - bar_height / 2,
            dog_off_leash_counts,
            height=bar_height,
            color=self.COLORS["chart3_dog_bar"],
            edgecolor="white",
            linewidth=0.8,
            label="Dog Off-Leash Areas",
        )
        ax.barh(
            y_positions + bar_height / 2,
            scaled_transit,
            height=bar_height,
            color=self.COLORS["chart3_transit_bar"],
            edgecolor="white",
            linewidth=0.8,
            label="Transit Stops (scaled)",
        )

        ax.set_yticks(y_positions)
        ax.set_yticklabels(sorted_neighbourhoods, fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlabel("Dog Off-Leash Areas", fontsize=11,
                      color=self.COLORS["text_color"])
        x_max = max(max_dog_count, max_transit_stops * scale)
        ax.set_xlim(0, x_max + 0.2)
        ax.set_xticks(np.arange(0, max_dog_count + 1, 1))

        transit_step = self._choose_transit_tick_step(max_transit_stops)

        transit_max_rounded = int(np.ceil(max_transit_stops / transit_step) * transit_step)
        transit_ticks = np.arange(0, transit_max_rounded + 1, transit_step)

        ax_top = ax.twiny()
        ax_top.set_xlim(ax.get_xlim())
        ax_top.set_xticks([tick * scale for tick in transit_ticks])
        ax_top.set_xticklabels([str(int(tick)) for tick in transit_ticks])
        ax_top.set_xlabel("Transit Stops", fontsize=11,
                          color=self.COLORS["text_color"])
        ax_top.tick_params(axis="x", colors=self.COLORS["text_color"])

        self._set_chart_title(
            ax,
            "Dog Parks + Transit, Side by Side",
        )
        ax.legend(loc="lower right", fontsize=9, frameon=True, framealpha=0.95)
        self._save_chart(fig, out)
