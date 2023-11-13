import json
import pandas as pd

def addExtremalAttribute(attr):
    if attr in properties.keys():
        name = properties[attr]
        extremal.append(name)
    else:
        extremal.append('')

with open('dataSources/extremals-geojson.js', 'r') as json_file:
    peaks_data = json.load(json_file)

id = 0
extremals = pd.DataFrame(columns=['id',
                                  'latitude',
                                  'longitude',
                                  'elevation',
                                  'name',
                                  'name_en',
                                  'wikipedia'])
for feature in peaks_data['features']:
    extremal = [id]
    id += 1
    
    coordinates = feature['geometry']['coordinates']
    latitude = coordinates[1]
    longitude = coordinates[0]
    extremal.append(latitude)
    extremal.append(longitude)
    
    properties = feature['properties']
    
    addExtremalAttribute('ele')
    addExtremalAttribute('name')
    addExtremalAttribute('name:en')
    addExtremalAttribute('wikipedia')
        
    extremals.loc[len(extremals)] = extremal

extremals.to_csv(f'dataSources/formattedExtremals.csv', index=False)