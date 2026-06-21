"""
Calibrates the atmospheric light curvature factor k against the confirmed extreme
lines of sight assembled by confirmed_los_parser.py.

For each confirmed line of sight (with manually filled coordinates), this finds the
largest light curvature k -- the straightest light, i.e. the least bending -- at
which the line of sight is still valid (geometrically unobstructed and above the
contrast threshold). The overall calibration is the smallest such k across every
confirmed line of sight: the largest k that leaves all of them unobstructed.

Reads data/clean/known_los.csv (the completed parser output) and writes
data/clean/known_los_with_curvature.csv.
"""

import pandas as pd
import commons as me

IN_PATH = '../data/clean/known_los.csv'
OUT_PATH = '../data/clean/known_los_with_curvature.csv'

MAX_CURVATURE = 7.7   # largest k to test (straightest light, least bending)
MIN_CURVATURE = 1.0   # smallest k to test (most bending, best line-of-sight conditions)
CURVATURE_STEP = 0.1

confirmed_los = pd.read_csv(IN_PATH)
print('\n')
print(f'Loaded {len(confirmed_los)} confirmed lines of sight from {IN_PATH}.')
print('\n')

# Drop lines of sight where the observer or target could not be pinpointed.
confirmed_los = confirmed_los.dropna(subset=['from_latitude', 'from_longitude', 'to_latitude', 'to_longitude'])
print(f'{len(confirmed_los)} remain after dropping those without observer/target coordinates.')
print('\n')

# Drop lines of sight whose reported distance disagrees with the distance implied
# by the identified coordinates by more than 1 km.
def get_confirmed_los_distance(los):
    return me.geod.line_length([los.from_longitude, los.to_longitude],
                               [los.from_latitude, los.to_latitude])

confirmed_los['distance_reported'] = confirmed_los.distance
confirmed_los['distance_true'] = round(confirmed_los.apply(get_confirmed_los_distance, axis=1) / 1000, 3)  # km
confirmed_los = confirmed_los.query('abs(distance_true - distance) < 1')
print(f'{len(confirmed_los)} remain after dropping those whose reported and measured distances disagree by >1 km.')
print('\n')

# For each line of sight, record the largest k at which it is still valid. Sweep k
# downward from the straightest light; the first k that validates a line of sight
# is its largest, so record it and stop testing that line of sight.
confirmed_los['curvature'] = None
test_curvature = MAX_CURVATURE

while confirmed_los.curvature.isna().any() and test_curvature >= MIN_CURVATURE:

    print(f'Testing k = {round(test_curvature, 1)} -- {confirmed_los.curvature.isna().sum()} line(s) of sight still unresolved.')

    for i in confirmed_los.index[confirmed_los.curvature.isna()]:
        los = confirmed_los.loc[i]

        observer = me.Summit(latitude=los.from_latitude,
                             longitude=los.from_longitude,
                             elevation=los.from_elevation)
        target = me.Summit(latitude=los.to_latitude,
                           longitude=los.to_longitude,
                           elevation=los.to_elevation)

        line_of_sight = me.LineOfSight(observer, target, light_curvature=test_curvature, shaded_ratio=0.5)
        line_of_sight.process_full_line_of_sight()

        if line_of_sight.is_valid():
            confirmed_los.at[i, 'curvature'] = round(test_curvature, 1)

    test_curvature -= CURVATURE_STEP

print('\n')

unresolved = confirmed_los.curvature.isna().sum()
if unresolved:
    print(f'{unresolved} line(s) of sight stayed invalid down to k = {MIN_CURVATURE}.')

resolved = confirmed_los.curvature.dropna()
if len(resolved):
    print(f'Calibration k = {resolved.min()} (largest k that keeps every resolved line of sight unobstructed).')

confirmed_los = confirmed_los[['from', 'from_area', 'from_elevation', 'from_latitude', 'from_longitude',
                               'to', 'to_area', 'to_elevation', 'to_latitude', 'to_longitude',
                               'distance_reported', 'distance_true', 'curvature']]

print('\n')

confirmed_los.to_csv(OUT_PATH, index=False)
print(f'Wrote {OUT_PATH}.')
print('\n')
