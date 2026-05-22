from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Any

import cv2
import numpy as np


FACE_SIZE = (160, 160)


@dataclass(slots=True)
class AuthorizedProfile:
    label_id: int
    name: str
    relation: str
    role: str
    created_at: str


@dataclass(slots=True)
class FaceIdentity:
    name: str
    relation: str
    role: str
    confidence: float
    label_id: int


@dataclass(slots=True)
class FaceScanResult:
    identities: list[FaceIdentity]
    unknown_faces: int
    total_faces: int
    preview_data_url: str


class FaceAuthService:
    """Local face enrollment and recognition using OpenCV LBPH."""

    def __init__(
        self,
        *,
        camera_index: int | None = None,
        width: int | None = None,
        height: int | None = None,
        threshold: float | None = None,
        data_dir: str = "data/face_auth",
    ) -> None:
        if not hasattr(cv2, "face"):
            raise RuntimeError("opencv-contrib-python es necesario para reconocimiento facial local.")

        from config import settings
        self.camera_index = settings.camera_index if camera_index is None else camera_index
        self.width = settings.camera_width if width is None else width
        self.height = settings.camera_height if height is None else height
        self.threshold = settings.face_recognition_threshold if threshold is None else threshold
        self.data_dir = Path(data_dir)
        self.samples_dir = self.data_dir / "samples"
        self.model_path = self.data_dir / "faces_lbph.yml"
        self.profiles_path = self.data_dir / "profiles.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.samples_dir.mkdir(parents=True, exist_ok=True)

        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(str(cascade_path))
        if self.detector.empty():
            raise RuntimeError("No pude cargar el detector facial local.")

    def enroll(self, name: str, relation: str = "owner", role: str = "owner", samples: int = 18) -> str:
        clean_name = self._clean_name(name)
        clean_relation = relation.strip().lower() or "autorizado"
        clean_role = role.strip().lower() or "trusted"

        profiles = self._load_profiles()
        label_id = self._label_for_profile(profiles, clean_name)
        profile_dir = self.samples_dir / str(label_id)
        profile_dir.mkdir(parents=True, exist_ok=True)

        faces = self._capture_face_samples(max(5, samples))
        if len(faces) < 5:
            raise RuntimeError("No obtuve suficientes muestras claras del rostro.")

        for index, face in enumerate(faces, start=1):
            cv2.imwrite(str(profile_dir / f"sample_{index:03d}.png"), face)

        profiles[str(label_id)] = {
            "label_id": label_id,
            "name": clean_name,
            "relation": clean_relation,
            "role": clean_role,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save_profiles(profiles)
        self.retrain()
        return clean_name

    def identify(self) -> FaceScanResult:
        frame = self._capture_frame()
        return self.identify_frame(frame)

    def identify_frame(self, frame) -> FaceScanResult:
        faces = self._detect_faces(frame)
        profiles = self._load_profiles()
        preview_data_url = self._frame_as_data_url(self._draw_preview(frame.copy(), faces), max_width=560)

        if not faces:
            return FaceScanResult([], 0, 0, preview_data_url)

        recognizer = self._load_recognizer()
        identities: list[FaceIdentity] = []
        unknown_faces = 0

        for (_, _, _, _, face_crop) in faces:
            label_id, distance = recognizer.predict(face_crop)
            profile = profiles.get(str(label_id))
            if profile and distance <= self.threshold:
                identities.append(
                    FaceIdentity(
                        name=str(profile.get("name", "Autorizado")),
                        relation=str(profile.get("relation", "autorizado")),
                        role=str(profile.get("role", "trusted")),
                        confidence=max(0.0, 100.0 - float(distance)),
                        label_id=int(label_id),
                    )
                )
            else:
                unknown_faces += 1

        return FaceScanResult(identities, unknown_faces, len(faces), preview_data_url)

    def list_profiles(self) -> list[AuthorizedProfile]:
        profiles = self._load_profiles()
        result: list[AuthorizedProfile] = []
        for profile in profiles.values():
            result.append(
                AuthorizedProfile(
                    label_id=int(profile.get("label_id", 0)),
                    name=str(profile.get("name", "")),
                    relation=str(profile.get("relation", "")),
                    role=str(profile.get("role", "")),
                    created_at=str(profile.get("created_at", "")),
                )
            )
        return sorted(result, key=lambda item: item.label_id)

    def delete_profile(self, name: str) -> bool:
        clean_name = self._clean_name(name)
        profiles = self._load_profiles()
        match_id = None
        for label_id, profile in profiles.items():
            if self._clean_name(str(profile.get("name", ""))).lower() == clean_name.lower():
                match_id = label_id
                break

        if match_id is None:
            return False

        profiles.pop(match_id, None)
        self._save_profiles(profiles)
        profile_dir = self.samples_dir / match_id
        if profile_dir.exists():
            for path in profile_dir.glob("*"):
                path.unlink(missing_ok=True)
            profile_dir.rmdir()
        self.retrain()
        return True

    def has_profiles(self) -> bool:
        return bool(self._load_profiles())

    def retrain(self) -> None:
        images: list[np.ndarray] = []
        labels: list[int] = []
        for profile_dir in self.samples_dir.iterdir():
            if not profile_dir.is_dir():
                continue
            try:
                label_id = int(profile_dir.name)
            except ValueError:
                continue

            for sample_path in profile_dir.glob("*.png"):
                image = cv2.imread(str(sample_path), cv2.IMREAD_GRAYSCALE)
                if image is None:
                    continue
                images.append(image)
                labels.append(label_id)

        if not images:
            self.model_path.unlink(missing_ok=True)
            return

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(images, np.array(labels, dtype=np.int32))
        recognizer.write(str(self.model_path))

    def _capture_face_samples(self, target_count: int) -> list[np.ndarray]:
        capture = self._open_capture()
        samples: list[np.ndarray] = []
        try:
            for _ in range(10):
                capture.read()
                time.sleep(0.03)

            attempts = 0
            while len(samples) < target_count and attempts < target_count * 8:
                attempts += 1
                ok, frame = capture.read()
                if not ok:
                    continue
                faces = self._detect_faces(frame)
                if len(faces) == 1:
                    samples.append(faces[0][4])
                time.sleep(0.06)
        finally:
            capture.release()
        return samples

    def _capture_frame(self):
        capture = self._open_capture()
        frame = None
        try:
            for _ in range(12):
                ok, candidate = capture.read()
                if ok:
                    frame = candidate
                time.sleep(0.03)
        finally:
            capture.release()

        if frame is None:
            raise RuntimeError("No pude capturar imagen de la camara.")
        return frame

    def _open_capture(self):
        capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError("No pude abrir la camara.")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        capture.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        return capture

    def _detect_faces(self, frame) -> list[tuple[int, int, int, int, np.ndarray]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.12, minNeighbors=5, minSize=(70, 70))
        result: list[tuple[int, int, int, int, np.ndarray]] = []
        for (x, y, w, h) in faces:
            crop = gray[y : y + h, x : x + w]
            crop = cv2.equalizeHist(cv2.resize(crop, FACE_SIZE, interpolation=cv2.INTER_AREA))
            result.append((int(x), int(y), int(w), int(h), crop))
        return result

    def _draw_preview(self, frame, faces: list[tuple[int, int, int, int, np.ndarray]]):
        for (x, y, w, h, _) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (32, 244, 181), 2)
        return frame

    def _load_recognizer(self):
        if not self.model_path.exists():
            raise RuntimeError("No hay rostros autorizados registrados.")
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(str(self.model_path))
        return recognizer

    def _load_profiles(self) -> dict[str, dict[str, Any]]:
        if not self.profiles_path.exists():
            return {}
        try:
            data = json.loads(self.profiles_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _save_profiles(self, profiles: dict[str, dict[str, Any]]) -> None:
        self.profiles_path.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")

    def _label_for_profile(self, profiles: dict[str, dict[str, Any]], name: str) -> int:
        for label_id, profile in profiles.items():
            if self._clean_name(str(profile.get("name", ""))).lower() == name.lower():
                return int(label_id)

        existing_ids = [int(label_id) for label_id in profiles.keys() if str(label_id).isdigit()]
        return (max(existing_ids) + 1) if existing_ids else 1

    def _clean_name(self, name: str) -> str:
        return " ".join(name.strip().split())

    def _frame_as_data_url(self, frame, max_width: int) -> str:
        height, width = frame.shape[:2]
        if width > max_width:
            scale = max_width / width
            frame = cv2.resize(frame, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
        if not ok:
            return ""
        return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
