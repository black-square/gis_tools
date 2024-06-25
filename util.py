import os
import json
from urllib.parse import urlsplit, urlunsplit, quote

def read_file(file_name):
    with open(os.path.expanduser(file_name), 'r', encoding="utf-8") as f:
        return f.read()

def save_json( file_name, data ):  
    with open(os.path.expanduser(file_name), 'w', encoding='utf-8') as file:  
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_json( file_name ):  
    with open(os.path.expanduser(file_name), encoding='utf-8') as file:
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
