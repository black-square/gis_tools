# -*- coding: UTF-8 -*-

import os
import json
import sys
import glob
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import namedtuple
import zipfile
import math

def Distance(coords1, coords2):
    #https://stackoverflow.com/a/21623206/3415353
    p = 0.017453292519943295     #Pi/180

    lat1 = coords1[0] * p
    lon1 = coords1[1] * p
    lat2 = coords2[0] * p
    lon2 = coords2[1] * p

    a = math.cos(lat2 - lat1) - math.cos(lat1) * math.cos(lat2) * (1 - math.cos(lon2 - lon1))
    return 12742000 * math.asin(math.sqrt(((1 - a) * 0.5))) #2*R*asin...

Label = namedtuple("Label", ["coords", "props"])

class Labels:
    MaxDistance = 3

    def __init__( self, fileContents ):
        src = json.loads(fileContents.decode())
        self.data = [Label(f['geometry']['coordinates'], f['properties']) for f in src["features"]]

    def ExtractReplacement(self, coords):
        for i, l in enumerate(self.data):
            if  Distance( l.coords, coords) <= self.MaxDistance:
                del self.data[i]
                return l.props

        return None

class PointInfo:
    def __init__( self, name ):
        self.name = name
        self.desc = ''

    @classmethod
    def FromPointAndLabel(cls, point, label):
        pi = cls(point.get("Title"))

        if label:
            oldname = pi.name
            pi.name = label["name"]

            if any(c.isalpha() for c in oldname):
                pi._AddDesc(oldname)

        loc = point.get("Location")

        if loc:
            pi._AddDesc(loc.get("Business Name"))  
            pi._AddDesc(loc.get("Address"))

        if label:
            pi._AddDesc(label.get("address"))

        pi._AddDesc(point.get("Updated"))
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

def WriteXML(tree, outFile, prettyXmlOutput):
    if not prettyXmlOutput:
        tree.write(outFile, encoding="UTF-8", xml_declaration=True)
    else:
        xmlstr = minidom.parseString(ET.tostring(tree.getroot())).toprettyxml(indent="   ")
        with open(outFile, "w", encoding="UTF-8") as f:
            f.write(xmlstr)

def main():
    if len(sys.argv) >= 3:
        srcPath = sys.argv[1]
        outFile = sys.argv[2]
        prettyXmlOutput = True
    else:
        srcPath = '/storage/emulated/0/Download/'
        outFile = '/storage/emulated/0/Android/data/net.osmand.plus/files/tracks/import/GoogleMapsExport.gpx'
        prettyXmlOutput = False #toprettyxml is broken for QPython3

    srcFile = FindFile(srcPath)

    print( "Loading from '{}'".format(srcFile) )

    archive = zipfile.ZipFile(srcFile, 'r')
    contents = archive.read('Takeout/Карты (ваши отзывы и места)/Сохраненные места.json')
    src = json.loads(contents.decode())
    contents = archive.read('Takeout/Карты/Места с ярлыками/Места с ярлыками.json')

    labels = Labels(contents)
    pointsRoot = src["features"]

    print("Loaded {} points and {} labels".format(len(pointsRoot), len(labels.data)))

    root = ET.Element('gpx', attrib={'version':'1.1'})
    tree = ET.ElementTree(root)

    for f in pointsRoot:
        coords = f['geometry']['coordinates']
        coords.reverse() #coords are mixed in the data file
        label = labels.ExtractReplacement(coords)
        pi = PointInfo.FromPointAndLabel(f['properties'], label)
        ExportPoint(root, coords, pi)

    print("{} labels haven't been merged".format(len(labels.data)))

    for l in labels.data:
        pi = PointInfo.FromLabel(l.props)
        ExportPoint(root, l.coords, pi)

    print( "Exported {} waypoints".format(len(root)) )
    WriteXML( tree, outFile, prettyXmlOutput )
    print( "Saved to '{}'".format(outFile) )

if __name__ == '__main__':
    main( )