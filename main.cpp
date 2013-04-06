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
#include "particle.h"

bool decorate=true;
bool procFailed=false;

Particle particles[]={Particle(),Particle()}; // outer, inner
cv::Mat* image=NULL;
cv::Mat* binary=NULL;
cv::Mat* cvtImage=NULL;
cv::Mat* preview=NULL;

bool filterColor(cv::Vec3b vec) {
    bool pass=true;
    // OpenCV hue is from 0..180
    pass&=(vec[0]>=64&&vec[0]<=85);  // H
    pass&=(vec[1]>=30&&vec[1]<=140); // L
    pass&=(vec[2]>=200);             // S
    return pass;
}

void filterImage() {
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

void processImage() {
    std::vector<std::vector<cv::Point> > contours;
    cv::findContours(binary->clone(),contours,CV_RETR_CCOMP,CV_CHAIN_APPROX_SIMPLE);
    int num_contours=0;
    for(unsigned int i=0;i<contours.size();i++) {
        double area=cv::contourArea(contours[i]);
        std::cout<<area<<std::endl;
        if(area<350) {
            continue;
        }
        num_contours++;
        if(area>particles[0].area) {
            particles[1].points=particles[0].points;
            particles[0].points=contours[i];
        } else {
            particles[1].points=contours[i];
        }
        particles[0].recalcArea();
    }
    if(num_contours<2) {
        std::cerr<<"Failed to find more than 2 valid contours"<<std::endl;
        procFailed=true;
        return;
    }
    particles[1].recalcArea();
    std::cout<<"outer area: "<<particles[0].area<<std::endl;
    std::cout<<"inner area: "<<particles[1].area<<std::endl;
}

void renderImage(cv::Point cursor=cv::Point(-1,-1)) {
    cv::Mat imgdraw=image->clone();
    cv::Mat prevdraw=preview->clone();
    int line=8;
    if(decorate&&!procFailed) {
        bool inner_fill=false;
        for(int i=1;i>=0;i--) {
            Particle* particle=&particles[i];
            std::vector<cv::Point>* points=&particle->points;
            const cv::Point* pPoints=&points->at(0);
            double polytest=cv::pointPolygonTest(*points,cursor,false);
            bool fill=polytest>0;
            int num_points=points->size();
            if(fill&&!inner_fill) {
                if(i==1) {
                    inner_fill=true;
                }
                cv::fillConvexPoly(imgdraw,pPoints,num_points,particle->color,line);
                cv::fillConvexPoly(prevdraw,pPoints,num_points,particle->color,line);
            } else {
                cv::polylines(imgdraw,&pPoints,&num_points,1,true,particle->color,1,line);
                cv::polylines(prevdraw,&pPoints,&num_points,1,true,particle->color,1,line);
            }
            for(unsigned int j=0;j<points->size();j++) {
                cv::Point point=points->at(j);
                cv::circle(imgdraw,point,2,particle->color,-1);
            }
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
    if(argc<2) {
        std::cout<<"Usage: "<<argv[0]<<" <picture>"<<std::endl;
        return 0;
    }
    srand(time(NULL));
    particles[0].color=randColor();
    particles[1].color=randColor();
    std::string filename(argv[1]);
    image=new cv::Mat(cv::imread(filename,1));
    filterImage();
    processImage();
    cv::namedWindow("Original image",CV_WINDOW_AUTOSIZE);
    cv::setMouseCallback("Original image",mouse,(void*)image);
    cv::namedWindow("Preview result",CV_WINDOW_AUTOSIZE);
    cv::setMouseCallback("Preview result",mouse,(void*)preview);
    renderImage();
/*    cv::namedWindow("Converted image",CV_WINDOW_AUTOSIZE);
    cv::imshow("Converted image",*cvtImage);
    cv::setMouseCallback("Converted image",mouse,(void*)cvtImage);*/
    while(true) {
        int key=cv::waitKey(0);
        key&=0xFF;
        if(key=='d') {
            decorate=!decorate;
            renderImage();
        }
        if(key==27) {
            break;
        }
    }
    return 0;
}

