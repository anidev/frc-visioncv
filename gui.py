import time
import cv2
import visionvars as vv

def doNothing(x):
    pass

class GUI:
    def __init__(self,title='612 Vision'):
        self.title=title
        cv2.namedWindow(title)
        if vv.debug:
            self.names=(("H Lo","L Lo","S Lo"),("H Hi","L Hi","S Hi"))
            self.createTrackbars()

    def createTrackbars(self):
        for i in xrange(0,3):
            cv2.createTrackbar(self.names[0][i], self.title, 0, 255, doNothing)
            cv2.setTrackbarPos(self.names[0][i], self.title, vv.color[0][i])
            cv2.createTrackbar(self.names[1][i], self.title, 0, 255, doNothing)
            cv2.setTrackbarPos(self.names[1][i], self.title, vv.color[1][i])

    def update(self):
        if not vv.debug:
            return
        newval=[[0,0,0],[0,0,0]]
        for i,names in enumerate(self.names):
            for j,name in enumerate(names):
                newval[i][j]=cv2.getTrackbarPos(name,self.title)
        vv.color=(tuple(newval[0]),tuple(newval[1]))

    def showImage(self,image):
        if vv.guiEnabled:
            cv2.imshow(self.title,image)
            key=cv2.waitKey(30)
            if key==27:
                return False
            return True
        else:
            time.sleep(0.3)
            return True

    def destroy(self):
        cv2.destroyAllWindows()
