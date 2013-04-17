#include <unistd.h>
#include <cstdlib>
#include <ctime>
#include <cstring>
#include <string>
#include <vector>
#include <iostream>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <networktables/NetworkTable.h>
#include "particle.h"
#include "ranges.h"

#define NTSERVER
const int teamID=612;

bool decorate=true;
bool procFailed=false;
bool mjpg=false;
color_range_t range;

Particle particle; // outer, inner
cv::VideoCapture video;
cv::Mat* image=NULL;
cv::Mat* binary=NULL;
cv::Mat* cvtImage=NULL;
cv::Mat* preview=NULL;
NetworkTable* table=NULL;

bool filterColor(cv::Vec3b& vec) {
    bool pass=true;
    // OpenCV hue is from 0..180
    pass&=(vec[0]>=range.low[0]&&vec[0]<=range.high[0]);  // H
    pass&=(vec[1]>=range.low[1]&&vec[1]<=range.high[1]);  // L
    pass&=(vec[2]>=range.low[2]&&vec[2]<=range.high[2]);  // S
    return pass;
}

void filterImage() {
    particle.area=0;
    cvtImage=new cv::Mat(image->size(),image->type(),cv::Scalar(0,0,0));
    binary=new cv::Mat(image->size(),CV_8UC1,cv::Scalar(0));
    preview=new cv::Mat(image->size(),image->type(),cv::Scalar(0,0,0));
    cv::cvtColor(*image,*cvtImage,CV_BGR2HLS,3);
    cv::Mat_<cv::Vec3b> cvtImage_=reinterpret_cast<cv::Mat_<cv::Vec3b>&>(*cvtImage);
    cv::Mat_<unsigned char> binary_=reinterpret_cast<cv::Mat_<unsigned char>&>(*binary);
    cv::Mat_<unsigned char> preview_=reinterpret_cast<cv::Mat_<unsigned char>&>(*preview);
    for(int y=0;y<image->rows;y++) {
        for(int x=0;x<image->cols;x++) {
            cv::Vec3b vec=cvtImage_.at<cv::Vec3b>(y,x);
            if(filterColor(vec)) {
                binary_.at<unsigned char>(y,x)=255;
                preview_.at<cv::Vec3b>(y,x)={255,255,255};
            } else {
                binary_.at<unsigned char>(y,x)=0;
                preview_.at<cv::Vec3b>(y,x)={0,0,0};
            }
        }
    }
}

bool filterContour(std::vector<cv::Point>& contour) {
    if(cv::contourArea(contour)<350) {
        return false;
    }
    return true;
}

void processImage() {
    std::vector<cv::Vec4i> hough;
    cv::HoughLinesP(*binary,hough,1,CV_PI/180,10,5);
    particle.points.reserve(hough.size()*2);
/*    for(unsigned int i=0;i<hough.size();i++) {
        cv::Vec4i& vec=hough[i];
        line(*image,cv::Point(vec[0],vec[1]),cv::Point(vec[2],vec[3]),cv::Scalar(0,0,255),1,8);
        line(*preview,cv::Point(vec[0],vec[1]),cv::Point(vec[2],vec[3]),cv::Scalar(0,0,255),1,8);
    }*/
    int num_contours=0;
    std::vector<std::vector<cv::Point> > contours;
    cv::findContours(hough,contours,CV_RETR_EXTERNAL,CV_CHAIN_APPROX_SIMPLE);
    for(unsigned int i=0;i<contours.size();i++) {
        double area=cv::contourArea(contours[i]);
        std::cout<<area<<std::endl;
        if(!filterContour(contours[i])) {
            continue;
        }
        std::vector<cv::Point> hull;
        std::vector<cv::Point> polygon;
        cv::convexHull(contours[i],hull);
        cv::approxPolyDP(hull,polygon,5,true);
        std::cout<<polygon.size()<<std::endl;
        if(polygon.size()!=4||!filterContour(polygon)) {
            continue;
        }
        num_contours++;
        if(area>particle.area) {
            particle.points=polygon;
            particle.recalcArea();
        }
    }
    if(num_contours<1) {
        std::cerr<<"Failed to find more than 1 valid contours"<<std::endl;
        procFailed=true;
        return;
    } else {
        procFailed=false;
    }
    std::cout<<"area: "<<particle.area<<std::endl;
    table->PutNumber("Area",particle.area);
}

void renderImage(cv::Point cursor=cv::Point(-1,-1)) {
    cv::Mat imgdraw=image->clone();
    cv::Mat prevdraw=preview->clone();
    int line=8;
    if(decorate&&!procFailed) {
        std::vector<cv::Point>* points=&particle.points;
        const cv::Point* pPoints=&points->at(0);
        double polytest=cv::pointPolygonTest(*points,cursor,false);
        bool fill=polytest>0;
        int num_points=points->size();
        if(fill) {
            cv::fillConvexPoly(imgdraw,pPoints,num_points,particle.color,line);
            cv::fillConvexPoly(prevdraw,pPoints,num_points,particle.color,line);
        } else {
            cv::polylines(imgdraw,&pPoints,&num_points,1,true,particle.color,1,line);
            cv::polylines(prevdraw,&pPoints,&num_points,1,true,particle.color,1,line);
        }
        for(unsigned int j=0;j<points->size();j++) {
            cv::Point point=points->at(j);
            cv::circle(imgdraw,point,2,particle.color,-1);
        }
    }
    cv::imshow("Original image",imgdraw);
    cv::imshow("Preview result",prevdraw);
}

void mouse(int event,int x,int y,int flags,void* image) {
    if(event==CV_EVENT_MOUSEMOVE) {
        cv::Point cursor(x,y);
        renderImage(cursor);
        return;
    }
    if(event!=CV_EVENT_LBUTTONUP) {
        return;
    }
    cv::Mat* mat=(cv::Mat*)image;
    cv::Vec3b vec=mat->at<cv::Vec3b>(y,x);
    std::cout<<(int)vec[0]<<", "<<(int)vec[1]<<", "<<(int)vec[2]<<std::endl;
}

cv::Scalar randColor() {
    cv::Scalar color(0);
    for(int v=0;v<3;v++) {
        color[v]=rand()%255;
    }
    return color;
}

int main(int argc,char* argv[]) {
#ifdef NTSERVER
    NetworkTable::SetIPAddress("127.0.0.1");
    NetworkTable::Initialize();
    table=NetworkTable::GetTable("PCVision");
#else
    table=null; //TODO NetworkTable client mode
#endif
    if(table==NULL) {
        std::cerr<<"Failed to get NetworkTable"<<std::endl;
        return 1;
    }
    if(argc<2) {
        std::cout<<"Usage: "<<argv[0]<<" [--blue|--green] [--mjpg] <picture>"<<std::endl;
        return 0;
    }
    srand(time(NULL));
    particle.color=randColor();
    bool colorset=false;
    int target_argc=1;
    for(int i=1;i<argc;i++) {
        if(strcmp(argv[i],"--green")==0) {
            std::cout<<"Using green threshold"<<std::endl;
            colorset=true;
            range=range_green;
            break;
        } else if(strcmp(argv[i],"--blue")==0) {
            std::cout<<"Using blue threshold"<<std::endl;
            colorset=true;
            range=range_blue;
            break;
        }
    }
    if(colorset) {
        target_argc++;
    } else {
        range=range_green;
        std::cout<<"Using green threshold"<<std::endl;
    }
    if(argc>2&&strcmp(argv[target_argc],"--mjpg")==0) {
        target_argc++;
        mjpg=true;
        std::string path(argv[target_argc]);
        if(!video.open(path)) {
            std::cerr<<"Failed to open mjpg stream"<<std::endl;
            return 1;
        }
        image=new cv::Mat(240,320,CV_8UC3);
        if(!video.read(*image)) {
            std::cerr<<"Failed to read from mjpg stream"<<std::endl;
            return 1;
        }
    } else {
        std::string filename(argv[target_argc]);
        image=new cv::Mat(cv::imread(filename,1));
    }
    filterImage();
    processImage();
    cv::namedWindow("Original image",CV_WINDOW_AUTOSIZE);
    cv::setMouseCallback("Original image",mouse,(void*)image);
    cv::namedWindow("Preview result",CV_WINDOW_AUTOSIZE);
    cv::setMouseCallback("Preview result",mouse,(void*)cvtImage);
    renderImage();
/*    cv::namedWindow("Converted image",CV_WINDOW_AUTOSIZE);
    cv::imshow("Converted image",*cvtImage);
    cv::setMouseCallback("Converted image",mouse,(void*)cvtImage);*/
    while(true) {
        int key=cv::waitKey((mjpg?100:0));
        key&=0xFF;
        if(key=='d') {
            decorate=!decorate;
            renderImage();
            continue;
        }
        if(key==27) {
            break;
        }
        if(mjpg) {
            delete image;
            image=new cv::Mat(240,320,CV_8UC3);
            if(!video.read(*image)) {
                std::cerr<<"Failed to read from mjpg stream"<<std::endl;
                sleep(1);
                continue;
            }
            filterImage();
            processImage();
            renderImage();
        }
    }
    return 0;
}
