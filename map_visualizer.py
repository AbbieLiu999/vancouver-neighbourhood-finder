"""
map_visualizer.py
=================
Map rendering mixin for Visualizer.
"""

import folium


class MapVisualizerMixin:
    """Folium map helpers and map rendering methods."""

    # ── Map helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _get_map_center():
        """Return the default Vancouver map center (lat, lon)."""
        return [49.248, -123.117]

    @staticmethod
    def _get_layer_emoji(layer_name):
        """Extract the leading emoji token from a layer name."""
        return layer_name.split()[0]

    @staticmethod
    def _get_layer_category_label(layer_name):
        """Extract the category text after the leading emoji."""
        return layer_name.split(" ", 1)[1]

    @staticmethod
    def _get_base_park_popup_text(park, neighbourhood_transit_count, neighbourhood_total_hectares):
        """Build popup text for the base all-parks layer."""
        facilities_list = ", ".join(
            park.facilities) if park.facilities else "No recorded facilities"
        return (
            f"{park.name}<br>"
            f"Neighbourhood: {park.neighbourhood}<br>"
            f"Area: {park.hectares:.1f} ha<br>"
            f"Facilities: {len(park.facilities)}<br>"
            f"{facilities_list}<br>"
            f"Transit stops nearby: {neighbourhood_transit_count}<br>"
            f"Total green space: {neighbourhood_total_hectares:.1f} ha"
        )

    @staticmethod
    def _get_category_facility_popup_text(emoji, park, category_label, matching_facilities_text):
        """Build popup text for category-specific park markers."""
        return (
            f"{emoji} {park.name}<br>"
            f"Neighbourhood: {park.neighbourhood}<br>"
            f"Area: {park.hectares:.1f} ha<br>"
            f"{category_label} facilities: {matching_facilities_text}"
        )

    @staticmethod
    def _get_category_emoji_icon(emoji):
        """Build a folium DivIcon for a category emoji marker."""
        return folium.DivIcon(
            html=f'<div style="font-size:20px;text-align:center;line-height:1">{emoji}</div>',
            icon_size=(24, 24),
            icon_anchor=(12, 12),
        )

    def _add_base_parks_layer(self, map_object):
        """Add the always-on all-parks layer to the map."""
        base_layer = folium.FeatureGroup(name="🌲 All Parks", show=True)
        for park in self.summary.registry.all_parks():
            neighbourhood_data = self.summary.data.get(park.neighbourhood, {})
            neighbourhood_transit_count = neighbourhood_data.get("transit_count", 0)
            neighbourhood_total_hectares = neighbourhood_data.get("total_hectares", 0.0)
            popup_text = self._get_base_park_popup_text(
                park,
                neighbourhood_transit_count,
                neighbourhood_total_hectares,
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

        base_layer.add_to(map_object)

    def _add_category_facility_layers(self, map_object):
        """Add one toggleable layer per facility category (except transit)."""
        for layer_name, layer_config in self.MAP_LAYERS.items():
            if layer_name == "🚌 Transit Stops":
                continue

            emoji = self._get_layer_emoji(layer_name)
            category_label = self._get_layer_category_label(layer_name)
            facility_types = layer_config["types"]
            facility_layer = folium.FeatureGroup(name=layer_name, show=False)
            seen_park_ids = set()

            for facility_type in facility_types:
                for park in self.summary.registry.parks_with_facility(facility_type):
                    if park.park_id in seen_park_ids:
                        continue
                    seen_park_ids.add(park.park_id)

                    matching_facilities = [
                        facility for facility in park.facilities if facility in facility_types
                    ]
                    matching_facilities_text = ", ".join(matching_facilities)
                    popup_text = self._get_category_facility_popup_text(
                        emoji,
                        park,
                        category_label,
                        matching_facilities_text,
                    )
                    folium.Marker(
                        location=[park.lat, park.lon],
                        icon=self._get_category_emoji_icon(emoji),
                        popup=folium.Popup(popup_text, max_width=260),
                        tooltip=f"{emoji} {park.name}  |  {matching_facilities_text}",
                    ).add_to(facility_layer)

            facility_layer.add_to(map_object)

    def _add_transit_stops_layer(self, map_object):
        """Add transit stop points as a toggleable layer."""
        transit_layer = folium.FeatureGroup(name="🚌 Transit Stops", show=False)
        assigned_transit_stops = [
            stop
            for stops_list in self.summary.network.stops_by_neighbourhood.values()
            for stop in stops_list
        ]

        for transit_stop in assigned_transit_stops:
            folium.CircleMarker(
                location=[transit_stop.lat, transit_stop.lon],
                radius=3,
                color=self.COLORS["map_transit_stop"],
                fill=True,
                fill_color=self.COLORS["map_transit_stop"],
                fill_opacity=0.65,
                weight=0,
                tooltip=transit_stop.name,
            ).add_to(transit_layer)

        transit_layer.add_to(map_object)

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
        output_path = "map.html"

        map_object = folium.Map(
            location=self._get_map_center(),
            zoom_start=12,
            tiles="CartoDB positron",
            control_scale=True,
        )

        self._add_base_parks_layer(map_object)
        self._add_category_facility_layers(map_object)
        self._add_transit_stops_layer(map_object)

        folium.LayerControl(collapsed=False).add_to(map_object)

        map_object.save(output_path)
        print(f"  Saved {output_path}")
