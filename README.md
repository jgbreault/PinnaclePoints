# PinnaclePoints

A **pinnacle point** is a point from which no higher point can be seen.

Interactive Map: https://jgbreault.github.io/PinnaclePoints/
<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/pics/pinnaclePoints_globe.png"/ width="25%">

Across the globe, 601 have been found. These are all pinnacle points with more than 300 m of prominence. The algorithm used for finding pinnacle points is outlined in the info section of the site, along with sources of error. The curvature of the Earth, and atmospheric refraction are taken into account.

**To run the algorithm:**
- Download Andrew Kirmse's list of <a href="https://www.andrewkirmse.com/prominence-update-2023#h.cap6s838fwux">11,866,713 summits</a> and put it into the dataSources directory.
- summitFormatter.py divides Andrew Kirmse's summits into patches based on latitude and longitude.
- pinnaclePointFinder.py uses an algorithm to find Earth's pinnacle points, in decending order of elevation.
- pinnaclePointFormatter.py finds the names and wikipedia link info for the found pinnacle points.
- pinnaclePointAnalysis.ipynb is used to generate index.html and pinnaclePoints.txt.
- index.html is a webapp showing all pinnacle points.
- pinnaclePoints.txt is the final result of pinnacle points in a txt file.

**The path of light between the two farthest points on Earth that can see each other:**
<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/pics/Longest_Unbroken_Light_Path_on_Earth_(538_km).png"/>

**Taking atmospheric refraction into account:**
<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/math/atmosphericRefraction.png" width="60%"/>

**Taking the curvature of the Earth into account:**
<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/math/earthCurvature.png"/>
