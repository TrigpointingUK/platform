"""
AWS Rekognition service for image analysis.
"""

import io
import logging
import math
from typing import Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image

from api.core.config import settings
from api.services.orientation_model import OrientationClassifier

logger = logging.getLogger(__name__)


class RekognitionService:
    """Service for AWS Rekognition image analysis."""

    def __init__(self, region_name: str = "eu-west-1"):
        """Initialise the Rekognition client."""
        try:
            self.client = boto3.client("rekognition", region_name=region_name)
        except Exception as e:
            logger.error(f"Failed to initialise Rekognition client: {e}")
            self.client = None
        # Orientation classifier (optional, lazy-loaded)
        self.orientation_model = (
            OrientationClassifier(model_path=settings.ORIENTATION_MODEL_PATH)
            if settings.ORIENTATION_MODEL_ENABLED
            else None
        )

    def analyse_orientation(self, image_bytes: bytes) -> Optional[Dict]:
        """
        Analyse image orientation using AWS Rekognition.

        Uses multiple approaches:
        1. Text detection and rotation analysis
        2. Face detection and orientation
        3. Object detection patterns

        Returns orientation confidence scores for 0°, 90°, 180°, 270° rotations.
        """
        if not self.client:
            logger.warning("Rekognition client not available for orientation analysis")
            return None

        logger.info(
            f"Starting orientation analysis for image ({len(image_bytes)} bytes)"
        )

        try:
            # Try text detection first
            logger.debug("Calling Rekognition detect_text API")
            text_response = self.client.detect_text(
                Image={"Bytes": image_bytes},
                Filters={
                    "WordFilter": {
                        "MinConfidence": 30.0,  # Lower threshold for better detection
                    }
                },
            )

            text_detections = text_response.get("TextDetections", [])
            logger.info(f"Found {len(text_detections)} text detections")

            # Analyse text orientations to infer image orientation
            orientations: Dict[str, float] = {
                "0": 0.0,
                "90": 0.0,
                "180": 0.0,
                "270": 0.0,
            }
            text_analysis_data = []

            for i, detection in enumerate(text_detections):
                if detection.get("Type") == "WORD":
                    geometry = detection.get("Geometry", {})
                    bbox = geometry.get("BoundingBox", {})
                    detected_text = detection.get("DetectedText", "")
                    confidence = detection.get("Confidence", 0)

                    # Get polygon points for more accurate rotation analysis
                    polygon = geometry.get("Polygon", [])

                    width = bbox.get("Width", 0)
                    height = bbox.get("Height", 0)

                    if width > 0 and height > 0 and len(polygon) >= 4:
                        aspect_ratio = width / height

                        # Calculate rotation from polygon points
                        angle_deg: float = 0.0
                        if len(polygon) >= 2:
                            p1, p2 = polygon[0], polygon[1]
                            dx = p2.get("X", 0) - p1.get("X", 0)
                            dy = p2.get("Y", 0) - p1.get("Y", 0)

                            # Calculate angle in degrees
                            angle_rad = math.atan2(dy, dx)
                            angle_deg = math.degrees(angle_rad)

                            # Normalize to 0-360
                            if angle_deg < 0:
                                angle_deg += 360

                        text_info = {
                            "text": detected_text,
                            "confidence": confidence,
                            "aspect_ratio": aspect_ratio,
                            "angle": angle_deg,
                            "bbox": bbox,
                        }
                        text_analysis_data.append(text_info)

                        # Log detailed info for first few detections
                        if i < 5:
                            logger.debug(
                                f"Text '{detected_text}': angle={angle_deg:.1f}°, "
                                f"aspect={aspect_ratio:.2f}, conf={confidence:.1f}"
                            )

                        # Classify orientation based on angle
                        weight = confidence / 100.0  # Use confidence as weight

                        if -15 <= angle_deg <= 15 or 345 <= angle_deg <= 360:
                            orientations["0"] += weight
                        elif 75 <= angle_deg <= 105:
                            orientations["90"] += weight
                        elif 165 <= angle_deg <= 195:
                            orientations["180"] += weight
                        elif 255 <= angle_deg <= 285:
                            orientations["270"] += weight
                        else:
                            # For angles in between, use aspect ratio heuristic
                            if aspect_ratio > 2.5:  # Very wide text
                                orientations["90"] += weight * 0.5
                                orientations["270"] += weight * 0.5
                            elif aspect_ratio < 0.4:  # Very tall text
                                orientations["0"] += weight * 0.5
                                orientations["180"] += weight * 0.5
                            else:
                                orientations["0"] += weight * 0.3

            logger.info(f"Text-based raw orientation scores: {orientations}")

            # Try face detection for additional orientation clues
            faces_count = 0
            try:
                logger.debug("Calling Rekognition detect_faces API")
                face_response = self.client.detect_faces(
                    Image={"Bytes": image_bytes}, Attributes=["POSE"]
                )

                faces = face_response.get("FaceDetails", [])
                faces_count = len(faces)
                logger.info(f"Found {faces_count} faces")

                for face in faces:
                    pose = face.get("Pose", {})
                    roll = pose.get("Roll", 0)  # Roll angle indicates rotation
                    confidence = face.get("Confidence", 0)

                    logger.debug(f"Face roll angle: {roll}°, confidence: {confidence}")

                    # Use face roll to adjust orientation scores
                    weight = confidence / 100.0 * 2  # Faces are strong indicators

                    if -15 <= roll <= 15:
                        orientations["0"] += weight
                    elif 75 <= roll <= 105:
                        orientations[
                            "270"
                        ] += weight  # Face roll is opposite to image rotation
                    elif roll >= 165 or roll <= -165:
                        orientations["180"] += weight
                    elif -105 <= roll <= -75:
                        orientations["90"] += weight

            except Exception as face_error:
                logger.debug(f"Face detection failed (not critical): {face_error}")

            # Try object/scene labels to infer orientation from inherently vertical objects and sky
            labels_count = 0
            label_samples: List[Dict[str, float | str]] = []
            try:
                logger.debug("Calling Rekognition detect_labels API")
                labels_response = self.client.detect_labels(
                    Image={"Bytes": image_bytes}, MaxLabels=50, MinConfidence=60.0
                )
                labels = labels_response.get("Labels", [])
                labels_count = len(labels)

                vertical_object_names = {
                    "Tower",
                    "Building",
                    "Skyscraper",
                    "Person",
                    "Tree",
                    "Pole",
                    "Lighthouse",
                    "Flagpole",
                    "Column",
                    "Mast",
                    "Monument",
                    "Crane",
                }

                # Heuristic 1: inherently vertical objects should be taller than wide in a correctly oriented image
                for label in labels:
                    name = label.get("Name", "")
                    if name in vertical_object_names:
                        for inst in label.get("Instances", []) or []:
                            bbox = inst.get("BoundingBox", {}) or {}
                            w = float(bbox.get("Width", 0.0))
                            h = float(bbox.get("Height", 0.0))
                            conf = float(
                                inst.get("Confidence", label.get("Confidence", 0.0))
                            )
                            if w <= 0.0 or h <= 0.0:
                                continue
                            aspect = w / h
                            weight = max(0.0, min(1.0, conf / 100.0)) * 1.5
                            # Very wide vertical object suggests 90/270 rotation
                            if aspect > 1.5:
                                orientations["90"] += weight
                                orientations["270"] += weight
                            # Very tall vertical object supports 0/180
                            elif (1.0 / aspect) > 1.5:
                                orientations["0"] += weight * 0.75
                                orientations["180"] += weight * 0.75
                            if len(label_samples) < 5:
                                label_samples.append(
                                    {"name": name, "aspect": aspect, "conf": conf}
                                )

                # Heuristic 2: sky should usually be at the top
                sky_bias = self._estimate_sky_bias(image_bytes)
                if sky_bias is not None:
                    top, bottom, left, right = sky_bias
                    # Normalise weights to [0, 1]
                    s_total = max(1e-6, top + bottom + left + right)
                    top_w = top / s_total
                    bottom_w = bottom / s_total
                    left_w = left / s_total
                    right_w = right / s_total

                    # Apply modest weights so text/face still dominate when present
                    orientations["0"] += top_w * 0.8
                    orientations["180"] += bottom_w * 0.8
                    orientations["90"] += left_w * 0.8
                    orientations["270"] += right_w * 0.8

            except Exception as labels_error:
                logger.debug(f"Label detection failed (not critical): {labels_error}")

            # If weak signal, optionally consult orientation model
            total = sum(orientations.values())
            weak_signal = total < 0.8  # heuristic threshold
            if weak_signal and self.orientation_model is not None:
                pred = self.orientation_model.predict(image_bytes)
                if pred is not None:
                    angle_str, prob = pred
                    if prob >= settings.ORIENTATION_MODEL_THRESHOLD:
                        # Boost model-predicted angle to dominate
                        orientations[angle_str] += 2.0 * prob
                        logger.info(
                            f"Orientation model boost: angle={angle_str}, prob={prob:.2f}"
                        )

            # Convert scores to confidence percentages
            total = sum(orientations.values())
            logger.info(f"Final raw scores: {orientations}, total: {total}")

            if total == 0:
                logger.warning(
                    "No orientation indicators found, defaulting to equal probabilities"
                )
                confidence_scores = {
                    "0": 25.0,
                    "90": 25.0,
                    "180": 25.0,
                    "270": 25.0,
                }
            else:
                confidence_scores = {
                    angle: (score / total) * 100
                    for angle, score in orientations.items()
                }

            # Determine most likely incorrect orientation
            max_incorrect = max(
                confidence_scores["90"],
                confidence_scores["180"],
                confidence_scores["270"],
            )

            likely_incorrect = max_incorrect > confidence_scores["0"]

            if likely_incorrect:
                suggested_rotation = max(
                    [
                        (angle, score)
                        for angle, score in confidence_scores.items()
                        if angle != "0"
                    ],
                    key=lambda x: x[1],
                )[0]
            else:
                suggested_rotation = "0"

            result = {
                "orientation_confidence": confidence_scores,
                "likely_incorrect": likely_incorrect,
                "suggested_rotation": suggested_rotation,
                "debug_info": {
                    "text_detections_count": len(text_detections),
                    "faces_count": faces_count,
                    "labels_count": labels_count,
                    "raw_scores": orientations,
                    "total_score": total,
                    "sample_text_data": text_analysis_data[:3],  # First 3 for debugging
                    "sample_label_data": label_samples,
                },
            }

            logger.info(
                f"Orientation analysis result: likely_incorrect={likely_incorrect}, "
                f"suggested={suggested_rotation}°, confidence_0={confidence_scores['0']:.1f}%"
            )
            return result

        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS Rekognition orientation analysis failed: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Orientation analysis failed: {e}")
            return {"error": str(e)}

    def moderate_content(self, image_bytes: bytes) -> Optional[Dict]:
        """
        Analyse image for inappropriate content using AWS Rekognition.

        Detects violence, pornography, advertisements, etc.
        """
        if not self.client:
            logger.warning("Rekognition client not available for content moderation")
            return None

        logger.info(f"Starting content moderation for image ({len(image_bytes)} bytes)")

        try:
            logger.debug("Calling Rekognition detect_moderation_labels API")
            response = self.client.detect_moderation_labels(
                Image={"Bytes": image_bytes}, MinConfidence=50.0
            )

            moderation_labels = response.get("ModerationLabels", [])
            logger.info(f"Found {len(moderation_labels)} moderation labels")

            # Categorise findings
            categories = {
                "inappropriate": False,
                "violence": False,
                "adult_content": False,
                "suggestive": False,
                "drugs": False,
                "tobacco": False,
                "alcohol": False,
                "gambling": False,
                "hate_symbols": False,
            }

            findings = []
            max_confidence = 0.0

            for label in moderation_labels:
                confidence = label.get("Confidence", 0)
                name = label.get("Name", "")
                parent_name = label.get("ParentName", "")

                max_confidence = max(max_confidence, confidence)

                finding = {
                    "label": name,
                    "confidence": confidence,
                    "parent": parent_name,
                }
                findings.append(finding)

                # Categorise the finding
                name_lower = name.lower()
                parent_lower = parent_name.lower()

                if any(
                    term in name_lower or term in parent_lower
                    for term in ["violence", "weapon", "blood"]
                ):
                    categories["violence"] = True
                    categories["inappropriate"] = True

                if any(
                    term in name_lower or term in parent_lower
                    for term in ["nudity", "explicit"]
                ):
                    categories["adult_content"] = True
                    categories["inappropriate"] = True

                if any(
                    term in name_lower or term in parent_lower
                    for term in ["suggestive", "revealing"]
                ):
                    categories["suggestive"] = True
                    categories["inappropriate"] = True

                if any(
                    term in name_lower or term in parent_lower
                    for term in ["drug", "narcotic"]
                ):
                    categories["drugs"] = True
                    categories["inappropriate"] = True

                if "tobacco" in name_lower or "tobacco" in parent_lower:
                    categories["tobacco"] = True
                    categories["inappropriate"] = True

                if "alcohol" in name_lower or "alcohol" in parent_lower:
                    categories["alcohol"] = True

                if "gambling" in name_lower or "gambling" in parent_lower:
                    categories["gambling"] = True
                    categories["inappropriate"] = True

                if any(
                    term in name_lower or term in parent_lower
                    for term in ["hate", "nazi", "confederate"]
                ):
                    categories["hate_symbols"] = True
                    categories["inappropriate"] = True

            result = {
                "findings": findings,
                "categories": categories,
                "max_confidence": max_confidence,
                "is_inappropriate": categories["inappropriate"],
                "total_labels": len(moderation_labels),
            }

            logger.info(
                f"Content moderation result: {len(findings)} findings, "
                f"inappropriate={categories['inappropriate']}, max_conf={max_confidence:.1f}"
            )
            return result

        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS Rekognition content moderation failed: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Content moderation failed: {e}")
            return {"error": str(e)}

    def _estimate_sky_bias(
        self, image_bytes: bytes
    ) -> Optional[Tuple[float, float, float, float]]:
        """Estimate distribution of sky-like pixels across top/bottom/left/right.

        Returns tuple (top, bottom, left, right) counts or None on failure.
        Uses a downscaled RGB heuristic to classify sky-like pixels.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                rgb_img = img.convert("RGB")
                # Downscale to reduce cost
                rgb_img.thumbnail((64, 64))
                width, height = rgb_img.size
                if width == 0 or height == 0:
                    return None
                pixels = rgb_img.load()
                if pixels is None:
                    return None
                top = bottom = left = right = 0

                for y in range(height):
                    for x in range(width):
                        pixel = pixels[x, y]
                        r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
                        # Sky heuristic: strong blue channel and not too dark
                        if b > 130 and b > r + 25 and b > g + 25:
                            if y < height // 2:
                                top += 1
                            else:
                                bottom += 1
                            if x < width // 2:
                                left += 1
                            else:
                                right += 1
                return float(top), float(bottom), float(left), float(right)
        except Exception as e:
            logger.debug(f"Sky bias estimation failed: {e}")
            return None

    # Removed EXIF orientation bias helper on request to avoid double-applying rotations.


def get_image_dimensions(image_bytes: bytes) -> tuple[Optional[int], Optional[int]]:
    """Get image dimensions from bytes using PIL."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        return image.width, image.height
    except Exception as e:
        logger.error(f"Failed to get image dimensions: {e}")
        return None, None
