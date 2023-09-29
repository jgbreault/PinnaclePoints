import numpy as np
import pandas as pd
import commonFunctions as func
import requests
import math
import os
    
'''
Determines if 2 points have direct line of sight.
'''
def hasDirectLos(p1, p2):
    dists, elvs = func.getLosData(p1[LAT], p1[LNG], p1[ELV], p2[LAT], p2[LNG], p2[ELV])

    # removing ends since they could be slightly above 0 after the translation/rotation
    if max(elvs[1:-1]) > 0:
        return False
    return True

'''
Gets the summits in the patch associated with a point.
'''
def getPatchSummits(lat, lng):
    if lat >= func.poleLat:
        return summitsTop
    elif lat < -func.poleLat:
        return summitsBtm
    else:
        latRangeMin = int(lat // func.patchSize * func.patchSize) # round down to nearst multiple of patchSize
        lngRangeMin = int(lng // func.patchSize * func.patchSize) # round down to nearst multiple of patchSize
        return summitPatches[f'{latRangeMin}_{latRangeMin + func.patchSize}_{lngRangeMin}_{lngRangeMin + func.patchSize}']

'''
Saves a snapshot of the progress so the program can stop and start from where you left off.
'''
def saveCheckpoint():
    np.savetxt(checkpointFile, remainingOtotw, delimiter=',', fmt=dataFormat)
    np.savetxt(outputFile, foundPp, delimiter=',', fmt=dataFormat)
    print('\n')
    print('CHECKPOINT SAVED')

ID  = 0 # ID (ordered by elevation)
LAT = 1 # latitude
LNG = 2 # longitude
ELV = 3 # elevation
HD  = 4 # max horizon distance

summitsDir = 'formattedSummits/'
dataFormat = '%d, %.4f, %.4f, %.2f, %.2f'

ototw = pd.read_csv('dataSources/ototw_p300m.csv')
ototw = ototw[['latitude', 'longitude', 'elevation_m']].sort_values(by='elevation_m', ascending=False)
ototw = ototw.rename(columns={'elevation_m': 'elevation'})
ototw['horizonDist'] = ototw.elevation.apply(func.horizonDistance).round(2)
ototw = ototw.reset_index()
ototw = ototw.drop(columns='index')
ototw = ototw.reset_index()
ototw = ototw.values

# getting patch data
summitsTop = np.genfromtxt(f'{summitsDir}summits_top.txt', delimiter=',')
summitsBtm = np.genfromtxt(f'{summitsDir}summits_btm.txt', delimiter=',')
summitPatches = {}
for i, lowerLng in enumerate(func.lngBoundaries[:-1]):
    upperLng = func.lngBoundaries[i+1]
    for j, lowerLat in enumerate(func.latBoundaries[:-1]):
        upperLat = func.latBoundaries[j+1]
        
        patchPath = f'{summitsDir}summits_{lowerLat}_{upperLat}_{lowerLng}_{upperLng}.txt'
        if os.path.exists(patchPath):
            summitPatches[f'{lowerLat}_{upperLat}_{lowerLng}_{upperLng}'] = np.genfromtxt(patchPath, delimiter=',')    

# loading from checkpoint
checkpointFile = f'{summitsDir}summits_checkpoint.txt'
if os.path.exists(checkpointFile):
    remainingOtotw = np.genfromtxt(checkpointFile, delimiter=',')
else:
    remainingOtotw = ototw
    
outputFile = f'{summitsDir}pinnaclePoints_raw.txt'
if os.path.exists(outputFile):
    foundPp = np.genfromtxt(f'{outputFile}', delimiter=',')
else:
    foundPp = []
    
# finding pinnacle points in decending order or elevation
ototwNum = len(ototw)
remainingOtotwNum = len(remainingOtotw)
foundPpNum = len(foundPp)
while remainingOtotwNum > 0:
    
    ppCandidate = remainingOtotw[0]
    print(f'Location: {ppCandidate[LAT]}, {ppCandidate[LNG]}')
    print(f'Elevation: {ppCandidate[ELV]}')
    print(f'OTOTW Remaining: {remainingOtotwNum} ({round(100*(1 - (remainingOtotwNum/ototwNum)), 2)}% complete)')
    print(f'\n')
    
    distanceBetweenOtotw = [func.distanceBetweenPoints(row[LAT],
                                                       ppCandidate[LAT],
                                                       row[LNG],
                                                       ppCandidate[LNG])
                            for row in remainingOtotw]
    
    mayseenIndices = np.where(distanceBetweenOtotw < remainingOtotw[:,HD] + ppCandidate[HD])[0]
    mayseenOtotw = remainingOtotw[mayseenIndices]
            
    # Bulk OTOTW point removal
    ototwIndicesToRemove = []
    for ototwPoint in mayseenOtotw:
        if ototwPoint[ID] == ppCandidate[ID]:
            ototwIndicesToRemove.append(ototwPoint[ID])
        else:
            if hasDirectLos(ppCandidate, ototwPoint) == True:
                ototwIndicesToRemove.append(ototwPoint[ID])
                
    print(f'OTOTW Removed: {len(ototwIndicesToRemove)}/{len(mayseenOtotw)}')
    
    remainingOtotw = remainingOtotw[~np.isin(remainingOtotw[:,ID], ototwIndicesToRemove)]
    remainingOtotwNum = len(remainingOtotw)
    patchSummits = getPatchSummits(ppCandidate[LAT], ppCandidate[LNG])
    
    if patchSummits.ndim == 1:
        # this is for patches holding a single summit
        mayseenHigherSummits = []
    else:
        distanceBetweenSummits = [func.distanceBetweenPoints(row[LAT],
                                                             ppCandidate[LAT],
                                                             row[LNG],
                                                             ppCandidate[LNG]) 
                                  for row in patchSummits]      
        
        # TODO: get self in a better way than "+ 0.1" to elevation
        mayseenHigherIndices = np.where((distanceBetweenSummits < patchSummits[:, HD] + ppCandidate[HD]) 
                                        & (patchSummits[:, ELV] > ppCandidate[ELV] + 0.1))[0]
        mayseenHigherSummits = patchSummits[mayseenHigherIndices]
        
        # sorting mayseenHigherSummits by distance to ppCandidate
        distanceBetweenSummits = [distanceBetweenSummits[i] for i in mayseenHigherIndices]
        mayseenHigherSummits = mayseenHigherSummits[np.argsort(distanceBetweenSummits)]

    print(f'Summits to Test: {len(mayseenHigherSummits)}')
      
    candidateIsPp = True
    for i, summit in enumerate(mayseenHigherSummits):
        if hasDirectLos(ppCandidate, summit):
            candidateIsPp = False
            print(f'Not a Pinnacle Point ({i+1} tested)...')
            break
    
    if candidateIsPp == True:
        if foundPpNum == 0:
            foundPp.append(ppCandidate)
        else:
            foundPp = np.concatenate((foundPp, [ppCandidate]))
            
        foundPpNum = len(foundPp)
        print(f'PINNACLE POINT {foundPpNum} FOUND!!!')
            
        if foundPpNum%4 == 0:
            saveCheckpoint()
    
    if remainingOtotwNum == 0:
        saveCheckpoint()
        
    print('\n#############################\n')