import pandas as pd
import commons as me
import time
import os

startTime = time.time()

candidates = pd.read_csv(me.summitFile).query('candidate')

candidates['pinnacle'] = None

numCandidates = len(candidates)
for i, candidate in enumerate(candidates.itertuples()):

    print(f'Candidate: {i+1}/{numCandidates}\n')
    
    print(f'Location: {candidate.latitude}, {candidate.longitude}')
    print(f'Elevation: {candidate.elevation} m\n')

    observer = me.Summit(summitId = candidate.summitId,
                         latitude = candidate.latitude,
                         longitude = candidate.longitude,
                         elevation = candidate.elevation)
    
    candidateIsPinnaclePoint = observer.isPinnaclePoint()

    candidates.loc[candidate.Index, 'pinnacle'] = candidateIsPinnaclePoint
        
    print(f'\n{len(candidates.query('pinnacle == True'))} pinnacle points found so far\n')

    print('##################################################\n')

pinnaclePoints = candidates.query('pinnacle == True')[['summitId', 'latitude', 'longitude', 'elevation']]

pinnaclePoints.to_csv(me.pinnaclePointFile, index=False)

endTime = time.time()
totalTime = round(endTime - startTime)

days = totalTime // 86400
hours = (totalTime % 86400) // 3600
minutes = (totalTime % 3600) // 60
seconds = totalTime % 60

print(f'{len(pinnaclePoints)} pinnacle points found in {days}d {hours}h {minutes}m {seconds}s!')
