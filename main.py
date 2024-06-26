import os
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

from ultralytics import YOLO
import cv2
import numpy as np
import util
from sort import *
from util import get_car, read_license_plate, write_csv

results = {}

mot_tracker = Sort()

# load models
coco_model = YOLO('yolov8n.pt')
license_plate_detector = YOLO('license_plate_detector.pt')

# load video
cap = cv2.VideoCapture(r"D:\GIT\License-plate-detection\images\3.jpeg")

vehicles = [2, 3, 5, 7]

# read frames
frame_nmr = -1
ret = True
while True:
    frame_nmr += 1
    ret, frame = cap.read()
    if ret:
        results[frame_nmr] = {}
        # detect vehicles
        detections = coco_model(frame)[0]
        detections_ = []
        for detection in detections.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = detection
            if int(class_id) in vehicles:
                detections_.append([x1, y1, x2, y2, score])

        # track vehicles
        track_ids = mot_tracker.update(np.asarray(detections_))

        # detect license plates
        license_plates = license_plate_detector(frame)[0]
        for license_plate in license_plates.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = license_plate

            # bounding box
            
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2) # convert to int values

            # put box in cam
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)

            # assign license plate to car
            xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)

            if car_id != -1:

                # crop license plate
                license_plate_crop = frame[int(y1):int(y2), int(x1): int(x2), :]
                
                #resizing
                # Get the original dimensions of the image
                original_height, original_width = license_plate_crop.shape[:2]

                # Define the scaling factors (percentages)
                scale_percent = 1000  # For example, increase size by 150%

                # Calculate the new dimensions
                new_width = int(original_width * scale_percent / 100)
                new_height = int(original_height * scale_percent / 100)
                new_size = (new_width, new_height)
                                
                cv2.imshow('frame',license_plate_crop)
                resized_image=cv2.resize(license_plate_crop,new_size,interpolation=cv2.INTER_CUBIC)
                cv2.imshow('frame',resized_image,)

                # process license plate
                license_plate_crop_gray = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
                _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)

                # read license plate number
                license_plate_text, license_plate_text_score = read_license_plate(license_plate_crop_thresh)

                # object details
                org = [x1, y1]
                font = cv2.FONT_HERSHEY_SIMPLEX
                fontScale = 1
                color = (255, 0, 0)
                thickness = 2

                if license_plate_text is not None:
                    results[frame_nmr][car_id] = {'car': {'bbox': [xcar1, ycar1, xcar2, ycar2]},
                                                  'license_plate': {'bbox': [x1, y1, x2, y2],
                                                                    'text': license_plate_text,
                                                                    'bbox_score': score,
                                                                    'text_score': license_plate_text_score}}
                
                print(license_plate_text)
                cv2.putText(frame,license_plate_text ,org, font, fontScale, color, thickness)            
        cv2.imshow('Frame', frame)            
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    # write results
        write_csv(results, './test.csv')