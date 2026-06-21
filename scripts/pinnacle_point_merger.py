import pandas as pd

prm = pd.read_csv('../data/results/pinnacle_points/prm/pinnacle_points.csv')
iso = pd.read_csv('../data/results/pinnacle_points/iso/pinnacle_points.csv')

iso['summit_id'] = -iso.summit_id
pinnacle_points = pd.concat([prm, iso])
pinnacle_points['candidate'] = True

pinnacle_points = (pinnacle_points.sort_values(by=['latitude', 'longitude', 'elevation'], ascending=[True, True, False])
                  .drop_duplicates(subset=['latitude', 'longitude'], keep='first')
                  .reset_index(drop=True))

pinnacle_points = pinnacle_points.sort_values('elevation', ascending=False)

pinnacle_points.to_csv('../data/results/pinnacle_points/prm_iso/pinnacle_points_merged.csv', index=False)