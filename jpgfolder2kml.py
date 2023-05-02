#!/usr/bin/env python3

import os, sys

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from pprint import pprint
import lxml.etree as ET
import re 
import mmap 

parser = ET.XMLParser(remove_blank_text=True)

from geopy.distance import distance
from geopy import Point

''' 
    2023-05 creator notes
    
    Script is to assist DJI drone image workflow:
        1) you fly dji drone and shoot images to sd card.
        2) you copy image folder to pc (or open on card)
        3) run this script to generate KML file
        4) open kml in Google Earch Pro:
            see geolocated and altitude-located images as numbered pins
                you can see image clicking on pin. (must open kml from the same folder where images are located)
            see direction of shooting (as 50m red line at ground level)
            see flight path (as blue line with altitude). 

    Developer notes - explain technical decisions:
        1) exif is used for date and gps information.
            it is converted to dictionary with exif-key converted to text key. 
        2) xmp is used for yaw data. 
            xmp is not read by regular exif extraction - using file search here. 
            xmp is "flattened" - all elements are in dictionary root, not cascaded down
            xmp key names are shortened only to include related name
        3) note that gimbalpitch is not availalbe in dji mini 2 data; this is dji intentional decision; 
        4) red line indicating direction is 50m offset to drone yaw direction. in typical situation it should help to understand direction. 
        
''' 



def shift_coordinates(lat: float, lon : float, azimuth : float, offset_m : float):
    start = Point(lat, lon)
    d = distance(meters=offset_m)
    dest = d.destination(point=start, bearing=azimuth)
    return dest

def etree_to_flat_dict(t):
    d = {}
    children = list(t)
    if children:
        for child_t in children: 
            d1 = etree_to_flat_dict(child_t)
            d.update(d1)
    if t.attrib:
        for k, v in t.attrib.items():
            k1 = re.sub(r'\{.*?\}', '', k)
            d[k1] = v
    if t.text:
        text = t.text.strip()
        if text:
            d[t.tag] = text
    return d

def image_exif_to_dict(image):
    d = {}
    for (k,v) in image._getexif().items():
        if TAGS.get(k)=='GPSInfo':
            for k1 in v:
                d[GPSTAGS.get(k1)] = v[k1]
            continue
        if len(str(v)) > 2000: continue
        d[TAGS.get(k)] = v
        #print('%s = %s' % (TAGS.get(k), v))
    return d

def read_xmp2(file_path):
    fd = open(file_path, 'rb')
    d= fd.read()
    xmp_start = d.find(b'<x:xmpmeta')
    xmp_end = d.find(b'</x:xmpmeta')
    xmp_str = d[xmp_start:xmp_end+12]
    return xmp_str 

def read_xmp(file_path):
    with open(file_path, 'rb', 0) as file:
        s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        
        xmp_start = s.find(b'<x:xmpmeta')
        xmp_end = s.find(b'</x:xmpmeta')
        if xmp_start: return s[xmp_start:xmp_end+12].decode()
        return ''

def convert_to_degrees(value):
    d, m, s = value
    return d + (m / 60.0) + (s / 3600.0)
    
def get_usefuldetail(file_path, filename):
    xmp_str = read_xmp(file_path)
    xmp_xml = ET.XML(xmp_str)
    xmp_dict2 = etree_to_flat_dict(xmp_xml)
    
    image = Image.open(file_path)
    exif_dict = image_exif_to_dict(image)
    exif_dict.update(xmp_dict2)
    pprint(exif_dict)
    
    if not exif_dict['GPSLatitude']: 
        raise "No gps data" # not suitable image

    details = {}
    
    details['point'] = Point(
        convert_to_degrees(exif_dict['GPSLatitude']), 
        convert_to_degrees(exif_dict['GPSLongitude']))
    details['alt'] = float(exif_dict['RelativeAltitude'])
    details['yaw'] = float(exif_dict['FlightYawDegree'])

    # point2 is for red vector showing direction of drone
    details['point2'] = distance(meters=50).destination(point = details['point'], bearing = details['yaw'])
    details['DateTime'] = exif_dict['DateTime']

    # point3 and point4 - estimated width of frame. 
    
    FocalLengthIn35mmFilm = exif_dict['FocalLengthIn35mmFilm']
    DigitalZoomRatio = exif_dict['DigitalZoomRatio']
    if FocalLengthIn35mmFilm: 
        if DigitalZoomRatio > 0: 
            FocalLengthIn35mmFilm = FocalLengthIn35mmFilm * DigitalZoomRatio
        meters_side = 50 / FocalLengthIn35mmFilm * (35/2)
        details['point3'] = distance(meters=meters_side).destination(point = details['point2'], bearing = details['yaw'] + 90)
        details['point4'] = distance(meters=meters_side).destination(point = details['point2'], bearing = details['yaw'] - 90)

    iconname = filename
    if iconname.startswith('DJI_'): iconname = iconname[4:]
    if iconname.endswith('.JPG'): iconname = iconname[:-4]
    details['iconname'] = iconname
    details['filename'] = filename
    return details


def process_folder_to_data():
    # create list, with images, will be ordered list
    image_list = []        
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".jpg"): 
            continue
        
        file_path = os.path.join(folder_path, filename)
        
        try: 
            details = get_usefuldetail(file_path, filename)
            image_list.append(details)
            print(f"{filename}: {details['point'].longitude} {details['point'].latitude}")
        except:
            print(f"{filename}: ignored, no GPS information (or yaw or altitude), possibly not DJI file")
    
    image_list.sort(key=lambda x: x['DateTime'])
    return image_list

def list_to_kml(image_list):
    if not image_list: 
        print("No suitable images in folder")
        return
    last_datetime_str = image_list[-1]['DateTime']
    last_datetime_str = last_datetime_str.replace(':','-')
    last_datetime_str = last_datetime_str.replace('_','T')
    kml_filename = 'drone_' + last_datetime_str + '.kml'
    
    kml = ET.Element('kml', {'xmlns': 'http://www.opengis.net/kml/2.2'})
    document = ET.SubElement(kml, 'Document')

    document.append(ET.XML('<Style id="shootline"><LineStyle><color>#7f0000ff</color></LineStyle></Style>'))
    document.append(ET.XML('<Style id="shootside"><LineStyle><color>#7fffff00</color></LineStyle></Style>'))
    document.append(ET.XML('<Style id="flightline"><LineStyle><color>#7fff0000</color><width>3</width></LineStyle></Style>'))

    flightpath_plain = ' '.join([f"{d['point'].longitude},{d['point'].latitude},{d['alt']}" for d in image_list])

    document.append(ET.XML(f'''
        <Placemark>
            <name>flight</name>
            <styleUrl>#flightline</styleUrl>
            <MultiGeometry>
                <LineString>
                    <altitudeMode>relativeToGround</altitudeMode>
                    <coordinates>{flightpath_plain}</coordinates>
                </LineString>
            </MultiGeometry>
        </Placemark>''', parser=parser))
    
    shootdirections_xml = ''
    for d in image_list:
        shootdirections_xml += f'''
            <LineString>
                <coordinates>{d['point'].longitude},{d['point'].latitude} {d['point2'].longitude},{d['point2'].latitude}</coordinates>
            </LineString>'''

    document.append(ET.XML(f'''
        <Placemark>
            <name>shooting directions</name>
            <styleUrl>#shootline</styleUrl>
            <MultiGeometry>{shootdirections_xml}</MultiGeometry>
        </Placemark>''', parser=parser))

    shootsides_xml = ''
    for d in image_list:
        alt3 = max(d['alt'] - 50, 1)
        shootsides_xml += f'''
            <LineString>
                <altitudeMode>relativeToGround</altitudeMode>
                <coordinates>
                {d['point'].longitude},{d['point'].latitude},{d['alt']} 
                {d['point3'].longitude},{d['point3'].latitude},{alt3} 
                {d['point4'].longitude},{d['point4'].latitude},{alt3} 
                {d['point'].longitude},{d['point'].latitude},{d['alt']}
                </coordinates>
            </LineString>'''
    document.append(ET.XML(f'''
        <Placemark>
            <name>shooting frames</name>
            <styleUrl>#shootside</styleUrl>
            <MultiGeometry>{shootsides_xml}</MultiGeometry>
        </Placemark>''', parser=parser))


    folder = ET.SubElement(document, 'Folder')
    ET.SubElement(folder, 'name').text='Drone images'
    for d in image_list:
        folder.append(ET.XML(f'''
            <Placemark>
                <name>{d['iconname']}</name>
                <description><![CDATA[<img style="max-width:500px;" src="{d['filename']}">]]></description>
                <Point>
                    <extrude>1</extrude>
                    <altitudeMode>relativeToGround</altitudeMode>
                    <coordinates>{d['point'].longitude},{d['point'].latitude},{d['alt']}</coordinates>
                </Point>
            </Placemark>''', parser=parser))

    with open(os.path.join(folder_path, kml_filename), "wb") as f:
        tree  = ET.ElementTree(kml)
        #tree.write(f, pretty_print=True)
        tree.write(f, pretty_print=True, encoding='UTF-8', xml_declaration=True, method='xml')

if sys.argv[-1] and os.path.isdir(sys.argv[-1]): 
    folder_path = sys.argv[-1]
else: 
    folder_path = os.getcwd()

a = process_folder_to_data()
    
#for i in a:
#    pprint(i)
list_to_kml(a)