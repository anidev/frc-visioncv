#! /usr/bin/env python

import urllib
import threading
import Queue
import numpy as np
import cv2
from verbose import verbose

class MJPG:
    def __init__(self,url):
        self.stopFlag=threading.Event()
        self.startFlag=threading.Event()
        self.images=Queue.Queue(6)
        self.thread=threading.Thread(target=self.__runClient,args=[url])
        self.thread.daemon=True
        self.lastImage=np.zeros((240,320,3),np.uint8)

    def __runClient(self,url):
        self.url=url
        try:
            self.stream=urllib.urlopen(url)
        except IOError:
            self.startFlag.set()
            return
        self.imgbytes=''
        self.startFlag.set()
        while not self.stopFlag.is_set():
            image=self.__readImage()
            try:
                self.images.put(image,True,0.1)
            except Queue.Full:
                verbose('MJPG image dropped - queue is full!')

    def __readImage(self):
        while True:
            a=self.imgbytes.find('\xff\xd8')
            b=self.imgbytes.find('\xff\xd9')
            if a==-1 or b==-1:
                self.imgbytes+=self.stream.read(4096)
            else:
                break
        jpg=self.imgbytes[a:b+2]
        self.imgbytes=self.imgbytes[b+2:]
        image=cv2.imdecode(np.fromstring(jpg,dtype=np.uint8),cv2.cv.CV_LOAD_IMAGE_COLOR)
        return image

    def start(self):
        self.thread.start()
        self.startFlag.wait()

    def stop(self):
        self.stopFlag.set()
        self.thread.join()

    def started(self):
        return self.startFlag.is_set() and not self.stopFlag.is_set()

    def getImage(self):
        try:
            image=self.images.get(True,0.1)
            self.lastImage=image
            return image
        except Queue.Empty:
            verbose('MJPG image queue is empty!')
        return self.lastImage

if __name__=='__main__':
    mjpg=MJPG('http://127.0.0.1:8080/')
    cv2.namedWindow('Image')
    while True:
        image=mjpg.getImage()
        cv2.imshow('Image',image)
        cv2.waitKey(10)
