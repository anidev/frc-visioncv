#include <unistd.h>
#include <cstdlib>
#include <ctime>
#include <string>
#include <vector>
#include <iostream>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/highgui/highgui.hpp>

cv::Mat* image=NULL;
cv::Mat* binary=NULL;
cv::Mat* cvtImage=NULL;
cv::Mat* preview=NULL;

void renderImage(cv::Point cursor) {
    cv::Mat imgdraw=image->clone();
    cv::Mat prevdraw=preview->clone();
    std::vector<std::vector<cv::Point> > contours;
    cv::findContours(binary->clone(),contours,CV_RETR_CCOMP,CV_CHAIN_APPROX_SIMPLE);
    std::cout<<"Contours found: "<<contours.size()<<std::endl;
    srand(time(NULL));
    for(int i=0;i<contours.size();i++) {
        cv::Scalar color(0);
        for(int v=0;v<3;v++) {
            color[v]=rand()%255;
        }
        double polytest=cv::pointPolygonTest(contours[i],cursor,false);
        bool fill=polytest>0;
        const cv::Point* points=&contours[i][0];
        int num_points=contours[i].size();
        if(fill) {
            cv::fillConvexPoly(imgdraw,points,num_points,color,8);
            cv::fillConvexPoly(prevdraw,points,num_points,color,8);
        } else {
            cv::polylines(imgdraw,&points,&num_points,1,true,color,1,8);
            cv::polylines(prevdraw,&points,&num_points,1,true,color,1,8);
        }
        for(int j=0;j<contours[i].size();j++) {
            cv::Point point=contours[i][j];
            cv::circle(imgdraw,point,2,color,-1);
        }
    }
    cv::imshow("Original image",imgdraw);
    cv::imshow("Preview result",prevdraw);
}

bool filterColor(cv::Vec3b vec) {
    bool pass=true;
    // OpenCV hue is from 0..180
    pass&=(vec[0]>=65&&vec[0]<=82);  // H
    pass&=(vec[1]>=60&&vec[1]<=200); // L
    pass&=(vec[2]>=254);             // S
    return pass;
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

int main(int argc,char* argv[]) {
    if(argc<2) {
        std::cout<<"Usage: "<<argv[0]<<" <picture>"<<std::endl;
        return 0;
    }
    std::string filename(argv[1]);
    image=new cv::Mat(cv::imread(filename,1));
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
    cv::namedWindow("Original image",CV_WINDOW_AUTOSIZE);
    cv::setMouseCallback("Original image",mouse,(void*)image);
    cv::namedWindow("Preview result",CV_WINDOW_AUTOSIZE);
    cv::setMouseCallback("Preview result",mouse,(void*)preview);
    renderImage(cv::Point(-1,-1));
/*    cv::namedWindow("Converted image",CV_WINDOW_AUTOSIZE);
    cv::imshow("Converted image",*cvtImage);
    cv::setMouseCallback("Converted image",mouse,(void*)cvtImage);*/
    while(true) {
        int key=cv::waitKey(0);
        if((key&255)==27) {
            break;
        }
    }
    return 0;
}

