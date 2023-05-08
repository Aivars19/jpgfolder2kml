# what jpgfolder2kml does
It processes folder with images (as taken from dji drone) and generate single kml file that can be opened with Google Earth. 
Main functionality:

- it will process folder (or tree of folders) into Google Earth Pro compatible KML file(s)
  - it will work acceptably fast on large data sets - both folder processing and showing KML with, say, 5000 images should be workable.  
  - kml file is named from last image datetime. (if you open several folders in Earth - file name should help you understand which is which). 

- kml shows every picture as pin. 
  - If pictures are named as DJI_0000.JPG, then only number is shown. Else - file name is shown. 
  - pin is located at altitude
  - pin has extrusion to ground - so you see precise location
  - pin has image link added, so clicking on pin will show image preview (with additional click can open full image inside GE). 
  - pin description contains more textual details extracted from file (date, azimuth, height)

- kml shows flight path as blue, altitude adjusted line.
  - line is in separate geometry, so can be turned on/off

- kml shows direction of camera
  - they point to ground where frame center should be
  - pitch angle relies on GimbalPitchDegree tag from file. DJIMini2 does not report gimbal pitch. Bigger DJI drones do report it. If not reported, -45 degrees assumed. 
  
- kml contains calculated ground frame for each pin
  - it is hidden by default
  - based on reported pitch, zoom, fov, directions - calculates what portion of ground is in frame. 
  - note that frame will be approximate: FOV reported is not precise, compass azimuth can be a few degrees off, when drone is in movement (or fights wind) pitch might be misreported some degrees, gps might be off some meters, altitude is relative to start point-not current point, digital zoom is not always reported .... etc. 

- script will try to open google earth with created KML(s) at the end of processing

# folder, argument, file placement

- if script is launched with argument, and argument is folder, then script will process that folder
- if script is launched without argument (or argument is not a valid folder), then script will process current working directory. 
- script will process subdirectories as well (so you can drop folder with all year collected images)
- output KML file is saved in processed folder (or subfolder), along with images. 
- output KML is only generated if folder contained valid images (with gps tags, altitude... as from dji drone)

# limitations
Tool is written and tested with dji mini2 output. It relies on common exif tags (datetime, gps, focal length), and also on dji specific tags saved in xmp (altitude, yaw). DJI mini2 unfortunately does not save gimbal value (tag exists but is always 0), so pitch of picture is not reported.  

# how to use on Windows
## run as script
Prerequisites:
- python3 with libraries lxml, Pillow, geopy, numpy, psutil
- if you have pip, then run
<!-- -->
    pip install lxml Pillow geopy numpy psutil

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
- python3 with libraries lxml, Pillow, geopy, numpy, psutil
- if you have pip, then run
<!-- -->
    pip install lxml Pillow geopy numpy psutil

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

