import numpy as np
import commonFunctions as func
import pandas as pd

isolationPoints = np.genfromtxt('../dataSources/generatedDatasets/historicalResults/iso-160km/pinnaclePointsRaw.txt', delimiter=',')
prominencePoints = np.genfromtxt('../dataSources/generatedDatasets/historicalResults/prm-300m/pinnaclePointsRaw.txt', delimiter=',')

pinnaclePoints = np.concatenate((isolationPoints[:, :func.ISO], prominencePoints)) # Merging datasets without isolation (or prominence)
pinnaclePoints = pinnaclePoints[pinnaclePoints[:, func.ELV].argsort()[::-1]] # Sorting by elevation descending
pinnaclePoints[:, func.ID] = np.arange(len(pinnaclePoints)) # Reindexing ID column

columnNames = ['id', 'latitude', 'longitude', 'elevation', 'MHD']
pinnaclePoints = pd.DataFrame(pinnaclePoints, columns=columnNames)

pinnaclePoints.to_csv(f'../dataSources/generatedDatasets/historicalResults/pinnaclePointsRawMerged.txt', index=False)