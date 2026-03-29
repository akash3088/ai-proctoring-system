import os
import json
from config import MISTRAL_MODEL_PATH
from pathlib import Path
from llama_cpp import Llama
try:
    from llama_cpp import Llama
    _llm = None
    if os.path.exists(MISTRAL_MODEL_PATH):
        _llm = Llama(model_path=MISTRAL_MODEL_PATH)
except Exception:
    _llm = None

def _build_prompt(event_meta):
    ts = event_meta.get("timestamp", "")
    uname = event_meta.get("username", "")
    det = event_meta.get("detected", {})
    lines = [
        "Create a one-sentence explanation for a proctor admin describing why the clip is suspicious.",
        f"User: {uname}",
        f"Time: {ts}",
        f"Detections: {json.dumps(det)}"
    ]
    return "\n".join(lines)

def explain_event(event_meta, timeout=10):
    det = event_meta.get("details", {})
    face_count = det.get("face_count", 0)
    gaze_shift = det.get("gaze_shift", False)
    
    prompt = (
        f"Explain the proctoring event for the admin in simple terms:\n"
        f"Face count: {face_count}\n"
        f"Gaze shift detected: {gaze_shift}\n"
        f"Other details: {json.dumps(det)}\n"
        f"Write a concise, human-readable explanation describing what happened."
    )
    
    if _llm is not None:
        try:
            resp = _llm(prompt, max_tokens=150, stop=["\n"])
            text = resp['choices'][0]['text'].strip()
            if text:
                return text
        except Exception:
            pass
    
    if face_count == 0:
        return "No face detected in front of the camera — candidate might be away."
    if face_count > 1:
        return f"Multiple faces ({face_count}) detected — possible assistance present."
    if gaze_shift:
        return "Candidate looked away from the screen — significant gaze/head movement detected."
    
    return "Suspicious activity detected; see recorded clip."