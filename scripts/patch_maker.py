import os
import pandas as pd
import commons as me

os.makedirs(me.patch_directory, exist_ok=True)

pole_lat = me.get_pole_latitude()
lat_boundaries = me.get_patch_lat_boundaries()
lng_boundaries = me.get_patch_lng_boundaries()

summits = pd.read_csv(me.summit_file)

summits['max_horizon_distance'] = summits.elevation.apply(me.horizon_distance).astype(int)

# Bottom patch
me.Patch(global_summits = summits,
         north_inner = -pole_lat,
         south_inner = -90)

# Middle patches
for lat in lat_boundaries[:-1]:
    for lng in lng_boundaries[:-1]:
        me.Patch(global_summits = summits,
                 north_inner = lat + me.patch_size, 
                 south_inner = lat, 
                 east_inner = lng + me.patch_size, 
                 west_inner = lng)

# Top patch
me.Patch(global_summits = summits,
         north_inner = 90,
         south_inner = pole_lat)