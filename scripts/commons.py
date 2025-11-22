import math
import pandas as pd
from textwrap import dedent
from pyproj import Geod
import numpy as np
import requests
import matplotlib.pyplot as plt
from scipy.integrate import quad


########## VARIABLES ##########

defaultLightCurvature = 6.4
defaultScatterCoef0 = 0.00001139 # Wavelength averaged scattering coefficient in 1/m, Penndorf 1957

# summitFile = '../data/clean/summits_prm.csv'
# pinnaclePointFile = '../data/results/pinnacle_points/prm/pinnacle_points.csv'
# patchDirectory = f'../data/patches/prm_{defaultLightCurvature}'

summitFile = '../data/clean/summits_iso.csv'
pinnaclePointFile = '../data/results/pinnacle_points/iso/pinnacle_points.csv'
patchDirectory = f'../data/patches/iso_{defaultLightCurvature}'

# summitFile = '../data/results/pinnacle_points/prm_iso/pinnacle_points_merged.csv'
# pinnaclePointFile = '../data/results/pinnacle_points/prm_iso/pinnacle_points.csv'
# patchDirectory = f'../data/patches/prm_iso_{defaultLightCurvature}'

defaultMaxSamplingDistance = 100 # in m
ignoreBuffer = 4000 # in m

earthRadius = 6371146 # in m (Mean Sea Level, GPS, and the Geoid. Witold Fraczek 2003)
atmosphereScaleHeight = 8500 # in m (https://web.archive.org/web/20250821225050/https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html)

geod = Geod(ellps='sphere')

apiRequestUrl = 'http://127.0.0.1:8080/v1/elevation'
apiRequestLimit = 100
session = requests.Session()

"""
Patch Size Info:
- Can't go below maxOffset = 6.614 = convertDistanceToDeltaLat(2*horizonDistance(everestElevation)), everestElevation = 8737.79
  Otherwise patches that border the pole-patches would cross beyond the poles
- Can only be an integer N where maxOffset < (90-N)/N < 90
"""
patchSize = 10
allowedPatchSizes = [10, 15, 18, 30, 45]
assert(patchSize in allowedPatchSizes)


########## FUNCTIONS ##########

def getPoleLatitude():
    return 90 - patchSize

def getPatchLatBoundaries():
    poleLat = getPoleLatitude()
    return np.arange(-poleLat, poleLat+patchSize, patchSize)
    
def getPatchLngBoundaries():
    return np.arange(-180, 180+patchSize, patchSize)

def horizonDistance(height, lightCurvature=defaultLightCurvature):
    if height > 0:
        return math.sqrt(2*(lightCurvature/(lightCurvature-1))*earthRadius*height)
    return 0

def getElevations(latitudes, longitudes):

    elevations = []
    for i in range(0, len(latitudes), apiRequestLimit):
        chunkLatitudes = latitudes[i : i+apiRequestLimit]
        chunkLongitudes = longitudes[i : i+apiRequestLimit]
    
        params = {'latitude': ','.join(map(str, chunkLatitudes)),
                  'longitude': ','.join(map(str, chunkLongitudes))}

        response = session.get(apiRequestUrl, params=params)
    
        if response.status_code == 200:
            data = response.json()
            elevations.extend(data['elevation'])
        else:
            print('Error:', response.status_code, response.text)

    return elevations


########## CLASSES ##########

class Point:

    def __init__(self,
                 latitude,
                 longitude,
                 elevation=None):
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation

class Summit(Point):

    def __init__(self,
                 latitude,
                 longitude,
                 elevation,
                 summitId=None,
                 prominence=None,
                 isolation=None):
        
        super().__init__(latitude,
                         longitude,
                         elevation)

        self.summitId = summitId
        self.prominence = prominence
        self.isolation = isolation

    def getMaxHorizonDistance(self):
        return horizonDistance(self.elevation)

    def getPatch(self):
        poleLatitude = getPoleLatitude()
        
        if self.latitude >= poleLatitude:
            return Patch(90, poleLatitude)
        
        elif self.latitude < -poleLatitude:
            return Patch(-poleLatitude, -90)
        
        else:
            # Round down to nearst multiple of patchSize
            latMin = int((self.latitude // patchSize) * patchSize)
            lngMin = int((self.longitude // patchSize) * patchSize)
    
            return Patch(latMin+patchSize, latMin, lngMin+patchSize, lngMin)

    def getDistanceTo(self, summit):
        return geod.line_length([summit.longitude, self.longitude], [summit.latitude, self.latitude])

    def isPinnaclePoint(self):

        # Candidates are Pinnacle Points until proven guilty
        isPinnaclePoint = True
        
        patchSummits = self.getPatch().summitsOuter
        patchSummits['distanceFromCandidate'] = round(patchSummits.apply(lambda patchSummit: round(self.getDistanceTo(patchSummit)), axis=1))        
        patchSummitsInMhdRange = patchSummits.query('(summitId != @self.summitId) & '
                                                    '(elevation > @self.elevation) & '
                                                    '(distanceFromCandidate < maxHorizonDistance + @self.getMaxHorizonDistance())')
    
        print(f'Potential Disqualifying Summits: {len(patchSummitsInMhdRange)}')
        
        patchSummitsInMhdRange = patchSummitsInMhdRange.sort_values('distanceFromCandidate')
    
        for j, summit in enumerate(patchSummitsInMhdRange.itertuples()):
    
            target = Summit(latitude = summit.latitude,
                            longitude = summit.longitude,
                            elevation = summit.elevation)

            candidateLineOfSight = LineOfSight(self, target)
    
            candidateLineOfSight.processFullLineOfSight()
    
            if not candidateLineOfSight.isObstructed() and candidateLineOfSight.hasContrast():
    
                print(f'Tested Potential Disqualifying Summits: {j+1}')
                print(f'In view of {summit.latitude}, {summit.longitude} ({round(summit.elevation)} m) {round(summit.distanceFromCandidate/1000)} km away')
                
                isPinnaclePoint = False
                break

        print(f'Pinnacle Point: {isPinnaclePoint}')

        return isPinnaclePoint

class LosPoint(Point):

    def __init__(self,
                 latitude,
                 longitude,
                 elevation,
                 surfaceDistance,
                 straightDistance,
                 scatterCoef0 = defaultScatterCoef0,
                 lightHeight = None,
                 groundHeight = None):
        
        super().__init__(latitude,
                         longitude,
                         elevation)
        
        self.surfaceDistance = surfaceDistance
        self.straightDistance = straightDistance
        self.lightHeight = lightHeight
        self.groundHeight = groundHeight
        self.scatterCoef0 = scatterCoef0

    def getScatteringCoef(self):
        lightHeightFromSeaLevel = self.elevation + (self.lightHeight - self.groundHeight)
        return self.scatterCoef0 * math.exp(-lightHeightFromSeaLevel/atmosphereScaleHeight)

class LineOfSight():

    def __init__(self,
                 observer,
                 target,
                 lightCurvature = defaultLightCurvature,
                 scatterCoef0 = defaultScatterCoef0,
                 minSamplingDistance = defaultMaxSamplingDistance):
        
        self.observer = observer
        self.target = target
        self.lightCurvature = lightCurvature
        self.scatterCoef0 = scatterCoef0
        self.minSamplingDistance = minSamplingDistance
        self.surfaceDistance = geod.line_length([self.observer.longitude, self.target.longitude], [self.observer.latitude, self.target.latitude])
        self.numSamples = math.ceil(self.observer.getDistanceTo(self.target)/minSamplingDistance)
        self.losPoints = []

    def processFullLineOfSight(self):
        
        lngLats = geod.npts(self.observer.longitude, self.observer.latitude, 
                            self.target.longitude, self.target.latitude, 
                            self.numSamples)

        latitudes = np.array(lngLats)[:, 1]
        longitudes = np.array(lngLats)[:, 0]

        elevations = getElevations(latitudes, longitudes)
    
        latitudes   = np.concatenate([[self.observer.latitude], latitudes, [self.target.latitude]])
        longitudes  = np.concatenate([[self.observer.longitude], longitudes, [self.target.longitude]])
        elevations  = np.concatenate([[self.observer.elevation], elevations, [self.target.elevation]])

        surfaceDistances = []
        for i, latitude in enumerate(latitudes):
            longitude = longitudes[i]
            surfaceDistances.append(geod.line_length([self.observer.longitude, longitude], [self.observer.latitude, latitude]))

        anglesBetweenObserverAndLosPoints = np.array(surfaceDistances)/earthRadius
        xDistances = earthRadius * np.sin(anglesBetweenObserverAndLosPoints)
        dropFromCurvature = earthRadius * (1 - np.cos(anglesBetweenObserverAndLosPoints))
        yHeights = elevations - dropFromCurvature - elevations[0]

        angleBelowHorizontal = -np.arctan(yHeights[-1]/xDistances[-1])
    
        rotationMatrix = np.array([[math.cos(angleBelowHorizontal), -math.sin(angleBelowHorizontal)],
                                   [math.sin(angleBelowHorizontal),  math.cos(angleBelowHorizontal)]])
        
        rotatedPoints = rotationMatrix @ np.array([xDistances, yHeights])
        straightDistances = rotatedPoints[0]
        groundHeights = rotatedPoints[1]

        distanceToTarget = straightDistances[-1]
        gamma = (self.lightCurvature*earthRadius)*(self.lightCurvature*earthRadius) - (distanceToTarget)*(distanceToTarget)
        lightHeights = np.sqrt(gamma + straightDistances*(distanceToTarget - straightDistances)) - np.sqrt(gamma)
        
        self.losPoints = [LosPoint(latitude, longitude, elevation, surfaceDistance, straightDistance, self.scatterCoef0, lightHeight, groundHeight) 
                          for (latitude, longitude, elevation, surfaceDistance, straightDistance, lightHeight, groundHeight) 
                          in zip(latitudes, longitudes, elevations, surfaceDistances, straightDistances, lightHeights, groundHeights)]

    def getStraightDistance(self):
        return self.losPoints[-1].straightDistance
    
    def getLightDistance(self):
        dx = np.diff([point.straightDistance for point in self.losPoints])
        dy = np.diff([point.lightHeight for point in self.losPoints])
        return np.hypot(dx, dy).sum()

    def isInPossibleRange(self):
        return self.observer.getMaxHorizonDistance() + self.target.getMaxHorizonDistance() > self.surfaceDistance

    def isObstructed(self):        
        return not all(losPoint.groundHeight < losPoint.lightHeight 
                       for losPoint 
                       in self.losPoints
                       if losPoint.straightDistance > ignoreBuffer and losPoint.straightDistance < self.getStraightDistance()-ignoreBuffer)

    # TODO: Do this correctly!
    def getLightElevation(self, x):

        h1 = self.observer.elevation
        h2 = self.target.elevation
        D = self.surfaceDistance
        R = earthRadius
        C = self.lightCurvature
        
        delta_h = h2 - h1
        d = math.sqrt(D**2 + delta_h**2)
        r = (C - 1)*R
        T = math.sqrt(r**2 - (d**2)/4)
        
        x0 = D/2 - (delta_h/d)*T
        y0 = (h1 + h2)/2 + (D/d)*T
        
        return y0 - math.sqrt(r**2 - (x - x0)**2)

    def getScatterCoef(self, lightElevation):
        return self.scatterCoef0 * math.exp(-lightElevation/atmosphereScaleHeight)

    def getContrast(self):
        scatterCoefIntegralResult, error = quad(lambda x: self.getScatterCoef(self.getLightElevation(x)), 0, self.surfaceDistance)     
        return math.exp(-scatterCoefIntegralResult)

    # TODO: Return properly once fixed
    def hasContrast(self):
        # return self.getContrast() > 0.02 # 0.02 is from Below the Horizon, Michael Vollmer, 2020
        return True

    def getMidPoint(self):
        pass
                                                            
    def plot(self, plotPath=''):

        distances = np.array([point.straightDistance/1000.0 for point in self.losPoints])
        groundHeight = np.array([point.groundHeight for point in self.losPoints])
        lightHeight = np.array([point.lightHeight for point in self.losPoints])
        
        plt.figure(figsize=(15,5))
        
        plt.plot(distances, lightHeight, color='orange', label='Light', lw=1)
        plt.plot(distances, groundHeight, color='k', label='Earth', lw=1)

        plt.fill_between(distances, y1=min(groundHeight), y2=groundHeight, color='silver')

        if self.isObstructed():
            maxGroundInd = np.argmax(groundHeight)
            plt.plot(distances[maxGroundInd], groundHeight[maxGroundInd], marker='x', color='red')
        
        plt.title('Line of sight test between\n' 
                  + f'{self.observer.latitude}, {self.observer.longitude} ({round(self.observer.elevation)} m) ' 
                  + f'and {self.target.latitude}, {self.target.longitude} ({round(self.target.elevation)} m)\n' 
                  + f'{round(self.surfaceDistance/1000.0, 1)} km apart '
                  + f'[N={self.numSamples}, C={self.lightCurvature}, contrast={round(self.getContrast(), 4)}, LOS={not self.isObstructed()}]')
        
        plt.xlabel('Distance (km)')
        plt.ylabel('Height (m)')
        
        fig = plt.gcf()
        fig.patch.set_facecolor('w')
        fig.set_dpi(300)
        plt.grid(ls=':')
        plt.legend()
        
        if plotPath != '':
            plt.savefig(plotPath, bbox_inches='tight')

        plt.show()

class Patch():

    def __init__(self,
                 northInner,
                 southInner,
                 eastInner=None,
                 westInner=None,
                 globalSummits=None):

        self.globalSummits = globalSummits
        
        self.numSummitsInner = None
        self.summitsOuter = None
        
        self.northInner = northInner
        self.southInner = southInner
        self.eastInner = eastInner
        self.westInner = westInner

        self.northOuter = None
        self.southOuter = None
        self.eastOuter = None
        self.westOuter = None

        self.latOffset = None
        self.lngOffset = None

        if type(globalSummits) == type(None):
            try:
                self.loadPatch()
            except:
                print(f'Error loading patch {self.getFileName()}')
        else:
            self.setOuterBounds()
            self.summitsOuter = self.getSummitsInRange(self.northOuter, self.southOuter, self.eastOuter, self.westOuter)
            self.numGlobalSummits = len(globalSummits)
            self.globalSummits = None  # No need to keep this populated once we have summitsOuter
            self.save()

    def __str__(self):        
        return self.getMetadata()

    def getFileName(self):
        if self.isPolePatch():
            fileName = f'{self.northInner}N_{self.southInner}S.csv'
        else:
            fileName = f'{self.northInner}N_{self.southInner}S_{self.eastInner}E_{self.westInner}W.csv'
        return fileName

    def loadPatch(self):
        fileName = self.getFileName()

        # reading metadata
        metaDataList = []
        with open(f'{patchDirectory}/{fileName}', 'r') as rawMetaData:
            for i, line in enumerate(rawMetaData):
                if i >= 17:
                    break
                metaDataList.append(line.strip().split(': '))
                
        self.numGlobalSummits = int(metaDataList[0][1])
        self.numSummitsInner = int(metaDataList[2][1])

        self.northOuter = float(metaDataList[10][1])
        self.southOuter = float(metaDataList[11][1])

        eastOuter = metaDataList[12][1]
        self.eastOuter = float(eastOuter) if eastOuter != 'None' else None
        westOuter = metaDataList[13][1]        
        self.westOuter = float(westOuter) if westOuter != 'None' else None


        self.latOffset = float(metaDataList[15][1])
        lngOffset = metaDataList[16][1] 
        self.lngOffset = float(lngOffset) if lngOffset != 'None' else None

        self.summitsOuter = pd.read_csv(f'{patchDirectory}/{fileName}', comment='#')

    def save(self):
        fileName = self.getFileName()
        
        # this is needed to add the metadata as a comment in csv before data
        with open(f'{patchDirectory}/{fileName}', 'w') as patchFile:
            patchFile.write(self.getMetadata(isComment=True))
            self.summitsOuter.to_csv(patchFile, index=False)
            print(f'Saved {fileName}')

    def getMetadata(self, isComment=False):
        
        metadata = dedent(f"""\
            Global Summits: {self.numGlobalSummits}

            Patch Summits (Inner): {self.numSummitsInner}
            Patch Summits (Outer): {len(self.summitsOuter)}

            North (Inner): {self.northInner}
            South (Inner): {self.southInner}
            East (Inner): {self.eastInner}
            West (Inner): {self.westInner}

            North (Outer): {self.northOuter}
            South (Outer): {self.southOuter}
            East (Outer): {self.eastOuter}
            West (Outer): {self.westOuter}

            Lat Offset: {self.latOffset}
            Lng Offset: {self.lngOffset}\
        """)
        
        if isComment:
            return '\n'.join('# ' + line for line in metadata.splitlines()) + '\n#\n'
        return metadata

    def isPolePatch(self):
        return self.eastInner is None and self.westInner is None

    def isLngSeamPatch(self, eastBound, westBound):
        return eastBound < 0 and westBound > 0

    def makeLatitudeValid(self, latitude):
        if latitude > 90:
            return 90
        elif latitude < -90:
            return -90
        return latitude

    def makeLongitudeValid(self, longitude):
        if longitude > 180:
            return longitude - 360
        elif longitude < -180:
            return longitude + 360
        return longitude

    def convertDistanceToDeltaLat(self, distance):
        return distance / 111320  # There are 111320 m per deg of latitude

    def convertDistanceToDeltaLng(self, distance, latitude):
        return self.convertDistanceToDeltaLat(distance) / math.cos(math.radians(latitude))

    def getOffsetDistance(self):
        summitsInner = self.getSummitsInRange(self.northInner, self.southInner, self.eastInner, self.westInner)
        self.numSummitsInner = len(summitsInner)
        return horizonDistance(self.globalSummits.elevation.max()) + horizonDistance(summitsInner.elevation.max())

    def getPatchSummits(latitude, longitude):
        poleLatitude = getPoleLatitude()
        
        if latitude >= poleLatitude:
            patchSummits = Patch(90, poleLatitude)
        
        elif latitude < -poleLatitude:
            patchSummits = Patch(-poleLatitude, -90)
        
        else:
            # Round down to nearst multiple of patchSize
            latMin = int((latitude // patchSize) * patchSize)
            lngMin = int((longitude // patchSize) * patchSize)

        return Patch(latMin+patchSize, latMin, lngMin+patchSize, lngMin)

    def setOuterBounds(self):
        offsetDistance = self.getOffsetDistance()
        
        self.latOffset = self.convertDistanceToDeltaLat(offsetDistance)
        self.northOuter = self.makeLatitudeValid(self.northInner + self.latOffset)
        self.southOuter = self.makeLatitudeValid(self.southInner - self.latOffset)

        if not self.isPolePatch():
            latForOffset = self.southInner if self.southInner < 0 else self.northInner
            self.lngOffset = self.convertDistanceToDeltaLng(offsetDistance, latForOffset)

            self.eastOuter = self.makeLongitudeValid(self.eastInner + self.lngOffset)
            self.westOuter = self.makeLongitudeValid(self.westInner - self.lngOffset)

    def getSummitsInRange(self, northBound, southBound, eastBound, westBound):
        
        latCondition = 'latitude >= @southBound and latitude < @northBound'
        
        if self.isPolePatch():
            summitsInRange = self.globalSummits.query(latCondition)
        elif self.isLngSeamPatch(eastBound, westBound):
            summitsInRange = self.globalSummits.query(latCondition + ' and (longitude >= @westBound or longitude < @eastBound)')
        else:
            summitsInRange = self.globalSummits.query(latCondition + ' and longitude >= @westBound and longitude < @eastBound')
        
        return summitsInRange