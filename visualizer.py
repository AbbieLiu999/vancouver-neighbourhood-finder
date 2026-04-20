"""
visualizer.py
=============
Facade class that exposes chart + map generation via one Visualizer API.
"""

import os

from chart_visualizer import ChartVisualizerMixin
from map_visualizer import MapVisualizerMixin
from profiles import MAP_LAYER_FACILITIES


class Visualizer(ChartVisualizerMixin, MapVisualizerMixin):
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
        "chart1_median_x": "#ff9f1c",
        "chart1_median_y": "#9b5de5",
        "chart3_dog_bar": "#ff7f50",
        "chart3_transit_bar": "#888888",
        "map_transit_stop": "#339af0",
    }

    # Map layer configuration (wraps shared facility definitions)
    MAP_LAYERS = {
        layer_name: {"types": facility_types}
        for layer_name, facility_types in MAP_LAYER_FACILITIES.items()
    }

    def __init__(self, summary, charts_dir="charts"):
        """Store summary context and create output directories."""
        self.summary = summary
        self.charts_dir = charts_dir
        os.makedirs(charts_dir, exist_ok=True)
