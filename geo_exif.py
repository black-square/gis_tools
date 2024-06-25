# py -3 -m pip install --upgrade pip
# py -3 -m pip install exifread pandas geopy

# HEIC read error: 
#   File "c:\Python39Miniconda\lib\site-packages\exifread\heic.py", line 171, in get_parser
#     return defs[box.name]
# KeyError: 'hdlr'
# Solution: py -3 -m pip install -U "exifread<3"

import argparse
import exifread
import webbrowser

def convert_coords_to_float(coord, ref):
    res = coord.values[0] + coord.values[1] / 60 + coord.values[2] / 3600

    if ref.values in ('S', 'W'):
        res = -res

    return float(res)

def get_coordinates(filepath):
    with open(filepath, 'rb') as f:
        tags = exifread.process_file(f, details=False)
        latitude_ref = tags.get('GPS GPSLatitudeRef', None)
        latitude = tags.get('GPS GPSLatitude', None)
        longitude_ref = tags.get('GPS GPSLongitudeRef', None)
        longitude = tags.get('GPS GPSLongitude', None)

        if latitude and longitude and latitude_ref and longitude_ref:
            lat_decimal_degrees = convert_coords_to_float(latitude, latitude_ref)
            long_decimal_degrees = convert_coords_to_float(longitude, longitude_ref)

            return (lat_decimal_degrees, long_decimal_degrees)
        else:
            return None

def get_address(coordinates):
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="myGeocoder")
    location = geolocator.reverse(coordinates)
    address = location.raw['address']

    return address

def main():
    parser = argparse.ArgumentParser( description="Parse EXIF geotag" )

    parser.add_argument( 'file', nargs='+', help='Files to process' )
    parser.add_argument( '--get_address', action='store_true', help='Display address instead' )
    parser.add_argument( '--to_csv', metavar='FILE', help="Export to CSV" )

    args = parser.parse_args()
    
    dataset = []

    for filepath in args.file:
        item = {'filepath': filepath} 
        dataset.append(item)
        
        coordinates = get_coordinates(filepath)

        if not coordinates:
            continue

        item['coordinates'] = '{:.6f},{:.6f}'.format(coordinates[0], coordinates[1])

        if args.get_address:
            address = get_address(coordinates)
            item['address'] = address
        else:
            url = f'https://www.google.com/maps/search/?api=1&query={coordinates[0]},{coordinates[1]}'
            webbrowser.open_new_tab(url)

    import pandas as pd
    df = pd.json_normalize(dataset, sep='.')

    if args.to_csv:
        df.to_csv(args.to_csv, encoding='utf-8')
    else:
        print(df.to_string())


if __name__ == '__main__':
    main()