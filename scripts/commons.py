"""
Shared constants, functions, and classes for the pinnacle point pipeline.

A pinnacle point is a point from which no higher point can be seen. The classes
below model the physics used to decide that: Earth's curvature, atmospheric
refraction (light bending), and atmospheric scattering (contrast). See
../misc/method.txt for the full method and ../misc/math/ for the derivations.

The shade irradiation ratio (atmospheric scattering) is set per line of sight
from its bearing. The other scripts import this module as `me` (e.g.
`import commons as me`).
"""

import math
import pandas as pd
from textwrap import dedent
from pyproj import Geod
import numpy as np
import requests
import matplotlib.pyplot as plt
from scipy.integrate import quad


########## VARIABLES ##########

# Switch the three paths below as a group to run the prominence dataset (prm),
# the isolation dataset (iso), or the merged final result (prm_iso).

default_light_curvature = 6.4
default_sea_level_scatter_coefficient = 0.00001139 # Wavelength averaged scattering coefficient in 1/m, Penndorf 1957
default_shaded_ratio = 0.5
default_shade_irradiation_ratio = 0.5
min_shade_irradiation_ratio = 0.1 # darkest the observer-side shadow gets (east-west sightlines), floored by diffuse skylight
default_max_sampling_distance = 100 # in m
ignore_buffer = 4000 # in m

summit_file = '../data/clean/summits_prm.csv'
pinnacle_point_file = '../data/results/pinnacle_points/prm/pinnacle_points.csv'
patch_directory = f'../data/patches/prm_{default_light_curvature}'

# summit_file = '../data/clean/summits_iso.csv'
# pinnacle_point_file = '../data/results/pinnacle_points/iso/pinnacle_points.csv'
# patch_directory = f'../data/patches/iso_{default_light_curvature}'

# summit_file = '../data/results/pinnacle_points/prm_iso/pinnacle_points_merged.csv'
# pinnacle_point_file = '../data/results/pinnacle_points/prm_iso/pinnacle_points.csv'
# patch_directory = f'../data/patches/prm_iso_{default_light_curvature}'

earth_radius = 6371146 # in m (Mean Sea Level, GPS, and the Geoid. Witold Fraczek 2003)
atmosphere_scale_height = 8500 # in m (https://web.archive.org/web/20250821225050/https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html)

geod = Geod(ellps='sphere')

api_request_url = 'http://127.0.0.1:8080/v1/elevation'
api_request_limit = 100
session = requests.Session()

# patch_size (in degrees) must divide 90 so the latitude bands and the pole caps
# tile cleanly (each pole cap spans the outermost patch_size degrees of latitude).
# Smaller patches give less overlap between neighbouring patches but produce more
# patch files. The outer-bound offset can exceed one patch near the tallest
# mountains, but those are far from the poles, and any latitude beyond +/-90 is
# clamped, so patches never cross the poles.
patch_size = 10
assert 90 % patch_size == 0, 'patch_size must divide 90'


########## FUNCTIONS ##########

def get_pole_latitude():
    return 90 - patch_size

def get_patch_lat_boundaries():
    pole_lat = get_pole_latitude()
    return np.arange(-pole_lat, pole_lat+patch_size, patch_size)
    
def get_patch_lng_boundaries():
    return np.arange(-180, 180+patch_size, patch_size)

def horizon_distance(height, light_curvature=default_light_curvature):
    """Maximum horizon distance (MHD): how far a point of the given height could
    see if all other land were at sea level. Returns 0 for non-positive heights."""
    if height > 0:
        return math.sqrt(2*(light_curvature/(light_curvature-1))*earth_radius*height)
    return 0

def get_elevations(latitudes, longitudes):
    """Look up ground elevations for the given coordinates via the locally hosted
    Open-Meteo elevation API, in chunks of api_request_limit."""

    elevations = []
    for i in range(0, len(latitudes), api_request_limit):
        chunk_latitudes = latitudes[i : i+api_request_limit]
        chunk_longitudes = longitudes[i : i+api_request_limit]
    
        params = {'latitude': ','.join(map(str, chunk_latitudes)),
                  'longitude': ','.join(map(str, chunk_longitudes))}

        response = session.get(api_request_url, params=params)
    
        if response.status_code == 200:
            data = response.json()
            elevations.extend(data['elevation'])
        else:
            print('Error:', response.status_code, response.text)

    return elevations


def light_elevation_at_fraction(observer_elevation,
                                target_elevation,
                                surface_distance,
                                fraction,
                                light_curvature=default_light_curvature):
    """Elevation above sea level of the (refracted) light ray a `fraction` of the
    way along each line of sight (0 = observer, 1 = target), per candidate.

    Vectorised, array-in/array-out form of LineOfSight.get_light_elevation, used to
    screen many candidate lines of sight at one sample point at once (see
    line_of_sight_finder.py). See ../misc/math/formatted/atmospheric_refraction.pdf."""
    R = earth_radius
    k = light_curvature
    h1 = observer_elevation
    h2 = target_elevation
    D = surface_distance

    x = fraction * D
    theta = x / R
    phi = D / R

    x1 = R + h1
    x2 = (R + h2) * np.cos(phi)
    y2 = (R + h2) * np.sin(phi)          # y1 = 0, so y2 - y1 = y2

    d = np.sqrt((x2 - x1)**2 + y2**2)    # chord between observer and target in the cross-section
    RL = k * R
    Z = np.sqrt(RL**2 - (d / 2)**2)

    Mx = (x1 + x2) / 2 - Z * (y2 / d)    # centre of the light-arc circle
    My = y2 / 2 + Z * ((x2 - x1) / d)

    proj = Mx * np.cos(theta) + My * np.sin(theta)
    light_distance_from_centre = proj + np.sqrt(proj**2 - (Mx**2 + My**2 - RL**2))

    return light_distance_from_centre - R


def points_at_fraction(observer_latitude,
                       observer_longitude,
                       forward_azimuth,
                       surface_distance,
                       fraction):
    """Latitude/longitude of the point a `fraction` of the way along each geodesic,
    following the observer-to-target great circle. Vectorised."""
    x = fraction * surface_distance
    longitudes, latitudes, _ = geod.fwd(observer_longitude, observer_latitude, forward_azimuth, x)
    return latitudes, longitudes


def screening_fractions():
    """Produce (numerator, denominator) sample points in screening order:

        1/2, then 1/4 3/4, then 3/8 5/8 1/8 7/8, then sixteenths, ...

    i.e. the middle first, then each successive halving level, and within a level
    the points nearest the middle (inner) before the points nearest the ends
    (outer), alternating to the left then the right of the middle. The numerators
    are the odd multiples of 1/2^k that are new at each level, so no point repeats.

    `yield` makes this a generator: each value is produced on demand (just loop over
    it), and the function pauses after each `yield` and resumes there on the next
    request. The `while True` is an endless sequence, so the caller must stop itself
    (the screen breaks once it converges); never wrap it in list()."""
    
    yield (1, 2)
    k = 2
    while True:
        denominator = 2**k
        middle = 2**(k - 1)
        for offset in range(1, middle, 2):          # odd offsets keep the numerator odd
            yield (middle - offset, denominator)     # inner/outer, left of middle
            yield (middle + offset, denominator)     # its mirror, right of middle
        k += 1


########## CLASSES ##########

class Point:
    """A location on Earth: latitude, longitude, and elevation. If elevation is
    not given, it is looked up from the Open-Meteo elevation API."""

    def __init__(self,
                 latitude,
                 longitude,
                 elevation=None):
        self.latitude = latitude
        self.longitude = longitude
        if elevation is None:
            elevation = get_elevations([latitude], [longitude])[0]
        self.elevation = elevation

class Summit(Point):
    """A mountain summit. Pinnacle point candidates are summits; the heavy
    lifting (is_pinnacle_point) lives here."""

    def __init__(self,
                 latitude,
                 longitude,
                 elevation=None,
                 summit_id=None,
                 prominence=None,
                 isolation=None):
        
        super().__init__(latitude,
                         longitude,
                         elevation)

        self.summit_id = summit_id
        self.prominence = prominence
        self.isolation = isolation

    def get_max_horizon_distance(self):
        return horizon_distance(self.elevation)

    def get_patch(self):
        """Return the Patch this summit falls in (a pole cap, or the 10x10 degree
        square it lands in)."""
        pole_latitude = get_pole_latitude()

        if self.latitude >= pole_latitude:
            return Patch(90, pole_latitude)

        elif self.latitude < -pole_latitude:
            return Patch(-pole_latitude, -90)

        else:
            # Round down to nearest multiple of patch_size
            lat_min = int((self.latitude // patch_size) * patch_size)
            lng_min = int((self.longitude // patch_size) * patch_size)
    
            return Patch(lat_min+patch_size, lat_min, lng_min+patch_size, lng_min)

    def is_pinnacle_point(self):
        """Return True if no higher summit has a valid line of sight with this one.

        Only summits in this summit's patch that are higher and within combined
        MHD range can disqualify it. They are tested nearest-first (nearer summits
        are likelier to be visible); the first valid line of sight disqualifies
        the candidate."""

        # Candidates are pinnacle points until proven guilty
        is_pinnacle_point = True
        
        patch_summits = self.get_patch().summits_outer
        distances_from_candidate = geod.inv(np.full(len(patch_summits), self.longitude),
                                          np.full(len(patch_summits), self.latitude),
                                          patch_summits.longitude.values,
                                          patch_summits.latitude.values)[2]
        patch_summits['distance_from_candidate'] = np.round(distances_from_candidate)
        patch_summits_in_mhd_range = patch_summits.query('(summit_id != @self.summit_id) & '
                                                    '(elevation > @self.elevation) & '
                                                    '(distance_from_candidate < max_horizon_distance + @self.get_max_horizon_distance())')
    
        print(f'Potential Disqualifying Summits: {len(patch_summits_in_mhd_range)}')
        
        patch_summits_in_mhd_range = patch_summits_in_mhd_range.sort_values('distance_from_candidate')
    
        for j, summit in enumerate(patch_summits_in_mhd_range.itertuples()):
    
            target = Summit(latitude = summit.latitude,
                            longitude = summit.longitude,
                            elevation = summit.elevation)

            candidate_line_of_sight = LineOfSight(self, target)

            # Early-exit check: abandons an obstructed line of sight as soon as a
            # batch of sampled elevations blocks it, and only tests contrast when
            # nothing does. Same result as process_full_line_of_sight + is_valid.
            if candidate_line_of_sight.is_valid_early():

                print(f'Tested Potential Disqualifying Summits: {j+1}')
                print(f'In view of {summit.latitude}, {summit.longitude} ({round(summit.elevation)} m) {round(summit.distance_from_candidate/1000)} km away')
                
                is_pinnacle_point = False
                break

        print(f'Pinnacle Point: {is_pinnacle_point}')

        return is_pinnacle_point

class LosPoint(Point):
    """One sampled point along a line of sight, carrying both its distance along
    the straight observer-target line and the heights of the ground and the light
    ray there (in the rotated frame; see LineOfSight.process_full_line_of_sight)."""

    def __init__(self,
                 latitude,
                 longitude,
                 elevation,
                 surface_distance,
                 straight_distance,
                 light_height = None,
                 ground_height = None):
        
        super().__init__(latitude,
                         longitude,
                         elevation)
        
        self.surface_distance = surface_distance
        self.straight_distance = straight_distance
        self.light_height = light_height
        self.ground_height = ground_height

class LineOfSight():
    """A candidate line of sight between an observer and a target summit.

    A line of sight is valid (is_valid) when it is both geometrically unobstructed
    (is_obstructed is False, accounting for Earth's curvature and refraction) and
    bright enough to see (has_contrast, accounting for atmospheric scattering).
    """

    def __init__(self,
                 observer,
                 target,
                 light_curvature = default_light_curvature,
                 sea_level_scatter_coefficient = default_sea_level_scatter_coefficient,
                 max_sampling_distance = default_max_sampling_distance,
                 shaded_ratio = default_shaded_ratio, 
                 shade_irradiation_ratio = None):
        
        self.observer = observer
        self.target = target
        self.light_curvature = light_curvature
        self.sea_level_scatter_coefficient = sea_level_scatter_coefficient
        self.max_sampling_distance = max_sampling_distance
        forward_azimuth, _, self.surface_distance = geod.inv(self.observer.longitude, self.observer.latitude,
                                                             self.target.longitude, self.target.latitude)
        self.forward_azimuth = forward_azimuth
        self.shaded_ratio = shaded_ratio
        # The shaded segment is the observer-side half of the path, where suppressing
        # airlight helps contrast most. How shadowed it can get depends on bearing: an
        # east-west sightline can sit in the sunrise/sunset shadow (irradiation ->
        # min_shade_irradiation_ratio), a north-south one cannot (the sun is broadside,
        # so irradiation -> 1 and there is no contrast benefit).
        if shade_irradiation_ratio is None:
            shade_irradiation_ratio = 1 - (1 - min_shade_irradiation_ratio)*abs(math.sin(math.radians(forward_azimuth)))
        self.shade_irradiation_ratio = shade_irradiation_ratio
        self.num_samples = math.ceil(self.surface_distance/max_sampling_distance)
        self.los_points = []

    def process_full_line_of_sight(self):
        """Sample the ground between observer and target, place every sample into
        the rotated vertical cross-section, and store the resulting LosPoints with
        ground and light heights ready for is_obstructed."""

        lng_lats = geod.npts(self.observer.longitude, self.observer.latitude,
                            self.target.longitude, self.target.latitude, 
                            self.num_samples)

        latitudes = np.array(lng_lats)[:, 1]
        longitudes = np.array(lng_lats)[:, 0]

        elevations = get_elevations(latitudes, longitudes)
    
        latitudes = np.concatenate([[self.observer.latitude], latitudes, [self.target.latitude]])
        longitudes = np.concatenate([[self.observer.longitude], longitudes, [self.target.longitude]])
        elevations = np.concatenate([[self.observer.elevation], elevations, [self.target.elevation]])

        surface_distances = []
        for i, latitude in enumerate(latitudes):
            longitude = longitudes[i]
            surface_distances.append(geod.line_length([self.observer.longitude, longitude], [self.observer.latitude, latitude]))

        angles_between_observer_and_los_points = np.array(surface_distances)/earth_radius
        x_distances = (earth_radius + elevations)*np.sin(angles_between_observer_and_los_points)
        drop_from_curvature = earth_radius * (1 - np.cos(angles_between_observer_and_los_points))
        y_heights = elevations*np.cos(angles_between_observer_and_los_points) - drop_from_curvature - elevations[0]

        angle_below_horizontal = -np.arctan(y_heights[-1]/x_distances[-1])

        rotation_matrix = np.array([[math.cos(angle_below_horizontal), -math.sin(angle_below_horizontal)],
                                   [math.sin(angle_below_horizontal),  math.cos(angle_below_horizontal)]])

        # Rotate so the straight observer-target line lies on the x-axis. Both the ground and
        # (below) the light arc are expressed in this same rotated frame, so their heights can
        # be compared directly in is_obstructed().
        rotated_points = rotation_matrix @ np.array([x_distances, y_heights])
        straight_distances = rotated_points[0]
        ground_heights = rotated_points[1]

        # Light bends as the arc of a circle of radius k*earth_radius through the observer and
        # target. In the rotated frame the height of light above the straight line is
        # y = sqrt(gamma + s*(D - s)) - sqrt(gamma), where gamma = (k*R)^2 - (D/2)^2 and D is
        # the straight (chord) distance to the target. See atmospheric_refraction.pdf.
        distance_to_target = straight_distances[-1]
        gamma = (self.light_curvature*earth_radius)**2 - (distance_to_target/2)**2
        light_heights = np.sqrt(gamma + straight_distances*(distance_to_target - straight_distances)) - np.sqrt(gamma)
        
        self.los_points = [LosPoint(latitude, longitude, elevation, surface_distance, straight_distance, light_height, ground_height) 
                          for (latitude, longitude, elevation, surface_distance, straight_distance, light_height, ground_height) 
                          in zip(latitudes, longitudes, elevations, surface_distances, straight_distances, light_heights, ground_heights)]
    
    def get_straight_distance(self):
        return self.los_points[-1].straight_distance
    
    def is_obstructed(self):
        """True if the ground rises above the light ray at any sample. Samples
        within ignore_buffer of either endpoint are skipped to avoid DEM noise
        near the summits falsely blocking the line of sight."""
        return not all(los_point.ground_height < los_point.light_height
                       for los_point 
                       in self.los_points
                       if los_point.straight_distance > ignore_buffer and los_point.straight_distance < self.get_straight_distance()-ignore_buffer)

    def get_light_distance_from_centre(self, x):

        h1 = self.observer.elevation
        h2 = self.target.elevation
        D = self.surface_distance
        R = earth_radius
        k = self.light_curvature
        
        theta = x/R
        phi = D/R
    
        x1 = R + h1
        y1 = 0
    
        x2 = (R+h2)*math.cos(phi)
        y2 = (R+h2)*math.sin(phi)
    
        d = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    
        RL = k*R
    
        Z = math.sqrt(RL**2 - (d/2)**2)
    
        Mx = (x1+x2)/2 - Z*((y2-y1)/d)
        My = (y1+y2)/2 + Z*((x2-x1)/d)
    
        L0 = (Mx*math.cos(theta)+My*math.sin(theta)) + math.sqrt((Mx*math.cos(theta) + My*math.sin(theta))**2 - (Mx**2 + My**2 - RL**2))

        return L0

    def get_light_elevation(self, x):
        return self.get_light_distance_from_centre(x) - earth_radius

    def get_scatter_coefficient(self, x):
        return self.sea_level_scatter_coefficient * math.exp(-self.get_light_elevation(x)/atmosphere_scale_height)

    def get_contrast(self):
        """Contrast of the target against the sky (Vollmer 2020). The path is split
        into a shaded segment (fraction shaded_ratio, starting at the observer) and
        a sunlit segment, and the scattering coefficient is integrated along the
        curved light path of each. The light-path element is ds = (L/R) dx to leading
        order, where L is the distance from Earth's centre to the ray, so the
        surface-distance integral is weighted by L/R. The shade irradiation ratio is
        set from the line-of-sight bearing (see __init__).
        See ../misc/math/raw/atmospheric_scattering.ipynb."""

        d1 = self.surface_distance * self.shaded_ratio  # shaded segment ends here

        # scattering coefficient per unit light-path length, integrated over surface
        # distance x: beta(height of ray at x) * (light-path element ds/dx = L/R)
        def optical_depth_density(x):
            return self.get_scatter_coefficient(x) * self.get_light_distance_from_centre(x)/earth_radius

        scatter_integral_shaded = quad(optical_depth_density, 0, d1)[0]
        scatter_integral_sunlit = quad(optical_depth_density, d1, self.surface_distance)[0]

        contrast = math.exp(-scatter_integral_sunlit)/(1 - self.shade_irradiation_ratio + (self.shade_irradiation_ratio/math.exp(-scatter_integral_shaded)))

        return contrast

    def has_contrast(self):
        return self.get_contrast() > 0.02 # 0.02 is from Below the Horizon, Michael Vollmer, 2020

    def is_valid(self):
        return not self.is_obstructed() and self.has_contrast()

    def is_obstructed_early(self):
        """Batched, early-exit form of is_obstructed that does NOT need
        process_full_line_of_sight to have been run first.

        Samples the ground between observer and target in chunks of
        api_request_limit and returns True the moment a chunk contains a point
        (outside ignore_buffer) where the ground reaches the ray, so an obstructed
        line of sight is abandoned without fetching the rest of its elevations.
        Returns False only after every chunk has come back clear. The rotated-frame
        geometry and the ignore_buffer skip match is_obstructed exactly; it just
        stops early and keeps no los_points (use process_full_line_of_sight + plot
        when you want to visualise the whole line of sight)."""

        R = earth_radius
        h1 = self.observer.elevation
        h2 = self.target.elevation
        D = self.surface_distance
        k = self.light_curvature
        num_samples = self.num_samples

        if num_samples < 1:
            return False

        # The rotation that puts the straight observer-target line on the x-axis
        # depends only on the target endpoint (the last point in
        # process_full_line_of_sight).
        theta_target = D / R
        x_target = (R + h2) * math.sin(theta_target)
        y_target = h2 * math.cos(theta_target) - R * (1 - math.cos(theta_target)) - h1
        angle = -math.atan(y_target / x_target)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        distance_to_target = cos_a * x_target - sin_a * y_target   # target's straight (chord) distance
        gamma = (k * R)**2 - (distance_to_target / 2)**2
        sqrt_gamma = math.sqrt(gamma)

        # Intermediate sample points, equally spaced along the geodesic (endpoints
        # excluded, as in process_full_line_of_sight). The i-th sample sits at
        # surface distance (i+1)/(num_samples+1) * D from the observer.
        lng_lats = geod.npts(self.observer.longitude, self.observer.latitude,
                             self.target.longitude, self.target.latitude, num_samples)
        sample_latitudes = np.array(lng_lats)[:, 1]
        sample_longitudes = np.array(lng_lats)[:, 0]
        sample_surface_distance = (np.arange(1, num_samples + 1) / (num_samples + 1)) * D

        for start in range(0, num_samples, api_request_limit):
            chunk = slice(start, start + api_request_limit)

            elevations = np.array(get_elevations(sample_latitudes[chunk], sample_longitudes[chunk]))
            s = sample_surface_distance[chunk]

            theta = s / R
            x = (R + elevations) * np.sin(theta)
            y = elevations * np.cos(theta) - R * (1 - np.cos(theta)) - h1
            straight = cos_a * x - sin_a * y
            ground_height = sin_a * x + cos_a * y
            light_height = np.sqrt(gamma + straight * (distance_to_target - straight)) - sqrt_gamma

            # Only points beyond ignore_buffer of either summit can obstruct (same as
            # is_obstructed). Give up on the first such blocking point.
            considered = (straight > ignore_buffer) & (straight < distance_to_target - ignore_buffer)
            if np.any(considered & (ground_height >= light_height)):
                return True

        return False

    def is_valid_early(self):
        """Like is_valid, but uses is_obstructed_early and only computes the
        (analytic) contrast when nothing obstructs the beam -- so obstructed lines
        of sight never pay for the contrast test. Same result as is_valid."""
        return not self.is_obstructed_early() and self.has_contrast()

    def plot(self, baseline='straight', legend_location='best', plot_path=''):
        """Plot the line of sight in the rotated frame used by is_obstructed: the
        straight observer-target line is the reference and ground and light heights
        are measured perpendicular to it (the exact geometry of the obstruction
        test). baseline='straight' keeps the straight line flat at 0;
        baseline='light' makes the light ray the flat reference instead."""

        distances = np.array([point.surface_distance/1000.0 for point in self.los_points])
        ground = np.array([point.ground_height for point in self.los_points])
        light = np.array([point.light_height for point in self.los_points])
        straight = np.zeros_like(distances)

        if baseline == 'light':
            ground, straight, light = ground - light, straight - light, light - light

        plt.figure(figsize=(15,5))

        plt.plot(distances, light, color='yellow', label='Light', lw=2)
        plt.plot(distances, straight, color='k', label='Straight', lw=1, ls='--')

        sky_top = max(ground.max(), light.max())
        if self.shade_irradiation_ratio < 1:

            plt.fill_between(distances, y1=ground, y2=sky_top,
                             color='cornflowerblue', label='Sky')
            plt.fill_between(distances, y1=ground, y2=sky_top,
                             where=(distances <= distances[-1]*self.shaded_ratio),
                             color='k', alpha=1-self.shade_irradiation_ratio, label='Shadow')

        plt.plot(distances, ground, color='k', lw=0.8)

        plt.fill_between(distances, y1=min(light.min(), ground.min(), straight.min()), y2=ground, color='darkgrey', label='Earth')

        obstructed = self.is_obstructed()
        if obstructed:
            max_ind = np.argmax(ground - light)
            plt.plot(distances[max_ind], ground[max_ind], marker='x', color='red')

        observer_label = f'{self.observer.latitude:.4f}°, {self.observer.longitude:.4f}° ({self.observer.elevation:.0f} m)'
        target_label = f'{self.target.latitude:.4f}°, {self.target.longitude:.4f}° ({self.target.elevation:.0f} m)'
        plt.title('Line-of-Sight Test\n'
                  f'{observer_label}  →  {target_label}\n' + 
                  f'Distance = {self.surface_distance/1000:.1f} km    '
                  f'Light Curvature = {self.light_curvature:.1f}    '
                  f'Obstructed = {obstructed}\n'
                  f'Bearing = {self.forward_azimuth % 360:.1f}°    '
                  f'Shade Irradiation = {self.shade_irradiation_ratio:.2f}    '
                  f'Shaded Ratio = {self.shaded_ratio:.2f}    '
                  f'Contrast = {self.get_contrast():.3f}')
        
        plt.xlabel('Distance (km)')

        plt.ylabel('Height (m)')
            
        fig = plt.gcf()
        fig.patch.set_facecolor('w')
        fig.set_dpi(300)
        plt.grid(ls=':', c='k', alpha=0.5)
        plt.legend(loc=legend_location, framealpha=1)
        
        if plot_path != '':
            plt.savefig(plot_path, bbox_inches='tight')

        plt.show()

class Patch():
    """A region of the globe used to limit which summits are checked against a
    candidate. Inner bounds tile the globe exactly; outer bounds extend far enough
    that every summit which could have a line of sight with an inner summit is
    included (see set_outer_bounds). Patches are cached as CSVs in patch_directory.
    """

    def __init__(self,
                 north_inner,
                 south_inner,
                 east_inner=None,
                 west_inner=None,
                 global_summits=None):

        self.global_summits = global_summits
        
        self.num_summits_inner = None
        self.summits_outer = None
        
        self.north_inner = north_inner
        self.south_inner = south_inner
        self.east_inner = east_inner
        self.west_inner = west_inner

        self.north_outer = None
        self.south_outer = None
        self.east_outer = None
        self.west_outer = None

        self.lat_offset = None
        self.lng_offset = None

        if type(global_summits) == type(None):
            try:
                self.load_patch()
            except Exception as error:
                print(f'Error loading patch {self.get_file_name()}: {error}')
        else:
            self.set_outer_bounds()
            self.summits_outer = self.get_summits_in_range(self.north_outer, self.south_outer, self.east_outer, self.west_outer)
            self.num_global_summits = len(global_summits)
            self.global_summits = None  # No need to keep this populated once we have summits_outer
            self.save()

    def __str__(self):        
        return self.get_metadata()

    def get_file_name(self):
        if self.is_pole_patch():
            file_name = f'{self.north_inner}N_{self.south_inner}S.csv'
        else:
            file_name = f'{self.north_inner}N_{self.south_inner}S_{self.east_inner}E_{self.west_inner}W.csv'
        return file_name

    def load_patch(self):
        file_name = self.get_file_name()

        # reading metadata
        metadata_list = []
        with open(f'{patch_directory}/{file_name}', 'r') as raw_metadata:
            for i, line in enumerate(raw_metadata):
                if i >= 17:
                    break
                metadata_list.append(line.strip().split(': '))
                
        self.num_global_summits = int(metadata_list[0][1])
        self.num_summits_inner = int(metadata_list[2][1])

        self.north_outer = float(metadata_list[10][1])
        self.south_outer = float(metadata_list[11][1])

        east_outer = metadata_list[12][1]
        self.east_outer = float(east_outer) if east_outer != 'None' else None
        west_outer = metadata_list[13][1]        
        self.west_outer = float(west_outer) if west_outer != 'None' else None


        self.lat_offset = float(metadata_list[15][1])
        lng_offset = metadata_list[16][1] 
        self.lng_offset = float(lng_offset) if lng_offset != 'None' else None

        self.summits_outer = pd.read_csv(f'{patch_directory}/{file_name}', comment='#')

    def save(self):
        file_name = self.get_file_name()
        
        # this is needed to add the metadata as a comment in csv before data
        with open(f'{patch_directory}/{file_name}', 'w') as patch_file:
            patch_file.write(self.get_metadata(is_comment=True))
            self.summits_outer.to_csv(patch_file, index=False)
            print(f'Saved {file_name}')

    def get_metadata(self, is_comment=False):
        
        metadata = dedent(f"""\
            Global Summits: {self.num_global_summits}

            Patch Summits (Inner): {self.num_summits_inner}
            Patch Summits (Outer): {len(self.summits_outer)}

            North (Inner): {self.north_inner}
            South (Inner): {self.south_inner}
            East (Inner): {self.east_inner}
            West (Inner): {self.west_inner}

            North (Outer): {self.north_outer}
            South (Outer): {self.south_outer}
            East (Outer): {self.east_outer}
            West (Outer): {self.west_outer}

            Lat Offset: {self.lat_offset}
            Lng Offset: {self.lng_offset}\
        """)
        
        if is_comment:
            return '\n'.join('# ' + line for line in metadata.splitlines()) + '\n#\n'
        return metadata

    def is_pole_patch(self):
        return self.east_inner is None and self.west_inner is None

    def is_lng_seam_patch(self, east_bound, west_bound):
        return east_bound < 0 and west_bound > 0

    def make_latitude_valid(self, latitude):
        if latitude > 90:
            return 90
        elif latitude < -90:
            return -90
        return latitude

    def make_longitude_valid(self, longitude):
        if longitude > 180:
            return longitude - 360
        elif longitude < -180:
            return longitude + 360
        return longitude

    def convert_distance_to_delta_lat(self, distance):
        return distance / 111320  # There are 111320 m per deg of latitude

    def convert_distance_to_delta_lng(self, distance, latitude):
        return self.convert_distance_to_delta_lat(distance) / math.cos(math.radians(latitude))

    def get_offset_bounds(self, offset_distance):
        """Inner bounds expanded outward by offset_distance. Returns
        (north, south, east, west); east and west are None for pole patches."""
        lat_offset = self.convert_distance_to_delta_lat(offset_distance)
        north = self.make_latitude_valid(self.north_inner + lat_offset)
        south = self.make_latitude_valid(self.south_inner - lat_offset)

        if self.is_pole_patch():
            return north, south, None, None

        lat_for_offset = self.south_inner if self.south_inner < 0 else self.north_inner
        lng_offset = self.convert_distance_to_delta_lng(offset_distance, lat_for_offset)
        east = self.make_longitude_valid(self.east_inner + lng_offset)
        west = self.make_longitude_valid(self.west_inner - lng_offset)
        return north, south, east, west

    def get_summits_within_offset(self, offset_distance):
        """Summits inside the inner bounds expanded by offset_distance."""
        north, south, east, west = self.get_offset_bounds(offset_distance)

        if self.is_pole_patch():
            return self.get_summits_in_range(north, south, None, None)

        lat_for_offset = self.south_inner if self.south_inner < 0 else self.north_inner
        lng_offset = self.convert_distance_to_delta_lng(offset_distance, lat_for_offset)
        if patch_size + 2*lng_offset >= 360:
            # the buffer wraps all the way around at this latitude; take the whole band
            return self.global_summits.query('latitude >= @south and latitude < @north')

        return self.get_summits_in_range(north, south, east, west)

    def get_offset_distance(self):
        summits_inner = self.get_summits_in_range(self.north_inner, self.south_inner, self.east_inner, self.west_inner)
        self.num_summits_inner = len(summits_inner)
        inner_max_elevation = summits_inner.elevation.max()

        # A disqualifying summit can only lie inside the outer bounds, and the outer
        # bounds never reach past this patch's neighbours. So the worst-case
        # disqualifier is the tallest summit in that neighbourhood -- far shorter than
        # Everest for most of the globe, which keeps the outer bounds (and the overlap
        # between patches) small.
        #
        # To find it safely, search the largest region the outer bounds could ever
        # cover (sized with the tallest summit on Earth). The real, smaller outer
        # bounds always fall inside this region, so its tallest summit is a valid worst
        # case. This searches global_summits, never the already-buffered patch files.
        largest_possible_offset = horizon_distance(self.global_summits.elevation.max()) + horizon_distance(inner_max_elevation)
        neighbourhood = self.get_summits_within_offset(largest_possible_offset)
        neighbourhood_max_elevation = neighbourhood.elevation.max()

        return horizon_distance(neighbourhood_max_elevation) + horizon_distance(inner_max_elevation)

    def set_outer_bounds(self):
        """Extend the inner bounds by MHD(tallest summit in this patch's neighbourhood)
        + MHD(tallest summit in this patch), so no possible line of sight into the patch
        is missed while keeping overlap small. Longitude uses the patch edge farthest
        from the equator (worst case)."""
        offset_distance = self.get_offset_distance()

        self.lat_offset = self.convert_distance_to_delta_lat(offset_distance)
        self.north_outer, self.south_outer, self.east_outer, self.west_outer = self.get_offset_bounds(offset_distance)

        if not self.is_pole_patch():
            lat_for_offset = self.south_inner if self.south_inner < 0 else self.north_inner
            self.lng_offset = self.convert_distance_to_delta_lng(offset_distance, lat_for_offset)

    def get_summits_in_range(self, north_bound, south_bound, east_bound, west_bound):
        
        lat_condition = 'latitude >= @south_bound and latitude < @north_bound'
        
        if self.is_pole_patch():
            summits_in_range = self.global_summits.query(lat_condition)
        elif self.is_lng_seam_patch(east_bound, west_bound):
            summits_in_range = self.global_summits.query(lat_condition + ' and (longitude >= @west_bound or longitude < @east_bound)')
        else:
            summits_in_range = self.global_summits.query(lat_condition + ' and longitude >= @west_bound and longitude < @east_bound')
        
        return summits_in_range