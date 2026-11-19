"""Stage 5 helper: a gameplay window that follows the main object.

Owner 2026-11-19: the gameplay fills the whole lower band (1080x1280, no blurred
bars, no letterbox) and the main object of the action stays completely visible.
So a 912x1080 window (the band's aspect) is cut from the 1920x1080 source and
its x position follows the main object:

1. sample the moment at 4 fps, 640x360, with the facecam blanked out;
2. detect objects with YOLOX-m (Apache-2.0, ONNX on the CPU, about 0.2 s a
   frame: no API cost and no GPU needed) and keep people, vehicles, aircraft
   and boats;
3. pick the main object per sample: confidence x size x closeness to the
   centre, sticky to the previous pick (the player's character or vehicle);
4. per sample, the window positions that hold the whole box form a corridor;
   a smoothed path is projected into the corridors (no jitter), clamped to
   the frame edge;
5. the renderer writes the path as one crop position per output frame.

A sample whose object is wider than the window has no corridor. The plan
counts those samples instead of cutting silently, and the check fails on them.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

SRC_W, SRC_H = 1920, 1080
BAND_W, BAND_H = 1080, 1280
CROP_W = int(round(SRC_H * BAND_W / BAND_H / 2)) * 2  # 912: the band's aspect at full height
SAMPLE_FPS = 4
MARGIN = 16           # source px kept free around the box
SMOOTH_S = 0.7        # Gaussian sigma of the camera path, seconds
MIN_SCORE = 0.30
INPUT = 640           # YOLOX input square
SCALE = SRC_W / INPUT  # 640x360 sample -> source px

# COCO ids that can be the main object of a GTA scene
MAIN_CLASSES = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
                5: "bus", 6: "train", 7: "truck", 8: "boat"}


class FollowError(Exception):
    pass


def model_path(data_dir: Path) -> Path:
    return data_dir / "models" / "yolox_m.onnx"


# --- sampling and detection ---------------------------------------------------------

def sample_frames(src: Path, a: float, b: float, *, blank: list[int] | None = None):
    """Yield (t, 360x640x3 BGR array) at SAMPLE_FPS, t relative to `a`."""
    import numpy as np

    w, h = INPUT, INPUT * SRC_H // SRC_W
    vf = f"fps={SAMPLE_FPS},scale={w}:{h}"
    if blank:
        x, y, bw, bh = [int(v / SCALE) for v in blank]
        vf += f",drawbox=x={x}:y={y}:w={bw}:h={bh}:color=0x727272:t=fill"
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src),
         "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        stdout=subprocess.PIPE)
    size, i = w * h * 3, 0
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            yield i / SAMPLE_FPS, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            i += 1
    finally:
        proc.stdout.close()
        proc.wait()


def _grids():
    import numpy as np

    grids, strides = [], []
    for s in (8, 16, 32):
        n = INPUT // s
        xv, yv = np.meshgrid(np.arange(n), np.arange(n))
        grids.append(np.stack((xv, yv), 2).reshape(-1, 2))
        strides.append(np.full((n * n, 1), s))
    return np.concatenate(grids), np.concatenate(strides)


def _nms(boxes, scores, thr: float = 0.45) -> list[int]:
    import numpy as np

    order, keep = scores.argsort()[::-1], []
    while order.size:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        iou = inter / (area[i] + area[order[1:]] - inter + 1e-9)
        order = order[1:][iou <= thr]
    return keep


def yolox_detector(model: Path):
    """frame (360x640 BGR) -> [{box: [x1, y1, x2, y2] in source px, score, cls}]."""
    import numpy as np
    import onnxruntime as ort

    if not model.exists():
        raise FollowError(f"detector model missing: {model} (YOLOX-m ONNX, see engine/README)")
    sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    grids, strides = _grids()

    def detect(frame) -> list[dict]:
        img = np.full((INPUT, INPUT, 3), 114, np.uint8)
        img[:frame.shape[0], :frame.shape[1]] = frame
        out = sess.run(None, {name: img.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
        xy = (out[:, :2] + grids) * strides
        wh = np.exp(out[:, 2:4]) * strides
        cls = out[:, 5:].argmax(1)
        score = out[:, 4] * out[np.arange(len(out)), 5 + cls]
        sel = (score >= MIN_SCORE) & np.isin(cls, list(MAIN_CLASSES))
        if not sel.any():
            return []
        xy, wh, cls, score = xy[sel], wh[sel], cls[sel], score[sel]
        boxes = np.concatenate([xy - wh / 2, xy + wh / 2], 1) * SCALE
        boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, SRC_W)
        boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, SRC_H)
        return [{"box": [round(float(v)) for v in boxes[i]], "score": round(float(score[i]), 3),
                 "cls": MAIN_CLASSES[int(cls[i])]} for i in _nms(boxes, score)]

    return detect


# --- main object and camera path ----------------------------------------------------

def _iou(p: list[int], q: list[int]) -> float:
    ix = max(0, min(p[2], q[2]) - max(p[0], q[0]))
    iy = max(0, min(p[3], q[3]) - max(p[1], q[1]))
    inter = ix * iy
    union = (p[2] - p[0]) * (p[3] - p[1]) + (q[2] - q[0]) * (q[3] - q[1]) - inter
    return inter / union if union > 0 else 0.0


def pick_main(dets: list[dict], prev: list[int] | None) -> dict | None:
    """The detection most likely to be the player's character or vehicle."""
    best, best_s = None, 0.0
    for d in dets:
        x1, y1, x2, y2 = d["box"]
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        area = (x2 - x1) * (y2 - y1) / (SRC_W * SRC_H)
        central = math.exp(-0.5 * (((cx - SRC_W / 2) / (0.3 * SRC_W)) ** 2
                                   + ((cy - SRC_H / 2) / (0.4 * SRC_H)) ** 2))
        s = d["score"] * math.sqrt(area) * central
        if prev and _iou(d["box"], prev) > 0.2:
            s *= 2.0
        if s > best_s:
            best, best_s = d, s
    return best


def _smooth(xs: list[float], sigma: float) -> list[float]:
    if sigma <= 0:
        return list(xs)
    r = max(1, int(3 * sigma))
    k = [math.exp(-0.5 * (i / sigma) ** 2) for i in range(-r, r + 1)]
    out = []
    for i in range(len(xs)):
        acc = wsum = 0.0
        for j, kw in enumerate(k):
            n = min(max(i + j - r, 0), len(xs) - 1)
            acc += kw * xs[n]
            wsum += kw
        out.append(acc / wsum)
    return out


def window(gameplay: list[int] | None) -> tuple[int, int, int, int]:
    """(crop_w, crop_h, left, right): the band-aspect window inside the gameplay rect."""
    gx, gy, gw, gh = gameplay or [0, 0, SRC_W, SRC_H]
    crop_w = min(gw, int(round(gh * BAND_W / BAND_H / 2)) * 2)
    return crop_w, gh, gx, gx + gw


def extent(b: list[int], left: float, right: float, crop_w: int) -> tuple[float, float, float]:
    """(x0, x2, centre) of what the window must hold for box `b`.

    GTA's chase camera keeps the player's vehicle or character on the picture's
    vertical centre line, and a detector box often misses one side of it: m5 at 24 s,
    a rolling jet, box 528-1203 px, jet 540-1380 px, the right wing was cut. When the
    centre line runs through the box, the box is mirrored about it and the window
    stays centred; where the mirror would be wider than the window, it grows only as
    far as the window allows (continuous, so the camera does not jump at the limit).
    """
    mid = (left + right) / 2
    if b[0] <= mid <= b[2] and b[2] - b[0] <= crop_w:
        half = max(mid - b[0], b[2] - mid)
        x0 = min(b[0], max(mid - half, b[2] - crop_w))
        x2 = max(b[2], min(mid + half, b[0] + crop_w))
        return x0, x2, mid
    return float(b[0]), float(b[2]), (b[0] + b[2]) / 2


def plan_path(boxes: list[list[int] | None], *, crop_w: int = CROP_W, left: int = 0,
              right: int = SRC_W, sample_fps: float = SAMPLE_FPS) -> dict:
    """Window left edges per sample: smooth, inside the frame, holding every box that fits."""
    lo_edge, hi_edge = float(left), float(right - crop_w)
    known = [i for i, b in enumerate(boxes) if b]
    desired, lo, hi, wide = [], [], [], []
    for i, b in enumerate(boxes):
        if b is None:  # no object: glide between the neighbours' centres
            before = max((k for k in known if k < i), default=None)
            after = min((k for k in known if k > i), default=None)
            near = [boxes[k] for k in (before, after) if k is not None]
            cx = (sum(extent(q, left, right, crop_w)[2] for q in near) / len(near)) if near \
                else (left + right) / 2
            lo.append(lo_edge)
            hi.append(hi_edge)
            wide.append(False)
        else:
            wide.append(b[2] - b[0] > crop_w)
            e0, e2, cx = extent(b, left, right, crop_w)
            # COCO boxes clip wing tips by up to ~120 px (m5, 2026-11-19): keep a margin of
            # 15 % of the width, shrinking smoothly to what fits; none at the frame edge
            m = min(max(MARGIN, 0.15 * (e2 - e0)), max(0.0, (crop_w - (e2 - e0)) / 2))
            x0, x2 = max(e0 - m, left), min(e2 + m, right)
            a_, b_ = max(lo_edge, float(x2 - crop_w)), min(hi_edge, float(x0))
            if a_ > b_:  # wider than the window: centre it (flagged above)
                a_ = b_ = min(max(cx - crop_w / 2, lo_edge), hi_edge)
            lo.append(a_)
            hi.append(b_)
        desired.append(min(max(cx - crop_w / 2, lo_edge), hi_edge))
    xs = [min(max(x, lo[i]), hi[i]) for i, x in enumerate(desired)]
    for _ in range(30):  # alternate smoothing and projection into the corridors
        xs = [min(max(x, lo[i]), hi[i]) for i, x in enumerate(_smooth(xs, SMOOTH_S * sample_fps))]
    return {"crop_w": crop_w, "sample_fps": sample_fps,
            "x": [int(round(x)) for x in xs], "boxes": boxes, "too_wide": wide}


def cam_region(facecam: list[int], pad_x: int = 120, pad_y: int = 40) -> list[int]:
    """The streamer's own cam inside the gameplay, padded: a keyed cam spills (ohnePixel's
    arm reached 120 px left of the calibrated rect, 2026-11-19, and the detector took it
    for a person). Blanked this wide for the detector; the render blurs a 40 px pad."""
    x, y, w, h = facecam
    x0, y0 = max(0, x - pad_x), max(0, y - pad_y)
    x1, y1 = min(SRC_W, x + w + pad_x), min(SRC_H, y + h + pad_y)
    return [x0 // 2 * 2, y0 // 2 * 2, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2]


def _centre(b: list[int]) -> tuple[float, float]:
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def _area(b: list[int]) -> int:
    return (b[2] - b[0]) * (b[3] - b[1])


def _same(p: list[int], q: list[int]) -> bool:
    """Same object a sample later: overlapping, or its centre moved under half a width."""
    (px, py), (qx, qy) = _centre(p), _centre(q)
    reach = 0.5 * max(p[2] - p[0], q[2] - q[0])
    return _iou(p, q) > 0.1 or math.hypot(px - qx, py - qy) < reach


HOLD_S = 2.0  # the main object counts as present this long after it was last seen


def track(detections: list[list[dict]], sample_fps: float = SAMPLE_FPS) -> list[list[int] | None]:
    """Main object per sample, with hysteresis: while the main object was seen within
    HOLD_S, a different object takes over only if it is at least half its size AND is
    picked twice in a row (size = the largest box accepted within HOLD_S, so a glimpse of
    a part does not lower the bar). Otherwise the sample counts as 'no object' and the camera
    glides (2026-11-19: an AI fighter jet took the camera for 1.5 s while the player's
    jet was hidden behind a tower)."""
    out: list[list[int] | None] = []
    recent, recent_i, pending = None, -10**9, None
    sizes: list[tuple[int, int]] = []  # (sample, area) of accepted boxes
    for i, dets in enumerate(detections):
        live = recent if (i - recent_i) / sample_fps <= HOLD_S else None
        ref = max((s for k, s in sizes if (i - k) / sample_fps <= HOLD_S), default=0)
        cand = pick_main(dets, live)
        box = cand["box"] if cand else None
        if box and live and not _same(box, live):
            if _area(box) < 0.5 * ref:
                box = None
            elif pending and _same(box, pending):
                pending = None
            else:
                pending, box = box, None
        elif box:
            pending = None
        if box:
            recent, recent_i = box, i
            sizes.append((i, _area(box)))
        out.append(box)
    return despike(out)


def despike(boxes: list[list[int] | None]) -> list[list[int] | None]:
    """Median of three per edge: one sample whose box swallowed a building (m5 at 22.25 s
    and 50.25 s: 936 and 1103 px for a jet of about 860) does not move the camera or
    count as too wide. Needs both neighbours. A box that neither neighbour confirms is
    dropped (m5 at 38 s: a tower read as a 'train' for one sample pulled the camera
    120 px); a real object is seen again a quarter second later."""
    out = list(boxes)
    for i, b in enumerate(boxes):
        if not b:
            continue
        near = [boxes[k] for k in (i - 1, i + 1) if 0 <= k < len(boxes) and boxes[k]]
        if not any(_same(b, q) for q in near):
            out[i] = None
        elif len(near) == 2:
            out[i] = [sorted(q[k] for q in (near[0], b, near[1]))[1] for k in range(4)]
    return out


def plan(src: Path, a: float, b: float, *, layout: dict, detector) -> dict:
    """Sample, detect, track and plan the window for the cut [a, b] of `src`."""
    facecam = layout.get("facecam")
    blank = cam_region(facecam) if facecam else None
    detections = [detector(frame) for _, frame in sample_frames(src, a, b, blank=blank)]
    if not detections:
        raise FollowError(f"no frames sampled from {src}")
    crop_w, crop_h, left, right = window(layout.get("gameplay"))
    return {**plan_path(track(detections), crop_w=crop_w, left=left, right=right),
            "crop_h": crop_h, "y": (layout.get("gameplay") or [0, 0])[1]}


def static(layout: dict) -> dict:
    """No detection: the window stays in the middle of the gameplay rect."""
    crop_w, crop_h, left, right = window(layout.get("gameplay"))
    x = (left + right - crop_w) // 2 // 2 * 2
    return {"crop_w": crop_w, "crop_h": crop_h, "y": (layout.get("gameplay") or [0, 0])[1],
            "sample_fps": SAMPLE_FPS, "x": [x], "boxes": [None], "too_wide": [False]}


# --- render and check ---------------------------------------------------------------

def x_at(follow: dict, t: float) -> int:
    """Window left edge at time t (linear between samples)."""
    xs, f = follow["x"], follow["sample_fps"]
    p = min(max(t * f, 0.0), len(xs) - 1)
    i = int(p)
    j = min(i + 1, len(xs) - 1)
    return int(round(xs[i] + (xs[j] - xs[i]) * (p - i)))


def sendcmd(follow: dict, duration: float, fps: float, target: str = "crop@follow") -> str:
    """One crop position per output frame, as an ffmpeg sendcmd script."""
    lines, n = [], int(math.ceil(duration * fps)) + 1
    last = None
    for k in range(n):
        t = k / fps
        x = x_at(follow, t)
        if x != last:
            lines.append(f"{t:.4f} {target} x {x};")
            last = x
    return "\n".join(lines) + "\n"


def misses(follow: dict) -> list[dict]:
    """Samples whose main object is not completely inside the window."""
    out = []
    for i, (b, x) in enumerate(zip(follow["boxes"], follow["x"])):
        if b and (b[0] < x or b[2] > x + follow["crop_w"]):
            out.append({"t": round(i / follow["sample_fps"], 2), "box": b, "x": x,
                        "too_wide": follow["too_wide"][i]})
    return out
