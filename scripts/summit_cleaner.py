import pandas as pd
import numpy as np
import commons as me
import time

def getBatchSummitElevations(batchSummits):
    
    latitudes = np.array(batchSummits.latitude)
    longitudes = np.array(batchSummits.longitude)
    elevations = np.array(batchSummits.elevation)

    apiElevations = me.getElevations(latitudes, longitudes)

    updatedElevations = []
    for i, apiElevation in enumerate(apiElevations): 
        if apiElevation > elevations[i]:
            elevations[i] = apiElevation

    batchSummits.elevation = elevations
    return batchSummits

def getSummitElevationsInBatches(summits):

    numSummits = len(summits)
    
    batches = np.array_split(summits, len(summits) // me.apiRequestLimit + 1)

    processedBatches = []
    for i, batch in enumerate(batches):

        if i%10000 == 0:
            print(f'Processed elevations for {i*me.apiRequestLimit}/{numSummits} summits')
  
        processedBatches.append(getBatchSummitElevations(batch))
    
    return pd.concat(processedBatches, ignore_index=True)

def fixBigBadElevations(df, ids):
    
    subset = df.loc[ids]
    lats = subset.latitude.tolist()
    lngs = subset.longitude.tolist()
    elevations = me.getElevations(lats, lngs)
    df.loc[ids, 'elevation'] = elevations

startTime = time.time()

print('PROMINENCE SUMMITS\n')

ototw = pd.read_csv('../data/raw/ototw_p300m.csv')
ototw = ototw[['latitude', 'longitude', 'elevation_m', 'prominence_m']]

prmSummitColNames = ['latitude', 'longitude', 'elevation', 'key_saddle_latitude', 'key_saddle_longitude', 'prominence']
prmSummits = pd.read_csv('../data/raw/all-peaks-sorted-p100.txt', names=prmSummitColNames)

startingNumPrmSummits = len(prmSummits)

prmSummits = prmSummits[['latitude', 'longitude', 'elevation', 'prominence']]

prmSummits = prmSummits.drop_duplicates()

prmSummits = prmSummits.merge(ototw[['latitude', 'longitude']], on=['latitude', 'longitude'], how='left', indicator='temp_merge')
prmSummits['candidate'] = prmSummits['temp_merge'].eq('both')
prmSummits = prmSummits.drop(columns=['temp_merge'])

# For some reason the co-ords for these 2 summits don't match exactly between OTOTW and Every_Mountain_in_the_World
prmSummits.loc[[266009, 532994], 'candidate'] = True

prmSummits.loc[prmSummits['longitude'] == 180.0, 'longitude'] -= 0.0001

prmSummits = getSummitElevationsInBatches(prmSummits)
prmSummits = prmSummits.sort_values('elevation', ascending=False)
prmSummits = prmSummits.reset_index(drop=True)

# TODO: Add comment, Grove hill
prmSummits.loc[[7763206], 'candidate'] = True

endingNumPrmSummits = len(prmSummits)

print(f'\nSummits before clean-up: {startingNumPrmSummits}')
print(f'Summits after clean-up: {endingNumPrmSummits} ({startingNumPrmSummits-endingNumPrmSummits} removed)')

numPrmCandidates = len(prmSummits.query('candidate == True'))
print(f'Number of Candidates: {numPrmCandidates} ({round(100*numPrmCandidates/endingNumPrmSummits, 3)}%)')

prmSummits.to_csv(f'../data/clean/summits_prm.csv', index_label='summitId')

print('\n##################################################\n')

print('ISOLATION SUMMITS\n')

isolationCadidateThresholdKm = 100 # in km

isoColNames = ['latitude', 'longitude', 'elevation_ft', 'ILP_latitude', 'ILP_longitude', 'isolation_km']
isoSummits = pd.read_csv('../data/raw/alliso-sorted.txt', names=isoColNames)

startingNumIsoSummits = len(isoSummits)

isoSummits['elevation'] = isoSummits.elevation_ft.divide(3.28084).round(2)
isoSummits['isolation'] = isoSummits.isolation_km.multiply(1000).round(2)

isoSummits = isoSummits[['latitude', 'longitude', 'elevation', 'isolation']]

isoSummits = isoSummits.drop_duplicates()

# There should not be any isolation less than 1 km (https://www.andrewkirmse.com/true-isolation)
isoSummits = isoSummits.query('isolation >= 1000') 

isoSummits['candidate'] = (isoSummits.isolation > isolationCadidateThresholdKm*1000) & (isoSummits.elevation > 0)

# Adding Everest
everest = prmSummits.head(1)
everestIsoData = [everest.latitude.values[0], 
                  everest.longitude.values[0], 
                  everest.elevation.values[0], 
                  None,
                  True]
everestIsoData = pd.DataFrame([everestIsoData], columns=isoSummits.columns)
isoSummits = pd.concat([everestIsoData, isoSummits], ignore_index=True)

isoSummits.loc[isoSummits['longitude'] == 180.0, 'longitude'] -= 0.0001

isoSummits = getSummitElevationsInBatches(isoSummits)
isoSummits = isoSummits.sort_values('elevation', ascending=False)
isoSummits = isoSummits.reset_index(drop=True)

fixBigBadElevations(isoSummits, [342, 13154544])

endingNumIsoSummits = len(isoSummits)

print(f'\nSummits before clean-up: {startingNumIsoSummits}')
print(f'Summits after clean-up: {endingNumIsoSummits} ({startingNumIsoSummits-endingNumIsoSummits-1} removed, 1 added)')

numIsoCandidates = len(isoSummits.query('candidate == True'))
print(f'Number of Candidates: {numIsoCandidates} ({round(100*numIsoCandidates/endingNumIsoSummits, 3)}%)')

isoSummits.to_csv(f'../data/clean/summits_iso.csv', index_label='summitId')

print('\n##################################################\n')

endTime = time.time()
totalTime = round(endTime - startTime)

days = totalTime // 86400
hours = (totalTime % 86400) // 3600
minutes = (totalTime % 3600) // 60
seconds = totalTime % 60

print(f'\n{days}d {hours}h {minutes}m {seconds}s to clean all {startingNumPrmSummits+startingNumIsoSummits} summits!')