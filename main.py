#! /usr/bin/env python

import sys
from collections import namedtuple
from random import randint
import cv2
import numpy as np
from pynetworktables import NetworkTable
from mjpg import *
from gui import *
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
imgsize=(240,320)

Particle=namedtuple('Particle',['area','points','centerX']) #changed
HotGoal=type('HotGoal',(),{'LEFT':-1,'RIGHT':1,'NONE':0})

def randColor():
    return (randint(0,255),randint(0,255),randint(0,255))

def convertImage(image):
    cvtImage=cv2.cvtColor(image,cv2.cv.CV_BGR2HLS)
    return cvtImage

def filterImage(image):
    binImage=np.zeros((len(image),len(image[0]),1),np.uint8)
    cv2.inRange(image,vv.color[0],vv.color[1],binImage)
    return binImage

def filterParticle(particle):
    return particle.area>vv.area_min and particle.area<vv.area_max

def combineImages(image1,image2):
    h,w=image1.shape[:2]
    comb=np.zeros((h,w*2,3),np.uint8)
    comb[:,:w]=image1
    comb[:,w:]=image2
    return comb

def binToColor(image):
    colorImage=np.expand_dims(image,2)
    colorImage=np.repeat(colorImage,3,2)
    return colorImage

def analyzeImage(image):
    # morphology
    # change this to this year's vision later
#    kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(10,10)) #changed
#    image=cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=4) #changed
    image=image.reshape(imgsize)
    imageCopy=np.copy(image)
    contours,hierarchy=cv2.findContours(imageCopy, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    particles=[]
    for contour in contours:
        hull=(cv2.convexHull(contour))
        polygon=cv2.approxPolyDP(hull,2,True)
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
    goal=determineHotGoal(particles)
    exportStuff(particles,goal)
    doRumbling(particles) #change the rumbling parameters later
    #combImage = binImage
    #particles = None
    return combImage,particles

def drawParticles(image,particles):
    particles=sortParticles(particles)[:2]
    drawImage=np.copy(image)
    for particle in particles:
        cv2.polylines(drawImage,np.array([particle.points]),True,vv.highlightColor,1,1)
        #cv2.circle(image,(particle.centerX,particle.centerY),2,vv.highlightColor) #changed
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
    return particle

def sortParticles(particles): # biggest to smallest
    return sorted(particles,key=lambda x:x.area,reverse=True)

def exportStuff(particles,goal):
    if vv.table==None:
        return
    if particles==None or len(particles)==0:
        vv.table.PutBoolean('1/Available',False)
    else:
        p=sortParticles(particles)[0]
        vv.table.PutBoolean('1/Available',True)
        vv.table.PutNumber('1/Area',p.area)
        vv.table.PutNumber('1/CenterX',p.centerX)
    if goal==None:
        goal=HotGoal.NONE
    vv.table.PutNumber('HotGoal',goal)

def determineHotGoal(particles):
    # how it works:
    # divide image into half vertically
    # get two biggest particles
    # if they are in opposite halves, near goal is not hot
    # if they are in same half, near goal is hot
    pSorted=sortParticles(particles)[:2]
    if len(pSorted)<2:
        return HotGoal.NONE
    leftHalf=rightHalf=False
    half=imgsize[1]/2
    for p in pSorted:
        print p.centerX
        if p.centerX>half:
            rightHalf=True
        else:
            leftHalf=True
    if leftHalf and not rightHalf:
        return HotGoal.LEFT
    elif rightHalf and not leftHalf:
        return HotGoal.RIGHT
    else:
        return HotGoal.NONE

def doRumbling(particles):
    if not rumble:
        return
    if len(particles)==0:
        return
    p=sortParticles(particles)[0]
    if p and p.area>3000:
        power=doRumble*0.8
        rumble.rumble(power,power)
   
def nothing(x):
    pass

def doMJPG(url):
    gui=GUI()
    mjpg=MJPG(url)
    mjpg.start()
    while True:
        gui.update()
        image=mjpg.getImage()
        combImage,particles=processImage(image)
        if not gui.showImage(combImage):
            break
    gui.destroy()
    mjpg.stop()

def doLocal(filename):
    gui=GUI()
    image=cv2.imread(filename,1)
    while True:
        gui.update()
        combImage, particles = processImage(image)
        if not gui.showImage(combImage):
            break
    gui.destroy()

def usage():
    print("Usage: %s [--debug] [--gui|--nogui] [--verbose|--silent] [--blue|--green|--yellow] <--mjpg|picture>" % sys.argv[0])
    print("")
    print("--debug: Activate debug mode")
    print("")
    print("--gui: Enable the gui (default)")
    print("--nogui: Disable the gui")
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
        vv.debug=True
        sys.argv.pop(0)
    if sys.argv[0]=='--gui':
        vv.guiEnabled=True
        sys.argv.pop(0)
    elif sys.argv[0]=='--nogui':
        vv.guiEnabled=False
        sys.argv.pop(0)
    if sys.argv[0]=='--verbose':
        setVerbose(True)
        sys.argv.pop(0)
    elif sys.argv[0]=='--silent':
        setVerbose(False)
        sys.argv.pop(0)
    if sys.argv[0]=='--blue':
        vv.color=vv.blue
    elif sys.argv[0]=='--green':
        vv.color=vv.green
    elif sys.argv[0]=='--yellow':
        vv.color=vv.yellow
    else:
        print('No color specified')
        exit(1)
    sys.argv.pop(0)
    vv.highlightColor=randColor()
    NetworkTable.SetIPAddress(ntIPdebug if vv.debug else ntIP)
    NetworkTable.SetClientMode()
    NetworkTable.Initialize()
    vv.table=NetworkTable.GetTable('PCVision')
    if vv.table==None:
        print("Failed to get NetworkTable")
        exit(1)
    if sys.argv[0]=='--mjpg':
        doMJPG(mjpgURLdebug if vv.debug else mjpgURL)
        exit(0)
    else:
        doLocal(sys.argv[0])
