"""
Assembles the confirmed extreme lines of sight used to calibrate atmospheric light
curvature (see confirmed_los_analysis.py).

Reads the saved Beyond Horizons table, keeps only the lines of sight backed by
photographic evidence, splits each FROM/TO description into name / area / elevation,
and appends a few extra confirmed lines of sight not catalogued by Beyond Horizons.

Beyond Horizons lists only names, areas, and elevations, so the latitude/longitude
columns are written empty and are filled in by hand afterwards. The completed file
is consumed by confirmed_los_analysis.py.

NOTE: this overwrites data/clean/known_los.csv, including any coordinates already
filled in manually. Run it once, then annotate the output.
"""

import pandas as pd
from io import StringIO

RAW_PATH = '../data/raw/beyond_horizons.txt'
OUT_PATH = '../data/clean/known_los.csv'

# Beyond Horizons' table was saved as HTML; read it back into a DataFrame.
with open(RAW_PATH, 'r', encoding='utf-8') as f:
    raw_los = pd.read_html(StringIO(f.read()))[0]
print(f'Read {len(raw_los)} lines of sight from Beyond Horizons ({RAW_PATH}).')

# Keep only lines of sight with photographic evidence (a non-empty POST column).
confirmed_los = raw_los.dropna(subset=['POST']).copy()
print(f'{len(confirmed_los)} of those are confirmed by photograph.')

# DIST looks like "1234 km"; keep the leading integer number of kilometres.
confirmed_los = confirmed_los.rename(columns={'DIST': 'distance'})
confirmed_los['distance'] = confirmed_los['distance'].str[:-4].astype(int)

# FROM/TO look like "Name - 1234 m. Area"; split into name, area, and elevation.
from_split1 = confirmed_los['FROM'].str.split(r'm\.\s*', expand=True)
from_split2 = from_split1[0].str.split(r'\s*–\s*', expand=True)
confirmed_los['from'] = from_split2[0]
confirmed_los['from_area'] = from_split1[1]
confirmed_los['from_elevation'] = from_split2[1]

to_split1 = confirmed_los['TO'].str.split(r'm\.\s*', expand=True)
to_split2 = to_split1[0].str.split(r'\s*–\s*', expand=True)
confirmed_los['to'] = to_split2[0]
confirmed_los['to_area'] = to_split1[1]
confirmed_los['to_elevation'] = to_split2[1]

confirmed_los = confirmed_los.drop_duplicates()

# Coordinates are not provided by Beyond Horizons; these are filled in manually.
confirmed_los['from_latitude'] = None
confirmed_los['from_longitude'] = None
confirmed_los['to_latitude'] = None
confirmed_los['to_longitude'] = None

confirmed_los = confirmed_los[['from', 'from_area', 'from_elevation', 'from_latitude', 'from_longitude',
                               'to', 'to_area', 'to_elevation', 'to_latitude', 'to_longitude',
                               'distance']]

# A few confirmed extreme lines of sight not catalogued by Beyond Horizons.
confirmed_los.loc[len(confirmed_los)] = ['Marcy', 'New York (US)', 1629, 44.11275, -73.92371,
                                         'Washington', 'New Hampshire', 1916, 44.27049, -71.30327,
                                         210]

confirmed_los = confirmed_los.sort_values('distance', ascending=False)
print(f'There are {len(confirmed_los)} confirmed extreme lines of sight for atmospheric light curvature analysis.')

confirmed_los.to_csv(OUT_PATH, index=False)
print(f'Wrote {OUT_PATH}. Fill in the latitude/longitude columns by hand, then run confirmed_los_analysis.py.')
