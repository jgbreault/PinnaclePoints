"""
Find the longest lines of sight on Earth between summits above a prominence
threshold, using the patch system for speed.

Candidate generation: each patch's outer summits are paired with its inner summits
(lower summit as observer, higher as target), and two cheap horizon filters plus a
distance/horizon geometry check drop pairs that can never span the distance
threshold. Each candidate pair belongs to exactly one patch, so patches are
independent and can be processed in any grouping.

Streaming in batches (to bound memory)
--------------------------------------
Candidates are accumulated as lightweight parallel arrays while patches are scanned.
Once at least candidate_batch_size of them have piled up (checked after each patch),
that whole batch is screened and fully analysed, the valid lines of sight are kept
and the rest of the batch is discarded, and scanning continues. Peak memory is
therefore bounded by one batch of candidates rather than every candidate on Earth,
which matters at low prominence thresholds where the candidate count explodes.

Progressive batched screen
--------------------------
Full line-of-sight analysis is expensive (it samples the ground every ~100 m along
each line and computes contrast), so each batch is screened first. Rather than
finishing one candidate at a time, a single sample point is tested across all
surviving candidates in the batch at once:

  1. the middle of every line of sight,
  2. then the quarters (1/4, 3/4),
  3. then the eighths, sixteenths, and so on,

and within each level the points nearest the middle (inner) before the points
nearest the ends (outer), alternating left then right of the middle. At each point
only obstruction is checked (no contrast), and a candidate is dropped the instant it
fails a single point. Points within ignore_buffer of either summit are skipped: a
point is only sampled when it is outside that buffer for every surviving candidate.
Sampling keeps refining until a newly sampled point removes no candidates.

Only the survivors then get full line-of-sight analysis, which also gives up early:
their sampled elevations are fetched in API-sized batches and the line of sight is
abandoned the moment a batch contains an obstructing point (LineOfSight.is_valid_early).
The contrast of the whole beam is only computed for the ones that no batch ever
blocks. Results are written to ../data/results/longest_los/.

Requires the patches (patch_maker.py) and the locally hosted elevation API used by
commons.
"""

import os
import time
import numpy as np
import pandas as pd
import commons as me

start_time = time.time()

prominence_threshold = 300       # in m
distance_threshold = 300*1000    # in m
candidate_batch_size = 1000000   # screen + analyse once this many candidates have accumulated
screen_block_size = 100000       # sample a screening point in blocks of this many (also its progress cadence)
analysis_progress_every = 100    # print full-analysis progress every this many survivors
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

# Candidate fields, accumulated as parallel arrays between processing batches.
fields = ['observer_summit_id', 'observer_latitude', 'observer_longitude', 'observer_elevation',
          'target_summit_id', 'target_latitude', 'target_longitude', 'target_elevation',
          'surface_distance', 'forward_azimuth']


def get_inner_summits(patch):
    """The summits of a loaded patch that fall within its inner bounds."""
    summits = patch.summits_outer
    inside = (summits.latitude >= patch.south_inner) & (summits.latitude < patch.north_inner)
    if not patch.is_pole_patch():
        inside &= (summits.longitude >= patch.west_inner) & (summits.longitude < patch.east_inner)
    return summits[inside]


def screen_and_analyse(observer_summit_id, observer_latitude, observer_longitude, observer_elevation,
                       target_summit_id, target_latitude, target_longitude, target_elevation,
                       surface_distance, forward_azimuth):
    """Screen one batch of candidate lines of sight, then fully analyse the
    survivors, and return the valid lines of sight.

    The progressive screen tests one sample point across all surviving candidates at
    a time (obstruction only), dropping any candidate the instant the ground blocks
    its ray. A point is skipped entirely unless it is outside ignore_buffer for every
    survivor. Survivors then get the full, early-exit obstruction + contrast test."""

    num = len(surface_distance)
    alive = np.ones(num, dtype=bool)
    print(f'  screening {num:,} candidates')

    for point_number, (numerator, denominator) in enumerate(me.screening_fractions(), start=1):

        alive_index = np.where(alive)[0]
        if len(alive_index) == 0:
            break

        fraction = numerator / denominator

        # Stop refining once the sample spacing is finer than full analysis would use.
        if surface_distance[alive_index].max() / denominator < me.default_max_sampling_distance:
            break

        # Skip this point unless it is outside ignore_buffer for every surviving
        # candidate (it does not count as a round that removed nothing).
        distance_along = fraction * surface_distance[alive_index]
        inside_buffer = ((distance_along < me.ignore_buffer)
                         | (distance_along > surface_distance[alive_index] - me.ignore_buffer))
        if np.any(inside_buffer):
            continue

        # Sample the point in blocks so the long points show progress as they go.
        total_this_point = len(alive_index)
        removed = 0
        processed = 0
        for block_start in range(0, total_this_point, screen_block_size):
            block = alive_index[block_start:block_start + screen_block_size]

            latitudes, longitudes = me.points_at_fraction(observer_latitude[block],
                                                           observer_longitude[block],
                                                           forward_azimuth[block],
                                                           surface_distance[block],
                                                           fraction)
            ground_elevation = np.array(me.get_elevations(latitudes, longitudes))
            light_elevation = me.light_elevation_at_fraction(observer_elevation[block],
                                                            target_elevation[block],
                                                            surface_distance[block],
                                                            fraction)

            # Obstructed at this point when the ground is at or above the ray.
            blocked = ground_elevation >= light_elevation
            alive[block[blocked]] = False
            removed += int(blocked.sum())
            processed += len(block)

            if processed < total_this_point:  # the final tally is printed just below
                print(f'      point {point_number} ({numerator}/{denominator}): '
                      f'sampled {processed:,}/{total_this_point:,}, {removed:,} blocked')

        print(f'    point {point_number} ({numerator}/{denominator}): '
              f'{total_this_point:,} sampled, {removed:,} blocked, {int(alive.sum()):,} remain')

        if removed == 0:
            break

    survivor_index = np.where(alive)[0]
    num_survivors = len(survivor_index)
    print(f'  {num_survivors:,}/{num:,} survived screening; running full analysis')

    valid = []
    for count, c in enumerate(survivor_index, start=1):
        observer = me.Summit(summit_id = observer_summit_id[c],
                             latitude = observer_latitude[c],
                             longitude = observer_longitude[c],
                             elevation = observer_elevation[c])
        target = me.Summit(summit_id = target_summit_id[c],
                           latitude = target_latitude[c],
                           longitude = target_longitude[c],
                           elevation = target_elevation[c])

        los = me.LineOfSight(observer, target)
        if los.is_valid_early():
            valid.append(los)

        if count % analysis_progress_every == 0 or count == num_survivors:
            print(f'    analysed {count:,}/{num_survivors:,}, {len(valid)} valid')

    print(f'  {len(valid)} valid lines of sight in this batch')
    return valid


chunks = {field: [] for field in fields}
pending = 0                  # candidates accumulated but not yet processed
num_candidates_total = 0
valid_lines_of_sight = []


def process_pending_batch(through_patch):
    """Concatenate the accumulated candidate chunks into one batch, screen and
    analyse it, keep the valid lines of sight, and clear the chunks."""
    global pending
    batch = {field: np.concatenate(chunks[field]) for field in fields}
    for field in fields:
        chunks[field].clear()
    print(f'\nProcessing {pending:,} candidates ({through_patch}):')
    valid_lines_of_sight.extend(screen_and_analyse(**batch))
    print(f'  running total: {len(valid_lines_of_sight)} valid lines of sight\n')
    pending = 0


for i, bounds in enumerate(patch_bounds):

    patch = me.Patch(*bounds)
    if patch.summits_outer is None or len(patch.summits_outer) == 0:
        continue

    outer = patch.summits_outer.query('prominence > @prominence_threshold')
    inner = get_inner_summits(patch).query('prominence > @prominence_threshold')
    if len(outer) == 0 or len(inner) == 0:
        continue

    # Each pair is built in the reverse direction: the lower summit is the observer
    # and the higher summit is the target. summit_ids run from the highest summit
    # (id 0) downwards, so the larger id is the lower summit.

    # The observer is the lower summit, so its horizon can reach no farther than the
    # target's; a target must therefore reach half the distance threshold on its own.
    targets = outer.query('max_horizon_distance > @distance_threshold/2')

    # Even paired with the tallest summit the patch can offer, an observer's combined
    # horizon must exceed the distance threshold.
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

        # Forward azimuth and distance from this observer to every candidate target.
        forward_azimuths, _, distances = me.geod.inv(np.full(len(targets), observer.longitude),
                                                     np.full(len(targets), observer.latitude),
                                                     target_longitude, target_latitude)
        observer_max_horizon_distance = me.horizon_distance(observer.elevation)

        # Keep pairs that are far enough apart and within combined horizon range. The
        # id comparison makes the observer the lower (larger-id) summit and generates
        # each pair from a single patch only.
        is_candidate = ((target_summit_id < observer.summit_id)
                        & (distances > distance_threshold)
                        & (distances < observer_max_horizon_distance + target_max_horizon_distance))

        kept = np.where(is_candidate)[0]
        if len(kept) == 0:
            continue

        n = len(kept)
        chunks['observer_summit_id'].append(np.full(n, observer.summit_id))
        chunks['observer_latitude'].append(np.full(n, observer.latitude))
        chunks['observer_longitude'].append(np.full(n, observer.longitude))
        chunks['observer_elevation'].append(np.full(n, observer.elevation))
        chunks['target_summit_id'].append(target_summit_id[kept])
        chunks['target_latitude'].append(target_latitude[kept])
        chunks['target_longitude'].append(target_longitude[kept])
        chunks['target_elevation'].append(target_elevation[kept])
        chunks['surface_distance'].append(distances[kept])
        chunks['forward_azimuth'].append(forward_azimuths[kept])
        pending += n
        num_candidates_total += n

    print(f'Patch {i+1}/{len(patch_bounds)}: {pending:,} candidates pending '
          f'({num_candidates_total:,} found, {len(valid_lines_of_sight)} valid so far)')

    # Process the accumulated candidates once enough have piled up.
    if pending >= candidate_batch_size:
        process_pending_batch(through_patch=f'through patch {i+1}/{len(patch_bounds)}')

# Process whatever is left over after the last patch.
if pending > 0:
    process_pending_batch(through_patch='final batch')

print(f'\n{num_candidates_total:,} line-of-sight candidates found in total')

if num_candidates_total == 0:
    print('No line-of-sight candidates found.')
    raise SystemExit


########## OUTPUT ##########

observer_summit_ids = []
observer_latitudes = []
observer_longitudes = []
observer_elevations = []

target_summit_ids = []
target_latitudes = []
target_longitudes = []
target_elevations = []

surface_distances = []
bearings = []
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
    bearings.append(los.forward_azimuth % 360)  # observer-to-target compass bearing, 0-360 deg
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
    'bearing': bearings,
    'contrast': contrasts
})

os.makedirs(result_directory, exist_ok=True)
los_data.to_csv(f'{result_directory}/longest_los.csv', index=False)
print(f'Wrote {result_directory}/longest_los.csv ({len(los_data)} valid lines of sight)')

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
max_los_data.to_csv(f'{result_directory}/longest_los_max.csv', index=False)

n_max, n_total = len(max_los_data), len(los_data)
percent_max = round(100*n_max/n_total, 2) if n_total else 0
print(f'Wrote {result_directory}/longest_los_max.csv '
      f'({n_max}/{n_total} ({percent_max}%) are the longest for both their summits)')
print('\n')

end_time = time.time()
total_time = round(end_time - start_time)

days = total_time // 86400
hours = (total_time % 86400) // 3600
minutes = (total_time % 3600) // 60
seconds = total_time % 60

print(f'Run Time: {days}d {hours}h {minutes}m {seconds}s')
