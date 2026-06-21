"""
Generates an interactive map of the longest lines of sight on Earth -- the longest
for each summit -- from data/results/longest_los/longest_los_max.csv.

Each line of sight is drawn as a great-circle line (a straight line in reality, so
gently curved on the map) between the observer and target summits. Both summits are
small black triangles with a bold coloured border, and the line shares that colour.
Colour encodes the distance of the line of sight, using the same colormap as the
pinnacle point map. Clicking the line, the observer, or the target opens a popup
with details. Output: ../longest-lines-of-sight.html (served at
pinnacle-points.com/longest-lines-of-sight).

Run line_of_sight_finder.py first to produce the results. (Lines that cross the
+/-180 deg meridian are drawn as-is and may wrap across the map -- rare at these
distances.)
"""

import folium
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
import commons as me
import math

los_data = pd.read_csv('../data/results/longest_los/longest_los_max.csv')
los_data = los_data.sort_values('distance', ascending=True)  # draw longest on top

# Same colormap as the pinnacle point map, here mapped over line-of-sight distance.
colors = [
    (0.0, 'limegreen'),
    (0.25, 'yellow'),
    (0.5, 'orange'),
    (0.75, 'red'),
    (1.0, 'indigo')
]
colormap = LinearSegmentedColormap.from_list('custom_colormap', colors)
min_distance = los_data.distance.min()
max_distance = los_data.distance.max()

def get_distance_color(distance):
    '''Colours a line of sight based on its distance'''
    
    span = max_distance - min_distance
    fraction = (distance - min_distance)/span if span else 0.5
    rgba_color = colormap(fraction)
    return "#{:02x}{:02x}{:02x}".format(
        int(rgba_color[0] * 255), # Red
        int(rgba_color[1] * 255), # Green
        int(rgba_color[2] * 255)  # Blue
    )

def get_summit_links(latitude, longitude):
    '''PeakBagger and Google Maps links for a summit'''
    
    lat_rounded = round(latitude, 4)
    lng_rounded = round(longitude, 4)
    return (
        f'<a href=https://www.peakbagger.com/search.aspx?tid=R&lat={lat_rounded}&lon={lng_rounded}&ss= target="_blank" rel="noopener noreferrer">PeakBagger</a> | '
        f'<a href=https://www.google.com/maps/place/{lat_rounded},{lng_rounded} target="_blank" rel="noopener noreferrer">Google Maps</a>'
    )

def get_geodesic_line(latitude_1, longitude_1, latitude_2, longitude_2, num_points=25):
    '''Great-circle path between two points, as [lat, lng] pairs for a folium PolyLine'''
    
    intermediate = me.geod.npts(longitude_1, latitude_1, longitude_2, latitude_2, num_points)
    return [[latitude_1, longitude_1]] + [[lat, lng] for lng, lat in intermediate] + [[latitude_2, longitude_2]]

line_of_sight_map = folium.Map(location=[0, 0], zoom_start=3, tiles=None, world_copy_jump=True)

folium.TileLayer(name = 'Street').add_to(line_of_sight_map)

folium.TileLayer(
          'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
          attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          name = 'Elevation',
          maxZoom = 16
          ).add_to(line_of_sight_map)

folium.raster_layers.TileLayer(name = 'Satellite',
                               maxZoom = 17,
                               tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                               attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                              ).add_to(line_of_sight_map)

folium.LayerControl().add_to(line_of_sight_map)

def add_summit_to_map(latitude, longitude, color, popup_text):
    '''
    Adds a summit (observer or target) to the map: a black triangle with a coloured
    border, plus an invisible circle for easier clicking on mobile
    '''

    folium.RegularPolygonMarker(
        location = [latitude, longitude],
        number_of_sides = 3,
        radius = 9,
        fill = True,
        fill_color = 'black',
        fill_opacity = 1,
        color = color,
        weight = 3,
        gradient = False,
        rotation = 30
    ).add_to(line_of_sight_map)

    invisible_circle = folium.CircleMarker(
        location = [latitude, longitude],
        radius = 12,
        fill = True,
        fill_opacity = 0,
        weight = 0
    ).add_to(line_of_sight_map)
    invisible_circle.add_child(folium.Popup(popup_text, max_width=300))

def add_line_of_sight_to_map(los):
    '''Draws a single line of sight: the connecting line and both summit markers'''

    color = get_distance_color(los.distance)
    distance_km = round(los.distance/1000, 1)
    contrast = round(los.contrast, 3)

    observer_elevation = round(los.observer_elevation)
    target_elevation = round(los.target_elevation)
    observer_location = f'{round(los.observer_latitude, 4)}, {round(los.observer_longitude, 4)}'
    target_location = f'{round(los.target_latitude, 4)}, {round(los.target_longitude, 4)}'

    line_coords = get_geodesic_line(los.observer_latitude, los.observer_longitude,
                                    los.target_latitude, los.target_longitude)

    line_text = (
        f'<b>Distance:</b> {distance_km} km<br>'
        f'<b>From:</b> {observer_location} ({observer_elevation} m)<br>'
        f'<b>To:</b> {target_location} ({target_elevation} m)'
    )

    # visible line, then an invisible wider line on top to make the line easy to click
    folium.PolyLine(line_coords, color=color, weight=4, opacity=0.85).add_to(line_of_sight_map)
    folium.PolyLine(line_coords, color=color, weight=12, opacity=0,
                    popup=folium.Popup(line_text, max_width=300)).add_to(line_of_sight_map)

    # Observer and target popups match the pinnacle point map's summit markers exactly.
    observer_text = (
        f'<b>Elevation:</b> {observer_elevation} m<br>'
        f'<b>Location:</b> {observer_location}<br>'
        + get_summit_links(los.observer_latitude, los.observer_longitude)
    )
    target_text = (
        f'<b>Elevation:</b> {target_elevation} m<br>'
        f'<b>Location:</b> {target_location}<br>'
        + get_summit_links(los.target_latitude, los.target_longitude)
    )

    add_summit_to_map(los.observer_latitude, los.observer_longitude, color, observer_text)
    add_summit_to_map(los.target_latitude, los.target_longitude, color, target_text)

for los in los_data.itertuples():
    add_line_of_sight_to_map(los)

legend_html = """
    <div style="
        background-color: rgba(255, 255, 255, 0.9);
        padding: 5px;
        font-size: 12px;
        position: absolute;
        top: 12px;
        right: 70px;
        z-index: 1000;
    ">
        <div style="cursor: pointer;" onclick="toggleLegend()">
            <div style="display: flex; align-items: center;" title="Legend">
                <div id="chevronIcon" style="margin-left: 11px; margin-right: 15px; width: 10px; height: 10px;
                    border-style: solid; border-width: 0 3px 3px 0; transform: rotate(225deg);"></div>
                <h4 style="margin: 0; margin-right: 30px;"><b>Longest<br>Lines of Sight</b></h4>
            </div>
            <div id="legendContent" style="display: block; margin-top: 20px;">

                <div style="
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  margin: 5px auto;
                ">
                      <div style="display: flex; justify-content: space-between; width: 90%; font-size: 12px; margin-bottom: 2px;">
                        <span><b>Distance</b></span>
                      </div>

                      <div style="
                        height: 18px;
                        border-radius: 2px;
                        background: linear-gradient(to right, limegreen, yellow, orange, red, indigo);
                        box-shadow: 0 0 3px rgba(0,0,0,0.3);
                        width: 90%;
                      "></div>

                      <div style="display: flex; justify-content: space-between; width: 90%; font-size: 12px;">
                        <span>MIN_DISTANCE_LABEL</span>
                        <span>MAX_DISTANCE_LABEL</span>
                      </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function toggleInfoWindow() {
            var infoWindow = document.getElementById("infoWindow");
            var infoIcon = document.getElementById("informationIcon");

            if (infoWindow.style.display === "block") {
                infoWindow.style.display = "none";
                infoIcon.style.fill = "rgba(255, 255, 255, 0.9)";
            } else {
                infoWindow.style.display = "block";
                infoIcon.style.fill = "rgba(255, 255, 0, 0.9)";
            }
        }

        // Close the info window when clicking anywhere outside it (or its icon).
        // Capture phase so it still fires over map markers that stop propagation.
        document.addEventListener("click", function(event) {
            var infoWindow = document.getElementById("infoWindow");
            if (!infoWindow || infoWindow.style.display !== "block") return;
            if (event.target.closest("#infoWindow") || event.target.closest("#infoIcon")) return;
            infoWindow.style.display = "none";
            var infoIcon = document.getElementById("informationIcon");
            if (infoIcon) infoIcon.style.fill = "rgba(255, 255, 255, 0.9)";
        }, true);
    </script>

    <script>
        function toggleLegend() {
            var contentDiv = document.getElementById("legendContent");
            var chevronIcon = document.getElementById("chevronIcon");

            if (contentDiv.style.display === "block") {
                contentDiv.style.display = "none";
                chevronIcon.style.transform = "rotate(45deg)";
            } else {
                contentDiv.style.display = "block";
                chevronIcon.style.transform = "rotate(225deg)";
            }
        }
    </script>
"""

legend_html = (legend_html
               .replace('MIN_DISTANCE_LABEL', f'{math.floor(min_distance/1000)} km')
               .replace('MAX_DISTANCE_LABEL', f'{math.ceil(max_distance/1000)} km'))

line_of_sight_map.get_root().html.add_child(folium.Element(legend_html))

line_of_sight_map.get_root().html.add_child(folium.Element('''
  <div id="losButton" style="position: absolute; bottom: 104px; right: 4px; cursor: pointer; z-index: 1001;">
      <a href="/" title="Pinnacle Points">
          <svg id="losIcon" width="50" height="50" viewBox="0 0 50 50">
              <title>Pinnacle Points</title>
              <defs>
                  <clipPath id="losIconClip"><circle cx="24" cy="24" r="20"></circle></clipPath>
              </defs>
              <circle cx="24" cy="24" r="20" fill="rgba(255, 255, 255, 0.9)"></circle>
              <g clip-path="url(#losIconClip)" stroke="black" stroke-width="1.5" stroke-linejoin="round">
                  <polygon points="19,10.4 10,26 28,26" fill="limegreen"></polygon>
                  <polygon points="29,10.4 20,26 38,26" fill="yellow"></polygon>
                  <polygon points="19,18.4 10,34 28,34" fill="orange"></polygon>
                  <polygon points="29,18.4 20,34 38,34" fill="red"></polygon>
              </g>
              <circle cx="24" cy="24" r="20" fill="none" stroke="black" stroke-width="4"></circle>
          </svg>
      </a>
  </div>
'''))

line_of_sight_map.get_root().html.add_child(folium.Element('''
    <div id="infoIcon" style="position: absolute; bottom: 10px; right: 0px; cursor: pointer; z-index: 1001;">
        <svg id="informationIcon" width="100" height="100" viewBox="0 0 50 50" fill="white" stroke="black" stroke-width="4"
            stroke-linecap="round" stroke-linejoin="round" onclick="toggleInfoWindow()" style="fill: rgba(255, 255, 255, 0.9)">
            <title>Info</title>
            <circle cx="24" cy="24" r="20"></circle>
            <line x1="24" y1="32" x2="24" y2="24"></line>
            <line x1="24" y1="16" x2="24" y2="16"></line>
        </svg>
    </div>
    <div id="infoWindow" style="display: none; overflow-y: auto; position: absolute; top: 50%; left: 50%;
        transform: translate(-50%, -50%); background-color: rgba(255, 255, 255, 0.9); padding: 30px; width: 95%;
        height: 50%;  z-index: 1000;">

        <h2>Summary</h2>
        <p>
            Two points have line of sight if light can travel from one to the other unobstructed
            with sufficent contrast for visibilty under clear atmospheric conditions.
            Many physical phenomenon are modelled including Earth's curvature, local topograpghy,
            atmospheric refraction, atmospheric scattering, and partial irradiation.
            This map shows all 111 ground-based lines of sight over 400 km long that are the longest for both the observer and target. 
            Lines of sight are only consdered if both the observer and target have over 500 m of prominence.
        </p>

        <h2>Links</h2>
        <ul>
            <li>
                <a target="_blank" rel="noopener noreferrer" href="https://raw.githubusercontent.com/jgbreault/PinnaclePoints/refs/heads/main/misc/method.txt">
                    Method
                </a>
            </li>
            <li>
                <a target="_blank" rel="noopener noreferrer" href="https://github.com/jgbreault/PinnaclePoints">
                    Github
                </a>
            </li>
            <li>
                <a target="_blank" rel="noopener noreferrer" href="https://github.com/jgbreault/PinnaclePoints/blob/main/data/results/longest_los/longest_los_max.csv">
                    CSV of lines of sight shown on map
                </a>
            </li>
            <li>
                <a target="_blank" rel="noopener noreferrer" href="https://github.com/jgbreault/PinnaclePoints/blob/main/data/results/longest_los/longest_los.csv">
                    CSV of all discovered lines of sight
                </a>
            </li>
        </ul>

        <h2>Data Sources</h2>
        <h4><a target="_blank" rel="noopener noreferrer" href="https://www.andrewkirmse.com/prominence-update-2023">1. Mountains by Prominence</a></h4>
        <p>
            Andrew Kirmse and Jonathan de Ferranti found all 11,866,713 summits on Earth with over 100 ft (~30 m) of prominence.
            Prominence is the minimum vertical distance one must descend to reach a higher point. 
            This dataset is used to identify summits beyond the prominence threshold of 500 m.
        </p>
        <h4><a target="_blank" rel="noopener noreferrer" href="https://open-meteo.com/en/docs/elevation-api">2. Open-Meteo's Elevation API</a></h4>
        <p>
            Open-Meteo offers an elevation API that can be used to find the elevation of any point on Earth.
            This API is used to find the elevation of points between summits that could obstruct line of sight.
        </p>
        <h4><a target="_blank" rel="noopener noreferrer" href="https://beyondrange.wordpress.com/lines-of-sight/">3. Beyond Horizons</a></h4>
        <p>
            Beyond Horizons has catalogued many of the longest lines of sight to ever be captured by photograph.
            These confirmed lines of sight are used to calibrate the way light bending is modelled from atmospheric refraction.
        </p>
    </div>
'''))

line_of_sight_map.save('../longest-lines-of-sight.html')
print('Saved ../longest-lines-of-sight.html')
