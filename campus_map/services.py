from thefuzz import process
import folium
from .models import Location


def find_location(query):
    """Fuzzy-matches a free-text query against known location names.
    Returns the best-matching Location object, or None if nothing scores well enough."""
    locations = list(Location.objects.all())
    if not locations:
        return None

    names = [loc.name for loc in locations]
    best_match, score = process.extractOne(query, names)

    if score < 60:  # below this, the match is probably unrelated — don't guess wildly
        return None

    return next(loc for loc in locations if loc.name == best_match)


def build_route_map(start, end):
    """Builds a Folium map showing both points and a straight line between them.
    start/end are Location objects."""
    midpoint_lat = (start.latitude + end.latitude) / 2
    midpoint_lng = (start.longitude + end.longitude) / 2

    fmap = folium.Map(location=[midpoint_lat, midpoint_lng], zoom_start=17)

    folium.Marker(
        [start.latitude, start.longitude],
        popup=start.name,
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(fmap)

    folium.Marker(
        [end.latitude, end.longitude],
        popup=end.name,
        icon=folium.Icon(color="red", icon="flag"),
    ).add_to(fmap)

    folium.PolyLine(
        locations=[[start.latitude, start.longitude], [end.latitude, end.longitude]],
        color="blue",
        weight=4,
    ).add_to(fmap)

    return fmap