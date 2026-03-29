import mediapipe as mp
import cv2
import numpy as np
from PIL import Image

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def pil_to_cv2(img_pil):
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def analyze_frame_and_score(pil_image):
    """
    Returns: (score, details)
    Detects:
      - no face, multiple faces
      - gaze shift
      - body out of frame
      - phone/book usage
    """
    frame = pil_to_cv2(pil_image)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    details = {}
    score = 0.0

    # Face detection
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(80,80))
    details['face_count'] = len(faces)
    if len(faces) == 0:
        score += 0.9
    elif len(faces) > 1:
        score += 0.9

    # Pose detection
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    if results.pose_landmarks:
        # Check if body is fully visible (simplified)
        y_coords = [lm.y for lm in results.pose_landmarks.landmark]
        if min(y_coords) > 0.05 and max(y_coords) < 0.95:
            details['body_visible'] = True
        else:
            score += 0.4
            details['body_visible'] = False

        # Detect if head is down (possible phone/book)
        nose = results.pose_landmarks.landmark[0]
        left_shoulder = results.pose_landmarks.landmark[11]
        right_shoulder = results.pose_landmarks.landmark[12]
        shoulders_y = (left_shoulder.y + right_shoulder.y)/2
        if nose.y > shoulders_y + 0.1:
            score += 0.4
            details['looking_down'] = True
        else:
            details['looking_down'] = False
    else:
        score += 0.3

    return min(1.0, score), details
