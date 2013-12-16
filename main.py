#! /usr/bin/env python

import sys
from collections import namedtuple
from random import randint
import cv2
import numpy as np
from pynetworktables import NetworkTable
from mjpg import *
import visionvars as vv

mjpgURL='http://10.6.12.11/axis-cgi/mjpg/video.cgi'
mjpgURLdebug='http://127.0.0.1:8080/video.jpg'
#mjpgURLdebug='http://watch.sniffdoghotel.com/axis-cgi/mjpg/video.cgi?resolution=320x240'
ntIP='10.6.12.2'
ntIPdebug='127.0.0.1'
debug=False
color=None
table=None
highlightColor=None

Particle=namedtuple('Particle',['area','points'])

def randColor():
    return (randint(0,255),randint(0,255),randint(0,255))

def convertImage(image):
    cvtImage=cv2.cvtColor(image,cv2.cv.CV_BGR2HLS)
    return cvtImage

def filterImage(image):
    binImage=np.zeros((len(image),len(image[0]),1),np.uint8)
    cv2.inRange(image,color[0],color[1],binImage)
    return binImage

def combineImages(image1,image2):
    h,w=image1.shape[:2]
    comb=np.zeros((h*2,w,3),np.uint8)
    comb[:h]=image1
    comb[h:]=image2
    return comb

def binToColor(image):
    colorImage=np.expand_dims(image,2)
    colorImage=np.repeat(colorImage,3,2)
    print(colorImage)
    return colorImage

def analyzeImage(image):
    # morphology
    kernel=cv2.getStructuringElement(cv2.MORPH_RECT,(2,2),anchor=(1,1))
    image=cv2.morphologyEx(image,cv2.MORPH_CLOSE,kernel,iterations=9)
    imageCopy=np.copy(image)
    contours,hierarchy=cv2.findContours(imageCopy,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);
    particles=[]
    for contour in contours:
        hull=cv2.convexHull(contour)
        polygon=cv2.approxPolyDP(hull,5,True)
        polygon=polygon[:,0]
        area=cv2.contourArea(polygon)
        particles.append(Particle(area,polygon))
    return image,particles

def processImage(image):
    cvtImage=convertImage(image)
    binImage=filterImage(cvtImage)
    binImage,particles=analyzeImage(binImage)
    binImage=binToColor(binImage)
    image=drawParticles(image,particles)
    binImage=drawParticles(binImage,particles)
    print("# particles: %s" % len(particles))
    combImage=combineImages(image,binImage)
    return combImage,particles

def drawParticles(image,particles):
    for particle in particles:
        print(highlightColor)
        cv2.polylines(image,np.array([particle.points]),True,highlightColor,1,1)
    return image

def doMJPG(url):
#    video=cv2.VideoCapture(url)
    mjpg=MJPG(url)
    while True:
#        retval,image=video.read()
        image=mjpg.getImage()
        combImage,particles=processImage(image)
        cv2.imshow("Image",combImage)
        key=cv2.waitKey(30)&0xFF
        if key==27:
            break

def doLocal(filename):
    image=cv2.imread(filename,1)
    combImage,particles=processImage(image)
    cv2.imshow("Image",combImage)
    while True:
        key=cv2.waitKey(10)
        if key==27:
            break

def usage():
    print("Usage: %s [--debug] [--blue|--green] <--mjpg|picture>" % sys.argv[0])
    print("")
    print("--debug: Activate debug mode")
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

if len(sys.argv)<3:
    usage()
    exit(0)
sys.argv.pop(0)
if sys.argv[0]=='--debug':
    debug=True
    sys.argv.pop(0)
if sys.argv[0]=='--blue':
    color=vv.blue
elif sys.argv[0]=='--green':
    color=vv.green
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