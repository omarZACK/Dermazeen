import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
import cv2
import numpy as np
from PIL import Image
import mediapipe as mp


class FaceAcneDetector:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )

    def detect_face_landmarks(self, image_bgr):
        try:
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(image_rgb)

            if results.multi_face_landmarks:
                return results.multi_face_landmarks[0]
            return None
        except Exception as e:
            return None

    def create_face_mask(self, image_bgr, face_landmarks):
        try:
            h, w = image_bgr.shape[:2]
            face_mask = np.zeros((h, w), dtype=np.uint8)
            lips_mask = np.zeros((h, w), dtype=np.uint8)
            left_eye_mask = np.zeros((h, w), dtype=np.uint8)
            right_eye_mask = np.zeros((h, w), dtype=np.uint8)

            if face_landmarks:
                face_points = []
                for landmark in face_landmarks.landmark:
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    face_points.append((x, y))

                face_oval_indices = [
                    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
                    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109
                ]

                lips_indices = [
                    0, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 29, 30, 31, 32,
                    61, 62, 72, 74, 78, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269,
                    270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285,
                    286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301,
                    302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317,
                    318, 319, 320, 321, 322, 324, 375, 402, 405, 415
                ]

                left_eye_indices = [
                    33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246,
                    161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7
                ]

                right_eye_indices = [
                    362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398,
                    398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382
                ]

                if len(face_points) > max(face_oval_indices + lips_indices + left_eye_indices + right_eye_indices):
                    face_contour = np.array([face_points[i] for i in face_oval_indices], dtype=np.int32)
                    cv2.fillPoly(face_mask, [face_contour], 255)

                    lips_contour = np.array([face_points[i] for i in lips_indices if i < len(face_points)],
                                            dtype=np.int32)
                    if len(lips_contour) > 0:
                        cv2.fillPoly(lips_mask, [lips_contour], 255)
                        kernel = np.ones((20, 20), np.uint8)
                        lips_mask = cv2.dilate(lips_mask, kernel, iterations=1)

                    left_eye_contour = np.array([face_points[i] for i in left_eye_indices if i < len(face_points)],
                                                dtype=np.int32)
                    if len(left_eye_contour) > 0:
                        cv2.fillPoly(left_eye_mask, [left_eye_contour], 255)
                        kernel = np.ones((15, 15), np.uint8)
                        left_eye_mask = cv2.dilate(left_eye_mask, kernel, iterations=1)

                    right_eye_contour = np.array([face_points[i] for i in right_eye_indices if i < len(face_points)],
                                                 dtype=np.int32)
                    if len(right_eye_contour) > 0:
                        cv2.fillPoly(right_eye_mask, [right_eye_contour], 255)
                        kernel = np.ones((15, 15), np.uint8)
                        right_eye_mask = cv2.dilate(right_eye_mask, kernel, iterations=1)

                    exclusion_mask = cv2.bitwise_or(lips_mask, left_eye_mask)
                    exclusion_mask = cv2.bitwise_or(exclusion_mask, right_eye_mask)

                    face_only_mask = cv2.bitwise_and(face_mask, cv2.bitwise_not(exclusion_mask))

                    return face_only_mask, lips_mask, left_eye_mask, right_eye_mask, exclusion_mask, face_mask

            return np.ones((h, w), dtype=np.uint8) * 255, lips_mask, left_eye_mask, right_eye_mask, np.zeros((h, w),
                                                                                                             dtype=np.uint8), np.ones(
                (h, w), dtype=np.uint8) * 255

        except Exception as e:
            h, w = image_bgr.shape[:2]
            return np.ones((h, w), dtype=np.uint8) * 255, np.zeros((h, w), dtype=np.uint8), np.zeros((h, w),
                                                                                                     dtype=np.uint8), np.zeros(
                (h, w), dtype=np.uint8), np.zeros((h, w), dtype=np.uint8), np.ones((h, w), dtype=np.uint8) * 255

    def analyze_color_features(self, image_bgr, face_mask):
        try:
            lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
            return {}, lab
        except Exception as e:
            return {}, image_bgr

    def create_red_zone_mask(self, image_bgr, lab, face_mask, red_threshold_percentile=70):
        try:
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

            lower_red1 = np.array([0, 50, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([160, 50, 50])
            upper_red2 = np.array([180, 255, 255])

            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(mask1, mask2)

            red_zone_mask = cv2.bitwise_and(red_mask, face_mask)

            return red_zone_mask
        except Exception as e:
            return np.zeros_like(face_mask)


class DualInputAcneClassifier(nn.Module):
    def __init__(self, num_classes=4):
        super().__init__()

        self.backbone1 = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        self.backbone1.fc = nn.Identity()

        self.backbone2 = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        self.backbone2.fc = nn.Identity()

        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(2048 * 2, 1024),
            nn.ReLU(),
            nn.BatchNorm1d(1024),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes)
        )

    def forward(self, original_img, adaptive_img):
        features1 = self.backbone1(original_img)
        features2 = self.backbone2(adaptive_img)
        combined = torch.cat([features1, features2], dim=1)
        output = self.classifier(combined)
        return output


def extract_correct_adaptive_log_output(image_np, face_detector):
    try:
        if image_np.shape[2] == 3:
            image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        else:
            image_bgr = image_np.copy()

        face_landmarks = face_detector.detect_face_landmarks(image_bgr)

        if face_landmarks is None:
            return np.zeros((image_np.shape[0], image_np.shape[1], 3), dtype=np.uint8)

        face_only_mask, lips_mask, left_eye_mask, right_eye_mask, exclusion_mask, face_mask = face_detector.create_face_mask(
            image_bgr, face_landmarks)

        color_features, lab = face_detector.analyze_color_features(image_bgr, face_only_mask)

        red_zone_mask = face_detector.create_red_zone_mask(
            image_bgr, lab, face_only_mask, red_threshold_percentile=70
        )
        red_zone_pixels = np.sum(red_zone_mask > 0)

        if red_zone_pixels == 0:
            return image_bgr.copy()

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_clahe = clahe.apply(gray)

        adaptive = cv2.adaptiveThreshold(
            gray_clahe, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            35, 5
        )
        adaptive_red_zones = cv2.bitwise_and(adaptive, red_zone_mask)

        blurred = cv2.GaussianBlur(gray_clahe, (5, 5), 0)
        log = cv2.Laplacian(blurred, cv2.CV_64F)
        log = cv2.convertScaleAbs(log)
        log_red_zones = cv2.bitwise_and(log, red_zone_mask)

        combined = cv2.bitwise_and(adaptive_red_zones, log_red_zones)

        kernel = np.ones((3, 3), np.uint8)
        combined_clean = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(combined_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid_contours = []
        for c in contours:
            area = cv2.contourArea(c)
            if 10 <= area <= 500:
                valid_contours.append(c)

        output = image_bgr.copy()

        for i, contour in enumerate(valid_contours):
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 2)

        return output

    except Exception as e:
        return np.zeros((image_np.shape[0], image_np.shape[1], 3), dtype=np.uint8)


def predict_single_image_exact_training_method(model_path, image_path, face_detector):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    try:
        print("Loading model...")
        checkpoint = torch.load(model_path, map_location=device)

        num_classes = checkpoint.get('num_classes', 4)
        class_names = checkpoint.get('class_names', ['Level_0', 'Level_1', 'Level_2', 'normal'])

        model = DualInputAcneClassifier(num_classes=num_classes)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)
        model.eval()

        print(f"Model loaded successfully")
        print(f"Number of classes: {num_classes}")
        print(f"Class names: {class_names}")

        image_pil = Image.open(image_path).convert('RGB')
        image_np = np.asarray(image_pil)

        adaptive_log_output = extract_correct_adaptive_log_output(image_np, face_detector)
        adaptive_log_rgb = cv2.cvtColor(adaptive_log_output, cv2.COLOR_BGR2RGB)

        transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        rgb_pil = Image.fromarray(image_np)
        rgb_transformed = transform(rgb_pil)
        rgb_transformed = rgb_transformed.unsqueeze(0).to(device)

        adaptive_pil = Image.fromarray(adaptive_log_rgb)
        adaptive_transformed = transform(adaptive_pil)
        adaptive_transformed = adaptive_transformed.unsqueeze(0).to(device)

        with torch.no_grad():
            if torch.cuda.is_available() and device.type == 'cuda':
                with torch.cuda.amp.autocast():
                    outputs = model(rgb_transformed, adaptive_transformed)
            else:
                outputs = model(rgb_transformed, adaptive_transformed)

            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            predicted_class = torch.argmax(outputs, dim=1).item()
            confidence = probabilities[0][predicted_class].item()
            all_probabilities = probabilities[0].cpu().numpy()

        print(f"Predicted Class: {class_names[predicted_class]}")
        print(f"Confidence Level: {confidence * 100:.2f}%")
        print("All Probabilities:")
        for i, (class_name, prob) in enumerate(zip(class_names, all_probabilities)):
            marker = "✓" if i == predicted_class else " "
            print(f"[{marker}] {class_name}: {prob * 100:.2f}%")

        return {
            'predicted_class': predicted_class,
            'predicted_class_name': class_names[predicted_class],
            'confidence': confidence,
            'all_probabilities': all_probabilities,
            'class_names': class_names
        }

    except Exception as e:
        print(f"Error in acne prediction: {e}")
        return None