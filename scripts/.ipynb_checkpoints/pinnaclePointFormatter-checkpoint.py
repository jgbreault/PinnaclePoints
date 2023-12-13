import pandas as pd
import commonFunctions as func

'''
Gets the prominence of the closest OTOTW to a summit.
'''
def getClosestOTOTWProminence(summit):
    distanceBetweenSummits = ototws.apply(lambda ototw: 
                                          func.geod.line_length([ototw.longitude, 
                                                                 summit.longitude], 
                                                                [ototw.latitude, 
                                                                 summit.latitude]), axis=1) 

    closestOTOTW = ototws.iloc[distanceBetweenSummits.idxmin()]

    return closestOTOTW.prominence_m

'''
Gets the name_local, name_en, and wikipedia info of the closest extremal to a summit.
'''
def getClosestExtremalInfo(summit):
    
    distanceBetweenSummits = extremals.apply(lambda extremal: 
                                             func.geod.line_length([extremal.longitude, 
                                                                    summit.longitude], 
                                                                   [extremal.latitude, 
                                                                    summit.latitude]), axis=1) 
    if distanceBetweenSummits.min() < 1000:
        closestExtremal = extremals.iloc[distanceBetweenSummits.idxmin()]
        
        closestName = closestExtremal['name']
        closestNameEn = closestExtremal.name_en
        closestWiki = closestExtremal.wikipedia
        
        if pd.isna(closestName) == True:
            closestName = ''
        if pd.isna(closestNameEn) == True:
            closestNameEn = ''
        if pd.isna(closestWiki) == True:
            closestWiki = ''
        
    else:
        closestName = ''
        closestNameEn = ''
        closestWiki = ''
        
    return pd.Series({'name_local': closestName,
                      'name_en': closestNameEn,
                      'wikipedia': closestWiki})

ototws = pd.read_csv('../dataSources/ototw_p300m.csv')
extremals = pd.read_csv('../dataSources/formattedExtremals.csv')

summits = pd.read_csv('../formattedSummits/pinnaclePoints_raw.txt', 
                      sep = ',', 
                      header = None,
                      names = ['id', 
                               'latitude', 
                               'longitude', 
                               'elevation', 
                               'h_distance'])

# convert horizon distance back to prominence
summits['prominence'] = summits.apply(getClosestOTOTWProminence, axis=1)

# add name/wiki info based on closest extremal point
summits[['name_local', 'name_en', 'wikipedia']] = summits.apply(getClosestExtremalInfo,
                                                                axis=1,
                                                                result_type='expand') 

summits = summits[['latitude', 
                   'longitude', 
                   'elevation', 
                   'prominence', 
                   'name_local', 
                   'name_en', 
                   'wikipedia']]
summits.to_csv('../pinnaclePoints.txt', index=False)