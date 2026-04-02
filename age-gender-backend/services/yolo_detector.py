#yolo_detector.py
import numpy as np
from typing import Optional, Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

if not CV2_AVAILABLE or not YOLO_AVAILABLE:
    missing = []
    if not CV2_AVAILABLE:
        missing.append("opencv-python")
    if not YOLO_AVAILABLE:
        missing.append("ultralytics")
    print(f"Warning: {', '.join(missing)} not installed.")
    print(f"Install with: pip install {' '.join(missing)}")


class YOLOObjectDetector:
    IGNORED_CLASSES = {
        'person', 'people', 'man', 'woman', 'child', 'boy', 'girl',
        'pedestrian', 'human'
    }
    
    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model_name = model_name
        self.model = None
        self.is_loaded = False
        
        if not CV2_AVAILABLE or not YOLO_AVAILABLE:
            print("YOLO not available. Install: pip install opencv-python ultralytics")
            return
        
        self._load_model()
    
    def _load_model(self) -> bool:
        try:
            self.model = YOLO(self.model_name)
            self.is_loaded = True
            return True
        except Exception as e:
            print(f"Error loading YOLO model: {str(e)}")
            return False
    
    def _filter_person_objects(self, results) -> List[Dict]:
        detections = []
        
        if len(results) == 0 or len(results[0].boxes) == 0:
            return detections
        
        boxes = results[0].boxes
        
        for i in range(len(boxes)):
            class_id = int(boxes.cls[i].cpu().numpy())
            confidence = float(boxes.conf[i].cpu().numpy())
            class_name = results[0].names[class_id]
            
            if class_name.lower() in self.IGNORED_CLASSES:
                continue
            
            detections.append({
                'object': class_name,
                'confidence': confidence,
                'class_id': class_id,
                'box': boxes.xyxy[i].cpu().numpy()
            })
        
        detections.sort(key=lambda x: x['confidence'], reverse=True)
        return detections
    
    def detect_from_webcam(
        self,
        confidence_threshold: float = 0.5,
        scan_duration: int = 3,
        headless: bool = False
    ) -> Optional[str]:
        if not self.is_loaded:
            if not headless:
                print("YOLO model not loaded")
            return None
        
        import time
        
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            if not headless:
                print("Cannot access webcam")
            return None
        
        best_object = None
        best_confidence = 0.0
        start_time = time.time()
        frame_count = 0
        
        current_detections = []
        
        try:
            while (time.time() - start_time) < scan_duration:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                if frame_count % 2 == 0:
                    results = self.model(frame, verbose=False)
                    detections = self._filter_person_objects(results)
                    current_detections = detections
                    
                    if detections:
                        for det in detections:
                            if det['confidence'] >= confidence_threshold:
                                if det['confidence'] > best_confidence:
                                    best_confidence = det['confidence']
                                    best_object = det['object']
                
                elapsed = time.time() - start_time
                time_left = max(0, scan_duration - int(elapsed))
                annotated_frame = frame.copy()
                
                # Draw bounding boxes for all detected objects
                for det in current_detections:
                    if det['confidence'] >= confidence_threshold:
                        box = det['box']
                        x1, y1, x2, y2 = map(int, box)
                        
                        # Different color for best object
                        if det['object'] == best_object:
                            color = (0, 255, 255)  # Yellow for best
                            thickness = 3
                        else:
                            color = (0, 255, 0)  # Green for others
                            thickness = 2
                        
                        # Draw bounding box
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
                        
                        # Draw label background
                        label = f"{det['object']}: {det['confidence']:.2f}"
                        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                        cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                                    (x1 + label_size[0], y1), color, -1)
                        
                        # Draw label text
                        cv2.putText(annotated_frame, label, (x1, y1 - 5),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                
                # Status text at top
                cv2.putText(annotated_frame, f"Scanning: {time_left}s remaining", (10, 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                if best_object:
                    cv2.putText(annotated_frame, f"Leading: {best_object} ({best_confidence:.2f})", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                else:
                    cv2.putText(annotated_frame, "No objects detected yet...", (10, 60),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
                
                cv2.putText(annotated_frame, "Press ESC to cancel", (10, 90),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                if not headless:
                    cv2.imshow('YOLO Auto-Detection', annotated_frame)
                    
                    if cv2.waitKey(1) & 0xFF == 27:
                        best_object = None
                        break
                else:
                    time.sleep(0.01)
                    
        except KeyboardInterrupt:
            best_object = None
        finally:
            cap.release()
            if not headless:
                cv2.destroyAllWindows()
        
        return best_object
    
    def detect_from_image(
        self,
        image_path: str,
        confidence_threshold: float = 0.5,
        show_result: bool = True
    ) -> Optional[str]:
        if not self.is_loaded:
            return None
        
        try:
            results = self.model(image_path, verbose=False)
            detections = self._filter_person_objects(results)
            
            if not detections:
                return None
            
            best = detections[0]
            
            if best['confidence'] < confidence_threshold:
                return None
            
            detected_object = best['object']
            
            if show_result:
                annotated = results[0].plot()
                cv2.imshow('YOLO Detection Result', annotated)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
            return detected_object
            
        except Exception as e:
            print(f"Error detecting from image: {str(e)}")
            return None
    
    def get_all_detections(
        self,
        image_or_frame,
        confidence_threshold: float = 0.5
    ) -> List[Dict]:
        if not self.is_loaded:
            return []
        
        try:
            results = self.model(image_or_frame, verbose=False)
            detections = self._filter_person_objects(results)
            detections = [d for d in detections if d['confidence'] >= confidence_threshold]
            return detections
            
        except Exception as e:
            print(f"Error in detection: {str(e)}")
            return []
    
    def get_stats(self) -> Dict:
        if not self.is_loaded:
            return {'loaded': False}
        
        return {
            'loaded': True,
            'model': self.model_name,
            'total_classes': len(self.model.names),
            'ignored_classes': list(self.IGNORED_CLASSES),
            'available_classes': [name for name in self.model.names.values() 
                                 if name.lower() not in self.IGNORED_CLASSES]
        }

