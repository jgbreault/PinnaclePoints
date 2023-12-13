import numpy as np
import pandas as pd
import commonFunctions as func
import requests
import math
import os

'''
Saves a snapshot of the progress so the program can stop and start from where you left off.
'''
def saveCheckpoint():
    np.savetxt(checkpointFile, remainingOtotw, delimiter=',', fmt=dataFormat)
    np.savetxt(outputFile, foundPp, delimiter=',', fmt=dataFormat)
    print('\n')
    print('CHECKPOINT SAVED')

ID  = func.ID
LAT = func.LAT
LNG = func.LNG
ELV = func.ELV
HD  = func.HD

dataFormat = '%d, %.4f, %.4f, %.2f, %.2f'
lineBreak = '\n#############################\n'

ototw = pd.read_csv('../dataSources/ototw_p300m.csv')
ototw = ototw[['latitude', 'longitude', 'elevation_m']].sort_values(by='elevation_m', ascending=False)
ototw = ototw.rename(columns={'elevation_m': 'elevation'})
ototw['horizonDist'] = ototw.elevation.apply(func.horizonDistance).round(2)
ototw = ototw.reset_index()
ototw = ototw.drop(columns='index')
ototw = ototw.reset_index()
ototw = ototw.values

summitPatches = func.getSummitPatches()

# loading from checkpoint
checkpointFile = f'{func.summitsDir}summits_checkpoint.txt'
if os.path.exists(checkpointFile):
    remainingOtotw = np.genfromtxt(checkpointFile, delimiter=',')
else:
    remainingOtotw = ototw
    
outputFile = f'{func.summitsDir}pinnaclePoints_raw.txt'
if os.path.exists(outputFile):
    foundPp = np.genfromtxt(f'{outputFile}', delimiter=',')
else:
    foundPp = []

print(lineBreak)
    
# finding pinnacle points in decending order or elevation
ototwNum = len(ototw)
remainingOtotwNum = len(remainingOtotw)
foundPpNum = len(foundPp)
while remainingOtotwNum > 0:
    
    ppCandidate = remainingOtotw[0]
    print(f'Location: {ppCandidate[LAT]}, {ppCandidate[LNG]}')
    print(f'Elevation: {ppCandidate[ELV]}')
    print(f'OTOTW Remaining: {remainingOtotwNum} ({round(100*(1-(remainingOtotwNum/ototwNum)), 2)}% complete)')
    print(f'\n')
    
    distanceBetweenOtotw = [func.geod.line_length([ototw[LNG], 
                                                   ppCandidate[LNG]], 
                                                  [ototw[LAT], 
                                                   ppCandidate[LAT]])
                            for ototw in remainingOtotw]
    
    mayseenIndices = np.where(distanceBetweenOtotw < remainingOtotw[:,HD] + ppCandidate[HD])[0]
    mayseenOtotw = remainingOtotw[mayseenIndices]
            
    # bulk OTOTW point removal
    ototwIndicesToRemove = []
    for ototwPoint in mayseenOtotw:
        # filtering out self and seen OTOTW
        if ototwPoint[ID] == ppCandidate[ID] or func.hasSight(ppCandidate, ototwPoint) == True:
            ototwIndicesToRemove.append(ototwPoint[ID])
                
    print(f'OTOTW Removed: {len(ototwIndicesToRemove)}/{len(mayseenOtotw)}')
    
    remainingOtotw = remainingOtotw[~np.isin(remainingOtotw[:,ID], ototwIndicesToRemove)]
    remainingOtotwNum = len(remainingOtotw)
    
    patchSummits = func.getPatchSummits(ppCandidate[LAT], ppCandidate[LNG], summitPatches)
    
    candidateIsPp = func.isPinnaclePoint(ppCandidate, patchSummits)
    
    if candidateIsPp == True:
        if foundPpNum == 0:
            foundPp.append(ppCandidate)
        else:
            foundPp = np.concatenate((foundPp, [ppCandidate]))
            
        foundPpNum = len(foundPp)
        saveCheckpoint()
        
    print(lineBreak)