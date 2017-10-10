#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import xml.etree.ElementTree as ET

def sortchildrenby(parent, attr):
    def sortlmb( child ):
      name = child.find(attr)
      
      if name is None:
          print('<{} lat="{}" lon="{}"'.format(child.tag, child.get('lat'), child.get('lon')))

      return child.find(attr).text
      
    res = sorted(parent, key=sortlmb)
    parent[:] = res
   
tree = ET.parse(sys.argv[1])
root = tree.getroot()

sortchildrenby(root, 'name')

for e in root:
    ext = e.find('extensions')
    
    if ext is not None:
      e.remove(ext)
    

tree.write(sys.argv[2], encoding="UTF-8", xml_declaration=True)
