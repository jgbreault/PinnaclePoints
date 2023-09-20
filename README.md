# PinnaclePoints

Visit https://jgbreault.github.io/PinnaclePoints/.

A **pinnacle point** is a point from which no higher point can be seen in a direct line of sight.

More specifically, a pinnacle point is a point with zero **inferiority**, where inferiority is defined as the maximum elevation that can be seen in a direct line of sight from a point minus the point's elevation. Since all points can see themselves, the minimum possible inferiority is zero.

- Download Andrew Kirmse's list of <a href="https://www.andrewkirmse.com/prominence-update-2023#h.cap6s838fwux">11,866,713 summits</a> and put it into the dataSources directory.
- Download Kai Xu's list of <a href="https://www.andrewkirmse.com/prominence-update-2023#h.cap6s838fwux">6,464 OTOTW mountains</a> and put it into the dataSources directory.
- summitFormatter.py divides Andrew Kirmse's summits into patches based on latitude and longitude.
- pinnaclePointFinder.py uses an algorithm to find Earth's pinnacle points, in decending order of elevation.
- pinnaclePointAnalysis.ipynb is used to generate index.html and pinnaclePoints.txt.
- index.html is a webapp showing all pinnacle points.
- pinnaclePoints.txt is the final result of pinnacle points in a txt file.

![Image](https://github.com/jgbreault/PinnaclePoints/blob/main/misc/pinnaclePoints_afroeurasia.png)
