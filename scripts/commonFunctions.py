import numpy as np
from pyproj import Geod
import requests
import math
from time import sleep
import matplotlib.pyplot as plt
import os

earthRadius = 6371146 # in m
geod = Geod(ellps='sphere')
losDistanceCutOff = 400*1000 # TODO: Put this in parameters
apiLimit = 100
lightCurvature = 5.6 # https://aty.sdsu.edu/explain/atmos_refr/bending.html

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
def isPinnaclePoint(candidate, 
                    patchSummits, 
                    hasIsolation = False, 
                    plotClosestInfo = False):

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
                plotLosElevationProfile(candidate[LAT], candidate[LNG], 
                                        candidate[ELV], 
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
        return np.sqrt(2*(lightCurvature/(lightCurvature-1))*earthRadius*height)
    return 0

'''
Gets the elevations for points via an OpenMeteo API
If inputting multiple points, must be comma separately, 100 max per call
Can only make 10,000 requests per day
'''
def getElevation(latStr, lngStr):
    response = requests.get(f'https://api.open-meteo.com/v1/elevation?latitude={latStr}&longitude={lngStr}')
    return response.json()['elevation']


'''
Rotates an elevation profile from getElevationProfile() by an angle
'''
def rotate(x, y, angle):
    
    rotationMatrix = np.array([[np.cos(angle), -np.sin(angle)],
                               [np.sin(angle),  np.cos(angle)]])
    
    rotatedPoint = rotationMatrix @ np.array([x, y])
    
    return rotatedPoint[0], rotatedPoint[1]

class Summit:

    def __init__(self,
                 latitude, 
                 longitude, 
                 elevation, 
                 id=None,
                 prominence=None, 
                 isolation=None):
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self.id = id # Delete?
        self.prominence = prominence
        self.isolation = isolation
        self.maxHorizonDistance = horizonDistance(elevation)
        
    def __str__(self):
        
        summitInfo = (f'Location: {self.latitude}, {self.longitude}\n' 
                      + f'Elevation: {round(self.elevation)} m\n')
        if self.prominence is not None:
            summitInfo += f'Prominence: {round(self.prominence)} m\n'
        if self.isolation is not None:
            summitInfo += f'Isolation: {round(self.isolation)} km\n'

        return summitInfo    

class LosPoint:
        
    def __init__(self, 
                 latitude,
                 longitude,
                 elevation=None,
                 surfaceDistance=None,
                 straightDistance=None,
                 earthHeight=None,
                 lightHeight=None):
        
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self.surfaceDistance = surfaceDistance
        self.straightDistance = straightDistance
        self.earthHeight = earthHeight
        self.lightHeight = lightHeight
            
    def __str__(self):
        summitInfo = (f'Location: {self.latitude}, {self.longitude}\n' 
                      + f'Elevation: {round(self.elevation)} m\n')
        if self.surfaceDistance is not None:
            summitInfo += f'Straight Distance: {round(self.straightDistance/1000)} km\n'
        if self.earthHeight is not None:
            summitInfo += f'Earth Height: {round(self.earthHeight)} m\n'
        if self.lightHeight is not None:
            summitInfo += f'Light Height: {round(self.lightHeight)} m\n'

        return summitInfo   
                 
class LineOfSight:
    
    straightDist = None

    def __init__(self, 
                 observer,
                 target,
                 numPoints=None,
                 losPoints=None,
                 sampleDist=1,
                 forceFull=False,
                 skipProcessing=False): # in km
        
        self.observer = observer
        self.target = target
        self.sampleDist = sampleDist
        self.forceFull = forceFull
        
        if losPoints is None:
            losPoints = []
        self.losPoints = losPoints
        
        self.surfaceDistance = geod.line_length([self.observer.longitude, self.target.longitude], 
                                                     [self.observer.latitude, self.target.latitude])
        
        if numPoints is not None:
            self.numPoints = numPoints
        elif len(self.losPoints) == 0:
            self.numPoints = math.ceil(self.surfaceDistance/(sampleDist*1000)) - 1 # numSamples - 1 
            
        if not skipProcessing:
            self.process()
        
    def getLatitudesAndLongitudes(self):
        lngLats = geod.npts(self.observer.longitude, self.observer.latitude, 
                                     self.target.longitude, self.target.latitude, 
                                     self.numPoints)

        longitudes = np.array(lngLats)[:, 0]
        latitudes = np.array(lngLats)[:, 1]
        
        return latitudes, longitudes
        
    def process(self):
                                            
        if len(self.losPoints) == 0:
            
            latitudes, longitudes = self.getLatitudesAndLongitudes()

            midPoint = int(math.ceil(self.numPoints/2))
            numBatches = int(math.ceil(self.numPoints/apiLimit))
            
            for i in range(numBatches):

                rangeStartOuter = int(midPoint - (i+1)*apiLimit/2)
                rangeEndOuter = int(midPoint + (i+1)*apiLimit/2)

                rangeStartInner = int(rangeStartOuter + apiLimit/2)
                rangeEndInner = int(rangeEndOuter - apiLimit/2)

                if rangeStartOuter < 0:
                    rangeStartOuter = 0

                if rangeEndOuter > self.numPoints:
                    rangeEndOuter = self.numPoints

                batchLats = (list(latitudes[rangeStartOuter:rangeStartInner]) 
                             + list(latitudes[rangeEndInner:rangeEndOuter]))
                batchLngs = (list(longitudes[rangeStartOuter:rangeStartInner]) 
                             + list(longitudes[rangeEndInner:rangeEndOuter]))

                los = LineOfSight(self.observer, self.target, losPoints = [LosPoint(latitude, longitude) 
                                                                           for (latitude, longitude) 
                                                                           in zip(batchLats, batchLngs)])

                if i == numBatches - 1:
                    self.losPoints += los.losPoints
                    self.losPoints = sorted(self.losPoints, key=lambda losPoint: losPoint.straightDistance)
                else:
                    self.losPoints += los.losPoints[1:-1]
                    
                if not self.passesLineOfSightTest() and not self.forceFull:
                    break
                                        
        else:
            longitudes = [point.longitude for point in self.losPoints]
            latitudes = [point.latitude for point in self.losPoints]
                    
            elevations = [point.elevation for point in self.losPoints]
            if any([elevation is None for elevation in elevations]):
                elevations = getElevation(','.join(map(str, latitudes)), ','.join(map(str, longitudes)))
            
            latitudes = [self.observer.latitude] + latitudes + [self.target.latitude]
            longitudes = [self.observer.longitude] + longitudes + [self.target.longitude]
            elevations = [self.observer.elevation] + elevations + [self.target.elevation]
                
            surfaceDistances = []
            for i, latitude in enumerate(latitudes):
                longitude = longitudes[i]
                distance = geod.line_length([self.observer.longitude, longitude], [self.observer.latitude, latitude])
                surfaceDistances.append(distance)

            angleBetweenPoints = np.array(surfaceDistances)/earthRadius
            straightDistances = earthRadius * np.sin(angleBetweenPoints)
            dropFromCurvature = earthRadius * (1 - np.cos(angleBetweenPoints))
            earthHeights = elevations - dropFromCurvature - elevations[0]

            angleBelowHorizontal = -np.arctan(earthHeights[-1]/straightDistances[-1])
            straightDistances, earthHeights = rotate(straightDistances, earthHeights, angleBelowHorizontal)

            distanceToTarget = straightDistances[-1]
            gamma = (lightCurvature*earthRadius)**2 - (distanceToTarget)**2
            lightPath = np.sqrt(gamma + straightDistances*(distanceToTarget - straightDistances)) - np.sqrt(gamma)

            self.losPoints = [LosPoint(latitude, longitude, elevation, 
                                       surfaceDistance, straightDistance, earthHeight, lightHeight) 
                              for (latitude, longitude, elevation, 
                                   surfaceDistance, straightDistance, earthHeight, lightHeight) 
                              in zip(latitudes, longitudes, elevations, 
                                     surfaceDistances, straightDistances, earthHeights, lightPath)]

    def plot(self, plotName=''):
                
        if len(self.losPoints) == 0:
            self.process()
                
        distances = [point.straightDistance/1000 for point in self.losPoints]
        earthHeight = [point.earthHeight for point in self.losPoints]
        lightHeight = [point.lightHeight for point in self.losPoints]
        
        plt.figure(figsize=(10,4))
        plt.plot(distances, lightHeight, color='orange', label='Light', lw=1)
        plt.plot(distances, earthHeight, color='k', label='Earth', lw=1)
        plt.title('Line of sight test between\n' 
                  + f'{self.observer.latitude}, {self.observer.longitude} ({round(self.observer.elevation)} m) ' 
                  + f'and {self.target.latitude}, {self.target.longitude} ({round(self.target.elevation)} m)\n' 
                  + f'{round(self.surfaceDistance/1000)} km apart ' 
                  + f'[N={self.numPoints}, SD={round(self.surfaceDistance/(self.numPoints+1), 1)} m, LOS={self.passesLineOfSightTest()}]')
        plt.xlabel('Distance (km)')
        plt.ylabel('Height (m)')
        
        fig = plt.gcf()
        fig.patch.set_facecolor('w')
        fig.set_dpi(200)
        plt.grid()
        plt.legend()
        
        if plotName != '':
            plt.savefig(plotName, dpi=200, bbox_inches='tight')

        plt.show()
        
    def passesLineOfSightTest(self):
        return all(losPoint.earthHeight < losPoint.lightHeight for losPoint in self.losPoints[1:-1])
        
    def passesMaxHorizonDistanceTest(self):
        testResult =  (self.surfaceDistance < self.observer.maxHorizonDistance + self.target.maxHorizonDistance 
                       and self.surfaceDistance > losDistanceCutOff)
            
        return testResult