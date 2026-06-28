"""
Divides the globe into spatial patches and saves one CSV per patch.

Each patch has an inner region (a non-overlapping tile of the globe) and an outer
region that extends beyond the inner bounds by each summit's maximum horizon distance
(MHD). A patch's CSV contains every summit whose inner-region tile overlaps with any
summit in the outer region, so that the pinnacle point and LOS finders can test all
candidate pairs without loading the full summit dataset.

The grid uses 10x10 degree tiles for mid-latitudes and a single polar cap at each pole
above/below the latitude where a 10-degree tile would become too narrow to be useful.
Run summit_cleaner.py first to produce the summit CSV.
"""

import os
import pandas as pd
import commons as me

os.makedirs(me.patch_directory, exist_ok=True)

pole_lat = me.get_pole_latitude()
lat_boundaries = me.get_patch_lat_boundaries()
lng_boundaries = me.get_patch_lng_boundaries()

summits = pd.read_csv(me.summit_file)

# Pre-compute each summit's maximum horizon distance so Patch can expand outer bounds.
summits['max_horizon_distance'] = summits.elevation.apply(me.horizon_distance).astype(int)

# South polar cap: a single patch covering everything south of pole_lat.
me.Patch(global_summits = summits,
         north_inner = -pole_lat,
         south_inner = -90)

# Mid-latitude 10x10 degree grid.
for lat in lat_boundaries[:-1]:
    for lng in lng_boundaries[:-1]:
        me.Patch(global_summits = summits,
                 north_inner = lat + me.patch_size,
                 south_inner = lat,
                 east_inner = lng + me.patch_size,
                 west_inner = lng)

# North polar cap: a single patch covering everything north of pole_lat.
me.Patch(global_summits = summits,
         north_inner = 90,
         south_inner = pole_lat)