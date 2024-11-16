import pandas as pd
import math
import commonFunctions as func

'''
Saves a patch of summits
'''
def savePatch(patchToSave, file):
    patchToSave = patchToSave[['latitude', 'longitude', 'elevation', 'MHD']]
    patchToSave.to_csv(f'{outputDir}/{file}', header=False)
    print(f'{file} saved')

'''
Checks for overflow from crossing the +180 longitude line
'''
def accountForCrossingPos180(lng):
    if lng > 180:
        return lng - 360
    return lng

'''
Checks for overflow from crossing the -180 longitude line
'''
def accountForCrossingNeg180(lng):
    if lng < -180:
        return lng + 360
    return lng

'''
Converts a distance in m the amount of degrees of latitude the distance covers
'''
def convertDistanceToDeltaLat(distance):
    return distance/111320 # There are 111320 m per deg of latitude

'''
Converts a distance in m the amount of degrees of longitude the distance covers at a specific latitude
'''
def convertDistanceToDeltaLng(distance, latitude):
    return convertDistanceToDeltaLat(distance)/math.cos(math.radians(latitude))

'''
Gets the summits within the bounds of lowLat, upLat, lowLng, upLng
'''
def getPatch(lowLat, upLat, lowLng, upLng):
    # Accounting for patches that border the -180/180 lng line
    if lowLng > 0 and upLng < 0:
        return summits.query('latitude >= @lowLat and latitude < @upLat and (longitude >= @lowLng or longitude < @upLng)')
    return summits.query('latitude >= @lowLat and latitude < @upLat and longitude >= @lowLng and longitude < @upLng')

# Getting input parameters
paramPath = 'parameters.txt'
with open(paramPath, 'r') as paramFile:
    inputParams = dict(param.strip().split(' = ') for param in paramFile)

inputFile = inputParams['summit_file']
outputDir = inputParams['patch_directory']
patchSize = int(inputParams['patch_size'])
assert 90%patchSize == 0, 'Patch size must be a factor of 90 (Eg: 5, 10, 15, 30, 45, 90)'

poleLat = func.getPoleLatitude(patchSize)
latBoundaries = func.getPatchLatBoundaries(patchSize)
lngBoundaries = func.getPatchLngBoundaries(patchSize)
maxVisibleDistance = 538000 # The farthest any point on Earth can see, it is known 
maxLatOffset = convertDistanceToDeltaLat(maxVisibleDistance)

# Getting the base set of summits
summits = pd.read_csv(inputFile)
summits = summits[['id', 'latitude', 'longitude', 'elevation']] # THESE COLUMNS MUST BE INCLUDED IN INPUT FILE
summits['MHD'] = summits.elevation.apply(func.horizonDistance).round(1)
summits = summits.sort_values('elevation', ascending=False)

# North Pole patch
summitsTop = summits.query(f'latitude >= {poleLat}')
if len(summitsTop > 0):
    summitsNearTop = summits.query(f'latitude < {poleLat} and latitude >= {poleLat - maxLatOffset}')
    farthestPossibleSeenDistanceTop = summitsNearTop.MHD.max() + summitsTop.MHD.max()
    
    if farthestPossibleSeenDistanceTop < maxVisibleDistance:
        latOffsetTop = convertDistanceToDeltaLat(farthestPossibleSeenDistanceTop)        
    else:
        latOffsetTop = maxLatOffset
        
    summitsTopWithOffset = summits.query(f'latitude >= {poleLat - maxLatOffset}')
    savePatch(summitsTopWithOffset, 'summits_top.txt')
    
# South Pole patch
summitsBtm = summits.query(f'latitude < {-poleLat}')
if len(summitsBtm > 0):
    summitsNearBtm = summits.query(f'latitude >= {-poleLat} and latitude < {-poleLat + maxLatOffset}')
    farthestPossibleSeenDistanceBtm = summitsNearBtm.MHD.max() + summitsBtm.MHD.max()
    
    if farthestPossibleSeenDistanceBtm < maxVisibleDistance:
        latOffsetBtm = convertDistanceToDeltaLat(farthestPossibleSeenDistanceBtm)        
    else:
        latOffsetBtm = maxLatOffset
        
    summitsBtmWithOffset = summits.query(f'latitude < {-poleLat + maxLatOffset}')
    savePatch(summitsBtmWithOffset, 'summits_btm.txt')

# Patches between poles
for i, lowerLat in enumerate(latBoundaries[:-1]):
    upperLat = latBoundaries[i+1]
    upperLatWithOffset = upperLat + maxLatOffset
    lowerLatWithOffset = lowerLat - maxLatOffset
    
    # A patch's farthest point from the equator is used for East and West offsets
    if lowerLat < 0:
        latForOffset = lowerLat
    else:
        latForOffset = upperLat
    
    for j, lowerLng in enumerate(lngBoundaries[:-1]):
        upperLng = lngBoundaries[j+1]
        maxLngOffset = convertDistanceToDeltaLat(maxVisibleDistance)
        
        maxLngOffset = convertDistanceToDeltaLng(maxVisibleDistance, latForOffset)
        upperLngWithOffset = accountForCrossingPos180(upperLng + maxLngOffset)
        lowerLngWithOffset = accountForCrossingNeg180(lowerLng - maxLngOffset)
        
        patch = getPatch(lowerLat, upperLat, lowerLng, upperLng)
                        
        # Don't save empty patches
        if len(patch) > 0:
            
            patchWithOffset = getPatch(lowerLatWithOffset, upperLatWithOffset, lowerLngWithOffset, upperLngWithOffset)        
            summitsNearPatch = patchWithOffset.drop(patch.index)
            farthestPossibleSeenDistance = summitsNearPatch.MHD.max() + patch.MHD.max()
            
            if farthestPossibleSeenDistance < maxVisibleDistance:
                
                latOffset = convertDistanceToDeltaLat(farthestPossibleSeenDistance)
                upperLatWithOffset = upperLat + latOffset
                lowerLatWithOffset = lowerLat - latOffset

                lngOffset = convertDistanceToDeltaLng(farthestPossibleSeenDistance, latForOffset)
                upperLngWithOffset = accountForCrossingPos180(upperLng + lngOffset)
                lowerLngWithOffset = accountForCrossingNeg180(lowerLng - lngOffset)
                        
                patchWithOffset = getPatch(lowerLatWithOffset, upperLatWithOffset, lowerLngWithOffset, upperLngWithOffset)
                        
            fileName = f'summits_{lowerLat}_{upperLat}_{lowerLng}_{upperLng}.txt'
            savePatch(patchWithOffset, fileName)
