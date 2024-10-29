# PinnaclePoints

A **pinnacle point** is a point from which no higher point can be seen.

Interactive Map: https://www.pinnacle-points.com

Blog: https://www.pinnacle-points.com/guide

What is a Pinnacle Point?: https://www.pinnacle-points.com/guide/screens/what_is_pinnacle_point

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/pics/pinnaclePoints_globe.png" width=60%/>

Across the globe, 601 have been found. These are all pinnacle points with more than 300 m of prominence. The algorithm used for finding pinnacle points is outlined in the info section of the Interactive Map, along with sources of error. The curvature of the Earth and atmospheric refraction are taken into account.

**Future Plans for Pinnacle Points:**
- Improve project structure
- Find all pinnacle points with an isolation greater than 50 km
- Blog components
- Add notable points to blog
    - Most prominent point to not be a pinnacle point
    - Most isolated point to not be a pinnacle point
- Summit more pinnacle points

**To Run the Algorithm:**
- Download Andrew Kirmse's list of <a href="https://www.andrewkirmse.com/prominence-update-2023#h.cap6s838fwux">11,866,713 summits</a> and put it into the dataSources directory.
- scripts/summitFormatter.py divides Andrew Kirmse's summits into patches based on latitude and longitude.
- scripts/pinnaclePointFinder.py uses an algorithm to find Earth's pinnacle points, in decending order of elevation.
- scripts/pinnaclePointFormatter.py finds the names and wikipedia link info for the found pinnacle points.
- scripts/pinnaclePointAnalysis.ipynb is used to generate index.html and pinnaclePoints.txt.
- index.html is an interactive map showing all pinnacle points.
- pinnaclePoints.txt is the final result of pinnacle points in a txt file.

**The path of light between the two farthest points on Earth that can see each other:**

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/pics/Longest_Unbroken_Light_Path_on_Earth_(538_km).png"/>

**Taking atmospheric refraction into account:**

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/math/atmosphericRefraction.jpg" width=60%/>

**Taking the curvature of the Earth into account:**

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/math/earthCurvature.png"/>
