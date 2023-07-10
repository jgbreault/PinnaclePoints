import numpy as np
from pyproj import Geod
import os

def distanceBetweenPoints(p1, p2):
    return geod.line_length([p1[LNG], p2[LNG]], [p1[LAT], p2[LAT]])

def getChunkSummits(lat, lng):
    polarBoundary = 60
    if lat >= polarBoundary:
        return summitsTop
    elif lat <= -polarBoundary:
        return summitsBtm
    else:
        lngRangeMin = lng // 5 * 5 # round down to nearst multiple of 5
        return summitSlices[lngRangeMin]

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

summitSlices = {}
longitudeBoundaries = np.arange(-180, 185, 5)
for i, lower in enumerate(longitudeBoundaries[:-1]):
    upper = longitudeBoundaries[i+1]
    summitSlices[lower] = np.genfromtxt(f'{summitsDir}summits_{lower}_{upper}.txt', delimiter=',')    

checkpointFile = f'{cwd}/summits_checkpoint.txt'
if os.path.exists(checkpointFile):
    remainingSummits = np.genfromtxt(checkpointFile, delimiter=',')
else:
    remainingSummits = summitsAll
    
outputFile = 'summits_result.txt'
if os.path.exists(outputFile):
    foundTops = np.genfromtxt(f'{outputFile}', delimiter=',')
else:
    foundTops = []
    
numSummits = len(summitsAll)
    
while len(remainingSummits) > 0:
    newTopFound = False
    topCandidate = remainingSummits[0]    
    horizonDistance = topCandidate[HD]
    
    chunkSummits = getChunkSummits(topCandidate[LAT], topCandidate[LNG])
    
    distanceBetweenSummits = np.apply_along_axis(distanceBetweenPoints, 
                                                 axis=1, 
                                                 arr=chunkSummits, 
                                                 p2=topCandidate)
    
    indicesSeenFromCandidate = np.where(distanceBetweenSummits <= horizonDistance)[0]
    idsSeenFromCandidate = chunkSummits[indicesSeenFromCandidate][:,ID]
    remainingSummits = remainingSummits[~np.isin(remainingSummits[:,ID], idsSeenFromCandidate)]
    
    numSummitsRemaining = len(remainingSummits)
    higherIndicesThatCanSeeCandidate = np.where((chunkSummits[:,ELV] >= topCandidate[ELV]) 
                                                & (chunkSummits[:,HD] >= distanceBetweenSummits))[0]
    higherSummitsSeenFromCandidate = len(higherIndicesThatCanSeeCandidate)
    
    # the point sees itself, thus the "== 1"
    if ((len(indicesSeenFromCandidate) == 1 and len(higherIndicesThatCanSeeCandidate) == 1)
        or (higherSummitsSeenFromCandidate == 1
            and chunkSummits[indicesSeenFromCandidate[1:]][:,ELV].max() < topCandidate[ELV])):
        
        newTopFound = True
        
        if len(foundTops) == 0:
            foundTops.append(topCandidate)
        else:
            foundTops = np.concatenate((foundTops, [topCandidate]))
        
        numTopsFound = len(foundTops)
        if numTopsFound%20 == 0 or numSummitsRemaining == 0:
            np.savetxt(checkpointFile, remainingSummits, delimiter=',', fmt=dataFormat)
            np.savetxt(outputFile, foundTops, delimiter=',', fmt=dataFormat) 
            
    if numSummitsRemaining == 0:
        np.savetxt(checkpointFile, remainingSummits, delimiter=',', fmt=dataFormat)
        np.savetxt(outputFile, foundTops, delimiter=',', fmt=dataFormat)  
    
    if newTopFound:   
        print(f"TOTW count: {len(foundTops)}")
        print(f"Summits remaining: {numSummitsRemaining} ({round(100*(1 - (numSummitsRemaining/numSummits)), 4)}% complete)")
        print("\n")