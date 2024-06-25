# -*- coding: UTF-8 -*-

import os
import json
import sys
import glob
import xml.etree.ElementTree as ET
from collections import namedtuple
import zipfile
import re
import urllib.request
import util

#https://developers.google.com/maps/billing-and-pricing/billing
GOOGLE_MAPS_KEY = None
GOOGLE_MAPS_PLACES_CACHE_FILE="~/.google_maps_places_cache.json"
GOOGLE_MAPS_PLACES_CACHE = {}

Label = namedtuple("Label", ["coords", "props"])

class Labels:
    MaxDistance = 30

    def __init__( self, fileContents ):
        src = json.loads(fileContents.decode())
        self.data = [Label(f['geometry']['coordinates'][::-1], f['properties']) for f in src["features"]]

    def ExtractReplacement(self, coords):
        for i, l in enumerate(self.data):
            if  util.Distance(l.coords, coords) <= self.MaxDistance:
                del self.data[i]
                return l.props

        return None

class PointInfo:
    def __init__( self, name ):
        self.name = name
        self.desc = ''

    @classmethod
    def FromPointAndLabel(cls, point, label):
        loc = point.get("location", {})
        name = loc.get("name", '') or point.get("name", '')
        pi = cls(name)

        if label:
            oldname = pi.name
            pi.name = label["name"]

            pi._AddDesc(label.get("address"))

            if any(c.isalpha() for c in oldname):
                pi._AddDesc(oldname)


        pi._AddDesc(loc.get("name"))
        pi._AddDesc(loc.get("address"))

        pi._AddDesc(point.get("name"))
        pi._AddDesc(point.get("address"))
        pi._AddDesc(point.get("date"))
        return pi

    @classmethod
    def FromLabel(cls, label):
        pi = cls(label["name"])
        pi._AddDesc(label.get("address"))
        return pi

    def _AddDesc( self, n ):
        if n and n not in self.name and n not in self.desc:
            if self.desc:
                self.desc += '\n'
                
            self.desc += n          

def ExportPoint(root, coords, pi):
    if not pi.name:
        print(f"Point without a name: {coords}")

    wpt = ET.SubElement(root, 'wpt', attrib={'lat':str(coords[0]), 'lon':str(coords[1])})
    ET.SubElement(wpt, 'name').text = pi.name
    
    if pi.desc:
        ET.SubElement(wpt, 'desc').text = pi.desc

def FindFile( path ):
    if path.endswith('.zip'):
        return path

    path = os.path.join( path, "takeout*.zip" )
    res = glob.glob(path)
    res.sort( reverse = True )

    if res:
        return res[0]

    raise EnvironmentError("Nothing has been found on path '{}'".format(path))

def ReadAtLeastOneFromArchive(archive, fileList):
    for file in fileList:
        try:
            return archive.read(file)
        except KeyError as e:
            print( str(e) )
    
    raise KeyError( "None file from the list has been found: " + str(fileList))

COORDS_PATTERN = re.compile(r'(-?\d+\.\d+),(-?\d+\.\d+)')

def ParseCoordsFromUrl(url):
    match = COORDS_PATTERN.search(url)

    if not match:
        return None

    latitude = float(match.group(1))
    longitude = float(match.group(2))
    return [latitude, longitude]
        

NAME_DATA_PATTERN = re.compile(r'/([^/]*)/@(-?\d+\.\d+),(-?\d+\.\d+)')

def FindNameAndCoords(data):
    match = NAME_DATA_PATTERN.search(data)

    if not match:
        return None, None, None
    
    name = match.group(1)
    latitude = float(match.group(2))
    longitude = float(match.group(3))
    return name.replace('+', ' '), [latitude, longitude], match.group(0)

PLACEID_PATTERN = re.compile(r'((?:ftid|cid)=[^&]+)')

def ExtractPlaceId(url):
    match = PLACEID_PATTERN.search(url)

    if not match:
        return None

    return match.group(1)

def WebRequest(url):
    try:
        print("Requesting content from url: ", url.replace(GOOGLE_MAPS_KEY, "*******"), " ... ", end=' ')
        print('OK')
        return urllib.request.urlopen(url).read().decode()
    except Exception as e:
        print('error: ', str(e))
        return None       

def LookupGoogleMapsAPI(url, properties):
    placeId = ExtractPlaceId(url)

    if not placeId or not GOOGLE_MAPS_KEY:
        return None

    contents = GOOGLE_MAPS_PLACES_CACHE.get(placeId)

    if not contents:
        url = f"https://maps.googleapis.com/maps/api/place/details/json?{placeId}&key={GOOGLE_MAPS_KEY}&fields=formatted_address%2Cname%2Cgeometry"
        contents = WebRequest(url)
        GOOGLE_MAPS_PLACES_CACHE[placeId] = contents
        util.save_json(GOOGLE_MAPS_PLACES_CACHE_FILE, GOOGLE_MAPS_PLACES_CACHE)

    if not contents:
        return None

    res = json.loads(contents).get('result')

    if not res:
        return None

    location = res.get('geometry').get('location')

    if not properties.get('name'):
        properties['name'] = res.get('name')

    if not properties.get('address'):
        properties['address'] = res.get('formatted_address')

    coords = [location['lat'], location['lng']]

    return coords

def LookupGoogleMapsDirect(url, properties):
    contents=GOOGLE_MAPS_PLACES_CACHE.get(url)

    if not contents:
        contents = WebRequest( util.fix_url(url) )

        if not contents:
            return None

        name, coords, found_str = FindNameAndCoords(contents)

        GOOGLE_MAPS_PLACES_CACHE[url] = found_str if found_str else 'ERORR'
        util.save_json(GOOGLE_MAPS_PLACES_CACHE_FILE, GOOGLE_MAPS_PLACES_CACHE)
    else:
        name, coords, _ = FindNameAndCoords(contents)

    if not coords:
        return None

    if not properties.get('name'):
        properties['name'] = name

    return coords

def LookupOSM(coords, properties):
    #https://nominatim.org/release-docs/latest/api/Reverse/
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={coords[0]}&lon={coords[1]}&zoom=18&addressdetails=1&extratags=1&namedetails=1"

    contents=GOOGLE_MAPS_PLACES_CACHE.get(url)

    if not contents:
        contents = WebRequest(url)
        GOOGLE_MAPS_PLACES_CACHE[url] = contents
        util.save_json(GOOGLE_MAPS_PLACES_CACHE_FILE, GOOGLE_MAPS_PLACES_CACHE)

    if not contents:
        return None

    res = json.loads(contents)

    if not res:
        return None

    if res.get('error'):
        return None

    address_short = []
    addr = res.get('address',{})
    
    if addr.get('house_number'):
        address_short.append(addr['house_number'])

    if addr.get('road'):
        address_short.append(addr['road'])

    address_short = ', '.join(address_short)
    address = res.get('display_name')

    name = res.get('name') or address_short or address

    if not properties.get('name'):
        properties['name'] = name

    if not properties.get('address'):
        properties['address'] = address
    
    return name

def ExtractCoordsAndProps(f):
    coords = f['geometry']['coordinates']
    properties = f['properties']
    coords.reverse() #coords are mixed in the data file
    
    if coords != [0, 0]:
        return coords, properties

    url = properties.get('google_maps_url')
    
    if not url:
        return None, "NO_URL"
    
    #We cannot use direct requsts only instead API ones as it quickly reaches
    #the limit of requests from single IP address
    coords = ( ParseCoordsFromUrl(url) or
        LookupGoogleMapsAPI(url, properties) or
        LookupGoogleMapsDirect(url, properties) )
    
    if coords:
        return coords, properties

    return None, url

def main():
    if len(sys.argv) >= 3:
        srcPath = sys.argv[1]
        outFile = sys.argv[2]
        prettyXmlOutput = True
    else:
        srcPath = '/storage/emulated/0/Download/'
        outFile = '/storage/emulated/0/Android/data/net.osmand.plus/files/tracks/import/GoogleMapsExport.gpx'
        prettyXmlOutput = False #toprettyxml is broken for QPython3

    srcPath = util.ExpandPath(srcPath)
    outFile = util.ExpandPath(outFile)

    srcFile = FindFile(srcPath)

    print( "Loading from '{}'".format(srcFile) )

    archive = zipfile.ZipFile(srcFile, 'r')
    contents = ReadAtLeastOneFromArchive(archive, [
        'Takeout/Maps (your places)/Saved Places.json',
        'Takeout/Карты (ваши места)/Сохраненные места.json' 
    ])

    src = json.loads(contents.decode())

    contents = ReadAtLeastOneFromArchive(archive, [
        'Takeout/Maps/My labeled places/Labeled places.json',
        'Takeout/Карты/Места с ярлыками/Места с ярлыками.json'
    ])

    try:
        global GOOGLE_MAPS_KEY
        GOOGLE_MAPS_KEY = util.read_file("~/.ssh/google_maps_key.txt")
    except FileNotFoundError as e:
        print("Google Maps API key hasn't been found: ", str(e))

    try:
        global GOOGLE_MAPS_PLACES_CACHE
        GOOGLE_MAPS_PLACES_CACHE = util.load_json(GOOGLE_MAPS_PLACES_CACHE_FILE)
    except FileNotFoundError as e:
        print("Google Maps Cache hasn't been found: ", str(e))
    
    labels = Labels(contents)
    
    pointsRoot = src["features"]

    print("Loaded {} points and {} labels".format(len(pointsRoot), len(labels.data)))

    root = ET.Element('gpx', attrib={'version':'1.1'})
    tree = ET.ElementTree(root)
    unknownUrs = []

    for f in pointsRoot:
        coords, properties = ExtractCoordsAndProps(f)
        
        if not coords:
            unknownUrs.append(properties)
            continue

        label = labels.ExtractReplacement(coords)
        pi = PointInfo.FromPointAndLabel(properties, label)

        if not pi.name:
            if ( LookupGoogleMapsDirect(properties.get('google_maps_url'), properties) or
                LookupOSM(coords, properties) ):
                pi = PointInfo.FromPointAndLabel(properties, label)

        ExportPoint(root, coords, pi)

    print(f"Unknown coords points: {len(unknownUrs)}")

    for u in unknownUrs:
        print(f"   {u}")

    print("{} labels haven't been merged:".format(len(labels.data)))

    for l in labels.data:
        print("   {}: {}".format(l.props["name"], l.coords))
        pi = PointInfo.FromLabel(l.props)
        ExportPoint(root, l.coords, pi)

    print( "Exported {} waypoints".format(len(root)) )
    util.WriteXML( tree, outFile, prettyXmlOutput )
    print( "Saved to '{}'".format(outFile) )

if __name__ == '__main__':
    main( )