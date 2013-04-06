#include "particle.h"
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>

void Particle::recalcArea() {
    area=cv::contourArea(points);
}
