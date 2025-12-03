import pandas as pd
import commons as me
import time

def getMinObserverElevation():
    maxElevation = summits.elevation.max()
    maxObserverMhd = me.horizonDistance(maxElevation)
    return 1/(2*me.earthRadius) * (me.defaultLightCurvature-1)/(me.defaultLightCurvature) * (distanceThreshold - maxObserverMhd)**2

def getMinTargetElevation():
    return (me.defaultLightCurvature-1)/(me.defaultLightCurvature) * (distanceThreshold)**2/(8*me.earthRadius)

startTime = time.time()

summitFile = f'../data/clean/summits_prm.csv'
prominenceThreshold = 500 # in m
distanceThreshold = 300*1000 # in m

summits = pd.read_csv(summitFile)
numGlobalSummits = len(summits)

minObserverElevation = getMinObserverElevation()
minTargetElevation = getMinTargetElevation()

summits = summits.query('prominence > @prominenceThreshold')
observers = summits.query('elevation > @minObserverElevation')
targets = summits.query('elevation > @minTargetElevation')

numSummits = len(summits)
numObervers = len(observers)
numTarget = len(targets)

print(f'{numSummits}/{numGlobalSummits} ({round(100*numSummits/numGlobalSummits, 2)}%) summits have at least {prominenceThreshold} m of prominence')
print(f'{numObervers}/{numSummits} ({round(100*numObervers/numSummits, 2)}%) are beyond the minimum observer elevation ({round(minObserverElevation)} m)')
print(f'{numTarget}/{numSummits} ({round(100*numTarget/numSummits, 2)}%) are beyond the minimum target elevation ({round(minTargetElevation)} m)')
print('\n')

candidateLinesOfSight = []
for i, observer in enumerate(observers.itertuples()):

    targetsForObserver = targets.query('summitId < @observer.summitId')
    for target in targetsForObserver.itertuples():

        obs = me.Summit(summitId = observer.summitId,
                        latitude = observer.latitude, 
                        longitude = observer.longitude, 
                        elevation = observer.elevation)
        
        trg = me.Summit(summitId = target.summitId,
                        latitude = target.latitude, 
                        longitude = target.longitude, 
                        elevation = target.elevation)

        candidateLos = me.LineOfSight(obs, trg)

        if candidateLos.isInPossibleRange() and candidateLos.surfaceDistance > distanceThreshold:
            candidateLinesOfSight.append(candidateLos)

    if i%1000 == 999 or i == numObervers-1:
        numLosCandidates = len(candidateLinesOfSight)
        print(f'Found {numLosCandidates} line of sight candidates in {i+1}/{numObervers} observers')

print('\n')

losPassedMidTest = []
for start in range(0, len(candidateLinesOfSight), me.apiRequestLimit):
    
    losBatch = candidateLinesOfSight[start:start + me.apiRequestLimit]

    observerLats = [los.observer.latitude for los in losBatch]
    observerLngs = [los.observer.longitude for los in losBatch]
    
    targetLats = [los.target.latitude for los in losBatch]
    targetLngs = [los.target.longitude for los in losBatch]

    midLats = []
    midLngs = []
    midLightElevations = []
    
    for los in losBatch:
        
        observerLat = los.observer.latitude
        observerLng = los.observer.longitude
        
        targetLat = los.target.latitude
        targetLng = los.target.longitude

        midPoint = me.geod.npts(observerLng, observerLat, targetLng, targetLat, 1)[0]

        midLats.append(midPoint[1])
        midLngs.append(midPoint[0])

        midLightElevations.append(los.getLightElevation(los.surfaceDistance/2))

    midElevations = me.getElevations(midLats, midLngs)

    for i, los in enumerate(losBatch):

        midLightElevation = midLightElevations[i]
        midElevation = midElevations[i]
        
        if midLightElevation > midElevation:
            losPassedMidTest.append(los)

numLosPassedMidTest = len(losPassedMidTest)
print(f'{numLosPassedMidTest}/{numLosCandidates} ({round(100*numLosPassedMidTest/numLosCandidates, 2)}%) ' + 
      'line of sight candidates passed the mid-point test')
print('\n')

validLinesOfSight = []
for i, los in enumerate(losPassedMidTest):
    
    los.processFullLineOfSight()

    losIsValid = los.isValid()
    los.losPoints = []
    
    if losIsValid:
        validLinesOfSight.append(los)

    if i%1000 == 999 or i == numLosPassedMidTest-1:
        print(f'Found {len(validLinesOfSight)} valid lines of sight in {i+1}/{numLosPassedMidTest} candidates')

print('\n')

observerSummitIds = []
observerLatitudes = []
observerLongitudes = []
observerElevations = []

targetSummitIds = []
targetLatitudes = []
targetLongitudes = []
targetElevations = []

surfaceDistances = []
contrasts = []

for los in validLinesOfSight:
    
    observerSummitIds.append(los.observer.summitId)
    observerLatitudes.append(los.observer.latitude)
    observerLongitudes.append(los.observer.longitude)
    observerElevations.append(los.observer.elevation)
    
    targetSummitIds.append(los.target.summitId)
    targetLatitudes.append(los.target.latitude)
    targetLongitudes.append(los.target.longitude)
    targetElevations.append(los.target.elevation)
    
    surfaceDistances.append(los.surfaceDistance)
    contrasts.append(los.getContrast())

losData = pd.DataFrame({
    'observer_summitId': observerSummitIds,
    'observer_latitude': observerLatitudes,
    'observer_longitude': observerLongitudes,
    'observer_elevation': observerElevations,
    'target_summitId': targetSummitIds,
    'target_latitude': targetLatitudes,
    'target_longitude': targetLongitudes,
    'target_elevation': targetElevations,
    'distance': surfaceDistances,
    'contrast': contrasts
})

maxLosData = losData.loc[losData.groupby('observer_summitId')['distance'].idxmax()]

losData['distance'] = losData.distance.astype(int)
losData['contrast'] = losData.contrast.round(4)

maxLosData['distance'] = maxLosData.distance.astype(int)
maxLosData['contrast'] = maxLosData.contrast.round(4)

losData.to_csv('../data/results/longest_los/longest_los.csv', index=False)
maxLosData.to_csv('../data/results/longest_los/longest_los_max.csv', index=False)

endTime = time.time()
totalTime = round(endTime - startTime)

days = totalTime // 86400
hours = (totalTime % 86400) // 3600
minutes = (totalTime % 3600) // 60
seconds = totalTime % 60

print(f'Run Time: {days}d {hours}h {minutes}m {seconds}s')