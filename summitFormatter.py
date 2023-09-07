import numpy as np
import pandas as pd
import os
from pyproj import Geod

def horizonDistance(prm):
    return np.sqrt(2*earthRadius*prm)

def distanceBetweenPoints(lng1, lng2, lat1, lat2):
    return geod.line_length([lng1, lng2], [lat1, lat2])

def saveSummits(summitsToSave, file):
    summitsToSave = summitsToSave[['latitude', 'longitude', 'elevation', 'h_distance']]
    summitsToSave.to_csv(f'{cwd}/formattedSummits/{file}', header=False)
    print(f'{file} saved')
    
earthRadius = 6371146 # in m
geod = Geod(ellps='sphere') # ellipsoid is slower
cwd = os.getcwd()

summits = pd.read_csv('all-peaks-sorted-p100.txt', sep=",", header=None)
summits.columns = ['latitude', 'longitude', 'elevation', 'saddle_lat', 'saddle_lng', 'prominence']
summits = summits[['latitude', 'longitude', 'elevation', 'prominence']]
summits['h_distance'] = summits.prominence.apply(horizonDistance).round(1)
summits = summits.sort_values('elevation', ascending=False)

# all summits
saveSummits(summits, 'summits_all.txt')

# summits around North Pole
poleLat = 80
summitsTop = summits.query(f'latitude >= @poleLat')
saveSummits(summitsTop, 'summits_top.txt')

# summits around South Pole
summitsBtm = summits.query(f'latitude < -@poleLat')
saveSummits(summitsBtm, 'summits_btm.txt')

patchSize = 5 # 1, 2, 5, 10, or 20
maxLng = 180
lngBoundaries = np.arange(-maxLng, maxLng+patchSize, patchSize)
latBoundaries = np.arange(-poleLat, poleLat+patchSize, patchSize)

maxHorizon = summits.h_distance.max()
for i, lowerLng in enumerate(lngBoundaries[:-1]):
    upperLng = lngBoundaries[i+1]
    for j, lowerLat in enumerate(latBoundaries[:-1]):
        upperLat = latBoundaries[j+1]
        
        summitsPatch = summits.query('latitude >= @lowerLat and latitude < @upperLat ' 
                                     + 'and longitude >= @lowerLng and longitude < @upperLng')
        if len(summitsPatch) > 0:
            maxSummitDistance = summitsPatch.h_distance.max() + maxHorizon
        
            if lowerLat < 0:
                latForOverlap = lowerLat
            else:
                latForOverlap = upperLat

            lngOverlap = 0
            lngOverlapStep = 0.1
            overlapDistance = distanceBetweenPoints(0, lngOverlap, latForOverlap, latForOverlap)
            while overlapDistance < maxSummitDistance:
                lngOverlap += lngOverlapStep
                overlapDistance = distanceBetweenPoints(0, lngOverlap, latForOverlap, latForOverlap)
            
            latOverlap = 0
            latOverlapStep = 0.1
            overlapDistance = distanceBetweenPoints(0, 0, 0, latOverlap)
            while overlapDistance < maxSummitDistance:
                latOverlap += latOverlapStep
                overlapDistance = distanceBetweenPoints(0, 0, 0, latOverlap)

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
