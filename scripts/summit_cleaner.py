"""
Cleans and enriches the raw summit datasets, producing two CSVs used by all
downstream scripts:

  data/clean/summits_prm.csv  — summits from the prominence dataset (Kirmse & de Ferranti)
  data/clean/summits_iso.csv  — summits from the isolation dataset (Kirmse & de Ferranti)

For each summit, the elevation is set to max(dataset value, Open-Meteo API value).
The raw dataset elevations can be slightly off; the API uses a higher-resolution DEM
and usually wins for tall peaks. Taking the max ensures we never underestimate height,
which is the conservative choice for a visibility analysis.

The 'candidate' flag marks summits that are worth testing as pinnacle point candidates.
For the prominence dataset this is the OTOTW (On-Top-Of-The-World) subset. For the
isolation dataset it is summits with isolation > 100 km (extreme isolation points are
strong candidates even if they are not OTOTW mountains).
"""

import pandas as pd
import numpy as np
import commons as me
import time


def get_batch_summit_elevations(batch_summits):
    """
    Replace each summit's elevation with max(dataset elevation, API elevation).

    The API (Open-Meteo) uses a finer DEM than the raw prominence/isolation datasets,
    so it is occasionally higher. We never want to underestimate a summit's height.
    """
    latitudes = np.array(batch_summits.latitude)
    longitudes = np.array(batch_summits.longitude)
    elevations = np.array(batch_summits.elevation)

    api_elevations = me.get_elevations(latitudes, longitudes)

    for i, api_elevation in enumerate(api_elevations):
        if api_elevation > elevations[i]:
            elevations[i] = api_elevation

    batch_summits.elevation = elevations
    return batch_summits


def get_summit_elevations_in_batches(summits):
    """Send elevation API requests in batches of me.api_request_limit summits."""
    num_summits = len(summits)
    batches = np.array_split(summits, len(summits) // me.api_request_limit + 1)

    processed_batches = []
    for i, batch in enumerate(batches):
        if i % 10000 == 0:
            print(f'Processed elevations for {i*me.api_request_limit}/{num_summits} summits')
        processed_batches.append(get_batch_summit_elevations(batch))

    return pd.concat(processed_batches, ignore_index=True)


def fix_big_bad_elevations(df, ids):
    """Re-fetch elevations for specific summit IDs that are known to be wrong in the API."""
    subset = df.loc[ids]
    lats = subset.latitude.tolist()
    lngs = subset.longitude.tolist()
    elevations = me.get_elevations(lats, lngs)
    df.loc[ids, 'elevation'] = elevations


start_time = time.time()

print('PROMINENCE SUMMITS\n')

ototw = pd.read_csv('../data/raw/ototw_p300m.csv')
ototw = ototw[['latitude', 'longitude', 'elevation_m', 'prominence_m']]

prm_summit_col_names = ['latitude', 'longitude', 'elevation', 'key_saddle_latitude', 'key_saddle_longitude', 'prominence']
prm_summits = pd.read_csv('../data/raw/all-peaks-sorted-p100.txt', names=prm_summit_col_names)

starting_num_prm_summits = len(prm_summits)

prm_summits = prm_summits[['latitude', 'longitude', 'elevation', 'prominence']]
prm_summits = prm_summits.drop_duplicates()

# Mark every summit that also appears in the OTOTW dataset as a candidate.
# OTOTW mountains are summits where no land rises above their horizontal plane —
# a necessary (but not sufficient) condition for a pinnacle point.
prm_summits = prm_summits.merge(ototw[['latitude', 'longitude']], on=['latitude', 'longitude'], how='left', indicator='temp_merge')
prm_summits['candidate'] = prm_summits['temp_merge'].eq('both')
prm_summits = prm_summits.drop(columns=['temp_merge'])

# Two summits whose coordinates differ by a tiny rounding error between the OTOTW
# and Kirmse datasets, so the merge above misses them. Manually confirmed as OTOTW.
prm_summits.loc[[266009, 532994], 'candidate'] = True

# Longitude 180.0 is on the antimeridian and causes wraparound bugs in geodesic
# calculations; nudge it just inside the boundary.
prm_summits.loc[prm_summits['longitude'] == 180.0, 'longitude'] -= 0.0001

prm_summits = get_summit_elevations_in_batches(prm_summits)
prm_summits = prm_summits.sort_values('elevation', ascending=False)
prm_summits = prm_summits.reset_index(drop=True)

# Grove Hill (index 7763206 after elevation-sort reset): the API returned a bad
# elevation on the first pass, causing it to sort much lower than its true rank.
# After re-sorting by the corrected elevation the index changes, so this override
# must be applied after the sort+reset. Confirmed OTOTW by manual inspection.
prm_summits.loc[[7763206], 'candidate'] = True

ending_num_prm_summits = len(prm_summits)

print(f'\nSummits before clean-up: {starting_num_prm_summits}')
print(f'Summits after clean-up: {ending_num_prm_summits} ({starting_num_prm_summits-ending_num_prm_summits} removed)')

num_prm_candidates = len(prm_summits.query('candidate == True'))
print(f'Number of Candidates: {num_prm_candidates} ({round(100*num_prm_candidates/ending_num_prm_summits, 3)}%)')

prm_summits.to_csv('../data/clean/summits_prm.csv', index_label='summit_id')

print('\n##################################################\n')

print('ISOLATION SUMMITS\n')

isolation_candidate_threshold_km = 100  # summits farther than this from any higher point are candidates

iso_col_names = ['latitude', 'longitude', 'elevation_ft', 'ILP_latitude', 'ILP_longitude', 'isolation_km']
iso_summits = pd.read_csv('../data/raw/alliso-sorted.txt', names=iso_col_names)

starting_num_iso_summits = len(iso_summits)

iso_summits['elevation'] = iso_summits.elevation_ft.divide(3.28084).round(2)
iso_summits['isolation'] = iso_summits.isolation_km.multiply(1000).round(2)

iso_summits = iso_summits[['latitude', 'longitude', 'elevation', 'isolation']]
iso_summits = iso_summits.drop_duplicates()

# The dataset includes some summits with < 1 km isolation that are likely data errors.
iso_summits = iso_summits.query('isolation >= 1000')

iso_summits['candidate'] = (iso_summits.isolation > isolation_candidate_threshold_km * 1000) & (iso_summits.elevation > 0)

# Everest is not in the isolation dataset (it has no higher neighbour, so isolation
# is undefined), but it is an obvious pinnacle point candidate — add it manually.
everest = prm_summits.head(1)
everest_iso_data = [everest.latitude.values[0],
                    everest.longitude.values[0],
                    everest.elevation.values[0],
                    None,
                    True]
everest_iso_data = pd.DataFrame([everest_iso_data], columns=iso_summits.columns)
iso_summits = pd.concat([everest_iso_data, iso_summits], ignore_index=True)

iso_summits.loc[iso_summits['longitude'] == 180.0, 'longitude'] -= 0.0001

iso_summits = get_summit_elevations_in_batches(iso_summits)
iso_summits = iso_summits.sort_values('elevation', ascending=False)
iso_summits = iso_summits.reset_index(drop=True)

# Indices 342 and 13154544 returned clearly wrong elevations from the API on the
# first pass (verified manually). Re-fetch them individually to correct the values.
fix_big_bad_elevations(iso_summits, [342, 13154544])

ending_num_iso_summits = len(iso_summits)

print(f'\nSummits before clean-up: {starting_num_iso_summits}')
print(f'Summits after clean-up: {ending_num_iso_summits} ({starting_num_iso_summits-ending_num_iso_summits-1} removed, 1 added)')

num_iso_candidates = len(iso_summits.query('candidate == True'))
print(f'Number of Candidates: {num_iso_candidates} ({round(100*num_iso_candidates/ending_num_iso_summits, 3)}%)')

iso_summits.to_csv('../data/clean/summits_iso.csv', index_label='summit_id')

print('\n##################################################\n')

end_time = time.time()
total_time = round(end_time - start_time)

days = total_time // 86400
hours = (total_time % 86400) // 3600
minutes = (total_time % 3600) // 60
seconds = total_time % 60

print(f'\n{days}d {hours}h {minutes}m {seconds}s to clean all {starting_num_prm_summits+starting_num_iso_summits} summits!')
