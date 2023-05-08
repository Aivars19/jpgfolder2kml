#!/usr/bin/env python3

import os, sys, platform, subprocess, math, re, mmap, time

import psutil
import numpy
from pprint import pprint

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

import lxml.etree as ET

parser = ET.XMLParser(remove_blank_text=True)

from geopy.distance import geodesic, distance
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


# ================ JPG FILE PARSER ===================

def exif_dict_from_file(file_path):
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

    def image_exif_to_dict(file_path):
        image = Image.open(file_path)
        d = {}
        for (k,v) in image._getexif().items():
            if TAGS.get(k)=='GPSInfo':
                for k1 in v:
                    d[GPSTAGS.get(k1)] = v[k1]
                continue
            if len(str(v)) > 2000: continue
            d[TAGS.get(k)] = v
        return d

    def read_xmp(file_path):
        with open(file_path, 'rb', 0) as file:
            s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            
            xmp_start = s.find(b'<x:xmpmeta')
            xmp_end = s.find(b'</x:xmpmeta')
            if xmp_start: return s[xmp_start:xmp_end+12].decode()
            return ''
    
    xmp_str = read_xmp(file_path)
    xmp_xml = ET.XML(xmp_str)
    xmp_dict2 = etree_to_flat_dict(xmp_xml)

    exif_dict = image_exif_to_dict(file_path)
    exif_dict.update(xmp_dict2)
    
    # delete known big fields that will make review of tags harder
    if 'XPComment' in exif_dict: del exif_dict['XPComment']
    if 'XPKeywords' in exif_dict: del exif_dict['XPKeywords']
    
    if DEBUG_PRINT: pprint(exif_dict)
    
    if not exif_dict['GPSLatitude']: 
        raise "No gps data" # not suitable image
    return exif_dict


# ============== vector calculations for frame =======

def make_frameonground(details):
    def rotate_z(vector1, angle_z):
        angle_z_rad = numpy.radians(-angle_z)
        rotation_z = numpy.array([[numpy.cos(angle_z_rad), -numpy.sin(angle_z_rad), 0],
                               [numpy.sin(angle_z_rad), numpy.cos(angle_z_rad), 0],
                               [0, 0, 1]])
        return numpy.dot(rotation_z, vector1)
    def rotate_x(vector1, angle_x):
        angle_x_rad = numpy.radians(angle_x)
        rotation_x = numpy.array([[1, 0, 0],
                           [0, numpy.cos(angle_x_rad), -numpy.sin(angle_x_rad)],
                           [0, numpy.sin(angle_x_rad), numpy.cos(angle_x_rad)]])
        return numpy.dot(rotation_x, vector1)

    def normalize_z(vector1, z):
        if vector1[2]* z < 0: 
            norm = numpy.linalg.norm(vector1)
            return vector1 / norm * 500
        return vector1 * (z / vector1[2])
    def geo_move(lon_lat_alt, vector_in_meters):
        p = Point(lon_lat_alt[1], lon_lat_alt[0])

        east = vector_in_meters[0]
        north = vector_in_meters[1]
        altitude = vector_in_meters[2]

        east_offset = geodesic(meters=east).destination(p, 90)
        north_offset = geodesic(meters=north).destination(east_offset, 0)

        lon_adj, lat_adj = north_offset.longitude, north_offset.latitude
        alt_adj = lon_lat_alt[2] + altitude
        adjusted_coord = (lon_adj, lat_adj, alt_adj)
        return adjusted_coord
    def frame_corner_vectors(focal_length_35mm_equivalent, frame_width_pixels, frame_height_pixels, digital_zoom):
        # return 4 vector for frame when shot facing north horzontal. 
        # units = pixels (used as vector)
        focal_length_pixels = get_focal_length_pixels(focal_length_35mm_equivalent, frame_width_pixels, frame_height_pixels, digital_zoom)
        ret = []
        for cx,cy in [(-1,-1),(-1,+1),(+1,+1),(+1,-1)]:
            vec = numpy.array([frame_width_pixels/2*cx, focal_length_pixels, frame_height_pixels/2*cy]) 
            norm = numpy.linalg.norm(vec)
            vec = vec / norm * 50
            ret.append(vec)
        return ret

    def get_focal_length_pixels(focal_length_35mm_equivalent, frame_width_pixels, frame_height_pixels, digital_zoom):
        # units = pixels (used as vector)
        
        # assumption 1 - focal length in 35mm is related to diagonal 
        sensor_diagonal_35mm = math.sqrt(36**2 + 24**2)  # diagonal of 35mm sensor (36mm x 24mm)
        diagonal_pixels = math.sqrt(frame_width_pixels**2 + frame_height_pixels**2)
        focal_length_pixels = (focal_length_35mm_equivalent * digital_zoom / sensor_diagonal_35mm) * diagonal_pixels
        
        # assumption 2 - focal length in 35mm is related to width
        #focal_length_pixels = (focal_length_35mm_equivalent * digital_zoom / 36.0) * frame_width_pixels

        return focal_length_pixels



    lon_lat_alt = details['lon_lat_alt']
    azimuth = details['camera_azimuth_assumed']
    pitch = details['camera_pitch_assumed']
    if not pitch or pitch>=0: pitch = PITCH_IF_NOT_REDABLE
    focal_length_35mm_equivalent = details['FocalLengthIn35mmFilm']
    if not focal_length_35mm_equivalent: focal_length_35mm_equivalent = 24.0
    frame_width_pixels, frame_height_pixels = details['ExifImageWidth'], details['ExifImageHeight']
    if not frame_width_pixels or not frame_height_pixels: frame_width_pixels, frame_height_pixels = 4000,3000
    digital_zoom = details['DigitalZoomRatio']
    corners = []

    corners.append(lon_lat_alt)

    # determine vector for centre
    NORTH_VECTOR = numpy.array([0,1,0])
    alt_offset = GROUND_FRAME_HEIGHT -lon_lat_alt[2]
    centre_vector = normalize_z(rotate_z(rotate_x(NORTH_VECTOR, pitch), azimuth), alt_offset)
    corners.append(geo_move(lon_lat_alt, centre_vector))

    frame_vectors = []
    if digital_zoom:
        frame_vectors += frame_corner_vectors(focal_length_35mm_equivalent, frame_width_pixels, frame_height_pixels, digital_zoom)
        frame_vectors.append(frame_vectors[-4])
        details['pixel_size_mrad'] = 1000 / get_focal_length_pixels(focal_length_35mm_equivalent, frame_width_pixels, frame_height_pixels, digital_zoom)
    else: 
        frame_vectors += frame_corner_vectors(focal_length_35mm_equivalent, frame_width_pixels, frame_height_pixels, 1.4)
        frame_vectors.append(frame_vectors[-4])
        details['pixel_size_mrad'] = pixel_size_mrad(focal_length_35mm_equivalent, frame_width_pixels, frame_height_pixels, 1.4)
    
    for frame_vector in frame_vectors:
        corners.append(geo_move(lon_lat_alt, normalize_z(rotate_z(rotate_x(frame_vector, pitch), azimuth), alt_offset)))
    
    details['frameonground'] = corners


# ===== process file into useful detail (useful exif,xmp + calculate frame) === 
def get_usefuldetail(file_path, filename):
    def convert_to_degrees(value):
        d, m, s = value
        return d + (m / 60.0) + (s / 3600.0)

    def safer_float(x):
        # simply calling float will have div by zero errors on some values (such as nan)
        try:
            return float(x)
        except:
            return 0.0

    details = {}
    exif_dict = exif_dict_from_file(file_path)
    
    details['lon_lat_alt'] = (
        convert_to_degrees(exif_dict['GPSLongitude']), 
        convert_to_degrees(exif_dict['GPSLatitude']),
        safer_float(exif_dict['RelativeAltitude']))
    details['FlightPitchDegree'] = safer_float(exif_dict['FlightPitchDegree'])
    details['FlightYawDegree'] = safer_float(exif_dict['FlightYawDegree'])
    details['DateTime'] = exif_dict['DateTime']
    details['GimbalPitchDegree'] = safer_float(exif_dict['GimbalPitchDegree'])
    details['GimbalYawDegree'] = safer_float(exif_dict['GimbalYawDegree'])
    
    details['camera_pitch_assumed'] = details['GimbalPitchDegree'] if details['GimbalPitchDegree'] else PITCH_IF_NOT_REDABLE
    details['camera_azimuth_assumed'] = details['GimbalYawDegree'] if details['GimbalYawDegree'] else details['FlightYawDegree']
    
    details['FocalLengthIn35mmFilm'] = safer_float(exif_dict['FocalLengthIn35mmFilm'])
    details['DigitalZoomRatio'] = safer_float(exif_dict['DigitalZoomRatio'])
    details['ExifImageWidth'] = safer_float(exif_dict['ExifImageWidth'])
    details['ExifImageHeight'] = safer_float(exif_dict['ExifImageHeight'])
    details['Model'] = exif_dict['Model']
    
    iconname = filename
    if iconname.startswith('DJI_'): iconname = iconname[4:]
    if iconname.endswith('.JPG'): iconname = iconname[:-4]
    details['iconname'] = iconname
    details['filename'] = filename
    make_frameonground(details)
    return details

# ===== process list of image details into KML file  ==========================
def list_to_kml(image_list, folder_path):
    def kml_point(lon_lat_alt):
        return ','.join([str(x) for x in lon_lat_alt])

    if not image_list: 
        print("No suitable images in folder")
        return
    last_datetime_str = image_list[-1]['DateTime']
    last_datetime_str = last_datetime_str.replace(':','-')
    last_datetime_str = last_datetime_str.replace('_','T')
    kml_filename = 'drone_' + last_datetime_str + '.kml'
    
    kml = ET.Element('kml', {'xmlns': 'http://www.opengis.net/kml/2.2'})
    document = ET.SubElement(kml, 'Document')
    document.append(ET.XML(f'<description>from {folder_path} {len(image_list)} images</description>'))

    document.append(ET.XML('<Style id="shootframe"><LineStyle><color>#7fffff00</color></LineStyle></Style>'))
    document.append(ET.XML('<Style id="flightline"><LineStyle><color>#7fff0000</color><width>3</width></LineStyle></Style>'))

    flightpath_plain = ' '.join([kml_point(d['lon_lat_alt']) for d in image_list])

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

    shoot_directions_xml = ''
    for d in image_list:
        frameonground = d['frameonground'][:2] # first two points are direction
        shoot_directions_xml += f'''
            <LineString>
                <altitudeMode>relativeToGround</altitudeMode>
                <coordinates>{ ' '.join([kml_point(p) for p in frameonground]) }</coordinates>
            </LineString>'''
    document.append(ET.XML(f'''
        <Placemark>
            <name>shooting directions</name>
            <styleUrl>#shootframe</styleUrl>
            <MultiGeometry>{shoot_directions_xml}</MultiGeometry>
        </Placemark>''', parser=parser))

    folder = ET.SubElement(document, 'Folder')
    ET.SubElement(folder, 'name').text='Drone images'
    for d in image_list:
        folder.append(ET.XML(f'''
            <Folder><name>{d['iconname']}</name>
            <Placemark>
                <name>{d['iconname']}</name>
                <description><![CDATA[<img style="max-width:500px;" src="{d['filename']}">]]>
                DateTime: {d['DateTime']}, azimuth: {d['camera_azimuth_assumed']}, altitude: {d['lon_lat_alt'][2]}
                </description>
                <Point>
                    <extrude>1</extrude>
                    <altitudeMode>relativeToGround</altitudeMode>
                    <coordinates>{kml_point(d['lon_lat_alt'])}</coordinates>
                </Point>
            </Placemark>
            <Placemark>
                <name>Frame</name>
                <description>
                GimbalPitchDegree: {d['GimbalPitchDegree']} FlightPitchDegree: {d['FlightPitchDegree']} pitch_assumed: {d['camera_pitch_assumed']}
                focal35mm: {d['FocalLengthIn35mmFilm']} zoom: {d['DigitalZoomRatio']} pixel_size_mrad {d['pixel_size_mrad']}

                </description>
                <visibility>0</visibility>
                <styleUrl>#shootframe</styleUrl>
                <LineString><altitudeMode>relativeToGround</altitudeMode><coordinates>{' '.join([kml_point(p) for p in d['frameonground']])}</coordinates></LineString>
            </Placemark>
            </Folder>''', parser=parser))

    kml_file_path = os.path.join(folder_path, kml_filename)
    with open(kml_file_path, "wb") as f:
        tree  = ET.ElementTree(kml)
        #tree.write(f, pretty_print=True)
        tree.write(f, pretty_print=True, encoding='UTF-8', xml_declaration=True, method='xml')
    
    global_kml_list.append(kml_file_path)

def open_google_earth_end():
    if not global_kml_list: return
    
    if platform.system() == 'Darwin':       
        # we are in macOS
        for kml_file_path in global_kml_list:
            subprocess.call(('open', kml_file_path))
    elif platform.system() == 'Windows':    
        # we are in Windows
        for kml_file_path in global_kml_list:
            os.startfile(kml_file_path)
    else:                                   
        # we are in linux variants
        open_in_linux()


def open_in_linux():
    if len(global_kml_list) > 1: 
        kml_filename = f'set_of_{len(global_kml_list)}_files.kml'
        
        kml = ET.Element('kml', {'xmlns': 'http://www.opengis.net/kml/2.2'})
        document = ET.SubElement(kml, 'Document')

        for pathfile in global_kml_list:
            path, file = os.path.split(pathfile)
            if path.startswith(folder_path): 
                path = path[len(folder_path):]
                if path.startswith('/'): path = path[1:]
     
            document.append(ET.XML(f'<NetworkLink><name>{file}</name><Link><href>{os.path.join(path, file)}</href></Link></NetworkLink>'))

        kml_file_path = os.path.join(folder_path, kml_filename)
        with open(kml_file_path, "wb") as f:
            tree  = ET.ElementTree(kml)
            tree.write(f, pretty_print=True, encoding='UTF-8', xml_declaration=True, method='xml')

    # let me explain - there is no way to open kml in google earth if google earth is already running
    # (apart from hijacking mouse)
    # so for linux we create single joined kml and place it folder
    google_earth_is_running = False
    for process in psutil.process_iter(['name', 'cmdline']):
        process_name = process.info['name']
        process_cmdline = ' '.join(process.info['cmdline'])
        if 'google-earth' in process_name or 'google-earth' in process_cmdline:
            google_earth_is_running = True

    if not is_google_earth_running:
        subprocess.call(('xdg-open', kml_file_path))
    else: 
        subprocess.call(('xdg-open', folder_path))
        
global_kml_list = []

# ===== MAIN PROCESSOR FOR PROVIDED FOLER ==== 
def process_folder_to_data(folder_path):
    # create list, with images, will be ordered list
    print(f"   === processing folder {folder_path}===")
    image_list = []        
    for filename in os.listdir(folder_path):
        
        full_path = os.path.join(folder_path, filename)
        if os.path.isdir(full_path): 
            process_folder_to_data(full_path)
            
        if not filename.lower().endswith(".jpg"): 
            continue
        
        if DEBUG_PRINT:
            details = get_usefuldetail(full_path, filename)
            image_list.append(details)
            print(f"{filename}: {details['lon_lat_alt']}")
        else:
            try: 
                details = get_usefuldetail(full_path, filename)
                image_list.append(details)
                #pprint(details)
                print(f"{filename}: {details['lon_lat_alt']}")
            except:
                print(f"{filename}: ignored, no GPS information (or yaw or altitude), possibly not DJI file")
    
    image_list.sort(key=lambda x: x['DateTime'])
    list_to_kml(image_list, folder_path)

# note this needs to be global 
if sys.argv[-1] and os.path.isdir(sys.argv[-1]): 
    folder_path = sys.argv[-1]
else: 
    folder_path = os.getcwd()


# can change while debugging. 
DEBUG_PRINT = False
PITCH_IF_NOT_REDABLE = -45.0 # -45 normal
GROUND_FRAME_HEIGHT = 1 # set higher for uneven terrain. 

# ACTION STARTS HERE
process_folder_to_data(folder_path)
open_google_earth_end()
