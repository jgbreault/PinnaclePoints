import numpy as np
import pandas as pd
import requests
import urllib.request
import math
import commonFunctions as func
import json
import os

'''
There are 2 elevation APIs I use. Both are free, so both have drawbacks. 

Open-Meteo has global coverage and is very fast. However, only allows 10,000 calls a day.
Open-Elevation only works between -60 and 60 lat, is slow, and crashes often. 

I use Open-Elevation between -60 and 60 lat (when I can) and Open-Meteo for the poles.
'''
def callElevationApi(lats, lngs):
    
    if max(lats) > 60 or min(lats) < -60:
        latStr = ','.join(map(str, lats))
        lngStr = ','.join(map(str, lngs))

        response = requests.get(f'https://api.open-meteo.com/v1/elevation?latitude={latStr}&longitude={lngStr}')
        elvs = response.json()['elevation']
    else:
        latLngs = [{}]*len(lats)
        for i in range(len(latLngs)):
            latLngs[i] = {"latitude":lats[i], "longitude":lngs[i]}
        location = {"locations":latLngs}
        locationJson = json.dumps(location, skipkeys=int).encode('utf8')

        url="https://api.open-elevation.com/api/v1/lookup"
        response = urllib.request.Request(url, locationJson, headers={'Content-Type': 'application/json'})
        response = urllib.request.urlopen(response)

        responseProc = response.read()
        responseProc = responseProc.decode("utf8")
        responseProc = json.loads(responseProc)
        responseProc = responseProc['results']
        response.close()

        elvs = []
        for i in range(len(responseProc)):
            elvs.append(responseProc[i]['elevation'])
    
    return elvs

'''
Generate a list of lats and lngs between the two input points along the geodesic.
'''
def getLatLngsBetweenPoints(lat1, lng1, lat2, lng2, numPoints=100):
    lngLats = func.geod.npts(lng1, lat1, lng2, lat2, numPoints)
    lngs = np.array(lngLats)[:,0]
    lats = np.array(lngLats)[:,1]
    return lats, lngs

'''
Generate a list of lats, lngs, dists, and elvs between the two input points along the geodesic.
Takes curvature into account.
dists and elvs start at 0.
'''
def getElevationProfile(lat1, lng1, elv1, lat2, lng2, elv2=np.nan):
    
    if np.isnan(elv2):
        elv2 = callElevationApi([lat2], [lng2])
    
    lats, lngs = getLatLngsBetweenPoints(lat1, lng1, lat2, lng2)  
    elvs = callElevationApi(lats, lngs)

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
        dist = func.distanceBetweenPoints(lat1, lat, lng1, lon)
        dists.append(dist)
    
    # adjusting for earth's curvature
    angleBetweenPoints = np.array(dists)/func.earthRadius
    dists = func.earthRadius * np.sin(angleBetweenPoints)
    dropFromCurvature = func.earthRadius * (1 - np.cos(angleBetweenPoints))
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
Determines if 2 points have direct line of sight.
'''
def hasDirectLos(p1, p2):
    
    lats, lngs, dists, elvs = getElevationProfile(p1[LAT], p1[LNG], p1[ELV], p2[LAT], p2[LNG], p2[ELV])
    
    # ROTATING TO MAKE LOS HORIZONTAL
    angleBelowHorizontal = -np.arctan(elvs[-1]/dists[-1])
    dists, elvs = rotateElevationProfile(dists, elvs, angleBelowHorizontal)

    #REMOVING ENDS SINCE THEY COULD BE SLIGHTLY ABOVE 0 AFTER THE TRANSLATION/ROTATION
    if max(elvs[1:-1]) > 0:
        return False
    return True

'''
Gets the summits in the patch associated with a point.
'''
def getPatchSummits(lat, lng):
    if lat >= func.poleLat:
        return summitsTop
    elif lat < -func.poleLat:
        return summitsBtm
    else:
        latRangeMin = int(lat // func.patchSize * func.patchSize) # round down to nearst multiple of patchSize
        lngRangeMin = int(lng // func.patchSize * func.patchSize) # round down to nearst multiple of patchSize
        return summitPatches[f'{latRangeMin}_{latRangeMin + func.patchSize}_{lngRangeMin}_{lngRangeMin + func.patchSize}']

'''
Saves a snapshot of the progress so the program can stop and start from where you left off.
'''
def saveCheckpoint():
    np.savetxt(checkpointFile, remainingOtotw, delimiter=',', fmt=dataFormat)
    np.savetxt(outputFile, foundPp, delimiter=',', fmt=dataFormat)
    print('\n')
    print('CHECKPOINT SAVED')

ID  = 0 # ID (ordered by elevation)
LAT = 1 # latitude
LNG = 2 # longitude
ELV = 3 # elevation
HD  = 4 # horizon distance

summitsDir = f'{func.cwd}/formattedSummits/'
dataFormat = '%d, %.4f, %.4f, %.1f, %.1f'

ototw = pd.read_csv(f'{func.cwd}/dataSources/ototw_p300m.csv')
ototw = ototw[['latitude', 'longitude', 'elevation_m']].sort_values(by='elevation_m', ascending=False)
ototw = ototw.rename(columns={'elevation_m': 'elevation'})
ototw['horizonDist'] = ototw.elevation.apply(func.horizonDistance).round(2)
ototw = ototw.reset_index()
ototw = ototw.drop(columns='index')
ototw = ototw.reset_index()
ototw = ototw.values

# getting patch data
summitsTop = np.genfromtxt(f'{summitsDir}summits_top.txt', delimiter=',')
summitsBtm = np.genfromtxt(f'{summitsDir}summits_btm.txt', delimiter=',')
summitPatches = {}
for i, lowerLng in enumerate(func.lngBoundaries[:-1]):
    upperLng = func.lngBoundaries[i+1]
    for j, lowerLat in enumerate(func.latBoundaries[:-1]):
        upperLat = func.latBoundaries[j+1]
        
        patchPath = f'{summitsDir}summits_{lowerLat}_{upperLat}_{lowerLng}_{upperLng}.txt'
        if os.path.exists(patchPath):
            summitPatches[f'{lowerLat}_{upperLat}_{lowerLng}_{upperLng}'] = np.genfromtxt(patchPath, delimiter=',')    

# loading from checkpoint
checkpointFile = f'{summitsDir}summits_checkpoint.txt'
if os.path.exists(checkpointFile):
    remainingOtotw = np.genfromtxt(checkpointFile, delimiter=',')
else:
    remainingOtotw = ototw
    
outputFile = f'{summitsDir}pinnaclePoints_raw.txt'
if os.path.exists(outputFile):
    foundPp = np.genfromtxt(f'{outputFile}', delimiter=',')
else:
    foundPp = []
    
# finding pinnacle points in decending order or elevation
ototwNum = len(ototw)
remainingOtotwNum = len(remainingOtotw)
foundPpNum = len(foundPp)
while remainingOtotwNum > 0:
    
    ppCandidate = remainingOtotw[0]
    print(f'Location: {ppCandidate[LAT]}, {ppCandidate[LNG]}')
    print(f'Elevation: {ppCandidate[ELV]}')
    print(f'OTOTW Remaining: {remainingOtotwNum} ({round(100*(1 - (remainingOtotwNum/ototwNum)), 2)}% complete)')
    print(f'\n')
    
    distanceBetweenOtotw = [func.distanceBetweenPoints(row[LNG],
                                                       ppCandidate[LNG],
                                                       row[LAT],
                                                       ppCandidate[LAT])
                            for row in remainingOtotw]
    
    mayseenIndices = np.where(distanceBetweenOtotw < remainingOtotw[:,HD] + ppCandidate[HD])[0]
    mayseenOtotw = remainingOtotw[mayseenIndices]
            
    # Bulk OTOTW point removal
    ototwIndicesToRemove = []
    for ototwPoint in mayseenOtotw:
        if ototwPoint[ID] == ppCandidate[ID]:
            ototwIndicesToRemove.append(ototwPoint[ID])
        else:
            if hasDirectLos(ppCandidate, ototwPoint) == True:
                ototwIndicesToRemove.append(ototwPoint[ID])
                
    print(f'OTOTW Removed: {len(ototwIndicesToRemove)}/{len(mayseenOtotw)}')
    
    remainingOtotw = remainingOtotw[~np.isin(remainingOtotw[:,ID], ototwIndicesToRemove)]
    remainingOtotwNum = len(remainingOtotw)
    patchSummits = getPatchSummits(ppCandidate[LAT], ppCandidate[LNG])
    
    if patchSummits.ndim == 1:
        # this is for patches holding a single summit
        mayseenHigherSummits = []
    else:
        distanceBetweenSummits = [func.distanceBetweenPoints(row[LNG],
                                                             ppCandidate[LNG],
                                                             row[LAT],
                                                             ppCandidate[LAT]) 
                                  for row in patchSummits]      
        
        mayseenHigherIndices = np.where((distanceBetweenSummits < patchSummits[:, HD] + ppCandidate[HD]) 
                                        & (patchSummits[:, ELV] > ppCandidate[ELV] + 0.1))[0]
        mayseenHigherSummits = patchSummits[mayseenHigherIndices]
        
        # sorting mayseenHigherSummits by distance to ppCandidate
        distanceBetweenSummits = [distanceBetweenSummits[i] for i in mayseenHigherIndices]
        mayseenHigherSummits = mayseenHigherSummits[np.argsort(distanceBetweenSummits)]

    print(f'Summits to Test: {len(mayseenHigherSummits)}')
      
    candidateIsPp = True
    for i, summit in enumerate(mayseenHigherSummits):
        if hasDirectLos(ppCandidate, summit):
            candidateIsPp = False
            print(f'Not a Pinnacle Point ({i+1} tested)...')
            break
    
    if candidateIsPp == True:
        if foundPpNum == 0:
            foundPp.append(ppCandidate)
        else:
            foundPp = np.concatenate((foundPp, [ppCandidate]))
            
        foundPpNum = len(foundPp)
        print(f'PINNACLE POINT {foundPpNum} FOUND!!!')
            
        if foundPpNum%5 == 0:
            saveCheckpoint()
    
    if remainingOtotwNum == 0:
        saveCheckpoint()
        
    print('\n#############################\n')