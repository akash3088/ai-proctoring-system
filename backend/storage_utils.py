# storage_utils.py
import os
from datetime import datetime
import json
import shutil

STORAGE_FOLDER = "suspicious_events"
os.makedirs(STORAGE_FOLDER, exist_ok=True)

def save_event_files(temp_video_path, event_meta):
    """
    Move temp video into suspicious_events and write metadata JSON.
    Returns (video_dest_path, metadata_json_path)
    """
    # ensure unique filenames
    video_name = event_meta["video"]
    dest_video_path = os.path.join(STORAGE_FOLDER, video_name)
    # move/copy file
    shutil.copyfile(temp_video_path, dest_video_path)

    # write metadata json (same base name)
    meta_name = event_meta["id"] + ".json"
    meta_path = os.path.join(STORAGE_FOLDER, meta_name)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(event_meta, f, indent=2, ensure_ascii=False)

    return dest_video_path, meta_path
