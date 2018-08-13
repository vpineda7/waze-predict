import pandas as pd
import json
from ast import literal_eval
from pprint import pprint
from math import floor
from math import sqrt
from uuid import uuid4

### THINGS TO CHANGE TO FINE GRAIN
# digits = place it rounds to. increase for smaller boxes
# buff = % buffer before it considers it close to the edge. increase for more boxes
# if buff = 0.05, any point calculated within 5% of the edge of the bounding box
# will be considered on the border and it will place another box next to it
# step = step used to calculate points along a line. decreasing this will make the
# program take longer to run, but it will have less points where the line gets within
# the buffer without triggering another box next to it. increasing passed 1 is not 
# recommended
digits = 3
buff = 0.05
step = 0.5


ratio = 10 ** digits
my_floor = lambda x: floor(x*ratio)/ratio

streets = dict()
base_streets = []

db = pd.read_csv("la_streets.csv")
l = len(db['path'])

def increment(square):
    x_0 = square[0]
    y_0 = square[1]
    x_1 = (square[0]*ratio+1)/ratio
    y_1 = (square[1]*ratio+1)/ratio
    return ((x_0,x_1),(y_0,y_1))

def check_border(point, square):
    total_square = increment(square)
    x = total_square[0]
    y = total_square[1]
    x_buff = ((x[1]*ratio-x[0]*ratio)/ratio)*buff
    y_buff = ((y[1]*ratio-y[0]*ratio)/ratio)*buff
    squares = set()
    squares.add(square)
    # adjacent
    if point[0] < x[0] + x_buff:
        x_new = round((square[0]*ratio-1)/ratio, digits)
        y_new = square[1]
        squares.add((x_new,y_new))
    if point[0] > x[1] - x_buff:
        x_new = round((square[0]*ratio+1)/ratio, digits)
        y_new = square[1]
        squares.add((x_new,y_new))
    if point[1] < y[0] + y_buff:
        x_new = square[0]
        y_new = round((square[1]*ratio-1)/ratio,digits)
        squares.add((x_new,y_new))
    if point[1] > y[1] - y_buff:
        x_new = square[0]
        y_new = round((square[1]*ratio+1)/ratio,digits)
        squares.add((x_new,y_new))
    # diagonal
    if point[0] < x[0] + x_buff and point[1] < y[0] + y_buff:
        x_new = round((square[0]*ratio-1)/ratio, digits)
        y_new = round((square[1]*ratio-1)/ratio,digits)
        squares.add((x_new,y_new))
    if point[0] > x[1] - x_buff and point[1] > y[1] - y_buff:
        x_new = round((square[0]*ratio+1)/ratio, digits)
        y_new = round((square[1]*ratio+1)/ratio,digits)
        squares.add((x_new,y_new))
    if point[0] < x[0] + x_buff and point[1] > y[1] - y_buff:
        x_new = round((square[0]*ratio-1)/ratio, digits)
        y_new = round((square[1]*ratio+1)/ratio,digits)
        squares.add((x_new,y_new))
    if point[0] > x[1] - x_buff and point[1] < y[0] + y_buff:
        x_new = round((square[0]*ratio+1)/ratio, digits)
        y_new = round((square[1]*ratio-1)/ratio,digits)
        squares.add((x_new,y_new))

    return squares

def cover_path(path):
    squares = set()
    for i in range(0,len(path)-1):
        start = (path[i]['x'],path[i]['y'])
        end = (path[i+1]['x'],path[i+1]['y'])
        # round down to get start and end points
        # remember we can uniquely identify these by coordinates of upper left corner
        start_square = tuple(map(my_floor, start))
        end_square = tuple(map(my_floor, end))
        start_squares = check_border(start,start_square)
        end_squares = check_border(end,end_square)
        for start_square in start_squares:
            squares.add(start_square)
        for end_square in end_squares:
            squares.add(end_square)
        total_start = increment(start_square)
        total_start_x = total_start[0]
        total_start_y = total_start[1]
        total_end = increment(end_square)
        total_end_x = total_end[0]
        total_end_y = total_end[1]
        diff = 1/ratio
        slope = (start[1] - end[1])/(start[0] - end[0])
        f = lambda x: x*slope + (start[1] - start[0]*slope)
        # parameterize line from start to end as f(t)
        # let f(0) = start
        delta_x = end[0] - start[0]
        delta_y = end[1] - start[1]
        dist = sqrt(delta_x*delta_x + delta_y*delta_y)
        f = lambda t: ((delta_x/dist)*t + start[0],
                       (delta_y/dist)*t + start[1])
        square = start_square
        t = 0
        while t <= dist:
            if square not in squares:
                squares[square] = []
            t += step/ratio
            point = f(t)
            square = tuple(map(my_floor,point))
            more_squares = check_border(point,square)
            for ms in more_squares:
                squares.add(ms)
    return squares

def handle_row(r):
    path = literal_eval(r['path'])
    street = r['street']
    if type(street) is not str:
        street = "N/A"
    base_streets.append((path,street,r['type']))
    squares = cover_path(path)
    for s in squares:
        if s not in streets:
            street_list = set()
            street_list.add(street)
            ty = set()
            ty.add(r['type'])
            streets[s] = (street_list, ty)
        else:
            st,ty = streets[s]
            collision = True
            st.add(street)
            ty.add(r['type'])
            streets[s] = st,ty


print("Phase 1. Bucketing data.")
wilshire = db['street'].str.contains("Wilshire",na=False)
vermont = db['street'].str.contains("Vermont",na=False)
section = db[vermont].append(db[wilshire])
for i,r in db.iterrows():
    if i%5000 == 0:
        print("{} of {}".format(i,l))
    to_examine = 100
    handle_row(r)
    """
    if i==to_examine:
        handle_row(r)
    """

print("Phase 2. Generating file.")
geojson = {}
geojson['type'] = "FeatureCollection"
features = []
diff = 1/ratio
i = 0
l = len(streets.keys())
csv_df = {"coordinates" : [], "streets": [], "type": [], "intersection": []}
for k,v in streets.items():
    if i%50000 == 0:
        print("{} of {}".format(i,l))
    i += 1
    csv_df['coordinates'].append(k)
    csv_df['streets'].append(v[0])
    csv_df['type'].append(v[1])
    if len(v[0]) > 1:
        csv_df['intersection'].append(1)
    else:
        csv_df['intersection'].append(0)
pd.DataFrame(csv_df).to_csv("data/street_grid.csv",index=False)
   
"""
for k,v in streets.items():
    if i%50000 == 0:
        print("{} of {}".format(i,l))
    full_square = increment(k)
    x = full_square[0]
    y = full_square[1]
    i += 1
    feature = {}
    feature['type'] = "Feature"
    feature['geometry'] = {}
    feature['geometry']['type'] = "Polygon"
    feature['geometry']['coordinates'] = [
            [
                [x[0], y[0]],
                [x[1], y[0]],
                [x[1], y[1]],
                [x[0], y[1]],
                [k[0], y[0]]
            ]
        ]
    feature['properties'] = {}
    feature['properties']['street'] = v[0]
    feature['properties']['type'] = v[1]
    features.append(feature)
for p,s,t in base_streets:
    feature = {}
    feature['type'] = "Feature"
    feature['geometry'] = {}
    feature['geometry']['type'] = "LineString"
    feature['geometry']['coordinates'] = []
    for d in p:
        feature['geometry']['coordinates'].append([d['x'],d['y']])
    feature['properties'] = {}
    feature['properties']['street'] = s
    feature['properties']['type'] = t
    feature['properties']['path'] = str(p)
    features.append(feature)


geojson['features'] = features

with open("geojsons/streets.geojson","w") as f:
    f.write(json.dumps(geojson, indent=4))
"""
