#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import xml.etree.ElementTree as ET
import util

def sortchildrenby(parent):
    def sortlmb( child ):
      coords = [float(child.get('lat')), float(child.get('lon'))]
      return util.Distance(coords, [0, 0])
      
    res = sorted(parent, key=sortlmb)
    parent[:] = res
   
root = ET.fromstring(ET.canonicalize(util.read_file(sys.argv[1]), strip_text=True))
tree = ET.ElementTree(root)

sortchildrenby(root)

for e in root:
    ext = e.find('extensions')
    
    if ext is not None:
      e.remove(ext)
    
util.WriteXML(tree, sys.argv[2], prettyXmlOutput=True)
