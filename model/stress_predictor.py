#!/usr/bin/env python3
"""
Stress Predictor Module for Music Therapy Box
Uses pre-trained Random Forest model for stress prediction
"""

import logging
import time
import numpy as np
import joblib
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum
import os

logger = logging.getLogger(__name__)

class StressLevel(Enum):
    NO_STRESS = "no_stress"
    STRESS = "stress"

@dataclass
class PredictionResult:
    stress_level: StressLevel
    confidence: float
    timestamp: float

class StressPredictor:
    """
    Simple stress predictor using pre-trained Random Forest model
    """
    
    def __init__(self, model_path: str = "model/random_forest/stress_random_forest.pkl"):
        """
        Initialize stress predictor with pre-trained model
        
        Args:
            model_path: Path to trained Random Forest model (.pkl file)
        """
        self.model_path = model_path
        self.model = None
        self.loaded = False
        self.ready = False
        
        # Feature names (matching training data)
        self.feature_names = [
            'hr_mean', 'hr_std', 'hr_min', 'hr_max', 'hr_range', 'hr_skew', 'hr_kurtosis',
            'eda_mean', 'eda_std', 'eda_min', 'eda_max', 'eda_range', 'eda_skew', 'eda_kurtosis', 'eda_slope'
        ]
        
        # Prediction history
        self.prediction_history = []
        
        # Load the model
        self._load_model()

    def _load_model(self):
        """Load the pre-trained Random Forest model"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.loaded = True
                self.ready = True
                logger.info(f"Loaded Random Forest model from {self.model_path}")
                logger.info(f"Model features: {len(self.feature_names)} features")
            else:
                logger.error(f" Model file not found: {self.model_path}")
                self.loaded = False
                self.ready = False
        except Exception as e:
            logger.error(f" Failed to load model: {e}")
            self.loaded = False
            self.ready = False

    def predict(self, features: Dict[str, float]) -> str:
        """
        Predict stress level from features
        
        Args:
            features: Dictionary containing the 15 extracted features
            
        Returns:
            Predicted stress level as string ("stress" or "no_stress")
        """
        try:
            if not self.ready:
                logger.warning("Model not ready")
                return "no_stress"
            
            # Prepare feature vector in correct order
            feature_vector = []
            for feature_name in self.feature_names:
                feature_vector.append(features.get(feature_name, 0.0))
            
            # Convert to numpy array and reshape for single prediction
            X = np.array(feature_vector).reshape(1, -1)
            
            # Make prediction
            prediction = self.model.predict(X)[0]
            
            # Get confidence from prediction probabilities
            probabilities = self.model.predict_proba(X)[0]
            confidence = float(np.max(probabilities))
            
            # Map prediction to stress level
            stress_level = "stress" if prediction == 1 else "no_stress"
            
            # Store prediction result
            result = PredictionResult(
                stress_level=StressLevel.STRESS if prediction == 1 else StressLevel.NO_STRESS,
                confidence=confidence,
                timestamp=time.time()
            )
            self.prediction_history.append(result)
            
            logger.info(f"Prediction: {stress_level} (confidence: {confidence:.2f})")
            return stress_level
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return "no_stress"

    def get_confidence(self) -> float:
        """
        Get confidence of last prediction
        
        Returns:
            Confidence value (0.0 to 1.0)
        """
        if self.prediction_history:
            return self.prediction_history[-1].confidence
        return 0.5

    def is_loaded(self) -> bool:
        """
        Check if model is loaded and ready
        
        Returns:
            True if model is loaded and ready
        """
        return self.loaded and self.ready

    def get_prediction_history(self, count: int = 10) -> List[PredictionResult]:
        """
        Get recent prediction history
        
        Args:
            count: Number of recent predictions to return
            
        Returns:
            List of recent PredictionResult objects
        """
        return self.prediction_history[-count:] if self.prediction_history else []

# Test function
def test_stress_predictor():
    """Test the stress predictor with sample data"""
    print("Testing Stress Predictor...")
    
    predictor = StressPredictor()
    
    if not predictor.is_loaded():
        print("Failed to load model!")
        return
    
    print("Model loaded successfully!")
    
    # Test with sample features (you would get these from your feature extraction)
    sample_features = {
        'hr_mean': 75.0,
        'hr_std': 5.2,
        'hr_min': 68.0,
        'hr_max': 82.0,
        'hr_range': 14.0,
        'hr_skew': 0.1,
        'hr_kurtosis': -0.5,
        'eda_mean': 8.5,
        'eda_std': 2.1,
        'eda_min': 6.0,
        'eda_max': 12.0,
        'eda_range': 6.0,
        'eda_skew': 0.3,
        'eda_kurtosis': -0.2,
        'eda_slope': 0.05
    }
    
    # Make prediction
    stress_level = predictor.predict(sample_features)
    confidence = predictor.get_confidence()
    
    print(f"Sample Prediction:")
    print(f"   Stress Level: {stress_level}")
    print(f"   Confidence: {confidence:.2f}")
    print("Test completed!")

if __name__ == "__main__":
    test_stress_predictor()
