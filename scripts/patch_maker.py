import pandas as pd
import commons as me

poleLat = me.getPoleLatitude()
latBoundaries = me.getPatchLatBoundaries()
lngBoundaries = me.getPatchLngBoundaries()

summits = pd.read_csv(me.summitFile)

summits['maxHorizonDistance'] = summits.elevation.apply(me.horizonDistance).astype(int)

# Bottom patch
me.Patch(globalSummits = summits,
         northInner = -poleLat,
         southInner = -90)

# Middle patches
for lat in latBoundaries[:-1]:
    for lng in lngBoundaries[:-1]:
        me.Patch(globalSummits = summits,
                 northInner = lat + me.patchSize, 
                 southInner = lat, 
                 eastInner = lng + me.patchSize, 
                 westInner = lng)

# Top patch
me.Patch(globalSummits = summits,
         northInner = 90,
         southInner = poleLat)