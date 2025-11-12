import pandas as pd

prm = pd.read_csv('../data/results/pinnacle_points/prm/pinnacle_points.csv')
iso = pd.read_csv('../data/results/pinnacle_points/iso/pinnacle_points.csv')

iso['summitId'] = -iso.summitId
pinnaclePoints = pd.concat([prm, iso])
pinnaclePoints['candidate'] = True

pinnaclePoints = (pinnaclePoints.sort_values(by=['latitude', 'longitude', 'elevation'], ascending=[True, True, False])
                  .drop_duplicates(subset=['latitude', 'longitude'], keep='first')
                  .reset_index(drop=True))

pinnaclePoints = pinnaclePoints.sort_values('elevation', ascending=False)

pinnaclePoints.to_csv('../data/results/pinnacle_points/prm_iso/pinnacle_points_merged.csv', index=False)