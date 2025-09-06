import pickle

import cv2
import numpy as np


class MelasmaDetector:
    """Lightweight version of your MelasmaDetector for inference only"""

    def __init__(self, model_path):
        self.hog = cv2.HOGDescriptor()
        self.svm = None
        self.scaler = None
        self.is_trained = False
        self.load_model(model_path)

    def extract_hog_features(self, image):
        """Extract HOG features from an image"""
        image = cv2.resize(image, (64, 128))
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        features = self.hog.compute(gray)
        return features.flatten()

    @staticmethod
    def extract_color_features(image):
        """Extract color-based features for melasma detection"""
        image = cv2.resize(image, (64, 128))
        hist_b = cv2.calcHist([image], [0], None, [32], [0, 256])
        hist_g = cv2.calcHist([image], [1], None, [32], [0, 256])
        hist_r = cv2.calcHist([image], [2], None, [32], [0, 256])
        color_features = np.concatenate([hist_b.flatten(), hist_g.flatten(), hist_r.flatten()])
        mean_colors = np.mean(image.reshape(-1, 3), axis=0)
        return np.concatenate([color_features, mean_colors])

    @staticmethod
    def extract_texture_features(image):
        """Extract texture features using gradients"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        gray = cv2.resize(gray, (64, 128))
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        texture_features = [
            np.mean(grad_x), np.std(grad_x),
            np.mean(grad_y), np.std(grad_y),
            np.mean(gray), np.std(gray)
        ]
        return np.array(texture_features)

    def extract_combined_features(self, image):
        """Combine multiple feature types"""
        hog_feat = self.extract_hog_features(image)
        color_feat = self.extract_color_features(image)
        texture_feat = self.extract_texture_features(image)
        return np.concatenate([hog_feat, color_feat, texture_feat])

    def predict(self, image):
        """Predict melasma from image"""
        if not self.is_trained:
            raise ValueError("Model not trained yet!")

        features = self.extract_combined_features(image)
        features_scaled = self.scaler.transform([features])
        prediction = self.svm.predict(features_scaled)[0]
        probability = self.svm.predict_proba(features_scaled)[0]

        return {
            'prediction': 'Melasma' if prediction == 1 else 'Normal',
            'confidence': float(max(probability)),
            'melasma_probability': float(probability[1]),
            'normal_probability': float(probability[0])
        }

    def load_model(self, filepath):
        """Load the trained model"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        self.svm = model_data['svm']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']