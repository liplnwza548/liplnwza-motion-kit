"""Per-pose clean-plate mouth animation for the LiplnwZa 3D-look sticker.

The generated clean plates are sampled only inside a fixed, pose-specific skin
mask. The original pose remains the immutable source everywhere else. Mouth
geometry is interpolated continuously from the supplied viseme schedule; this
is a 2D compositor, not a 3D facial rig or phoneme recognizer.
"""
from __future__ import annotations

from bisect import bisect_right
import json
import math
from pathlib import Path
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

POSES = ("explain", "point_right", "thinking", "magnify", "point_left", "thumbs_up")
PARAMS = {
    "CLOSED": (44.0, 0.5, 0.0, 0.12),
    "AA": (56.0, 29.0, 0.25, 0.28),
    "EE": (57.0, 11.0, 0.60, 0.20),
    "OH": (31.0, 28.0, 0.10, 0.70),
    "OO": (19.0, 18.0, 0.04, 0.90),
    "FV": (44.0, 5.0, 0.75, 0.22),
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def register(original: Image.Image, clean: Image.Image, eyes):
    """Align the edited clean plate to the exact source using two eye patches."""
    org = np.asarray(original.convert("RGB"), dtype=np.float64)
    src = np.asarray(clean.convert("RGB"), dtype=np.float64)
    found, scores = [], []
    for x, y in eyes:
        x, y = round(x), round(y)
        radius = 14
        target = org[y-radius:y+radius, x-radius:x+radius]
        target = target - target.mean(axis=(0, 1))
        target_norm = np.sqrt((target * target).sum())
        best = (-2.0, None)
        for dy in range(-14, 15):
            for dx in range(-14, 15):
                candidate = src[y+dy-radius:y+dy+radius, x+dx-radius:x+dx+radius]
                if candidate.shape != target.shape:
                    continue
                candidate = candidate - candidate.mean(axis=(0, 1))
                score = (target * candidate).sum() / (target_norm * np.sqrt((candidate*candidate).sum()) + 1e-9)
                if score > best[0]:
                    best = (float(score), (x + dx, y + dy))
        found.append(best[1])
        scores.append(best[0])
    if any(point is None for point in found):
        raise ValueError("Could not register clean plate to mascot eyes")
    A, b = [], []
    for (x, y), (u, v) in zip(found, eyes):
        A.extend([[x, -y, 1, 0], [y, x, 0, 1]])
        b.extend([u, v])
    c, d, tx, ty = np.linalg.solve(A, b)
    matrix = np.array([[c, -d, tx], [d, c, ty], [0, 0, 1.0]])
    aligned = clean.transform(
        original.size,
        Image.Transform.AFFINE,
        tuple(np.linalg.inv(matrix)[:2].ravel()),
        Image.Resampling.BICUBIC,
    )
    return aligned, {"source_eye_centers": found, "target_eye_centers": eyes, "correlation": scores, "matrix": matrix.tolist()}


def cubic_path(points, samples=32):
    out = [points[0]]
    start = np.asarray(points[0], dtype=float)
    for i in range(1, len(points), 3):
        c1, c2, end = [np.asarray(point, dtype=float) for point in points[i:i+3]]
        for t in np.linspace(0, 1, samples)[1:]:
            out.append(tuple((1-t)**3*start + 3*(1-t)**2*t*c1 + 3*(1-t)*t*t*c2 + t**3*end))
        start = end
    return out


def compose_mouth(params, profile):
    width, height, teeth, rounding = params
    width *= profile["width_scale"]
    height *= profile["height_scale"]
    scale = 4
    canvas_w, canvas_h = 128, 112
    ox, oy = canvas_w / 2, canvas_h / 2

    def p(x, y):
        return ((ox + x) * scale, (oy + y) * scale)

    mouth = Image.new("RGBA", (canvas_w * scale, canvas_h * scale))
    draw = ImageDraw.Draw(mouth)
    if height > 2:
        top = -height * (0.27 + 0.22 * rounding)
        bottom = height * (0.67 - 0.13 * rounding)
        corner = -height * 0.16 * (1 - rounding)
        side = 0.34 + 0.18 * rounding
        cavity = cubic_path([
            p(-width/2, corner), p(-width*side, top-height*.10), p(width*side, top-height*.10), p(width/2, corner),
            p(width*(.39+.13*rounding), bottom*.96), p(-width*(.28+.24*rounding), bottom*1.12), p(-width/2, corner),
        ])
        cavity_mask = Image.new("L", mouth.size)
        ImageDraw.Draw(cavity_mask).polygon(cavity, fill=255)
        yy = np.indices((canvas_h*scale, canvas_w*scale))[0] / scale - oy
        q = np.clip((yy - top) / max(1, bottom - top), 0, 1)
        grad = np.zeros((canvas_h*scale, canvas_w*scale, 4), dtype=np.uint8)
        for channel, (low, high) in enumerate(((54, 125), (14, 35), (18, 35))):
            grad[:, :, channel] = (low + (high-low)*q).astype(np.uint8)
        grad[:, :, 3] = np.asarray(cavity_mask)
        mouth.alpha_composite(Image.fromarray(grad))
        inner = Image.new("RGBA", mouth.size)
        inner_draw = ImageDraw.Draw(inner)
        band = max(.5, min(height*.48, height*teeth))
        if height > 4 and teeth > .07:
            tooth = cubic_path([
                p(-width*.44, top-.3), p(-width*.25, top-1.7), p(width*.25, top-1.7), p(width*.44, top-.3),
                p(width*.30, top+band+1), p(-width*.28, top+band+1), p(-width*.44, top-.3),
            ])
            inner_draw.polygon(tooth, fill="#f8eee1")
            inner_draw.line(tooth[:32], fill="#cab4a4", width=2)
        if height > 10:
            inner_draw.ellipse([p(-width*.28, height*.32), p(width*.33, height*.94)], fill="#dc6b6a")
            inner_draw.ellipse([p(-width*.24, height*.34), p(width*.24, height*.70)], fill="#e98680")
        inner.putalpha(Image.fromarray(np.minimum(np.asarray(inner.getchannel("A")), np.asarray(cavity_mask))))
        mouth.alpha_composite(inner)
        draw = ImageDraw.Draw(mouth)
        draw.line(cavity + [cavity[0]], fill=(133, 57, 40, 220), width=4, joint="curve")
        lower = cubic_path([
            p(-width*.38, height*.34), p(-width*.12, bottom+2.1), p(width*.22, bottom+2.1), p(width*.40, height*.33),
        ])
        draw.line(lower, fill=(225, 132, 100, 160), width=5, joint="curve")
    else:
        line = cubic_path([p(-width/2, -1), p(-width*.15, 3), p(width*.20, 3), p(width/2, -1)])
        draw.line(line, fill=(147, 61, 40, 235), width=5, joint="curve")
    mouth = mouth.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
    return mouth.rotate(profile["angle"], Image.Resampling.BICUBIC, expand=True)


class PoseMouthRig:
    def __init__(self, rig_root, voice_path, viseme_path, words_path):
        self.root = Path(rig_root)
        self.profiles = read_json(self.root / "profiles.json")["poses"]
        if set(self.profiles) != set(POSES):
            raise ValueError("Profiles must cover exactly the six supported mascot poses")
        self.visemes = read_json(Path(viseme_path))
        self.viseme_times = [item["start"] for item in self.visemes]
        self.words = read_json(Path(words_path))
        with wave.open(str(voice_path), "rb") as audio:
            self.sample_rate = audio.getframerate()
            self.audio = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(float) / 32768
        self.duration = len(self.audio) / self.sample_rate
        self.dt = 1 / 120
        self.parameter_timeline = self._make_parameter_timeline()
        self.pose_data = {}
        self.registration = {}
        for pose in POSES:
            self._prepare_pose(pose)

    def _make_parameter_timeline(self):
        if not self.visemes:
            raise ValueError("Viseme cues are required to animate the mouth")
        current = np.array(PARAMS["CLOSED"], dtype=float)
        low_time = 0.0
        values = []
        end_time = self.duration + 0.15
        for time in np.arange(-.125, end_time, self.dt):
            if time < 0:
                target = np.array(PARAMS[self.visemes[0]["shape"]], dtype=float)
            else:
                lookahead = time + .018
                index = max(0, bisect_right(self.viseme_times, lookahead) - 1)
                shape = self.visemes[index]["shape"]
                a = max(0, int((time - .035) * self.sample_rate))
                b = min(len(self.audio), int((time + .035) * self.sample_rate))
                rms = math.sqrt(float(np.mean(self.audio[a:b] ** 2))) if b > a else 0.0
                low_time = low_time + self.dt if rms < .006 else 0.0
                if low_time > .11 or (self.words and time >= self.words[-1]["end"] + .02):
                    shape = "CLOSED"
                target = np.array(PARAMS[shape], dtype=float)
            delta = (target - current) * (1 - np.exp(-self.dt / np.array([.045, .040, .055, .050])))
            delta = np.clip(delta, -np.array([240, 240, 7, 8]) * self.dt, np.array([240, 240, 7, 8]) * self.dt)
            current = current + delta
            if time >= -1e-5:
                values.append(current.copy())
        return np.asarray(values)

    def _prepare_pose(self, pose):
        profile = self.profiles[pose]
        original = Image.open(self.root / "original" / f"{pose}.png").convert("RGBA")
        clean = Image.open(self.root / "clean" / f"{pose}.png").convert("RGBA").resize(original.size, Image.Resampling.LANCZOS)
        aligned, registration = register(original, clean, profile["eyes"])
        registration["max_eye_correlation"] = max(registration["correlation"])
        registration["min_eye_correlation"] = min(registration["correlation"])
        if registration["min_eye_correlation"] < .72:
            raise ValueError(f"Clean plate registration is too weak for {pose}: {registration['correlation']}")

        hard = Image.new("L", original.size, 0)
        ImageDraw.Draw(hard).polygon([tuple(point) for point in profile["mask_polygon"]], fill=255)
        mask = hard.filter(ImageFilter.GaussianBlur(2.6))
        ma = np.asarray(mask)
        org = np.asarray(original).copy()
        plate = np.asarray(aligned).copy()

        # Correct a small uniform color cast using cheek pixels just outside the repair polygon.
        expanded = np.asarray(hard.filter(ImageFilter.MaxFilter(13))) > 8
        ring = expanded & (ma < 2)
        skin = (org[:, :, 0] > 175) & (org[:, :, 1] > 90) & (org[:, :, 0] > org[:, :, 1] + 15)
        clean_skin = (plate[:, :, 0] > 175) & (plate[:, :, 1] > 90)
        samples = ring & skin & clean_skin
        offset = np.median(org[:, :, :3][samples].astype(float) - plate[:, :, :3][samples].astype(float), axis=0) if samples.sum() >= 8 else np.zeros(3)
        offset = np.clip(offset, -18, 18)
        plate[:, :, :3] = np.clip(plate[:, :, :3].astype(float) + offset, 0, 255).astype(np.uint8)
        plate[:, :, 3] = org[:, :, 3]
        base = Image.composite(Image.fromarray(plate), original, mask)
        if not np.array_equal(np.asarray(base)[ma == 0], org[ma == 0]):
            raise AssertionError(f"Clean plate changed pixels outside repair mask for {pose}")

        occluder = Image.new("L", original.size, 0)
        if "occluder_ellipse" in profile:
            # Restore the source magnifying-glass rim above the animated mouth.
            factor = 4
            hi = Image.new("L", (original.width * factor, original.height * factor), 0)
            box = [round(value * factor) for value in profile["occluder_ellipse"]]
            ImageDraw.Draw(hi).ellipse(box, outline=255, width=round(profile["occluder_width"] * factor))
            band = np.asarray(hi.resize(original.size, Image.Resampling.LANCZOS))
            rgb = org[:, :, :3].astype(np.int16)
            neutral_gray = (rgb.max(axis=2) - rgb.min(axis=2) <= 22) & (rgb.mean(axis=2) < 190) & (rgb.mean(axis=2) > 15)
            # Keep only the dark neutral rim pixels inside the repair zone. A broad
            # ellipse also caught the original mouth visible through the lens.
            ys, xs = np.indices(ma.shape)
            clip = xs <= profile.get("occluder_clip_x_max", original.width)
            occluder_array = np.where((band > 0) & (ma > 0) & neutral_gray & clip, np.minimum(band, ma), 0).astype(np.uint8)
            occluder = Image.fromarray(occluder_array)
            base = Image.composite(original, base, occluder)

        self.pose_data[pose] = {"original": original, "base": base, "mask": mask, "occluder": occluder, "profile": profile}
        self.registration[pose] = {**registration, "skin_offset": offset.tolist(), "mask_bounds": list(mask.getbbox()), "repair_pixels": int((ma > 0).sum()), "outside_mask_exact": True}

    def parameters(self, time):
        x = max(0.0, min(len(self.parameter_timeline) - 1.0, time / self.dt))
        i = int(x)
        j = min(i + 1, len(self.parameter_timeline) - 1)
        return self.parameter_timeline[i] * (1 - (x-i)) + self.parameter_timeline[j] * (x-i)

    def frame(self, pose, time):
        if pose not in self.pose_data:
            raise ValueError(f"Unsupported pose: {pose}")
        data = self.pose_data[pose]
        mouth = compose_mouth(self.parameters(time), data["profile"])
        anchor_x, anchor_y = data["profile"]["anchor"]
        left = round(anchor_x - mouth.width / 2)
        top = round(anchor_y - mouth.height / 2)
        layer = Image.new("RGBA", data["base"].size)
        layer.alpha_composite(mouth, (left, top))
        layer.putalpha(Image.fromarray(np.minimum(np.asarray(layer.getchannel("A")), np.asarray(data["mask"]))))
        result = data["base"].copy()
        result.alpha_composite(layer)
        if data["occluder"].getbbox():
            result = Image.composite(data["original"], result, data["occluder"])
        return result

    def static_frame(self, pose, shape):
        """Diagnostic still used to inspect all six viseme shapes on every pose."""
        data = self.pose_data[pose]
        mouth = compose_mouth(PARAMS[shape], data["profile"])
        x, y = data["profile"]["anchor"]
        layer = Image.new("RGBA", data["base"].size)
        layer.alpha_composite(mouth, (round(x-mouth.width/2), round(y-mouth.height/2)))
        layer.putalpha(Image.fromarray(np.minimum(np.asarray(layer.getchannel("A")), np.asarray(data["mask"]))))
        result = data["base"].copy()
        result.alpha_composite(layer)
        if data["occluder"].getbbox():
            result = Image.composite(data["original"], result, data["occluder"])
        return result

    def write_registration(self, path):
        Path(path).write_text(json.dumps(self.registration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
