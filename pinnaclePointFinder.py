import numpy as np
from pyproj import Geod
import os

def distanceBetweenPoints(p1, p2):
    return geod.line_length([p1[LNG], p2[LNG]], [p1[LAT], p2[LAT]])

def getPatchSummits(lat, lng, patchSize):
    if lat >= poleLat:
        return summitsTop
    elif lat < -poleLat:
        return summitsBtm
    else:
        latRangeMin = int(lat // patchSize * patchSize) # round down to nearst multiple of patchSize
        lngRangeMin = int(lng // patchSize * patchSize) # round down to nearst multiple of patchSize
        return summitPatches[f'{latRangeMin}_{latRangeMin + patchSize}_{lngRangeMin}_{lngRangeMin + patchSize}']
    
def saveCheckpoint():
    np.savetxt(checkpointFile, remainingSummits, delimiter=',', fmt=dataFormat)
    np.savetxt(outputFile, foundTops, delimiter=',', fmt=dataFormat)
    print('CHECKPOINT SAVED')
    print('\n')
    
poleLat = 80
patchSize = 5
maxLng = 180
lngBoundaries = np.arange(-maxLng, maxLng+patchSize, patchSize)
latBoundaries = np.arange(-poleLat, poleLat+patchSize, patchSize)

ID  = 0 # ID (ordered by elevation)
LAT = 1 # latitude
LNG = 2 # longitude
ELV = 3 # elevation
HD  = 4 # horizon distance

cwd = os.getcwd()
summitsDir = f'{cwd}/formattedSummits/'
geod = Geod(ellps='sphere') # ellipsoid is slower
dataFormat = '%d, %.4f, %.4f, %.1f, %.1f'

summitsAll = np.genfromtxt(f'{summitsDir}summits_all.txt', delimiter=',')
summitsTop = np.genfromtxt(f'{summitsDir}summits_top.txt', delimiter=',')
summitsBtm = np.genfromtxt(f'{summitsDir}summits_btm.txt', delimiter=',')
summitPatches = {}
for i, lowerLng in enumerate(lngBoundaries[:-1]):
    upperLng = lngBoundaries[i+1]
    for j, lowerLat in enumerate(latBoundaries[:-1]):
        upperLat = latBoundaries[j+1]
        
        patchPath = f'{summitsDir}summits_{lowerLat}_{upperLat}_{lowerLng}_{upperLng}.txt'
        if os.path.exists(patchPath):
            summitPatches[f'{lowerLat}_{upperLat}_{lowerLng}_{upperLng}'] = np.genfromtxt(patchPath, delimiter=',')    

checkpointFile = f'{summitsDir}summits_checkpoint.txt'
if os.path.exists(checkpointFile):
    remainingSummits = np.genfromtxt(checkpointFile, delimiter=',')
else:
    remainingSummits = summitsAll
    
outputFile = f'{summitsDir}summits_result.txt'
if os.path.exists(outputFile):
    foundTops = np.genfromtxt(f'{outputFile}', delimiter=',')
else:
    foundTops = []
    
numSummits = len(summitsAll)
    
while len(remainingSummits) > 0:
    topCandidate = remainingSummits[0]   
    topCandidateElv = topCandidate[ELV]
    
    patchSummits = getPatchSummits(topCandidate[LAT], topCandidate[LNG], patchSize)
    
    if patchSummits.ndim == 1:
        remainingSummits = remainingSummits[~np.isin(remainingSummits[:,ID], patchSummits[ID])]
        higherSeenSummits = np.where(patchSummits[ELV] >= topCandidateElv)[0]
    else:
        distanceBetweenSummits = np.apply_along_axis(distanceBetweenPoints, axis=1, arr=patchSummits, p2=topCandidate)
        seenIndices = np.where(distanceBetweenSummits <= patchSummits[:,HD] + topCandidate[HD])[0]
        seenSummits = patchSummits[seenIndices]
        remainingSummits = remainingSummits[~np.isin(remainingSummits[:,ID], seenSummits[:,ID])]
        higherSeenSummits = np.where(seenSummits[:,ELV] >= topCandidateElv)[0]
        
    numHigherSeenSummits = len(higherSeenSummits) - 1 # subtracting 1 to account for self
    numSummitsRemaining = len(remainingSummits)    
    if numHigherSeenSummits == 0:        
        if len(foundTops) == 0:
            foundTops.append(topCandidate)
        else:
            foundTops = np.concatenate((foundTops, [topCandidate]))
        
        numTopsFound = len(foundTops)            
        print(f'Pinnacle Points Found: {numTopsFound}')
        print(f'Summits Remaining: {numSummitsRemaining} ({round(100*(1 - (numSummitsRemaining/numSummits)), 5)}% complete)')
        print('\n')
        
        if numTopsFound%20 == 0:
            saveCheckpoint()
            
    if numSummitsRemaining == 0:
        saveCheckpoint()