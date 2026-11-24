import xml.dom.minidom
from typing import Dict, List
import requests
import json

"""
This module contains utility functions for reading and writing XML files.
"""

# read an XML file and return the content as a string.

def read_xml(file_path):
    with open(file_path, 'r') as file:
        return file.read()

# write a string to an XML file.

def write_xml(file_path, xml_string):
    with open(file_path, 'w') as file:
        file.write(xml_string)

# parse an XML string and return a DOM object.

def parse_xml(xml_string):
    return xml.dom.minidom.parseString(xml_string)

# read an XML file and write it back with indentation.
# output_path defaults to the input file.

def format_xml(file_path, output_path=None, indent="  "):
    if output_path is None:
        output_path = file_path
    dom = parse_xml(read_xml(file_path))
    pretty_xml = dom.toprettyxml(indent=indent)
    lines = [line for line in pretty_xml.splitlines() if line.strip()]
    write_xml(output_path, "\n".join(lines) + "\n")

# Gets a json file from a url

def get_json(feed_url: str) -> Dict:
    response = requests.get(feed_url)
    return response.json()

# Gets a json file from a local path

def get_local_json(path: str):
    with open(path, 'r') as f:
         return json.load(f)

# Returns the highest timestamp from a list of timestamps

def get_latest_feed(latest: List[str]) -> int:
    # print(max(map(int, latest)))
    if not latest:
        raise ValueError("getLatestFeed expects a non-empty array")
    return max(map(int, latest))

# Uploads data to s3
import boto3

def upload_to_s3(dest: str, buffer: bytes, content_type: str = 'application/json'):
    s3 = boto3.client('s3')
    try:
        s3.put_object(
            Bucket="gdn-cdn",
            Key=dest,
            Body=buffer,
            ContentType=content_type,
            ACL='public-read',
            CacheControl="max-age=30"
        )
        print(f"https://interactive.guim.co.uk/{dest}")
    except Exception as err:
        print(f"Error: {err}")

# Saves a file locally

def save_to_file(dest: str, buffer: bytes):    
    with open(dest, 'wb') as f:
        f.write(buffer)