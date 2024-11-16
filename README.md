# PinnaclePoints

A **pinnacle point** is a point from which no higher point can be seen.

Across the globe, 602 have been found. These are all pinnacle points with more than 300 m of prominence. The algorithm used for finding pinnacle points is outlined in the info section of the Interactive Map, along with sources of error. The curvature of the Earth, atmospheric refraction, and local topography are taken into account. The base dataset is a list of 11,866,713 high points with over 100 feet of prominence. I use an elevation API to find the elvation of points between these high points.

Interactive Map: https://www.pinnacle-points.com

My Pinnacle Point Journal: https://www.pinnacle-points.com/guide

What is a Pinnacle Point?: https://www.pinnacle-points.com/guide/screens/what_is_pinnacle_point

<img src="https://github.com/jgbreault/PinnaclePoints/blob/main/misc/pics/pinnaclePoints_globe.png" width=66.66%/>

**Future Plans:**
- Find all pinnacle points with isolation greater than 100 km
- Algorithmically find all the longest lines of sight on Earth
- Mention notable points on blog
    - Most prominent point to not be a pinnacle point
    - Most isolated point to not be a pinnacle point
- Summit more pinnacle points
- Framework for blog

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
│   ├── analysis.ipynb         # Used to analyze datasets and generate the interactive map
│   ├── commonFunctions.py     # Holds common functions used throughout this directory
│   ├── parameters.txt         # Holds parameters that determine which dataset to use, etc...
│   ├── patchMaker.py          # Divides summit_file into patches
│   ├── pinnaclePointFinder.py # Identifies pinnacle points in candidate_file, outputs to pinnaclePointsRaw.txt
│   └── pinnaclePointNamer.py  # Names pinnaclePointsRaw.txt by scraping PeakBagger, Wiki info by nearest extremal
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
│       ├── checkpoint.py            # Checkpoint of remaining candidates to validate, saved after each found pinnacle point
│       ├── faultyPinnaclePoints.txt # Used to catalogue misidentified pinnacle points
│       ├── pinnaclePointsRaw.txt    # The raw result of identified pinnacle points from pinnaclePointFinder.py
│       ├── historicalResults/
│       │   ├── iso_1km/             # The results that used all_iso-1km.txt as a base dataset
│       │   └── prm_100ft/           # The results that used all_prm-100ft.txt as a base dataset
│       ├── isolationPatches/        # Patches from all_iso-1km.txt
│       └── prominencePatches/       # Patches from all_prm-100ft.txt
├── guide/ # My pinnacle point blog
└── misc/
    ├── pinnaclePoints.apk # Downloadable app for android
    ├── math/              # Derivations of equations used in the algorithm
    ├── pics/              # Pics used in this README and more
    └── scientificPapers/  # Relevant scientific papers
```

**Running the Algorithm:**

- Add your summit_file and candidate_file (defined below) to dataSources/baseDatasets/
    - My summit_files are too large to include in github without LFS. My sources are on the interactive map. 
- Specify your parameters in scripts/parameters.txt (you can use copies from historicalResults/)
    - summit_file: the base dataset of summits, Must have id, latitude, longitude, and elevation. Sort summit_file by elevation.
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
