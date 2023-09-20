import numpy as np
import os
from pyproj import Geod

cwd = os.getcwd()

earthRadius = 6371146 # in m
geod = Geod(ellps='sphere')

poleLat = 80
patchSize = 5
maxLng = 180
lngBoundaries = np.arange(-maxLng, maxLng+patchSize, patchSize)
latBoundaries = np.arange(-poleLat, poleLat+patchSize, patchSize)

'''
Finds the maximum harizon distance of an observer at a given height
'''
def horizonDistance(height):
    return np.sqrt(2*earthRadius*height)

'''
Finds the distance between 2 points on Earth's surface assuming a sphere
'''
def distanceBetweenPoints(lat1, lat2, lng1, lng2):
    return geod.line_length([lat1, lat2], [lng1, lng2])