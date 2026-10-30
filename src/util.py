import xml.dom.minidom

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

