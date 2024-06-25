import os
import json
import math
from urllib.parse import urlsplit, urlunsplit, quote
from xml.dom import minidom
import xml.etree.ElementTree as ET

def Distance(coords1, coords2):
    #Haversine formula
    #https://stackoverflow.com/a/21623206/3415353
    p = math.pi / 180

    lat1 = coords1[0]
    lon1 = coords1[1]
    lat2 = coords2[0]
    lon2 = coords2[1]

    a = 0.5 - math.cos((lat2-lat1)*p)/2 + math.cos(lat1*p) * math.cos(lat2*p) * (1-math.cos((lon2-lon1)*p))/2
    return 12742000 * math.asin(math.sqrt(a))

def ExpandPath( path ):
    return os.path.expandvars( os.path.expanduser(path) )

def read_file(file_name):
    with open(ExpandPath(file_name), 'r', encoding="utf-8") as f:
        return f.read()

def save_json( file_name, data ):  
    with open(ExpandPath(file_name), 'w', encoding='utf-8') as file:  
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_json( file_name ):  
    with open(ExpandPath(file_name), encoding='utf-8') as file:
        data = json.load(file)

    return data 

def loads_json(string_data):
    return json.loads(string_data) 

def fix_url(url):
    """
    Convert non-ASCII characters only to percent-encodings.
    And space to plus sign.
    """
    scheme, netloc, path, query, fragment = urlsplit(url)
    path = quote(path, safe="/")
    query = quote(query, safe="=&")
    return urlunsplit((scheme, netloc, path, query, fragment))

def WriteXML(tree, outFile, prettyXmlOutput):
    if not prettyXmlOutput:
        tree.write(outFile, encoding="UTF-8", xml_declaration=True)
    else:
        xmlstr = minidom.parseString(ET.tostring(tree.getroot())).toprettyxml(indent="   ")
        with open(outFile, "w", encoding="UTF-8") as f:
            f.write(xmlstr)
