import cv2
import time
import requests
import tempfile
import threading
import numpy as np
import mediapipe as mp
import os
import psutil
from pynput import keyboard
from pynput import mouse
import pyttsx3
from queue import Queue

SERVER_URL_UPLOAD = "http://127.0.0.1:5000/upload"
SERVER_URL_WARNING = "http://127.0.0.1:5000/warning"
CAMERA_INDEX = 1
THRESHOLD_SUSPICION = 0.7
RECORD_DURATION = 5
COOLDOWN = 10
SCREEN_TERMINATE_DELAY = 5
USERNAME = "akash"

last_frame = None
last_upload_time = 0
warning_count = 0
eye_closed_start = None
face_not_facing_start = None

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_fullbody.xml")
mp_hands = mp.solutions.hands
hands_detector = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.6)
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.6)


engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

tts_queue = Queue()

def tts_worker():
    """Speak all queued messages one after another."""
    while True:
        text = tts_queue.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()
        tts_queue.task_done()

tts_thread = threading.Thread(target=tts_worker, daemon=True)
tts_thread.start()

def speak_text(text):
    """Add text safely to the speech queue."""
    tts_queue.put(text)


def _rect_area(rect):
    x, y, w, h = rect
    return max(0, w) * max(0, h)

def _intersection_area(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x_left = max(ax, bx)
    y_top = max(ay, by)
    x_right = min(ax + aw, bx + bw)
    y_bottom = min(ay + ah, by + bh)
    if x_right < x_left or y_bottom < y_top:
        return 0
    return (x_right - x_left) * (y_bottom - y_top)

def detect_phone_book(frame):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands_detector.process(frame_rgb)
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            x_coords = [lm.x for lm in hand_landmarks.landmark]
            y_coords = [lm.y for lm in hand_landmarks.landmark]
            if max(x_coords) - min(x_coords) > 0.25 or max(y_coords) - min(y_coords) > 0.25:
                return True
    return False

def detect_suspicious(frame):
    global last_frame, eye_closed_start, face_not_facing_start
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5)
    bodies = body_cascade.detectMultiScale(gray, 1.05, 3)
    score = 0.0
    warnings = []

    if len(faces) == 0:
        if len(bodies) > 0:
            score += 0.8
            warnings.append("Only body detected")
        else:
            score += 0.7
            warnings.append("No face or body found")
    elif len(faces) > 1:
        score += 0.9
        warnings.append("Extra face detected")

    other_person_detected = False
    primary_face = None
    if len(faces) >= 1:
        faces_sorted = sorted(faces, key=lambda r: r[2]*r[3], reverse=True)
        primary_face = faces_sorted[0]
        pf_area = _rect_area(primary_face)

    for b in bodies:
        b_area = _rect_area(b)
        inter = _intersection_area(primary_face, b) if primary_face is not None else 0
        if b_area > 500 and (primary_face is None or (inter / float(b_area)) < 0.2):
            other_person_detected = True
            break

    if other_person_detected:
        score += 0.9
        warnings.append("Other person detected")

    if detect_phone_book(frame):
        score += 0.9
        warnings.append("Phone/Book detected")

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_results = face_mesh.process(frame_rgb)
    eyes_visible = False
    gaze_forward = True

    if face_results.multi_face_landmarks:
        for face_landmarks in face_results.multi_face_landmarks:
            left_eye = [face_landmarks.landmark[i] for i in range(33, 133)]
            right_eye = [face_landmarks.landmark[i] for i in range(362, 462)]
            left_y = np.mean([lm.y for lm in left_eye])
            right_y = np.mean([lm.y for lm in right_eye])
            left_x = np.mean([lm.x for lm in left_eye])
            right_x = np.mean([lm.x for lm in right_eye])
            eyes_visible = True
            if abs(left_y - right_y) > 0.13 or abs(left_x - right_x) > 0.13:
                gaze_forward = False

    now = time.time()
    if not eyes_visible and len(faces) > 0:
        if eye_closed_start is None:
            eye_closed_start = now
        elif now - eye_closed_start > 5:
            score += 0.8
            warnings.append("Eyes closed >5s")
    else:
        eye_closed_start = None

    if not gaze_forward and eyes_visible:
        if face_not_facing_start is None:
            face_not_facing_start = now
        elif now - face_not_facing_start > 5:
            score += 0.5
            warnings.append("Looking away >5s")
    else:
        face_not_facing_start = None

    if last_frame is not None:
        diff = cv2.absdiff(last_frame, gray)
        motion_level = np.mean(diff)
        if motion_level > 60:
            score += 0.2
            warnings.append("Sudden movement detected")

    last_frame = gray.copy()
    return min(score, 1.0), warnings

def record_clip(cap, duration=RECORD_DURATION):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    out = cv2.VideoWriter(temp_file.name, cv2.VideoWriter_fourcc(*'mp4v'), 20, (640, 480))
    start = time.time()
    while time.time() - start < duration:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
    out.release()
    return temp_file.name

def upload_video(path):
    try:
        with open(path, 'rb') as f:
            files = {'file': f}
            data = {'username': USERNAME}
            requests.post(SERVER_URL_UPLOAD, files=files, data=data, timeout=20)
            msg = f"Video uploaded: {os.path.basename(path)}"
            print(msg)
            speak_text(msg)
    except:
        pass
    finally:
        if os.path.exists(path):
            os.remove(path)

def send_warning(reason):
    global warning_count
    warning_count += 1
    payload = {'username': USERNAME, 'reason': reason}
    try:
        requests.post(SERVER_URL_WARNING, json=payload, timeout=5)
        msg = f"Warning {warning_count} for {USERNAME}: {reason}"
        print(msg)
        speak_text(msg)  
    except:
        msg = f"Failed to send warning for {USERNAME}"
        print(msg)
        speak_text(msg)

def check_remote_control():
    remote_tools = ['AnyDesk.exe', 'TeamViewer.exe', 'chrome_remote_desktop.exe']
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] in remote_tools:
                msg = f"Warning: Remote control detected ({proc.info['name']}). Exam terminating in {SCREEN_TERMINATE_DELAY} seconds."
                print(msg)
                speak_text(msg)
                time.sleep(SCREEN_TERMINATE_DELAY)
                os._exit(0)
        except:
            continue

tab_switch_keys = {keyboard.Key.alt_l, keyboard.Key.tab}
browser_forbidden_keys = {keyboard.Key.cmd, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}
mouse_clicks = 0
mouse_last_time = time.time()

def on_press(key):
    if key in tab_switch_keys or key in browser_forbidden_keys:
        msg = f"Warning: Forbidden key pressed ({key}). Exam terminating in {SCREEN_TERMINATE_DELAY} seconds."
        print(msg)
        speak_text(msg)
        time.sleep(SCREEN_TERMINATE_DELAY)
        os._exit(0)

def on_click(x, y, button, pressed):
    global mouse_clicks, mouse_last_time
    if pressed:
        current_time = time.time()
        mouse_clicks += 1
        if mouse_clicks >= 3 and (current_time - mouse_last_time) < 3:
            msg = f"Warning: Excessive mouse clicks detected ({mouse_clicks}). Exam terminating in {SCREEN_TERMINATE_DELAY} seconds."
            print(msg)
            speak_text(msg)
            time.sleep(SCREEN_TERMINATE_DELAY)
            os._exit(0)
        if (current_time - mouse_last_time) > 2:
            mouse_clicks = 0
        mouse_last_time = current_time

def monitor_keyboard_mouse():
    with keyboard.Listener(on_press=on_press) as kl, mouse.Listener(on_click=on_click) as ml:
        kl.join()
        ml.join()

def monitor_camera():
    global last_upload_time, warning_count
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Camera not accessible")
        speak_text("Camera not accessible")
        return

    threading.Thread(target=monitor_keyboard_mouse, daemon=True).start()
    stable_start = time.time()
    while time.time() - stable_start < 3:
        cap.read()

    while True:
        check_remote_control()
        ret, frame = cap.read()
        if not ret:
            break

        score, warnings = detect_suspicious(frame)
        color = (0, 0, 255) if score >= THRESHOLD_SUSPICION else (0, 255, 0)
        cv2.putText(frame, f"Suspicion: {score:.2f} | {' | '.join(warnings)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.imshow("AI Proctor - Live Feed", frame)

        if score >= THRESHOLD_SUSPICION and (time.time() - last_upload_time) > COOLDOWN:
            last_upload_time = time.time()
            for reason in warnings:
                send_warning(reason)
            clip_path = record_clip(cap)
            threading.Thread(target=lambda p=clip_path: upload_video(p)).start()

        if warning_count >= 3:
            msg = "Exam closed due to 3 warnings"
            print(msg)
            speak_text(msg)
            warning_count = 0
            break

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    tts_queue.put(None)  

if __name__ == "__main__":
    monitor_camera()
