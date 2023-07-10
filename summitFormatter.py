import numpy as np
import pandas as pd
import os

earthRadius = 6371146 # in m
feetToMetres = 3.28084

cwd = os.getcwd()

def horizonDistance(prm):
    return np.sqrt(2*earthRadius*prm)

def saveSummits(summitsToSave, file):
    summitsToSave = summitsToSave[["latitude", "longitude", "elevation", "h_distance"]]
    summitsToSave.to_csv(f"{cwd}/formattedSummits/{file}", header=False)
    print(f"{file} saved")

summits = pd.read_csv('prominence-p100.txt', sep=",", header=None)
summits.columns = ["latitude", "longitude", "elevation", "saddle_lat", "saddle_lng", "prominence"]
summits = summits[["latitude", "longitude", "elevation", "prominence"]]
summits.elevation = summits.elevation.divide(feetToMetres).round(1)
summits.prominence = summits.prominence.divide(feetToMetres).round(1)
summits["h_distance"] = summits.prominence.apply(horizonDistance).round(1)
summits = summits.sort_values('elevation', ascending=False)

# all summits
saveSummits(summits, "summits_all.txt")

# summits around North Pole
latBoundary = 60
summitsTop = summits.query(f"latitude >= @latBoundary")
saveSummits(summitsTop, "summits_top.txt")

# summits around South Pole
summitsBtm = summits.query(f"latitude <= -@latBoundary")
saveSummits(summitsBtm, "summits_btm.txt")

# summits in 5 lng deg strip (plus overlap)
latOverlap = 3
lngOverlap = 6
cut = latBoundary + latOverlap # to have an overlap equal to max horizon distance
longitudeBoundaries = np.arange(-180, 185, 5)
for i, lower in enumerate(longitudeBoundaries[:-1]):
    lowerLabel = lower
    upper = longitudeBoundaries[i + 1]
    upperLabel = upper
        
    if lower - lngOverlap < -180:
        lower = 360 + lower - lngOverlap
    else:
        lower -= lngOverlap
    
    if upperLabel + lngOverlap > 180:
        upper = -360 + upper + lngOverlap 
    else:
        upper += lngOverlap
        
    if lower > 0 and upper < 0:
        summitsStrip = summits.query('latitude > -@cut and latitude < @cut and (longitude >= @lower or longitude < @upper)')
    else:
        summitsStrip = summits.query('latitude > -@cut and latitude < @cut and longitude >= @lower and longitude < @upper')

    fileName = f"summits_{lowerLabel}_{upperLabel}.txt"
    saveSummits(summitsStrip, fileName)
