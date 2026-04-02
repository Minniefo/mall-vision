# roi.py
import cv2
import numpy as np


def bbox_bottom_center(bbox):
    """
    bbox from MTCNN: [x, y, width, height]
    Returns bottom-center point (cx, cy)
    """
    x, y, w, h = bbox
    cx = int(x + w / 2)
    cy = int(y + h)
    return (cx, cy)


def point_in_polygon(point, polygon):
    """
    Check if point lies inside polygon using OpenCV.
    """
    poly_np = np.array(polygon, dtype=np.int32)
    return cv2.pointPolygonTest(poly_np, point, False) >= 0


def is_in_near_zone(bbox, near_zone_polygon):
    """
    Returns True if bbox bottom-center lies inside near-zone polygon.
    """
    point = bbox_bottom_center(bbox)
    return point_in_polygon(point, near_zone_polygon)
