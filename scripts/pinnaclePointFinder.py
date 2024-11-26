import numpy as np
import pandas as pd
import commonFunctions as func
import os
    
params = func.getParameters()
summitFile = params['candidate_file']
candidateFile = params['candidate_file']
hasIsolation = eval(params['has_isolation'])
patchDir = params['patch_directory']
patchSize = int(params['patch_size'])
poleLat = func.getPoleLatitude(patchSize)
isSingleGlobalPatch = eval(params['is_single_global_patch'])

ID  = func.ID
LAT = func.LAT
LNG = func.LNG
ELV = func.ELV
MHD = func.MHD

candidates = pd.read_csv(candidateFile)
candidates['MHD'] = candidates.elevation.apply(func.horizonDistance).round(1)

if hasIsolation:
    candidates = candidates[['id', 'latitude', 'longitude', 'elevation', 'MHD', 'isolation']]
else:
    candidates = candidates[['id', 'latitude', 'longitude', 'elevation', 'MHD']]
    
candidates = candidates.values

# Loading from checkpoint
checkpointFile = f'../dataSources/generatedDatasets/checkpoint.txt'
if os.path.exists(checkpointFile):
    remainingCandidates = np.genfromtxt(checkpointFile, delimiter=',')
else:
    remainingCandidates = candidates
    
outputFile = f'../dataSources/generatedDatasets/pinnaclePointsRaw.txt'
if os.path.exists(outputFile):
    foundPp = np.genfromtxt(outputFile, delimiter=',')
else:
    foundPp = []
    
if isSingleGlobalPatch:
    patchSummits = np.genfromtxt(summitFile, delimiter=',', skip_header=1)
    
# Finding pinnacle points in decending order or elevation
candidateNum = len(candidates)
remainingCandidateNum = len(remainingCandidates)
foundPpNum = len(foundPp)
while remainingCandidateNum > 0:
    
    candidate = remainingCandidates[0]
    print(f'Location: {candidate[LAT]}, {candidate[LNG]}')
    print(f'Elevation: {candidate[ELV]}')
    print(f'Candidates Remaining: {remainingCandidateNum} ({round(100*(1-(remainingCandidateNum/candidateNum)), 2)}% complete)')
    
    # Finding lower candidates that can be seen, for removal
    distanceBetweenCandidates = [func.geod.line_length([candidate2[LNG], candidate[LNG]], [candidate2[LAT], candidate[LAT]]) 
                                 for candidate2 in remainingCandidates]
    
    lowerIndicesToTest = np.where(distanceBetweenCandidates < remainingCandidates[:,MHD] + candidate[MHD])[0]
    lowerCandidatesToTest = remainingCandidates[lowerIndicesToTest]
            
    indicesToRemove = []
    for i, testCandidate in enumerate(lowerCandidatesToTest):
        
        # Filtering out self and other seen summits which would have a lower (or equal) elevation
        # Also removing summits within 20 km to prevent weird close points, hard to explain briefly but trust me
        removeCandidateCondition = (candidate[ID] == testCandidate[ID]
                                    or func.hasSight(candidate, testCandidate)
                                    or distanceBetweenCandidates[lowerIndicesToTest[i]] < 20000) # 20 km
        
        if removeCandidateCondition:
            indicesToRemove.append(testCandidate[ID])
                    
    remainingCandidates = remainingCandidates[~np.isin(remainingCandidates[:,ID], indicesToRemove)]
    remainingCandidateNum = len(remainingCandidates)
    print(f'Candidates Removed: {len(indicesToRemove)} out of {len(lowerIndicesToTest)} tested')
    
    if not isSingleGlobalPatch:
        patchSummits = func.getPatchSummits(candidate[LAT], candidate[LNG], patchDir, patchSize, poleLat)
    
    candidateIsPp = func.isPinnaclePoint(candidate, patchSummits, hasIsolation)
    
    if candidateIsPp == True:
        if foundPpNum == 0:
            foundPp.append(candidate)
        else:
            foundPp = np.concatenate((foundPp, [candidate]))
            
        foundPpNum = len(foundPp)
        
        # Saving checkpoint
        np.savetxt(checkpointFile, remainingCandidates, delimiter=',')
        np.savetxt(outputFile, foundPp, delimiter=',')
        print(f'CHECKPOINT SAVED ({len(foundPp)} pinnacle points found)')
        
    print('\n#############################\n')