"""
Merges the prominence-based and isolation-based pinnacle point results into one CSV.

The two pipelines (summits_prm.csv and summits_iso.csv) are run separately and may
find the same physical summit under slightly different coordinates. Isolation summit
IDs are negated to avoid collisions with prominence summit IDs in the merged file.
Duplicates are resolved by (latitude, longitude): when two rows share the same
coordinates, the one with the higher elevation is kept (sort descending before dedup).
"""

import pandas as pd

prm = pd.read_csv('../data/results/pinnacle_points/prm/pinnacle_points.csv')
iso = pd.read_csv('../data/results/pinnacle_points/iso/pinnacle_points.csv')

# Negate isolation IDs so they don't collide with prominence IDs in the merged file.
iso['summit_id'] = -iso.summit_id

pinnacle_points = pd.concat([prm, iso])
pinnacle_points['candidate'] = True

# When the same physical summit appears in both datasets, keep the row with the higher
# elevation (sort descending first so drop_duplicates keeps='first' gets the best one).
pinnacle_points = (pinnacle_points
                   .sort_values(by=['latitude', 'longitude', 'elevation'], ascending=[True, True, False])
                   .drop_duplicates(subset=['latitude', 'longitude'], keep='first')
                   .reset_index(drop=True))

pinnacle_points = pinnacle_points.sort_values('elevation', ascending=False)

pinnacle_points.to_csv('../data/results/pinnacle_points/prm_iso/pinnacle_points_merged.csv', index=False)