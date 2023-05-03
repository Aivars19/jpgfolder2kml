# what jpgfolder2kml does
It processes folder with images (as taken from dji drone) and generate single kml file that can be opened with Google Earth. 
Functionality features:
- kml file is named based on last image datetime. (if you open several folders in Earth - file name should help you understand which is which). 
- kml contains flight path as blue, altitude adjusted line. 
- kml shows every picture as pin. If pictures are named as DJI_0000.JPG, then only number is shown. Else - file name is shown. 
- pin has image link added, so clicking on pin will show image preview (with additional click can open full image inside GE). 
- pin is located at altitude
- pin has extrusion to ground. 
- there is extra geometry added so that from each pin you see direction and frame field of view as triangle. 
- works acceptably on large data sets - 500 images (2gb) shouldn't be issue for processing and for displaying in Earth 

# limitations
tool is written and tested with dji mini2 output. It relies on common exif tags (datetime, gps, focal length), and also on dji specific tags saved in xmp (altitude, yaw). 
dji mini2 unfortunately does not save gimbal value (tag exists), so pitch of picture is not reported. Directional triangles show 45 degree angle when over 50m above ground, or flatter angle if close to ground. 

# how to use on Windows
## run as script
Prerequisites:
- python3 with libraries lxml, Pillow, geopy
- if you have pip, then run
    pip install lxml Pillow geopy

open command line into folder with images. Then run script here without parameters 
    python %USERPROFILE%\Downloads\jpgfolder2kml.py 
open command line anywhere. Then run script here with image folder as parameter
    python %USERPROFILE%\Downloads\jpgfolder2kml.py "d:\DCIM\100MEDIA"

## make script executable
associate .py with python (so doubleclicking will run it)
Now you can drop folder onto script and script will launch and do it's job. 

# how to use on Linux
## run as script
Prerequisites:
- python3 with libraries lxml, Pillow, geopy
- if you have pip, then run
    pip install lxml Pillow geopy

open command line into folder with images. Then run script here without parameters 
    python3 $HOME\Downloads\jpgfolder2kml.py 
open command line anywhere. Then run script here with image folder as parameter
    python3 $HOME\Downloads\jpgfolder2kml.py /media/user1/disk/DCIM/100MEDIA

## make drop-able shortcut
Create .desktop file and place it on desktop. 
See help about .desktop elsewhere, related to current script this should help: 
    Exec=python3 /home/user1/Downloads/jpgfolder2kml.py %U
    MimeType=inode/directory;
Now you can drop folder onto shortcut and sript will launch and do it's job. 

