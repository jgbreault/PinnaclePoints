import numpy as np
from pyproj import Geod
import requests
import math
from time import sleep
import matplotlib.pyplot as plt
import os

earthRadius = 6371146 # in m
maxVisibleDistance = 538000 # The farthest any point on Earth can see, it is known 
geod = Geod(ellps='sphere')

ID  = 0 # id (ordered by elevation)
LAT = 1 # latitude
LNG = 2 # longitude
ELV = 3 # elevation
MHD = 4 # max horizon distance
ISO = 5 # isolation

'''
Gets the stored parameters
summit_file, has_isolation, candidate_file, patch_directory, and patch_size
'''
def getParameters():
    with open('parameters.txt', 'r') as paramFile:
        inputParams = dict(param.strip().split(' = ') for param in paramFile)
    return inputParams

'''
Gets the latitude to base the pole patches on, dependent on patchSize
'''
def getPoleLatitude(patchSize):
    return 90 - patchSize

'''
Gets the latitudes used as boundaries for the patches
'''
def getPatchLatBoundaries(patchSize):
    poleLat = getPoleLatitude(patchSize)
    return np.arange(-poleLat, poleLat+patchSize, patchSize)
    
'''
Gets the longitudes used as boundaries for the patches
'''
def getPatchLngBoundaries(patchSize):
    return np.arange(-180, 180+patchSize, patchSize)

'''
Plotting the path of light between 2 points
'''
def plotLosElevationProfile(lat1, lng1, elv1, 
                            lat2, lng2, elv2, 
                            savePlot=False, 
                            plotTitle='', 
                            xLabel=''):
    
    dists, elvs = getLosData(lat1, lng1, elv1, lat2, lng2, elv2)
    lightPath = getLightPath(dists)
    dists = dists/1000 # m to km
        
    plt.figure(figsize=(10,4))
    plt.plot(dists, elvs, color='k')
    plt.plot(dists, lightPath, color='orange', 
             label='Path of light bent from atmospheric refraction') # light with bending
    plt.plot(dists, np.zeros(len(dists)), linestyle=':', c='darkorange', 
             label='Path of light if there was no atmosphere') # light without bending
    plt.fill_between(dists, lightPath, elvs, alpha=1, color='red', where=(elvs > lightPath),
                label='Land that blocks line of sight')
    plt.fill_between(dists, 0, elvs, alpha=0.33, color='grey', where=(elvs > 0),
                    label='Land that would block line of sight if there was no atmosphere')
    
    if xLabel == '':
        xLabel = 'Distance from Observer to Target (km)'
    
    plt.xlabel(xLabel)
    plt.ylabel('Vertical Distance (m)')
    fig = plt.gcf()
    fig.patch.set_facecolor('w')
    fig.set_dpi(160)
    plt.grid()
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=1)
    
    if plotTitle != '':
        plt.title(plotTitle)
        
    if savePlot == True and plotTitle != '':
        plt.savefig(f'../misc/pics/{plotTitle.replace(" ", "_")}') 
    
    plt.show()

'''
Gets the summits in the patch associated with a point
'''
def getPatchSummits(lat, lng, patchDir, patchSize, poleLat):    
    if lat >= poleLat:
        return np.genfromtxt(f'{patchDir}/summits_top.txt', delimiter=',')
    
    elif lat < -poleLat:
        return np.genfromtxt(f'{patchDir}/summits_btm.txt', delimiter=',')
    
    else:
        # Round down to nearst multiple of patchSize
        latRangeMin = int(lat // patchSize * patchSize)
        lngRangeMin = int(lng // patchSize * patchSize)
        return np.genfromtxt(f'{patchDir}/summits_{latRangeMin}_{latRangeMin+patchSize}_{lngRangeMin}_{lngRangeMin+patchSize}.txt',
                             delimiter=',')

'''
Determines if a summit is a pinnacle point
Must include a patch that contains the summit as input
'''
def isPinnaclePoint(candidate, patchSummits, hasIsolation=False, plotClosestInfo=False):

    # For patches holding a single summit
    if patchSummits.ndim == 1:
        higherSummitsToTest = []
        
    else:
        distanceBetweenSummits = [geod.line_length([patchSummit[LNG], candidate[LNG]], [patchSummit[LAT], candidate[LAT]])
                                  for patchSummit in patchSummits]   
        
        sightTestCondition = ((distanceBetweenSummits < patchSummits[:, MHD] + candidate[MHD])
                             & (patchSummits[:, ELV] > candidate[ELV]) # Equal elevation does not disqualify
                             & (patchSummits[:, ID] != candidate[ID]))
        
        if hasIsolation:
            # 0.99 is just to ensure I capture the nearest higher summit
            sightTestCondition &= (distanceBetweenSummits > candidate[ISO]*0.99)
        
        higherIndicesToTest = np.where(sightTestCondition)[0]
        higherSummitsToTest = patchSummits[higherIndicesToTest]
        
        # Sorting higherSummitsToTest by distance to summit to test summits in order of distance
        distanceBetweenSummits = [distanceBetweenSummits[i] for i in higherIndicesToTest]
        higherSummitsToTest = higherSummitsToTest[np.argsort(distanceBetweenSummits)]

    print(f'Higher Summits to Test: {len(higherSummitsToTest)}')

    candidateIsPinnaclePoint = True
    for i, testSummit in enumerate(higherSummitsToTest):
        if hasSight(candidate, testSummit):
            candidateIsPinnaclePoint = False
            
            distanceToClosestHigherSummit = geod.line_length([testSummit[LNG], candidate[LNG]], [testSummit[LAT], candidate[LAT]])
            
            print(f'{candidate[LAT]}, {candidate[LNG]} at {candidate[ELV]} m is in view of\n' + 
                  f'{testSummit[LAT]}, {testSummit[LNG]} at {testSummit[ELV]} m ({i+1} summits tested)\n' +
                  f'{round(distanceToClosestHigherSummit/1000)} km away')
            
            if plotClosestInfo:
                plotLosElevationProfile(summit[LAT], summit[LNG], 
                                        summit[ELV], 
                                        testSummit[LAT], testSummit[LNG], 
                                        testSummit[ELV])

            break
            
    if candidateIsPinnaclePoint:
        print(f'{candidate[LAT]}, {candidate[LNG]} at {candidate[ELV]} m is a pinnacle point!')
    
    return candidateIsPinnaclePoint

'''
Finds the horizon distance of an observer at a given height
The 7/6 factor accounts for atmospheric refraction
'''
def horizonDistance(height):
    if height > 0:
        return np.sqrt(2*(7.0/6.0)*earthRadius*height)
    return 0

'''
Generate a list of lats and lngs between the two input points along the geodesic
'''
def getLatLngsBetweenPoints(lat1, lng1, lat2, lng2):
    lngLats = geod.npts(lng1, lat1, lng2, lat2, 100) # 100 max per API call
    lngs = np.array(lngLats)[:, 0]
    lats = np.array(lngLats)[:, 1]
    return lats, lngs

'''
Gets the elevations for points via an OpenMeteo API
If inputting multiple points, must be comma separately, 100 max per call
Can only make 10,000 requests per day
'''
def getElevation(latStr, lngStr):
    response = requests.get(f'https://api.open-meteo.com/v1/elevation?latitude={latStr}&longitude={lngStr}')
    return response.json()['elevation']

'''
Generate a list of 100 lats, lngs, dists, and elvs between the two input points along the geodesic
Takes Earth's curvature into account
dists and elvs start at 0
'''
def getElevationProfile(lat1, lng1, elv1, lat2, lng2, elv2):
        
    # Calling elevation API
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
    for i, lat in enumerate(lats):
        lon = lngs[i]
        dist = geod.line_length([lng1, lon], [lat1, lat])
        dists.append(dist)
    
    # Adjusting for earth's curvature
    angleBetweenPoints = np.array(dists)/earthRadius
    dists = earthRadius * np.sin(angleBetweenPoints)
    dropFromCurvature = earthRadius * (1 - np.cos(angleBetweenPoints))
    elvs = elvs - dropFromCurvature - elvs[0]
    
    return lats, lngs, dists, elvs

'''
Rotates an elevation profile from getElevationProfile() by an angle
'''
def rotateElevationProfile(dists, elvs, angle):
    dists = (dists * math.cos(angle)) - (elvs * math.sin(angle))
    elvs = (dists * math.sin(angle)) + (elvs * math.cos(angle))
    return dists, elvs

'''
Gets the distance and elevation data along the LOS between 2 points
'''
def getLosData(lat1, lng1, elv1, lat2, lng2, elv2):
    
    lats, lngs, dists, elvs = getElevationProfile(lat1, lng1, elv1, lat2, lng2, elv2)
    
    # Rotating to make LOS horizontal
    angleBelowHorizontal = -np.arctan(elvs[-1]/dists[-1])
    dists, elvs = rotateElevationProfile(dists, elvs, angleBelowHorizontal)
    
    return dists, elvs

'''
Finds the path light takes between 2 points taking atmospheric refraction into account
Approximated as the arc or a circle with radius 7*R_earth
'''
def getLightPath(dists):
    distanceToTarget = dists[-1]
    gamma = (7.0*earthRadius)**2 - (distanceToTarget)**2
    return np.sqrt(gamma + dists*(distanceToTarget - dists)) - np.sqrt(gamma)

'''
Determines if 2 points have direct line of sight
Curvature of the Earth, atmospheric refraction, and local topography are taken into account
'''
def hasSight(p1, p2):
 
    dists, elvs = getLosData(p1[LAT], p1[LNG], p1[ELV], p2[LAT], p2[LNG], p2[ELV])
    lightPath = getLightPath(dists)

    # Removing ends since they could be slightly above 0 after the translation/rotation
    return not (elvs[1:-1] > lightPath[1:-1]).any()