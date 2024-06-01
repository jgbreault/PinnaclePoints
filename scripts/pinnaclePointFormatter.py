import pandas as pd
import commonFunctions as func
from bs4 import BeautifulSoup
import requests

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
Gets the wikipedia info of the closest extremal to a summit within 1 km
'''
def getClosestExtremalInfo(summit):
    
    distanceBetweenSummits = extremals.apply(lambda extremal: 
                                             func.geod.line_length([extremal.longitude, 
                                                                    summit.longitude], 
                                                                   [extremal.latitude, 
                                                                    summit.latitude]), axis=1) 
    if distanceBetweenSummits.min() < 1000:
        closestExtremal = extremals.iloc[distanceBetweenSummits.idxmin()]

        closestWiki = closestExtremal.wikipedia
        
        if pd.isna(closestWiki) == True:
            closestWiki = ''
        
    else:
        closestWiki = ''
        
    return closestWiki

'''
Gets the name of the nearest peak from PeakBagger within 1 km
'''
def scrapeMountainName(pinnacle):
    response = requests.get(f'https://www.peakbagger.com/search.aspx?tid=R&lat={pinnacle.latitude}&lon={pinnacle.longitude}&ss=&u=m')
    soup = BeautifulSoup(response.text, 'html.parser')
    
    newName = None
    tableTitle = soup.find('h2', text=lambda text: text and 'Radius Search from' in text)
    if tableTitle:
        tableRows = tableTitle.find_next('tr').parent.find_all('tr')
        if len(tableRows) > 2:
            firstRow = tableRows[1] # need to skip header
            firstRowCells = firstRow.find_all('td')

            nameCell = firstRowCells[0].text
            distanceCell = firstRowCells[4].text

            if float(distanceCell) < 1.0:
                newName = nameCell

    return newName

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

summits['summit_name'] = summits.apply(scrapeMountainName, axis=1)

# convert horizon distance back to prominence
summits['prominence'] = summits.apply(getClosestOTOTWProminence, axis=1)

# add name/wiki info based on closest extremal point
summits['wikipedia'] = summits.apply(getClosestExtremalInfo, axis=1) 

summits = summits[['latitude', 
                   'longitude', 
                   'elevation', 
                   'prominence', 
                   'summit_name', 
                   'wikipedia']]
summits.to_csv('../pinnaclePoints.txt', index=False)