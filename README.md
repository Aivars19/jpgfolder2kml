# jpgfolder2kml
Process folder with dji images, create kml with positioned points, image preview, path and direction. 

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

# limitations
tool is written and tested with dji mini2 output. It relies on common exif tags (datetime, gps, focal length), and also on dji specific tags saved in xmp (altitude, yaw). 
dji mini2 unfortunately does not save gimbal value (tag exists), so pitch of picture is not reported. Directional triangles show 45 degree angle when over 50m above ground, or flatter angle if close to ground. 

# how to use
Method 1: 
open windows command line or linux terminal into folder with images. 
Run script here. 
> python jpgfolder2kml.py 

(if .py file is made executable you can skip python and run by script name). 

Method 2:
Run script with folder as parameter. (output kml file is saved in the given folder)
> python jpgfolder2kml.py c:\images\folder1

Method 3: drop folder on script. 

Method 3a: make .py script executable (windows or linux) and you can drop image folder on script. 

Method 3b: use pyinstaller to create exe or linux executable  - now you can drop image folder on it. 

Method 3c: place shortcut on Desktop, and drop image folder on it.  
