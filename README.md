# PinnaclePoints
A **pinnacle point** is a point from which no higher point can be seen. More specifically, a pinnacle point is a point with zero **inferiority**, where inferiority is defined as the maximum elevation that can be seen in a direct line of sight from a point minus the point's elevation. Since all points can see themselves, the minimum possible inferiority is zero.

Visit https://jgbreault.github.io/PinnaclePoints/.

- Download Andrew Kirmse's list of <a href="https://www.andrewkirmse.com/prominence">7,798,709 summits</a> and put it into the head directory to set up the base dataset.
- summitFormatter.py divides Andrew Kirmse's summits into groups based on latitude and longitude. This massively improves the computation time of the pinnaclePointFinder. Also, the horizon distance of each summit of determined, defined as &radic;(2 x R_earth x Prominence).
- pinnaclePointFinder.py uses an algorithm to find Earth's pinnacle points, in decending order of elevation. I define two summits to be in view if their geospatial distance is less than the sum of their horizon distances.
- pinnaclePointFormatter.py adds country and state/province information for each pinnacle point.
- pinnaclePointAnalysis.ipynb is used to visulaize the results, and generate index.html.
- index.html is a webapp showing all 2779 pinnacle points with their horizon distances.
- pinnaclePoints.txt is the final result of 2779 pinnacle points in a txt file.

![Image](https://github.com/jgbreault/PinnaclePoints/blob/main/images/pinnaclePoints_world.png)
![Image](https://github.com/jgbreault/PinnaclePoints/blob/main/images/pinnaclePoints_europe.png)
![Image](https://github.com/jgbreault/PinnaclePoints/blob/main/images/pinnicalPoints_top25Countries.png)