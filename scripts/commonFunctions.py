import numpy as np
import pandas as pd
from pyproj import Geod
import requests
import math
from time import sleep
import matplotlib.pyplot as plt
import os

earthRadius = 6371146 # in m
geod = Geod(ellps='sphere')
summitsDir = '../formattedSummits/'
northPole = 'northPole'
southPole = 'southPole'

poleLat = 80
patchSize = 10
maxLng = 180
lngBoundaries = np.arange(-maxLng, maxLng+patchSize, patchSize)
latBoundaries = np.arange(-poleLat, poleLat+patchSize, patchSize)

ID  = 0 # ID (ordered by elevation)
LAT = 1 # latitude
LNG = 2 # longitude
ELV = 3 # elevation
HD  = 4 # max horizon distance

'''
Plotting distance vs elevation from persepctive of the direct line of sight.
'''
def plotLosElevationProfile(lat1, lng1, elv1, 
                            lat2, lng2, elv2, 
                            savePlot=False, 
                            plotTitle='', 
                            printInfo=True,
                            xLabel=''):
    
    dists, elvs = getLosData(lat1, lng1, elv1, lat2, lng2, elv2)

    lightPath = getLightPath(dists)
    
    dists = dists/1000 # m to km
    
    if printInfo == True:
        
        if (elvs[1:-1] > lightPath[1:-1]).any():
            print('Light Path: No')
        else:
            print('Light Path: Yes')

        if max(elvs[1:-1]) > 0:
            print('Direct Line of Sight: No')
        else:
            print('Direct Line of Sight: Yes')

        print(f'Distance: {round(dists[-1])} km')
        
    hasLineOfSight = np.all(lightPath[1:-1]>elvs[1:-1])
    landBlocking = ''
    if hasLineOfSight:
        landBlocking = ' (none)'        
    
    plt.figure(figsize=(10,4))
    plt.plot(dists, elvs, color='k')
    plt.plot(dists, lightPath, color='orange', 
             label='Path of light bent from atmospheric refraction') # light with bending
    plt.plot(dists, np.zeros(len(dists)), linestyle=':', c='darkorange', 
             label='Path of light if there was no atmosphere') # light without bending
    plt.fill_between(dists, lightPath, elvs, alpha=1, color='red', where=(elvs > lightPath),
                label=f'Land that blocks line of sight{landBlocking}')
    plt.fill_between(dists, 0, elvs, alpha=0.33, color='grey', where=(elvs > 0),
                    label='Land that would block line of sight if there was no atmosphere')
    
    if xLabel == '':
        xLabel = 'Distance from Observer to Target (km)'
    
    plt.xlabel(xLabel)
    plt.ylabel('Vertical Distance (m)')
    fig = plt.gcf()
    fig.patch.set_facecolor('w')
    fig.set_dpi(120)
    plt.grid()
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=1)
    
    if plotTitle != '':
        plt.title(plotTitle)
        
    if savePlot == True and plotTitle != '':
        plt.savefig(f'../misc/pics/{plotTitle.replace(" ", "_")}') 
    
    plt.show()

'''
Returns a big dictionary of the patches.
'''
def getSummitPatches(printInfo=True):
    
    summitPatches = {}
    summitPatches[northPole] = np.genfromtxt(f'{summitsDir}summits_top.txt', delimiter=',')
    summitPatches[southPole] = np.genfromtxt(f'{summitsDir}summits_btm.txt', delimiter=',')
    
    for i, lowerLng in enumerate(lngBoundaries[:-1]):
        upperLng = lngBoundaries[i+1]
        for j, lowerLat in enumerate(latBoundaries[:-1]):
            upperLat = latBoundaries[j+1]

            latLngRange = f'{lowerLat}_{upperLat}_{lowerLng}_{upperLng}'
            patchPath = f'{summitsDir}summits_{latLngRange}.txt'
            if os.path.exists(patchPath):
                summitPatches[latLngRange] = np.genfromtxt(patchPath, delimiter=',')
                
                if printInfo == True:
                    print(f'{latLngRange} data loaded')
                
    return summitPatches

'''
Gets the summits in the patch associated with a point.
'''
def getPatchSummits(lat, lng, summitPatches):
    if lat >= poleLat:
        return summitPatches[northPole]
    elif lat < -poleLat:
        return summitPatches[southPole]
    else:
        latRangeMin = int(lat // patchSize * patchSize) # round down to nearst multiple of patchSize
        lngRangeMin = int(lng // patchSize * patchSize) # round down to nearst multiple of patchSize
        return summitPatches[f'{latRangeMin}_{latRangeMin + patchSize}_{lngRangeMin}_{lngRangeMin + patchSize}']

'''
Determines if a summit is a pinnacle point.
Must include the patch that contains the summit as input.
'''
def isPinnaclePoint(summit, patchSummits, plotClosestInfo=False, testingCustomPoint=False):

    if patchSummits.ndim == 1:
        # this is for patches holding a single summit
        mayseenHigherSummits = []
    else:
        distanceBetweenSummits = [geod.line_length([patchSummit[LNG], 
                                                    summit[LNG]], 
                                                   [patchSummit[LAT], 
                                                    summit[LAT]])
                                  for patchSummit in patchSummits]   
        
        if testingCustomPoint == True:
            minDistBetweenPP = 1000
        else:
            minDistBetweenPP = 0
        
        mayseenHigherIndices = np.where((np.array(distanceBetweenSummits) > minDistBetweenPP) 
                                        & (distanceBetweenSummits < patchSummits[:, HD] + summit[HD])
                                        & (patchSummits[:, ELV] > summit[ELV])
                                        & ~((patchSummits[:, LAT] == summit[LAT]) # filtering out self, could improve?
                                            & (patchSummits[:, LNG] == summit[LNG])))[0]
        mayseenHigherSummits = patchSummits[mayseenHigherIndices]
        
        # sorting mayseenHigherSummits by distance to summit
        distanceBetweenSummits = [distanceBetweenSummits[i] for i in mayseenHigherIndices]
        mayseenHigherSummits = mayseenHigherSummits[np.argsort(distanceBetweenSummits)]

    print(f'Higher Summits to Test Sight: {len(mayseenHigherSummits)}')

    candidateIsPp = True
    for i, mayseenHigherSummit in enumerate(mayseenHigherSummits):
        if hasSight(summit, mayseenHigherSummit):
            candidateIsPp = False
            
            distanceToClosestHigherSummit = geod.line_length([mayseenHigherSummit[LNG], 
                                                              summit[LNG]], 
                                                             [mayseenHigherSummit[LAT], 
                                                              summit[LAT]])
            
            print(f'{summit[LAT]}, {summit[LNG]} at {summit[ELV]} m is in view of \n' + 
                  f'{mayseenHigherSummit[LAT]}, {mayseenHigherSummit[LNG]} at {mayseenHigherSummit[ELV]} m ({i+1} summits tested)\n' +
                  f'{round(distanceToClosestHigherSummit/1000)} km away')
            
            if plotClosestInfo == True:
                plotLosElevationProfile(summit[LAT], summit[LNG], 
                                        summit[ELV], 
                                        mayseenHigherSummit[LAT], mayseenHigherSummit[LNG], 
                                        mayseenHigherSummit[ELV],
                                        printInfo = False)
                
            break
            
    if candidateIsPp == True:
        print(f'{summit[LAT]}, {summit[LNG]} at {summit[ELV]} m is a pinnacle point!')
    
    return candidateIsPp

'''
Finds the maximum harizon distance of an observer at a given height.
The 7/6 is to account for atmospheric refraction.
'''
def horizonDistance(height):
    return np.sqrt(2*(7.0/6.0)*earthRadius*height)

'''
Generate a list of lats and lngs between the two input points along the geodesic.
'''
def getLatLngsBetweenPoints(lat1, lng1, lat2, lng2, numPoints=100):
    lngLats = geod.npts(lng1, lat1, lng2, lat2, numPoints)
    lngs = np.array(lngLats)[:, 0]
    lats = np.array(lngLats)[:, 1]
    return lats, lngs

'''
Gets the elevations for points via OpenMeteo API.
If inputting multiple points, must be comma separately
Can only make 10,000 requests per day
'''
def getElevation(latStr, lngStr):
    response = requests.get(f'https://api.open-meteo.com/v1/elevation?latitude={latStr}&longitude={lngStr}')
    return response.json()['elevation']

'''
Generate a list of lats, lngs, dists, and elvs between the two input points along the geodesic.
Takes curvature into account.
dists and elvs start at 0.
'''
def getElevationProfile(lat1, lng1, elv1, lat2, lng2, elv2):
    
    # sleep(60*60/5000)#24*60*60/10000) # rate limiting 10,000 calls per day
    
    # calling elevation API
    lats, lngs = getLatLngsBetweenPoints(lat1, lng1, lat2, lng2)
    latStr = ','.join(map(str, lats))
    lngStr = ','.join(map(str, lngs))
    elvs = getElevation(latStr, lngStr)

    # npts doesn't include start/end points, so prepend/append them
    lngs = np.insert(lngs, 0, lng1)
    lngs = np.append(lngs, lng2)
    lats = np.insert(lats, 0, lat1)
    lats = np.append(lats, lat2)
    elvs = np.insert(elvs, 0, elv1)
    elvs = np.append(elvs, elv2)

    dists = []
    for i in range(len(lats)):
        lat = lats[i]
        lon = lngs[i]
        dist = geod.line_length([lng1, lon], [lat1, lat])
        dists.append(dist)
    
    # adjusting for earth's curvature
    angleBetweenPoints = np.array(dists)/earthRadius
    dists = earthRadius * np.sin(angleBetweenPoints)
    dropFromCurvature = earthRadius * (1 - np.cos(angleBetweenPoints))
    elvs = elvs - dropFromCurvature - elvs[0]
    
    return lats, lngs, dists, elvs

'''
Rotates an elevation profile from getElevationProfile() be an angle.
'''
def rotateElevationProfile(dists, elvs, angle):
    dists = (dists * math.cos(angle)) - (elvs * math.sin(angle))
    elvs = (dists * math.sin(angle)) + (elvs * math.cos(angle))
    return dists, elvs

'''
Gets the distance and elevation data along the LOS between 2 points.
'''
def getLosData(lat1, lng1, elv1, lat2, lng2, elv2):
    
    lats, lngs, dists, elvs = getElevationProfile(lat1, lng1, elv1, lat2, lng2, elv2)
    
    # rotating to make LOS horizontal
    angleBelowHorizontal = -np.arctan(elvs[-1]/dists[-1])
    dists, elvs = rotateElevationProfile(dists, elvs, angleBelowHorizontal)
    
    return dists, elvs

'''
Finds the path light takes between 2 points taking atmospheric refraction into account.
Approximated as the arc or a circle with radius 7*R_earth.
'''
def getLightPath(dists):
    distanceToTarget = dists[-1]
    lightPathPartial = (7.0*earthRadius)**2 - (distanceToTarget)**2
    return np.sqrt(lightPathPartial + dists*(distanceToTarget - dists)) - np.sqrt(lightPathPartial)

'''
Determines if 2 points have direct line of sight.
'''
def hasSight(p1, p2):
 
    dists, elvs = getLosData(p1[LAT], p1[LNG], p1[ELV], p2[LAT], p2[LNG], p2[ELV])
    
    lightPath = getLightPath(dists)

    # removing ends since they could be slightly above 0 after the translation/rotation
    return not (elvs[1:-1] > lightPath[1:-1]).any()