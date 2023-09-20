import numpy as np
import pandas as pd
import commonFunctions as func

'''
Used to save patches
'''
def saveSummits(summitsToSave, file):
    summitsToSave = summitsToSave[['latitude', 'longitude', 'elevation', 'h_distance']]
    summitsToSave.to_csv(f'{func.cwd}/formattedSummits/{file}', header=False)
    print(f'{file} saved')
    
summits = pd.read_csv('dataSources/all-peaks-sorted-p100.txt', sep=",", header=None)
summits.columns = ['latitude', 'longitude', 'elevation', 'saddle_lat', 'saddle_lng', 'prominence']
summits = summits[['latitude', 'longitude', 'elevation', 'prominence']]
summits['h_distance'] = summits.elevation.apply(func.horizonDistance).round(1)
summits = summits.sort_values('elevation', ascending=False)

# summits around North Pole
summitsTop = summits.query(f'latitude >= {func.poleLat}')
saveSummits(summitsTop, 'summits_top.txt')

# summits around South Pole
summitsBtm = summits.query(f'latitude < {-func.poleLat}')
saveSummits(summitsBtm, 'summits_btm.txt')

# summits between poles
maxHorizon = summits.h_distance.max()
for i, lowerLng in enumerate(func.lngBoundaries[:-1]):
    upperLng = func.lngBoundaries[i+1]
    for j, lowerLat in enumerate(func.latBoundaries[:-1]):
        upperLat = func.latBoundaries[j+1]
        
        summitsPatch = summits.query('latitude >= @lowerLat and latitude < @upperLat ' 
                                     + 'and longitude >= @lowerLng and longitude < @upperLng')
        if len(summitsPatch) > 0:
            maxSummitDistance = summitsPatch.h_distance.max() + maxHorizon
        
            # adding overlap to account for summits being able to see beyond the patch
            if lowerLat < 0:
                latForOverlap = lowerLat
            else:
                latForOverlap = upperLat

            lngOverlap = 0
            lngOverlapStep = 0.1
            overlapDistance = func.distanceBetweenPoints(latForOverlap, latForOverlap, 0, lngOverlap)
            while overlapDistance < maxSummitDistance:
                lngOverlap += lngOverlapStep
                overlapDistance = func.distanceBetweenPoints(latForOverlap, latForOverlap, 0, lngOverlap)
            
            latOverlap = 0
            latOverlapStep = 0.1
            overlapDistance = func.distanceBetweenPoints(0, latOverlap, 0, 0)
            while overlapDistance < maxSummitDistance:
                latOverlap += latOverlapStep
                overlapDistance = func.distanceBetweenPoints(0, latOverlap, 0, 0)

            # the logic is to account for crossing the 180 lng line
            if lowerLng - lngOverlap < -180:
                lowerLngWithOverlap = 360 + lowerLng - lngOverlap
            else:
                lowerLngWithOverlap = lowerLng - lngOverlap

            if upperLng + lngOverlap > 180:
                upperLngWithOverlap = -360 + upperLng + lngOverlap 
            else:
                upperLngWithOverlap = upperLng + lngOverlap
                
            lowerLatWithOverlap = lowerLat - latOverlap
            upperLatWithOverlap = upperLat + latOverlap

            if lowerLngWithOverlap > 0 and upperLngWithOverlap < 0:
                summitsPatchOverlap = summits.query('latitude >= @lowerLatWithOverlap and latitude <= @upperLatWithOverlap ' 
                                                    + 'and (longitude >= @lowerLngWithOverlap or longitude <= @upperLngWithOverlap)')
            else:
                summitsPatchOverlap = summits.query('latitude >= @lowerLatWithOverlap and latitude <= @upperLatWithOverlap ' 
                                                    + 'and longitude >= @lowerLngWithOverlap and longitude <= @upperLngWithOverlap')
                        
            if len(summitsPatch) != 0:
                fileName = f'summits_{lowerLat}_{upperLat}_{lowerLng}_{upperLng}.txt'
                saveSummits(summitsPatchOverlap, fileName)
