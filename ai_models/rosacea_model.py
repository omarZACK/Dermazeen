import pickle

import cv2
import numpy as np


class RosaceaDetector:
    """Wrapper class for rosacea detection model"""

    def __init__(self, model_path):
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.is_loaded = False
        self.load_model(model_path)

    def load_model(self, filepath):
        """Load the trained rosacea model"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)

            self.model = data["model"]
            self.scaler = data["scaler"]
            self.feature_names = data["feature_names"]
            self.is_loaded = True
        except Exception as e:
            print(f"Failed to load rosacea model: {e}")
            self.is_loaded = False

    @staticmethod
    def extract_features(opencv_image):
        """Extract features from OpenCV image (BGR format)"""
        # Convert BGR to RGB for processing
        img = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)

        r = img[:, :, 0].astype(np.float32)
        g = img[:, :, 1].astype(np.float32)

        rg_ratio = r / (g + 1e-6)
        rg_ratio_mean = np.mean(rg_ratio)
        rg_ratio_std = np.std(rg_ratio)
        rg_ratio_90 = np.percentile(rg_ratio, 90)

        rg_diff = r - g
        rg_diff_mean = np.mean(rg_diff)
        rg_diff_std = np.std(rg_diff)

        red_area_percentage = np.mean(r > 150) * 100

        lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        a_channel = lab[:, :, 1]
        lab_a_mean = np.mean(a_channel)
        lab_a_std = np.std(a_channel)

        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        saturation = np.mean(hsv[:, :, 1])
        red_intensity = np.mean(r)

        edges = cv2.Canny(img, 100, 200)
        vessel_density = np.mean(edges > 0)

        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        texture_var = np.var(gray)

        return np.array([
            rg_ratio_mean, rg_ratio_std, rg_ratio_90,
            rg_diff_mean, rg_diff_std, red_area_percentage,
            lab_a_mean, lab_a_std, saturation,
            red_intensity, vessel_density, texture_var
        ]).reshape(1, -1)

    def predict(self, opencv_image):
        """Predict rosacea from OpenCV image"""
        if not self.is_loaded:
            raise ValueError("Rosacea model not loaded!")

        try:
            # Extract features
            x = self.extract_features(opencv_image)
            x_scaled = self.scaler.transform(x)

            # Make prediction
            pred_class_index = self.model.predict(x_scaled)[0]
            pred_proba = self.model.predict_proba(x_scaled)[0]

            # Map to result format
            pred_label = "Rosacea" if pred_class_index == 1 else "Normal"
            confidence = float(pred_proba[pred_class_index])
            rosacea_probability = float(pred_proba[1]) if len(pred_proba) > 1 else 0.0
            normal_probability = float(pred_proba[0])

            return {
                'prediction': pred_label,
                'confidence': confidence,
                'rosacea_probability': rosacea_probability,
                'normal_probability': normal_probability
            }
        except Exception as e:
            raise ValueError(f"Rosacea prediction failed: {str(e)}")
