#! /usr/bin/env python

import sys
from collections import namedtuple
from random import randint
import cv2
import numpy as np
from pynetworktables import NetworkTable
from mjpg import *
import visionvars as vv
from verbose import *
try:
    import rumble
except Exception:
    rumble=False

mjpgURL='http://10.6.12.11/axis-cgi/mjpg/video.cgi'
mjpgURLdebug='http://127.0.0.1:8080/video.jpg'
#mjpgURLdebug='http://watch.sniffdoghotel.com/axis-cgi/mjpg/video.cgi?resolution=320x240'
#mjpgURLdebug='http://212.24.177.174:8092/axis-cgi/mjpg/video.cgi?resolution=320x240'
ntIP='10.6.12.2'
ntIPdebug='127.0.0.1'
debug=False
color=None
table=None
highlightColor=None

Particle=namedtuple('Particle',['area','points','centerX']) #changed

def randColor():
    return (randint(0,255),randint(0,255),randint(0,255))

def convertImage(image):
    cvtImage=cv2.cvtColor(image,cv2.cv.CV_BGR2HLS)
    return cvtImage

def filterImage(image):
    binImage=np.zeros((len(image),len(image[0]),1),np.uint8)
    cv2.inRange(image,color[0],color[1],binImage)
    return binImage

def filterParticle(particle):
    return particle.area>vv.area_min and particle.area<vv.area_max

def combineImages(image1,image2):
    h,w=image1.shape[:2]
    comb=np.zeros((h*2,w,3),np.uint8)
    comb[:h]=image1
    comb[h:]=image2
    return comb

def binToColor(image):
    colorImage=np.expand_dims(image,2)
    colorImage=np.repeat(colorImage,3,2)
    return colorImage

def analyzeImage(image):
    # morphology
    # change this to this year's vision later
    kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(10,10)) #changed
    image=cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=4) #changed
    imageCopy=np.copy(image)
    contours,hierarchy=cv2.findContours(imageCopy, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    particles=[]
    for contour in contours:
        hull=(cv2.convexHull(contour))
        polygon=cv2.approxPolyDP(hull,5,True)
        polygon=polygon[:,0]
        particle=makeParticle(polygon)
        if filterParticle(particle):
            particles.append(particle)
    return image,particles

def processImage(image):
    sizedImage=cv2.resize(image,(320,240))
    image=sizedImage
    cvtImage=convertImage(image)
    binImage=filterImage(cvtImage)
    binImage,particles=analyzeImage(binImage)
    binImage=binToColor(binImage)
    drawImage=drawParticles(image,particles)
    drawBinImage=drawParticles(binImage,particles)
    verbose("# particles: %s" % len(particles))
    combImage=combineImages(drawImage,drawBinImage)
    exportParticles(particles)
    doRumbling(particles) #change the rumbling parameters later
    #combImage = binImage
    #particles = None
    return combImage,particles

def drawParticles(image,particles):
    drawImage=np.copy(image)
    for particle in particles:
        cv2.polylines(drawImage,np.array([particle.points]),True,highlightColor,1,1)
        #cv2.circle(image,(particle.centerX,particle.centerY),2,highlightColor) #changed
    return drawImage

def makeParticle(polygon):
    area=cv2.contourArea(polygon)
    m=cv2.moments(np.array([polygon]))
    if m['m00']==0:
        centerX=0
    else:
        centerX=int(m['m10']/m['m00'])
        #centerY=int(m['m01']/m['m00']) #changed
    particle=Particle(area,polygon,centerX)
    print 'area: %s' % area
    return particle

def biggestParticle(particles):
    return max(particles,key=lambda x:x.area)

def exportParticles(particles):
    if table==None:
        return None
    if particles==None or len(particles)==0:
        table.PutBoolean('1/Available',False)
        return None
    else:
        p=biggestParticle(particles)
        table.PutBoolean('1/Available',True)
        table.PutNumber('1/Area',p.area)
        table.PutNumber('1/CenterX',p.centerX)
        return p

def doRumbling(particles):
    if not rumble:
        return
    if len(particles)==0:
        return
    p=biggestParticle(particles)
    if p and p.area>3000:
        power=doRumble*0.8
        rumble.rumble(power,power)

def doMJPG(url):
#    video=cv2.VideoCapture(url)
    mjpg=MJPG(url)
    mjpg.start()
    while True:
#        retval,image=video.read()
        image=mjpg.getImage()
        combImage,particles=processImage(image)
        cv2.imshow("Image",combImage)
        key=cv2.waitKey(30)&0xFF
        if key==27:
            break
    mjpg.stop()

def doLocal(filename):
    image=cv2.imread(filename,1)
    combImage,particles=processImage(image)
    cv2.imshow("Image",combImage)
    while True:
        key=cv2.waitKey(10)
        if key==27:
            break

def usage():
    print("Usage: %s [--debug] [--verbose|--silent] [--blue|--green|--yellow] <--mjpg|picture>" % sys.argv[0])
    print("")
    print("--debug: Activate debug mode")
    print("")
    print("--verbose: Activate verbose mode (default)")
    print("--silent: Disable verbose mode")
    print("")
    print("")
    print("--mjpg: MJPG Axis camera streaming")
    print("        Default URL: %s" % mjpgURL)
    print("        Debug URL: %s" % mjpgURLdebug)
    print("")
    print("picture: Path of local picture file")
    print("")
    print("NetworkTable default IP: %s" % ntIP)
    print("NetworkTable debug IP: %s" % ntIPdebug)
    print("")

if __name__=='__main__':
    if len(sys.argv)<3:
        usage()
        exit(0)
    sys.argv.pop(0)
    if sys.argv[0]=='--debug':
        debug=True
        sys.argv.pop(0)
    if sys.argv[0]=='--verbose':
        setVerbose(True)
        sys.argv.pop(0)
    elif sys.argv[0]=='--silent':
        setVerbose(False)
        sys.argv.pop(0)
    if sys.argv[0]=='--blue':
        color=vv.blue
    elif sys.argv[0]=='--green':
        color=vv.green
    elif sys.argv[0]=='--yellow':
        color=vv.yellow
    else:
        print('No color specified')
        exit(1)
    sys.argv.pop(0)
    highlightColor=randColor()
    NetworkTable.SetIPAddress(ntIPdebug if debug else ntIP)
    NetworkTable.SetClientMode()
    NetworkTable.Initialize()
    table=NetworkTable.GetTable('PCVision')
    if table==None:
        print("Failed to get NetworkTable")
        exit(1)
    if sys.argv[0]=='--mjpg':
        doMJPG(mjpgURLdebug if debug else mjpgURL)
        exit(0)
    else:
        doLocal(sys.argv[0])
