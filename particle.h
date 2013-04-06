#ifndef PARTICLE_H

#include <vector>
#include <opencv2/core/core.hpp>

class Particle {
public:
    cv::Scalar color;
    std::vector<cv::Point> points;
    double area;
    void recalcArea();
};

#endif // PARTICLE_H