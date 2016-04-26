#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
import re
import codecs
import json

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
INTEGER_KEYS = ['maxspeed', 'frequency', 'layer', 'tracks', 'gauge']

postcode_pattern = re.compile(r'(LV)*[-]?\s*(\d{4})')

def clean_postcode(postcode):
    matches = postcode_pattern.findall(postcode)
    postcodes = map(lambda x: 'LV-' + x[1], matches)

    if len(postcodes) == 1:
        return postcodes[0]
    elif len(postcodes) > 1:
        return postcodes
    else:
        return None

def shape_node_attributes(element, node):
    for key, value in element.attrib.iteritems():

        if key in CREATED:
            if 'created' not in node:
                node['created'] = dict()
            node['created'][key] = value

        elif key == 'lat' or key == 'lon':
            if 'pos' not in node:
                node['pos'] = [None, None]

            index = 0 if key == 'lat' else 1
            node['pos'][index] = float(value)
        else:
            node[key] = value

class SpecialCaseException(Exception):
    pass

def convert_value_if_applicable(key, value):
    if key in INTEGER_KEYS:
        value = int(value)

    elif key == 'lanes':
        try:
            value = int(value)
        except:
            value = value.split('|')

    elif key == 'capacity':
        if value in ['~50', '3-4', 'daudz']:
            raise SpecialCaseException()
        else:
            value = int(value)

    elif key == 'voltage':
        if value == '110000;fixme':
            value = 110000
        else :
            try:
                value = int(value)
            except:
                value = map(int, value.split(';'))

    elif key == 'building:levels':
        if value in ['2B', '1;2']:
            raise SpecialCaseException()
        else:
            value = float(value)

    elif value == 'yes':
        value = True

    elif value == 'no':
        value = False

    return value

def shape_node_tags(element, node):
    for tag in element.iter("tag"):
        key = tag.attrib['k']

        if problemchars.search(key):
            continue

        value = tag.attrib['v']

        try:
            value = convert_value_if_applicable(key, value)
        except SpecialCaseException:
            # Discarded special case
            continue

        if key.startswith('addr:'):
            key = key.replace('addr:', '')

            if ':' not in key:
                if 'address' not in node:
                    node['address'] = {}

                if key == 'postcode':
                    postcode = clean_postcode(value)
                    if postcode:
                        node['address']['postcode'] = postcode
                else:
                    node['address'][key] = value
        else:
            d = node
            keys = key.split(':')

            #Reserved key for resolving nested object and explicit value conflicts
            assert all(key != 'value' for key in keys)

            for inner_key in keys[:-1]:
                if inner_key in d and type(d[inner_key]) != dict:
                    old_value = d[inner_key]
                    d[inner_key] = dict(value=old_value)
                elif inner_key not in d:
                    d[inner_key] = dict()

                d = d[inner_key]

            final_key = keys[-1]

            if final_key in d and type(d[final_key]) == dict:
                d[final_key]['value'] = value
            else:
                d[final_key] = value

def shape_way_node_refs(element, node):
    for nd_tag in element.findall('nd'):
        if 'node_refs' not in node:
            node['node_refs'] = []

        node['node_refs'].append(nd_tag.attrib['ref'])

def shape_element(element):
    node = {}
    if element.tag == "node" or element.tag == "way" :
        node['type'] = element.tag

        shape_node_attributes(element, node)
        shape_node_tags(element, node)

        if element.tag == "way":
            shape_way_node_refs(element, node)

        return node
    else:
        return None

def process_map(file_in, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    count = 1000
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")

            # count -= 1
            if count ==0 :
                break
    return data

if __name__ == "__main__":
    data = process_map('riga_latvia.osm', False)
