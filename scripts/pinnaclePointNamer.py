import pandas as pd
import commonFunctions as func
from bs4 import BeautifulSoup
import requests
import re


'''
Gets the name and wikipedia info of the closest extremal to a summit within 1 km
'''
def getClosestExtremalInfo(summit):
    
    distanceBetweenSummits = extremals.apply(lambda extremal: 
                                             func.geod.line_length([extremal.longitude, 
                                                                    summit.longitude], 
                                                                   [extremal.latitude, 
                                                                    summit.latitude]), axis=1)
    
    if distanceBetweenSummits.min() < 1000: # 1 km threshold
        closestExtremal = extremals.iloc[distanceBetweenSummits.idxmin()]

        closestNameEn = closestExtremal.name_en
        closestNameLocal = closestExtremal.name_local
        closestWiki = closestExtremal.wikipedia
        
        # Use english name if exists
        if not pd.isna(closestNameEn):
            closestName = closestNameEn
        # Use local name otherwise
        elif not pd.isna(closestNameLocal):
            closestName = closestNameLocal
        else:
            closestName = ''
            
        if pd.isna(closestWiki):
            closestWiki = ''
            
    else:
        closestName = ''
        closestWiki = ''
    
    print(f'Extremal Name for #{summit.name+1}: {closestName}') 
        
    return closestName, closestWiki

'''
Scraping the name of the nearest peak within 1 km from PeakBagger
TODO Ask Andrew if he can help me with the 403 error, haha
'''
def scrapePeakBaggerName(summit):
    response = requests.get(f'https://www.peakbagger.com/search.aspx?tid=R&lat={summit.latitude}&lon={summit.longitude}&ss=&u=m')
    print(response.status_code)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    summitName = summit.summit_name
    tableTitle = soup.find('h2', text=lambda text: text and 'Radius Search from' in text)
    
    if tableTitle:
        tableRows = tableTitle.find_next('tr').parent.find_all('tr')
                
        if len(tableRows) >= 2:
            firstRow = tableRows[1] # need to skip header
            firstRowCells = firstRow.find_all('td')

            nameCell = firstRowCells[0].text
            distanceCell = firstRowCells[4].text
            
            if float(distanceCell) < 1.0: # 1 km threshold
                summitName = nameCell
                print(f'PeakBagger Override for #{summit.name+1}: {summitName}') 

    return summitName

params = func.getParameters()    
candidateFile = params['candidate_file']
hasIsolation = eval(params['has_isolation'])
isSingleGlobalPatch = eval(params['is_single_global_patch'])

candidates = pd.read_csv(candidateFile)
extremals = pd.read_csv('../dataSources/baseDatasets/extremals.txt')

if hasIsolation:
    pinnaclePointColumns = ['id', 'latitude', 'longitude', 'elevation', 'MHD', 'isolation']
else:
    pinnaclePointColumns =['id', 'latitude', 'longitude', 'elevation', 'MHD']

pinnaclePoints = pd.read_csv('../dataSources/generatedDatasets/pinnaclePointsRaw.txt', 
                             sep = ',', 
                             header = None,
                             names = pinnaclePointColumns)

# Add name and wiki info based on closest extremal point
pinnaclePoints[['summit_name', 'wikipedia']] = pinnaclePoints.apply(getClosestExtremalInfo, axis=1, result_type='expand') 

# Overwrite name with PeakBagger info if exists
#TODO: Talk to Andrew about about the 403 error
# pinnaclePoints['summit_name'] = pinnaclePoints.apply(scrapePeakBaggerName, axis=1)

# Get prominence from candidateFile based on id if it exists
if not hasIsolation and not isSingleGlobalPatch:
    pinnaclePoints = pinnaclePoints.merge(candidates[['id', 'prominence']], on='id', how='left')

pinnaclePoints['latitude'] = pinnaclePoints['latitude'].round(4)
pinnaclePoints['longitude'] = pinnaclePoints['longitude'].round(4)
pinnaclePoints['elevation'] = pinnaclePoints['elevation'].round(2)

if hasIsolation:
    pinnaclePoints['isolation'] = pinnaclePoints['isolation'].round()  
    pinnaclePoints = pinnaclePoints[['latitude', 'longitude', 'elevation', 'isolation', 'summit_name', 'wikipedia']]
    
elif not hasIsolation and not isSingleGlobalPatch:
    pinnaclePoints['prominence'] = pinnaclePoints['prominence'].round(2)   
    pinnaclePoints = pinnaclePoints[['latitude', 'longitude', 'elevation', 'prominence', 'summit_name', 'wikipedia']]
    
else:
    pinnaclePoints = pinnaclePoints[['latitude', 'longitude', 'elevation', 'summit_name', 'wikipedia']]

pinnaclePoints.to_csv('../pinnaclePoints.txt', index=False)