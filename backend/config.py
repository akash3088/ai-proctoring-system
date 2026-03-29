import os

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to models
MODEL_DIR = os.path.join(BASE_DIR, "models")

# Change this to the mistral model you want to use
# e.g. "mistral_instruct_2k_m.gguf" inside your models folder
MISTRAL_MODEL_PATH = os.path.join(MODEL_DIR, "mistral_instruct_2k_m.gguf")

# Folder to store uploaded and flagged events
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
FLAGGED_FOLDER = os.path.join(BASE_DIR, "flagged_events")

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FLAGGED_FOLDER, exist_ok=True)

print("[CONFIG] Model dir:", MODEL_DIR)
print("[CONFIG] Upload folder:", UPLOAD_FOLDER)
print("[CONFIG] Flagged folder:", FLAGGED_FOLDER)
