import pandas as pd
import commons as me
import time

start_time = time.time()

candidates = pd.read_csv(me.summit_file).query('candidate').copy()

candidates['pinnacle'] = None

num_candidates = len(candidates)
for i, candidate in enumerate(candidates.itertuples()):

    print(f'Candidate: {i+1}/{num_candidates}\n')
    
    print(f'Location: {candidate.latitude}, {candidate.longitude}')
    print(f'Elevation: {candidate.elevation} m\n')

    observer = me.Summit(summit_id = candidate.summit_id,
                         latitude = candidate.latitude,
                         longitude = candidate.longitude,
                         elevation = candidate.elevation)
    
    candidate_is_pinnacle_point = observer.is_pinnacle_point()

    candidates.loc[candidate.Index, 'pinnacle'] = candidate_is_pinnacle_point

    num_pinnacle_points_so_far = len(candidates.query('pinnacle == True'))
    print(f'\n{num_pinnacle_points_so_far} pinnacle points found so far\n')

    print('##################################################\n')

pinnacle_points = candidates.query('pinnacle == True')[['summit_id', 'latitude', 'longitude', 'elevation']]

pinnacle_points.to_csv(me.pinnacle_point_file, index=False)

end_time = time.time()
total_time = round(end_time - start_time)

days = total_time // 86400
hours = (total_time % 86400) // 3600
minutes = (total_time % 3600) // 60
seconds = total_time % 60

print(f'{len(pinnacle_points)} pinnacle points found in {days}d {hours}h {minutes}m {seconds}s!')
