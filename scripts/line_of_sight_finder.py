"""
Find the longest lines of sight on Earth between summits above a prominence
threshold, using the patch system for speed.

Each patch's outer bounds are built to contain every summit that could share a
line of sight with a summit in its inner region, so pairing each patch's inner
summits with its outer summits finds every possible pair without comparing every
summit against every other. Each pair is built in the reverse direction, with the
lower summit as the observer and the higher as the target: the contrast model
shadows the observer-side air, and shadowing the denser air at the lower end
suppresses the most airlight, giving the pair its best chance of being visible (see
../misc/method.txt). summit_ids run from the highest summit (id 0) to the lowest, so
the larger id is the lower summit; comparing ids keeps each pair to a single patch
and makes the lower summit the observer. Two cheap horizon filters drop summits that
can never reach the distance threshold before any pairing. Only cheap geometry runs
at the pairing stage (vectorised), so a LineOfSight is built only for pairs that are
far enough apart and within combined horizon range. Each survivor is then
pre-screened with a single midpoint elevation check before the full line-of-sight
test is run. Results are written to ../data/results/longest_los/.

Requires the patches to be generated first (patch_maker.py) and the locally hosted
elevation API used by commons. Work in progress.
"""

import os
import time
import numpy as np
import pandas as pd
import commons as me

start_time = time.time()

prominence_threshold = 500    # in m
distance_threshold = 400*1000 # in m
result_directory = '../data/results/longest_los'

# Every patch, as (north_inner, south_inner, east_inner, west_inner). Built the
# same way as patch_maker.py: a cap at each pole and a 10x10 degree grid between.
pole_lat = me.get_pole_latitude()
lat_boundaries = me.get_patch_lat_boundaries()
lng_boundaries = me.get_patch_lng_boundaries()

patch_bounds = [(-pole_lat, -90, None, None)]
for lat in lat_boundaries[:-1]:
    for lng in lng_boundaries[:-1]:
        patch_bounds.append((lat + me.patch_size, lat, lng + me.patch_size, lng))
patch_bounds.append((90, pole_lat, None, None))


def get_inner_summits(patch):
    """The summits of a loaded patch that fall within its inner bounds."""
    summits = patch.summits_outer
    inside = (summits.latitude >= patch.south_inner) & (summits.latitude < patch.north_inner)
    if not patch.is_pole_patch():
        inside &= (summits.longitude >= patch.west_inner) & (summits.longitude < patch.east_inner)
    return summits[inside]


candidate_lines_of_sight = []
for i, bounds in enumerate(patch_bounds):

    patch = me.Patch(*bounds)
    if patch.summits_outer is None or len(patch.summits_outer) == 0:
        continue

    outer = patch.summits_outer.query('prominence > @prominence_threshold')
    inner = get_inner_summits(patch).query('prominence > @prominence_threshold')
    if len(outer) == 0 or len(inner) == 0:
        continue

    # Each pair is built in the reverse direction: the lower summit is the observer
    # and the higher summit is the target (see the module docstring). summit_ids run
    # from the highest summit (id 0) downwards, so the larger id is the lower summit.

    # The observer is the lower summit, so its horizon can reach no farther than the
    # target's; a target must therefore reach half the distance threshold on its own
    # for the pair to span it. Drop summits too short to ever be a target.
    targets = outer.query('max_horizon_distance > @distance_threshold/2')

    # Even paired with the tallest summit the patch can offer, an observer's combined
    # horizon must exceed the distance threshold. Drop summits too short to ever be
    # an observer.
    tallest_max_horizon_distance = outer.max_horizon_distance.max()
    inner = inner.query('max_horizon_distance > @distance_threshold - @tallest_max_horizon_distance')

    if len(targets) == 0 or len(inner) == 0:
        continue

    target_latitude = targets.latitude.values
    target_longitude = targets.longitude.values
    target_elevation = targets.elevation.values
    target_summit_id = targets.summit_id.values
    target_max_horizon_distance = targets.max_horizon_distance.values

    for observer in inner.itertuples():

        # Distance from this observer to every candidate target.
        distances = me.geod.inv(np.full(len(targets), observer.longitude),
                                np.full(len(targets), observer.latitude),
                                target_longitude, target_latitude)[2]
        observer_max_horizon_distance = me.horizon_distance(observer.elevation)

        # Keep pairs that are far enough apart and within combined horizon range. The
        # id comparison makes the observer the lower (larger-id) summit and generates
        # each pair from a single patch only.
        is_candidate = ((target_summit_id < observer.summit_id)
                        & (distances > distance_threshold)
                        & (distances < observer_max_horizon_distance + target_max_horizon_distance))

        for j in np.where(is_candidate)[0]:
            obs = me.Summit(summit_id = observer.summit_id,
                            latitude = observer.latitude,
                            longitude = observer.longitude,
                            elevation = observer.elevation)
            trg = me.Summit(summit_id = target_summit_id[j],
                            latitude = target_latitude[j],
                            longitude = target_longitude[j],
                            elevation = target_elevation[j])
            candidate_lines_of_sight.append(me.LineOfSight(obs, trg))

    print(f'Patch {i+1}/{len(patch_bounds)}: {len(candidate_lines_of_sight)} line-of-sight candidates so far')

num_los_candidates = len(candidate_lines_of_sight)
print(f'\n{num_los_candidates} line-of-sight candidates found\n')

los_passed_mid_test = []
for start in range(0, len(candidate_lines_of_sight), me.api_request_limit):

    los_batch = candidate_lines_of_sight[start:start + me.api_request_limit]

    observer_lats = [los.observer.latitude for los in los_batch]
    observer_lngs = [los.observer.longitude for los in los_batch]

    target_lats = [los.target.latitude for los in los_batch]
    target_lngs = [los.target.longitude for los in los_batch]

    mid_lats = []
    mid_lngs = []
    mid_light_elevations = []

    for los in los_batch:

        observer_lat = los.observer.latitude
        observer_lng = los.observer.longitude

        target_lat = los.target.latitude
        target_lng = los.target.longitude

        mid_point = me.geod.npts(observer_lng, observer_lat, target_lng, target_lat, 1)[0]

        mid_lats.append(mid_point[1])
        mid_lngs.append(mid_point[0])

        mid_light_elevations.append(los.get_light_elevation(los.surface_distance/2))

    mid_elevations = me.get_elevations(mid_lats, mid_lngs)

    for i, los in enumerate(los_batch):

        mid_light_elevation = mid_light_elevations[i]
        mid_elevation = mid_elevations[i]

        if mid_light_elevation > mid_elevation:
            los_passed_mid_test.append(los)

num_los_passed_mid_test = len(los_passed_mid_test)
print(f'{num_los_passed_mid_test}/{num_los_candidates} ({round(100*num_los_passed_mid_test/num_los_candidates, 2)}%) ' +
      'line-of-sight candidates passed the mid-point test')
print('\n')

valid_lines_of_sight = []
for i, los in enumerate(los_passed_mid_test):

    los.process_full_line_of_sight()

    los_is_valid = los.is_valid()
    los.los_points = []

    if los_is_valid:
        valid_lines_of_sight.append(los)

    if i%1000 == 999 or i == num_los_passed_mid_test-1:
        print(f'Found {len(valid_lines_of_sight)} valid lines of sight in {i+1}/{num_los_passed_mid_test} candidates')

print('\n')

observer_summit_ids = []
observer_latitudes = []
observer_longitudes = []
observer_elevations = []

target_summit_ids = []
target_latitudes = []
target_longitudes = []
target_elevations = []

surface_distances = []
contrasts = []

for los in valid_lines_of_sight:

    observer_summit_ids.append(los.observer.summit_id)
    observer_latitudes.append(los.observer.latitude)
    observer_longitudes.append(los.observer.longitude)
    observer_elevations.append(los.observer.elevation)

    target_summit_ids.append(los.target.summit_id)
    target_latitudes.append(los.target.latitude)
    target_longitudes.append(los.target.longitude)
    target_elevations.append(los.target.elevation)

    surface_distances.append(los.surface_distance)
    contrasts.append(los.get_contrast())

los_data = pd.DataFrame({
    'observer_summit_id': observer_summit_ids,
    'observer_latitude': observer_latitudes,
    'observer_longitude': observer_longitudes,
    'observer_elevation': observer_elevations,
    'target_summit_id': target_summit_ids,
    'target_latitude': target_latitudes,
    'target_longitude': target_longitudes,
    'target_elevation': target_elevations,
    'distance': surface_distances,
    'contrast': contrasts
})

# Pair each line of sight with both of its summits, so a summit can claim its
# longest line of sight whether it appears as the observer or the target.
summit_los = pd.concat([
    los_data[['observer_summit_id', 'distance']].rename(columns={'observer_summit_id': 'summit_id'}),
    los_data[['target_summit_id', 'distance']].rename(columns={'target_summit_id': 'summit_id'})
])
max_distance_per_summit = summit_los.groupby('summit_id')['distance'].max()

# Keep a line of sight only if its distance is the longest for BOTH of its summits.
is_max = ((los_data['distance'] == los_data['observer_summit_id'].map(max_distance_per_summit))
          & (los_data['distance'] == los_data['target_summit_id'].map(max_distance_per_summit)))
max_los_data = los_data[is_max].copy()

n_max, n_total = len(max_los_data), len(los_data)
print(f'{n_max}/{n_total} ({100*n_max/n_total:.2f}%) lines of sight are the longest for both their summits')
print('\n')

end_time = time.time()
total_time = round(end_time - start_time)

days = total_time // 86400
hours = (total_time % 86400) // 3600
minutes = (total_time % 3600) // 60
seconds = total_time % 60

print(f'Run Time: {days}d {hours}h {minutes}m {seconds}s')
