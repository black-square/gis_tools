# -*- coding: UTF-8 -*-

import json
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile

def Add( s, n ):
    if n:
        s += n
        s += '\n'
    
    return s

if len(sys.argv) >= 3:
    inFile = sys.argv[1]
    outFile = sys.argv[2]
    prettyXmlOutput = True
else:
    inFile = '/storage/emulated/0/Download/takeout.zip'
    outFile = '/storage/emulated/0/Android/data/net.osmand.plus/files/tracks/import/GoogleMapsExport.gpx'
    prettyXmlOutput = False #toprettyxml is broken for QPython3

if inFile.endswith('.zip'):
    archive = zipfile.ZipFile(inFile, 'r')
    contents = archive.read('Takeout/Карты (ваши отзывы и места)/Сохраненные места.json')
    src = json.loads(contents.decode())
else:
    with open(inFile) as json_file:
        src = json.load(json_file)

root = ET.Element('gpx', attrib={'version':'1.1'})
tree = ET.ElementTree(root)

for f in src["features"]:
    coords = f['geometry']['coordinates']
    wpt = ET.SubElement(root, 'wpt', attrib={'lat':str(coords[1]), 'lon':str(coords[0])})

    props = f['properties']
    name = props.get("Title")
    ET.SubElement(wpt, 'name').text = name

    desc = ''
    loc = props.get("Location")

    if loc:
        bn = loc.get("Business Name")

        if bn != name:
            desc = Add(desc, bn)
            
        desc = Add(desc, loc.get("Address"))

    desc = Add(desc, props.get("Updated"))
    ET.SubElement(wpt, 'desc').text = desc.strip()

if not prettyXmlOutput:
    tree.write(outFile, encoding="UTF-8", xml_declaration=True)
else:
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
    with open(outFile, "w", encoding="UTF-8") as f:
        f.write(xmlstr)

print( "Converted {} elements".format(len(root.getchildren())) )