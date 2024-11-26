# PinnaclePoints

A **pinnacle point** is a point from which no higher point can be seen.

Across the globe, 885 have been found. These are all pinnacle points with more than 300 m (1000 ft) of prominence or more than 160 km (100 miles) of isolation. The curvature of the Earth, atmospheric refraction, and local topography are taken into account. Two summits are defined to have line-of-sight if light can theoretically travel from one to the other under ideal atmospheric conditions. An explanation of the algorithm used can be found at pinnaclePointAlgorithmExplained.txt.

Interactive Map: https://www.pinnacle-points.com

My Pinnacle Point Journal: https://www.pinnacle-points.com/guide

What is a Pinnacle Point?: https://www.pinnacle-points.com/guide/screens/what_is_pinnacle_point

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/pics/pinnaclePoints_globe.png" width=70%/>

**Future Plans:**
- Algorithmically find all the longest lines of sight on Earth
- Summit more pinnacle points
- Framework for blog
- Mention notable points on blog
    - Most prominent point to not be a pinnacle point
    - Most isolated point to not be a pinnacle point
    
**Data Sources:**
1. <a href="https://www.andrewkirmse.com/prominence-update-2023">Mountains by Prominence</a>
    - Andrew Kirmse and Jonathan de Ferranti found all 11,866,713 summits on Earth with over 100 ft (30 m) of prominence. I use this dataset to find all pinnacle points with more than 300 m (1000 ft) of prominence.
2. <a href="https://www.andrewkirmse.com/true-isolation">Mountains by Isolation</a>
    - Andrew Kirmse and Jonathan de Ferranti found all 24,749,518 summits on Earth with over 1 km (0.6 miles) of isolation. I use this dataset to find all pinnacle points with more than 160 km (100 miles) of isolation.
3. <a href="https://ototwmountains.com/">On-Top-Of-The-World Mountains</a>
    - An on-top-of-the-world mountain (OTOTW) is a summit where no land rises above the horizontal plane from the summit. Since any land that rises above the horizontal plane would have higher elevation than the summit itself, if a summit is not an OTOTW then it can not be a pinnacle point either. In other words, pinnacle points are a subset of OTOTWs. Kai Xu found all 6,464 OTOTWs on Earth with over 300 m (1000 ft) of prominence. I identify which of these 6,464 summits are pinnacle points. Andreas Geyer-Schulz deserves mention as well for his
<a href="https://nuntius35.gitlab.io/extremal_peaks/">extremal peaks</a>.
4. <a href="https://aty.sdsu.edu/explain/atmos_refr/horizon.html">Atmospheric Refraction</a>
    - The exact path light takes in the atmosphere depends on many factors. However, according to the San Diego State University, a ray's path can be approximated as the arc of a circle with radius seven times greater than Earth's. I use this when determining if two summits have line-of-sight.
5. <a href="https://aty.sdsu.edu/explain/atmos_refr/horizon.html">Open-Meteo and Copernicus</a>
    - Open-Meteo provides a free elevation API that uses the <a href="https://doi.org/10.5270/ESA-c5d3d65">Copernicus DEM</a>. I use this API to find the elevation of points that are not in any of my datasets.

**Sources of Error:**
- The Earth is approximated as a sphere instead of an ellipsoid. This is done for simpler math.
- There is some inherent error in the data. The datasets have resolutions ranging from of 30 m (1 arcsecond) to 90 m (3 arcseconds). All data sources are surface elevation models, so trees and buildings are included.
- Only 100 equidistant points are sampled when determining if two summits have an obstructed line-of-sight. Some points that could block line-of sight may not be captured in this sample. By increasing the number of sampled points, more pinnacle points could be found.
- The algorithm assumes there to be no land below sea level, which is not quite true. Any pinnacle points below sea level would not have been identified. It is possible for some identified pinnacle points that are near basins below sea level to not truly be pinnacle points. This is because these points can see farther across their basin in reality than they could if the basin did not descend below sea level.
- Only summits with more than 300 m (1000 ft) of prominence or more than 160 km (100 miles) of isolation are considered. The promience threshold is determined by the OTOTWs dataset since I only consider points in Source 1 that are OTOTWs. When finding pinnacle points in Source 2, high isolation points are obvious strong candidates when identifying pinnacle points. The specific value for the isolation threshold was decided arbitarily. Computation time increases considerably as the isolation threshold is lowered.
- To take atmospheric refraction into account, light rays are approximated as arcs of circles (Source 4). The path light takes in the atmosphere is in fact much more complex and depends on many factors. Since the distance you can see from a given point depends on temperature and pressure, the distance you can see from a point technically changes with the seasons and even the time of day. Additionally, the approximation of light following the arc of a circle only holds true for altitudes that are small compared to the 8 km height of the <a href="https://aty.sdsu.edu/explain/thermal/hydrostatic.html#homog">homogeneous atmosphere</a>. This project is slightly outside of this scope.

**App Download:**

Since the app is only available by downloading the APK, only Android devices are currently supported. I might put the app on the Android and Apple app stores eventually. Follow these steps to get the app on your Android device:
- Go to misc/pinnaclePoints.apk
- Click the button that looks like [...] (three dots).
- Click [Download]. Open the APK on your device when it is done downloading. You may get a message similar to "For your security, your device is not allowed to install apps from this source". You'll have to go to your settings and allow unknown installs from this source. Feel free to change it back afterwards.
- Click [Install].

**Project Structure:**
```
PinnaclePoints/
├── CNAME              # Needed to host index.html on pinnacle-points.com
├── pinnaclePoints.txt # The final pinacle point reuslt used in the interactive map 
├── index.html         # Interactive pinnacle point map
├── scripts/
│   ├── analysis.ipynb            # Used to analyze datasets and generate the interactive map
│   ├── commonFunctions.py        # Holds common functions used throughout this directory
│   ├── historicalResultMerger.py # Used to merge results from different runs in a big file full of duplicates
│   ├── lineOfSightFinder.py      # A work in progress, no looky
│   ├── parameters.txt            # Holds parameters that determine which dataset to use, etc...
│   ├── patchMaker.py             # Divides summit_file into patches
│   ├── pinnaclePointFinder.py    # Identifies pinnacle points in candidate_file, outputs to pinnaclePointsRaw.txt
│   └── pinnaclePointNamer.py     # Names pinnacle points based on closest extremal or closest PeakBagger summit
├── dataSources/
│   ├── baseDatasets/
│   │   ├── extremals.txt            # Essentially OTOTW from a different source. Only used for Wiki info and some names.
│   │   ├── isolationSummits/
│   │   │   ├── all_iso-1km.txt      # All summits with over 1 km of isolation (MISSING: too large to include)
│   │   │   └── all_iso-100km.txt    # All summits with over 100 km of isolation
│   │   └── prominenceSummits/
│   │       ├── all_prm-100ft.txt    # All summits with over 100 ft of prominence (MISSING: too large to include)
│   │       └── ototw_prm-300m.txt   # All OTOTW with over 300 m of prominence
│   └── generatedDatasets/
│       ├── faultyPinnaclePoints.txt # Used to catalogue misidentified pinnacle points
│       ├── historicalResults/
│       │   ├── iso-1km/             # The results that used all_iso-1km.txt as a base dataset
│       │   ├── prm-100ft/           # The results that used all_prm-100ft.txt as a base dataset
│       │   └── prm_and_iso/         # The merged results from iso-1km and prm-100ft
│       ├── isolationPatches/        # Patches from all_iso-1km.txt (MISSING: add directory yourself)
│       └── prominencePatches/       # Patches from all_prm-100ft.txt (MISSING: add directory yourself)
├── guide/ # My pinnacle point blog
└── misc/
    ├── pinnaclePoints.apk                  # Downloadable app for android
    ├── pinnaclePointAlgorithmExplained.txt # An explanation of of the pinnacle point algorithm 
    ├── math/                               # Derivations of equations used in the algorithm
    ├── pics/                               # Pics used in this README and more
    └── scientificPapers/                   # Relevant scientific papers
```

**Running the Algorithm:**

- Add your summit_file and candidate_file (defined below) to dataSources/baseDatasets/
    - My summit_files are too large to include in github without LFS. My sources are on the interactive map. 
- Specify your parameters in scripts/parameters.txt (you can use copies from historicalResults/)
    - summit_file: the base dataset of summits, Must have id, latitude, longitude, and elevation. Sort summit_file by elevation descending.
    - has_isolation: a boolean, does summit_file include isolation? If so the algorithm is faster. 
    - candidate_file: records from summit_file that I want to test as pinnacle points
    - patch_directory: directory of the pathches used by the algorthm
    - patch_size: patches are patch_size deg latitude by patch_size deg longitude
- Run scripts/patchMaker.py to divide summit_file into patches. Smaller patch_size is faster but takes more space.
- Run scripts/pinnaclePointFinder.py to generate the raw pinnacle point result in pinnaclePointsRaw.txt
    - Only 10,000 line-of-sight tests can be done a day, an API restication
- Run scripts/pinnaclePointFormatter.py to format and give names to pinnaclePointsRaw.txt, generates pinnaclePoints.txt

**The path of light between the two farthest points on Earth that can see each other:**

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/pics/Longest_Unbroken_Light_Path_on_Earth_(538_km).png"/>

**Taking atmospheric refraction into account:**

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/math/atmosphericRefraction.jpg" width=60%/>

**Taking the curvature of the Earth into account:**

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/math/earthCurvature.png"/>
