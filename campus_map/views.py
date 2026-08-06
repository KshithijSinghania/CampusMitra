from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Location
from .services import find_location, build_route_map


@login_required
def map_view(request):
    fmap_html = None
    error = None

    if request.method == "POST":
        start_query = request.POST.get("start", "").strip()
        end_query = request.POST.get("end", "").strip()

        start_loc = find_location(start_query)
        end_loc = find_location(end_query)

        if not start_loc or not end_loc:
            error = "Couldn't match one or both locations. Try a different spelling."
        else:
            fmap = build_route_map(start_loc, end_loc)
            fmap_html = fmap._repr_html_()  # renders the Folium map as embeddable HTML

    locations = Location.objects.all()
    return render(request, "campus_map/map.html", {
        "locations": locations,
        "fmap_html": fmap_html,
        "error": error,
    })