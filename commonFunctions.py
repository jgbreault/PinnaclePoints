import numpy as np
from pyproj import Geod
import requests
import math
from time import sleep

earthRadius = 6371146 # in m
geod = Geod(ellps='sphere')

poleLat = 80
patchSize = 5
maxLng = 180
lngBoundaries = np.arange(-maxLng, maxLng+patchSize, patchSize)
latBoundaries = np.arange(-poleLat, poleLat+patchSize, patchSize)

'''
Finds the maximum harizon distance of an observer at a given height.
'''
def horizonDistance(height):
    return np.sqrt(2*earthRadius*height)

'''
Finds the distance between 2 points on Earth's surface assuming a sphere.
'''
def distanceBetweenPoints(lat1, lat2, lng1, lng2):
    return geod.line_length([lng1, lng2], [lat1, lat2])

'''
Generate a list of lats and lngs between the two input points along the geodesic.
'''
def getLatLngsBetweenPoints(lat1, lng1, lat2, lng2, numPoints=100):
    lngLats = geod.npts(lng1, lat1, lng2, lat2, numPoints)
    lngs = np.array(lngLats)[:,0]
    lats = np.array(lngLats)[:,1]
    return lats, lngs

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
    response = requests.get(f'https://api.open-meteo.com/v1/elevation?latitude={latStr}&longitude={lngStr}')
    elvs = response.json()['elevation']

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
        dist = distanceBetweenPoints(lat1, lat, lng1, lon)
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