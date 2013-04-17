#ifndef RANGES_H
#define RANGES_H

#include <opencv2/core/core.hpp>

struct color_range_t {
public:
    cv::Scalar low;
    cv::Scalar high;
};

// All in HLS
color_range_t range_green={{ 54, 50,220},{ 78,130,255}};
color_range_t range_blue= {{107, 65,120},{129, 150,255}};

#endif // RANGES_Hotal
