import pandas as pd
import numpy as np
import commonFunctions as func

ID  = func.ID
LAT = func.LAT
LNG = func.LNG
ELV = func.ELV
MHD = func.MHD
ISO = func.ISO

params = func.getParameters()
summitFile = params['summit_file']
patchDir = params['patch_directory']
patchSize = int(params['patch_size'])
poleLat = func.getPoleLatitude(patchSize)

# Loading from checkpoint
checkpointFile = f'../dataSources/generatedDatasets/checkpoint.txt' # TODO: Change this
if os.path.exists(checkpointFile):
    remainingSummits = np.genfromtxt(checkpointFile, delimiter=',')
else:
    summits = pd.read_csv(summitFile)
    summits = summits.sort_value(by='prominence', ascending=False)
    summits['MHD'] = summits.elevation.apply(func.horizonDistance).round(1)
    summits = summits[['id', 'latitude', 'longitude', 'elevation', 'MHD']]
    summits = summits.values
    remainingSummits = summits
    
outputFile = f'../dataSources/generatedDatasets/longestLOS.txt' # TODO: Change this
if os.path.exists(outputFile):
    lineOfSights = np.genfromtxt(f'{outputFile}', delimiter=',')
else:
    lineOfSights = []

for i, observer in enumerate(remainingSummits):
    
    # May have to handle single summit patches
    
    patchSummits = func.getPatchSummits(observer[LAT], observer[LNG], patchDir, patchSize, poleLat)
    
    distanceBetweenSummits = [geod.line_length([patchSummit[LNG], observer[LNG]], [patchSummit[LAT], observer[LAT]])
                              for patchSummit in patchSummits]
    
    summitIndicesInRange = np.where(distanceBetweenSummits < patchSummits[:, MHD] + observer[MHD])[0]
                                    & (patchSummits[:, ID] != observer[ID])
        
    summitsInRange = patchSummits[summitIndicesInRange]
    
    # Sorting summitsInRange by distance descending
    inRangeSortOrder = np.flip(np.argsort([distanceBetweenSummits[i] for i in summitIndicesInRange]))
    distanceBetweenSummits = distanceBetweenSummits[inRangeSortOrder]
    summitsInRange = summitsInRange[inRangeSortOrder]
    
    for i, target in enumerate(summitsInRange):
        
        if func.hasSight(observer, target):
            # farthest LOS for this summit found!!!
            lineOfSights.append([observer[ID], observer[LAT], observer[LNG], observer[ELV],
                                 target[ID], target[LAT], target[LNG], target[ELV],
                                 distanceBetweenSummits[i]])
            
            # np.savetxt(checkpointFile, remainingSummits[i+1:], delimiter=',')
            # np.savetxt(outputFile, lineOfSights, delimiter=',')
            print(f'CHECKPOINT SAVED ({len(lineOfSights)} pinnacle points found)')

            break