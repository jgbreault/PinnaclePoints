"""
Generates the interactive pinnacle point map from
data/results/pinnacle_points/prm_iso/pinnacle_points.csv.

Each pinnacle point is drawn as a triangular marker coloured by elevation. Summits
that were misidentified by the algorithm (data/clean/faulty_pinnacle_points.csv) are
drawn hollow with a line to their true location. Clicking a marker opens a popup with
details and external links. Output: ../index.html (served at pinnacle-points.com/).
"""

import folium
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
import commons as me

pinnacle_points = pd.read_csv('../data/results/pinnacle_points/prm_iso/pinnacle_points.csv')
faulty_towers = pd.read_csv('../data/clean/faulty_pinnacle_points.csv')

# Elevation colormap shared by the pinnacle point and LOS mapper: sea level → Everest.
_colormap = LinearSegmentedColormap.from_list('custom_colormap', [
    (0.0,  'limegreen'),
    (0.25, 'yellow'),
    (0.5,  'orange'),
    (0.75, 'red'),
    (1.0,  'indigo'),
])
_max_elevation = pinnacle_points.elevation.max()

def get_pinnacle_point_color(elevation):
    '''Colours a pinnacle point marker based on its elevation'''
    rgba = _colormap(elevation / _max_elevation)
    return '#{:02x}{:02x}{:02x}'.format(int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))

def get_marker_text(summit):

    lat_rounded = f'{summit.latitude:.4f}'
    lng_rounded = f'{summit.longitude:.4f}'

    marker_text = (
        f'<b>Elevation:</b> {round(summit.elevation)} m<br>'
        f'<b>Location:</b> {lat_rounded}, {lng_rounded}<br>'
        f'<a href=https://www.peakbagger.com/search.aspx?tid=R&lat={lat_rounded}&lon={lng_rounded}&ss= target="_blank" rel="noopener noreferrer">PeakBagger</a> | '
        f'<a href=https://www.google.com/maps/place/{lat_rounded},{lng_rounded} target="_blank" rel="noopener noreferrer">Google Maps</a>'
    )

    return marker_text

def add_point_to_map(summit):
    '''Adds a summit to the pinnacle point map'''

    correction = faulty_towers.query('summit_id == @summit.summit_id')

    if len(correction) == 1:

        latitude_false = correction.latitude_false.values[0]
        longitude_false = correction.longitude_false.values[0]
        elevation_false = correction.elevation_false.values[0]
        latitude_true = correction.latitude_true.values[0]
        longitude_true = correction.longitude_true.values[0]
        elevation_true = correction.elevation_true.values[0]
        fault_type = correction.type.values[0]

        summit_color = get_pinnacle_point_color(elevation_true)

        def make_popup_text(lat, lng, elv, extra=''):
            lat_str = f'{lat:.4f}'
            lng_str = f'{lng:.4f}'
            text = (
                f'<b>Elevation:</b> {round(elv)} m<br>'
                f'<b>Location:</b> {lat_str}, {lng_str}<br>'
                f'<a href=https://www.peakbagger.com/search.aspx?tid=R&lat={lat_str}&lon={lng_str}&ss= target="_blank" rel="noopener noreferrer">PeakBagger</a> | '
                f'<a href=https://www.google.com/maps/place/{lat_str},{lng_str} target="_blank" rel="noopener noreferrer">Google Maps</a>'
            )
            if extra:
                text += f'<br><br>{extra}'
            return text

        if fault_type == 0:

            marker_false = folium.RegularPolygonMarker(
                location = [latitude_false, longitude_false],
                number_of_sides=3,
                radius = 11,
                fill = True,
                fill_color = summit_color,
                fill_opacity = 0,
                opacity = 1,
                weight = 1,
                color = summit_color,
                gradient = False,
                rotation = 30
            ).add_to(pinnacle_point_map)

            # For better usability on mobile
            invisible_circle_false = folium.CircleMarker(
                location = [latitude_false, longitude_false],
                radius = 12,
                fill = True,
                fill_opacity = 0,
                weight = 0
            ).add_to(pinnacle_point_map)

            invisible_circle_false.add_child(folium.Popup(
                make_popup_text(latitude_false, longitude_false, elevation_false, 'Misidentified by algorithm'),
                max_width=300).add_to(invisible_circle_false))

            # Adding a line to the true summit for misidentifications
            fault_to_true_line = [[latitude_false, longitude_false], [latitude_true, longitude_true]]
            folium.PolyLine(fault_to_true_line, color=summit_color, weight=1, opacity=1).add_to(pinnacle_point_map)

            marker_true = folium.RegularPolygonMarker(
                location = [latitude_true, longitude_true],
                number_of_sides=3,
                radius = 11,
                fill = True,
                fill_color = summit_color,
                fill_opacity = 1,
                weight = 1,
                color = 'black',
                gradient = False,
                rotation = 30
            ).add_to(pinnacle_point_map)

            # For better usability on mobile
            invisible_circle_true = folium.CircleMarker(
                location = [latitude_true, longitude_true],
                radius = 12,
                fill = True,
                fill_opacity = 0,
                weight = 0
            ).add_to(pinnacle_point_map)

            invisible_circle_true.add_child(folium.Popup(
                make_popup_text(latitude_true, longitude_true, elevation_true),
                max_width=300).add_to(invisible_circle_true))

    else:

        marker = folium.RegularPolygonMarker(
            location = [summit.latitude, summit.longitude],
            number_of_sides=3,
            radius = 11,
            fill = True,
            fill_color = get_pinnacle_point_color(summit.elevation),
            fill_opacity = 1,
            weight = 1,
            color = 'black',
            gradient = False,
            rotation = 30
        ).add_to(pinnacle_point_map)

        # For better usability on mobile
        invisible_circle = folium.CircleMarker(
            location = [summit.latitude, summit.longitude],
            radius = 12,
            fill = True,
            fill_opacity = 0,
            weight = 0
        ).add_to(pinnacle_point_map)
        invisible_circle.add_child(folium.Popup(get_marker_text(summit), max_width=300).add_to(invisible_circle))

summits = pinnacle_points.sort_values('elevation', ascending=True)
pinnacle_point_map = folium.Map(location=[0, 15], zoom_start=3, tiles=None, world_copy_jump=True)

folium.TileLayer(name = 'Street').add_to(pinnacle_point_map)

folium.TileLayer(
          'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
          attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          name = 'Elevation',
          maxZoom = 16
          ).add_to(pinnacle_point_map)

folium.raster_layers.TileLayer(name = 'Satellite',
                               maxZoom = 17,
                               tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                               attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                              ).add_to(pinnacle_point_map)

folium.LayerControl().add_to(pinnacle_point_map)

summits.apply(add_point_to_map, axis=1)

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
                <h4 style="margin: 0; margin-right: 30px;"><b>Pinnacle Points</b></h4>
            </div>
            <div id="legendContent" style="display: block; margin-top: 5px;">
                <center style="margin-top: 15px; margin-bottom: 15px;">
                    Points from which no higher<br>elevation can be seen
                </center>

                <div style="
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  margin: 5px auto;
                ">
                      <div style="display: flex; justify-content: space-between; width: 90%; font-size: 12px; margin-bottom: 2px;">
                        <span><b>Elevation</b></span>
                      </div>

                      <div style="
                        height: 18px;
                        border-radius: 2px;
                        background: linear-gradient(to right, limegreen, yellow, orange, red, indigo);
                        box-shadow: 0 0 3px rgba(0,0,0,0.3);
                        width: 90%;
                      "></div>

                      <div style="display: flex; justify-content: space-between; width: 90%; font-size: 12px;">
                        <span>Sea Level</span>
                        <span>Mt. Everest</span>
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

pinnacle_point_map.get_root().html.add_child(folium.Element(legend_html))

pinnacle_point_map.get_root().html.add_child(folium.Element('''
    <div id="sunButton" style="position: absolute; bottom: 104px; right: 4px; cursor: pointer; z-index: 1001;">
        <a href="/longest-lines-of-sight" title="Longest Lines of Sight">
            <svg id="sunIcon" width="50" height="50" viewBox="0 0 50 50">
                <title>Longest Lines of Sight</title>
                <defs>
                    <clipPath id="sunIconClip"><circle cx="24" cy="24" r="20"></circle></clipPath>
                </defs>
                <circle cx="24" cy="24" r="20" fill="rgba(255, 255, 255, 0.9)"></circle>
                <g clip-path="url(#sunIconClip)" stroke="black" stroke-width="1.5" stroke-linejoin="round">
                    <path d="M 24,26.6 L 18,16.2 A 7 7 0 0 1 30,16.2 Z" fill="gold"></path>
                    <polygon points="18,16.2 9,31.8 27,31.8" fill="grey"></polygon>
                    <polygon points="30,16.2 21,31.8 39,31.8" fill="grey"></polygon>
                    <polygon points="18,16.2 13.95,23.22 22.05,23.22" fill="white"></polygon>
                    <polygon points="30,16.2 25.95,23.22 34.05,23.22" fill="white"></polygon>
                </g>
                <circle cx="24" cy="24" r="20" fill="none" stroke="black" stroke-width="4"></circle>
            </svg>
        </a>
    </div>
'''))

pinnacle_point_map.get_root().html.add_child(folium.Element('''
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
            Pinnacle points are points from which no higher elevation can be seen. Two
            points have line of sight if light can travel from one to the other unobstructed
            with sufficient contrast for visibility under clear atmospheric conditions. Many
            physical phenomena are modelled including Earth's curvature, local topography,
            atmospheric refraction, atmospheric scattering, and partial irradiation. It is
            possible for two pinnacle points with equal elevation to have line of sight since
            neither would be high enough to disqualify the other. This map shows all 1554
            pinnacle points on Earth with at least 300 m of prominence or 100 km of isolation.
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
                <a target="_blank" rel="noopener noreferrer" href="https://github.com/jgbreault/PinnaclePoints/blob/main/data/results/pinnacle_points/prm_iso/pinnacle_points.csv">
                    CSV of all pinnacle points
                </a>
            </li>
        </ul>

        <h2>Data Sources</h2>
        <h4><a target="_blank" rel="noopener noreferrer" href="https://ototwmountains.com/">1. On-Top-Of-The-World Mountains</a></h4>
        <p>
            On-top-of-the-world (OTOTW) mountains are mountains where no land rises above its horizontal plane.
            Since any land that rises above the horizontal plane would have a higher elevation than the mountain itself,
            if a mountain is not an OTOTW mountain then it can not be a pinnacle point either.
            In other words, pinnacle points are a subset of OTOTW mountains.
            Kai Xu found all 6,464 OTOTW mountains on Earth with over 300 m of prominence.
        </p>
        <h4><a target="_blank" rel="noopener noreferrer" href="https://www.andrewkirmse.com/prominence-update-2023">2. Mountains by Prominence</a></h4>
        <p>
            Andrew Kirmse and Jonathan de Ferranti found all 11,866,713 summits on Earth with over 100 ft (~30 m) of prominence.
            Prominence is the minimum vertical distance one must descend to reach a higher point.
            OTOTW mountains were identified using this dataset,
            so this dataset is used to help determine which OTOTW mountains qualify as pinnacle points.
        </p>
        <h4><a target="_blank" rel="noopener noreferrer" href="https://www.andrewkirmse.com/true-isolation">3. Mountains by Isolation</a></h4>
        <p>
            Andrew Kirmse and Jonathan de Ferranti found all 24,749,518 summits on Earth with over 1 km of isolation.
            Isolation is the distance to the nearest higher point. Extreme isolation points are strong pinnacle point candidates,
            so this dataset is used to find all pinnacle points with an isolation of at least 100 km.
        </p>
        <h4><a target="_blank" rel="noopener noreferrer" href="https://open-meteo.com/en/docs/elevation-api">4. Open-Meteo's Elevation API</a></h4>
        <p>
            Open-Meteo offers an elevation API that can be used to find the elevation of any point on Earth.
            This API is used to find the elevation of points between summits that could obstruct line of sight.
        </p>
        <h4><a target="_blank" rel="noopener noreferrer" href="https://beyondrange.wordpress.com/lines-of-sight/">5. Beyond Horizons</a></h4>
        <p>
            Beyond Horizons has catalogued many of the longest lines of sight to ever be captured by photograph.
            These confirmed lines of sight are used to calibrate the way light bending is modelled from atmospheric refraction.
        </p>
    </div>
'''))

pinnacle_point_map.save('../index.html')
print('Saved ../index.html')
