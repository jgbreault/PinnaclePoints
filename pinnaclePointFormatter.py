import pandas as pd
import os

def getProminence(hDist):
    return hDist*hDist/2/earthRadius

def getLocation(summit, resolution):
    location = geocode((summit['latitude'], summit['longitude']), language='en')    
    if location == None:
        return ''
    else:
        return location.raw['address'].get(resolution, '')

earthRadius = 6371146 # in m
cwd = os.getcwd()
columnNames = ['id', 'latitude', 'longitude', 'elevation_m', 'h_distance']

summits = pd.read_csv(f'{cwd}/formattedSummits/summits_result.txt', 
                      sep = ',', 
                      header = None,
                      names = columnNames)
summits['prominence_m'] = summits.h_distance.apply(getProminence).round(1)

summits = summits[['latitude', 'longitude', 'elevation_m', 'prominence_m']]
summits.to_csv(f'{cwd}/pinnaclePoints.txt', index=False)