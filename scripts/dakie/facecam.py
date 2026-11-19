"""Find the streamer's webcam overlay and track the face inside it.

Run in its own process (OpenCV and PyAV bundle clashing ffmpeg dylibs on macOS).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PROFILE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")


def _faces(gray):
    out = []
    for cas in (CASCADE, PROFILE):
        for (x, y, w, h) in cas.detectMultiScale(gray, 1.1, 6, minSize=(28, 28)):
            out.append((int(x), int(y), int(w), int(h)))
    return out


def detect(video: Path, samples: int = 60, track_step: float = 0.5) -> dict:
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dets = []  # (frame_idx, x, y, w, h)
    for fi in np.linspace(0, max(n - 1, 0), samples).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
        ok, frame = cap.read()
        if not ok:
            continue
        for f in _faces(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)):
            dets.append((fi, *f))
    if not dets:
        return {"mode": "none", "W": W, "H": H, "reason": "no face found"}

    # A webcam overlay = a face that keeps showing up in the same place.
    best, best_hits = None, 0
    for d in dets:
        cx, cy = d[1] + d[3] / 2, d[2] + d[4] / 2
        near = [e for e in dets if abs(e[1] + e[3] / 2 - cx) < d[3] * 0.8 and abs(e[2] + e[4] / 2 - cy) < d[4] * 0.8]
        hits = len({e[0] for e in near})
        if hits > best_hits:
            best, best_hits = near, hits
    presence = best_hits / samples
    fx = np.median([e[1] + e[3] / 2 for e in best])
    fy = np.median([e[2] + e[4] / 2 for e in best])
    fs = np.median([e[3] for e in best])
    if presence < 0.3:
        return {"mode": "none", "W": W, "H": H, "reason": f"no stable face (best presence {presence:.0%})"}
    if fs > H * 0.3:
        return {"mode": "fullcam", "W": W, "H": H, "reason": "face fills the frame (camera-only stream)"}

    # Webcam box: face scaled to a typical head-and-shoulders crop (4:3), clamped to the frame.
    bw, bh = fs * 2.6, fs * 2.6 * 0.75 / 1.0
    bh = max(bh, fs * 2.0)
    x0 = int(np.clip(fx - bw / 2, 0, W - bw))
    y0 = int(np.clip(fy - bh * 0.45, 0, H - bh))
    box = [x0, y0, int(bw), int(bh)]

    # Track the face within the box over time (smoothed), for a stable crop.
    track = []
    step = max(1, int(fps * track_step))
    for fi in range(0, n, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            break
        pad = int(fs)
        rx0, ry0 = max(0, x0 - pad), max(0, y0 - pad)
        roi = frame[ry0: y0 + int(bh) + pad, rx0: x0 + int(bw) + pad]
        fs_ = _faces(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)) if roi.size else []
        if fs_:
            x, y, w, h = max(fs_, key=lambda r: r[2] * r[3])
            track.append([round(fi / fps, 2), rx0 + x + w / 2, ry0 + y + h / 2])
    cap.release()
    if track:
        arr = np.array(track)
        k = 5
        for col in (1, 2):
            arr[:, col] = np.convolve(np.pad(arr[:, col], k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
        track = [[float(a), round(float(b), 1), round(float(c), 1)] for a, b, c in arr]
    side = "right" if fx > W / 2 else "left"
    return {"mode": "overlay", "W": W, "H": H, "box": box, "face": [float(fx), float(fy), float(fs)],
            "presence": round(presence, 2), "side": side, "track": track}


if __name__ == "__main__":
    res = detect(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "track"}))
