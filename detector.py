# backend/detector.py
import cv2
import numpy as np
import mediapipe as mp
from PIL import Image

# Haarcascade face detector (fast)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# MediaPipe FaceMesh for gaze/head heuristics
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, min_detection_confidence=0.5)

def pil_to_cv2(img_pil):
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def analyze_frame_and_score(pil_image):
    """
    Input: PIL image (RGB)
    Returns: (score (0.0-1.0), details dict)
    Simple heuristic:
      - no face visible -> +0.6
      - more than 1 face -> +0.9
      - gaze shift -> +0.4
    """
    frame = pil_to_cv2(pil_image)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(80,80))

    details = {}
    face_count = len(faces)
    details['face_count'] = face_count
    score = 0.0

    if face_count == 0:
        score += 0.6
    elif face_count > 1:
        score += 0.9
    else:
        # single face -> check gaze/head pose with MediaPipe FaceMesh
        # convert to RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        if results and results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark
            # indices for approximate eye/nose landmarks:
            left_eye = lm[33]   # left eye outer
            right_eye = lm[263] # right eye outer
            nose_tip = lm[1]    # nose tip
            # compute gaze proxy: eyes midpoint x - nose x
            eyes_mid_x = (left_eye.x + right_eye.x) / 2.0
            gaze = eyes_mid_x - nose_tip.x
            details['gaze'] = float(gaze)
            # heuristics threshold
            if abs(gaze) > 0.06:
                score += 0.4
                details['gaze_shift'] = True
            else:
                details['gaze_shift'] = False
        else:
            # no landmarks found (maybe face too small) -> small suspicion
            score += 0.2

    score = min(1.0, score)
    return score, details
