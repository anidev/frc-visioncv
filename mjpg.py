#! /usr/bin/env python

import urllib
import numpy as np
import cv2

class MJPG:
    def __init__(self,url):
        self.url=url
        self.stream=urllib.urlopen(url)
        self.imgbytes=''

    def getImage(self):
        while True:
            a=self.imgbytes.find('\xff\xd8')
            b=self.imgbytes.find('\xff\xd9')
            if a==-1 or b==-1:
                self.imgbytes+=self.stream.read(16384)
            else:
                break
        jpg=self.imgbytes[a:b+2]
        self.imgbytes=self.imgbytes[b+2:]
        image=cv2.imdecode(np.fromstring(jpg,dtype=np.uint8),cv2.cv.CV_LOAD_IMAGE_COLOR)
        return image

if __name__=='__main__':
    mjpg=MJPG('http://127.0.0.1:8080/')
    cv2.namedWindow('Image')
    while True:
        image=mjpg.getImage()
        cv2.imshow('Image',image)
        cv2.waitKey(10)
