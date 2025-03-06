import commonFunctions as func
import os
import pandas as pd
import math
import numpy as np

minProminence = 1000 # in m TODO: put this in parameters

def saveCheckpoint(remainingObservers, foundLinesOfSight):
    remainingObservers = pd.DataFrame([obj.__dict__ for obj in remainingObservers])
    remainingObservers.to_csv(checkpointFile, sep=',', index=False, header=True)
    foundLinesOfSight.to_csv(outputFile, sep=',', index=False, header=True)
    print('*** CHECKPOINT SAVED ***')

params = func.getParameters()
summitFile = params['summit_file']

# Loading from checkpoint
checkpointFile = f'../dataSources/generatedDatasets/checkpoint.txt'
if os.path.exists(checkpointFile):
    summits = pd.read_csv(checkpointFile)
else:
    summits = pd.read_csv(summitFile)
    summits = summits.query('prominence > @minProminence')
    summits = summits.sort_values('elevation', ascending=False)

summits = summits.apply(lambda s: func.Summit(
    s.latitude, s.longitude, s.elevation, id=s.id, prominence=s.prominence), axis=1).tolist() # Get rid of Id, prominence?
        
outputFile = f'../dataSources/generatedDatasets/longestLOS.txt'
if os.path.exists(outputFile):
    linesOfSight = pd.read_csv(outputFile)
else:
    linesOfSight = pd.DataFrame(columns=['latitude_O', 'longitude_O', 'elevation_O', 'prominence_O', 
                                         'latitude_T', 'longitude_T', 'elevation_T', 'prominence_T', 
                                         'distance'])

# Find longest LOS longer than losDistanceCutOff for each summit
for observerId, observer in enumerate(summits):
    
    # Find targets where LOS is yet to be tested (lower elevation summits)
    candidateTargets = summits[observerId+1:]
    
    print(f'\n##### {len(candidateTargets)} Summits Left #####\n')
        
    # Define initial list of new LOS candidates
    losCandidates = [func.LineOfSight(observer, target, numPoints=1, skipProcessing=True) for target in candidateTargets]
                 
    # Find LOS candidates that could be seen if all land was at sea level
    losCandidates = [los for los in losCandidates if los.passesMaxHorizonDistanceTest()]
    
    print(f'LOS candidates after distance cuts: {len(losCandidates)}')

    # Sort LOS candidates by distance (farthest first)
    losCandidates = sorted(losCandidates, key=lambda point: point.surfaceDistance, reverse=True) # Not actually needed
            
    # Process in batches of apiLimit
    numCandidatesTested = 0
    numLosCandidateBatches = int(math.ceil(len(losCandidates)/func.apiLimit))
    for batchId in range(numLosCandidateBatches):
        losCandidateBatchMidLats = []
        losCandidateBatchMidLngs = []
        losCandidateBatch = losCandidates[batchId*func.apiLimit:(batchId+1)*func.apiLimit]
        
        # Find latitudes and longitudes for midpoints
        for losCandidate in losCandidateBatch:
            latitudeAsList, longitudeAsList = losCandidate.getLatitudesAndLongitudes()
            losCandidateBatchMidLats.append(latitudeAsList[0])
            losCandidateBatchMidLngs.append(longitudeAsList[0])
        
        # Find elevations for midpoints
        losCandidateBatchMidElvs = func.getElevation(','.join(map(str, losCandidateBatchMidLats)), 
                                                     ','.join(map(str, losCandidateBatchMidLngs)))
        
        losCandidate = None
        for losCandidateBatchId in range(len(losCandidateBatch)):
            
            numCandidatesTested += 1
            
            losCandidate = func.LineOfSight(observer, 
                                       losCandidateBatch[losCandidateBatchId].target, 
                                       losPoints = [func.LosPoint(losCandidateBatchMidLats[losCandidateBatchId],
                                                                  losCandidateBatchMidLngs[losCandidateBatchId],
                                                                  losCandidateBatchMidElvs[losCandidateBatchId])])

            # Check if LOS is blocked by midpoint
            if losCandidate.passesLineOfSightTest():
                
                losCandidate = func.LineOfSight(observer, losCandidate.target, numPoints=func.apiLimit)
                
                # Check if LOS is blocked when numPoints=apiLimit
                if losCandidate.passesLineOfSightTest():
                    
                    losCandidate = func.LineOfSight(observer, losCandidate.target, sampleDist=1) # Is 0.1 doable?
                    
                    # Check if LOS is blocked when sampleDist=0.1km
                    if losCandidate.passesLineOfSightTest():
                        
                        print(f'LOS FOUND after testing {numCandidatesTested} candidates, ' + 
                              f'{round(losCandidate.surfaceDistance/1000)} km long!!!')

                        linesOfSight.loc[len(linesOfSight)] = [losCandidate.observer.latitude,
                                                               losCandidate.observer.longitude,
                                                               losCandidate.observer.elevation,
                                                               losCandidate.observer.prominence,
                                                               losCandidate.target.latitude,
                                                               losCandidate.target.longitude,
                                                               losCandidate.target.elevation,
                                                               losCandidate.target.prominence,
                                                               losCandidate.surfaceDistance]
    
    saveCheckpoint(candidateTargets, linesOfSight)