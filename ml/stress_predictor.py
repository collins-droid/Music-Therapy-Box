#!/usr/bin/env python3
"""
Stress Predictor Module for Music Therapy Box
Machine Learning model for stress level prediction based on physiological data
"""

import logging
import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import os

logger = logging.getLogger(__name__)

class StressLevel(Enum):
    LOW = "low_stress"
    NORMAL = "neutral"
    HIGH = "high_stress"
    STRESS = "stress"
    RELAXED = "relaxed"

@dataclass
class SensorData:
    gsr_conductance: float
    heart_rate: float
    timestamp: float

@dataclass
class PredictionResult:
    stress_level: StressLevel
    confidence: float
    features: Dict[str, float]
    timestamp: float

class StressPredictor:
    """
    Machine Learning stress predictor for Music Therapy Box
    Analyzes physiological data to determine stress levels
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize stress predictor
        
        Args:
            model_path: Path to trained ML model file
        """
        self.model_path = model_path
        self.model = None
        self.loaded = False
        self.ready = False
        
        # Prediction history
        self.prediction_history = []
        self.max_history = 1000
        
        # Feature extraction parameters
        self.config = {
            'window_size': 60,  # seconds
            'min_samples': 10,  # Minimum samples for prediction
            'confidence_threshold': 0.6,  # Minimum confidence for valid prediction
            'log_predictions': True,
            'log_file': 'stress_predictions.txt',
            'model_file': 'stress_model.json'
        }
        
        # Baseline data for normalization
        self.baseline_data = None
        
        # Initialize predictor
        self._initialize_predictor()

    def _initialize_predictor(self) -> bool:
        """Initialize the stress prediction model"""
        try:
            # Try to load pre-trained model
            if self.model_path and os.path.exists(self.model_path):
                self._load_model(self.model_path)
            else:
                # Use rule-based fallback model
                self._create_fallback_model()
            
            self.loaded = True
            self.ready = True
            
            logger.info("Stress predictor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize stress predictor: {e}")
            self._create_fallback_model()
            self.loaded = True
            self.ready = True
            return False

    def _load_model(self, model_path: str):
        """Load trained ML model from file"""
        try:
            with open(model_path, 'r') as f:
                model_data = json.load(f)
            
            # In a real implementation, this would load a proper ML model
            # For now, we'll use the model parameters for rule-based prediction
            self.model = model_data
            logger.info(f"Loaded stress prediction model from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise

    def _create_fallback_model(self):
        """Create rule-based fallback model"""
        self.model = {
            'type': 'rule_based',
            'parameters': {
                'gsr_thresholds': {
                    'low': 5.0,      # μS
                    'high': 25.0     # μS
                },
                'hr_thresholds': {
                    'low': 60,       # BPM
                    'high': 100      # BPM
                },
                'weights': {
                    'gsr': 0.6,      # GSR weight in prediction
                    'hr': 0.4        # Heart rate weight in prediction
                }
            }
        }
        logger.info("Created rule-based fallback stress prediction model")

    def predict(self, features: Dict[str, float]) -> str:
        """
        Predict stress level from features (expected by main script)
        
        Args:
            features: Dictionary containing extracted features
            
        Returns:
            Predicted stress level as string
        """
        try:
            if not self.ready:
                logger.warning("Stress predictor not ready")
                return "neutral"
            
            # Extract key features
            gsr_conductance = features.get('gsr_conductance', 0.0)
            heart_rate = features.get('heart_rate', 0.0)
            
            # Create prediction result
            prediction_result = self._make_prediction(gsr_conductance, heart_rate, features)
            
            # Add to history
            self.prediction_history.append(prediction_result)
            if len(self.prediction_history) > self.max_history:
                self.prediction_history.pop(0)
            
            # Log prediction
            if self.config['log_predictions']:
                self._log_prediction(prediction_result)
            
            logger.info(f"Stress prediction: {prediction_result.stress_level.value} (confidence: {prediction_result.confidence:.2f})")
            
            return prediction_result.stress_level.value
            
        except Exception as e:
            logger.error(f"Failed to make stress prediction: {e}")
            return "neutral"

    def _make_prediction(self, gsr: float, hr: float, features: Dict[str, float]) -> PredictionResult:
        """Make stress level prediction using the model"""
        try:
            if self.model['type'] == 'rule_based':
                return self._rule_based_prediction(gsr, hr, features)
            else:
                # In a real implementation, this would use a proper ML model
                return self._rule_based_prediction(gsr, hr, features)
                
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            # Return neutral as fallback
            return PredictionResult(
                stress_level=StressLevel.NORMAL,
                confidence=0.5,
                features=features,
                timestamp=time.time()
            )

    def _rule_based_prediction(self, gsr: float, hr: float, features: Dict[str, float]) -> PredictionResult:
        """Rule-based stress prediction"""
        params = self.model['parameters']
        
        # Normalize features using baseline if available
        if self.baseline_data:
            gsr_normalized = self._normalize_feature(gsr, 'gsr_conductance')
            hr_normalized = self._normalize_feature(hr, 'heart_rate')
        else:
            gsr_normalized = gsr
            hr_normalized = hr
        
        # Calculate stress scores
        gsr_score = self._calculate_gsr_score(gsr_normalized, params['gsr_thresholds'])
        hr_score = self._calculate_hr_score(hr_normalized, params['hr_thresholds'])
        
        # Weighted combination
        weights = params['weights']
        combined_score = (gsr_score * weights['gsr'] + hr_score * weights['hr'])
        
        # Determine stress level
        stress_level, confidence = self._score_to_stress_level(combined_score)
        
        return PredictionResult(
            stress_level=stress_level,
            confidence=confidence,
            features={
                'gsr_conductance': gsr,
                'heart_rate': hr,
                'gsr_score': gsr_score,
                'hr_score': hr_score,
                'combined_score': combined_score
            },
            timestamp=time.time()
        )

    def _normalize_feature(self, value: float, feature_name: str) -> float:
        """Normalize feature using baseline data"""
        if not self.baseline_data or feature_name not in self.baseline_data:
            return value
        
        baseline_mean = self.baseline_data[feature_name]['mean']
        baseline_std = self.baseline_data[feature_name]['std']
        
        if baseline_std > 0:
            return (value - baseline_mean) / baseline_std
        else:
            return value - baseline_mean

    def _calculate_gsr_score(self, gsr: float, thresholds: Dict[str, float]) -> float:
        """Calculate GSR-based stress score (0.0 to 1.0)"""
        if gsr <= thresholds['low']:
            return 0.0  # Low stress
        elif gsr >= thresholds['high']:
            return 1.0  # High stress
        else:
            # Linear interpolation between thresholds
            return (gsr - thresholds['low']) / (thresholds['high'] - thresholds['low'])

    def _calculate_hr_score(self, hr: float, thresholds: Dict[str, float]) -> float:
        """Calculate heart rate-based stress score (0.0 to 1.0)"""
        if hr <= thresholds['low']:
            return 0.0  # Low stress
        elif hr >= thresholds['high']:
            return 1.0  # High stress
        else:
            # Linear interpolation between thresholds
            return (hr - thresholds['low']) / (thresholds['high'] - thresholds['low'])

    def _score_to_stress_level(self, score: float) -> Tuple[StressLevel, float]:
        """Convert combined score to stress level and confidence"""
        if score <= 0.2:
            return StressLevel.RELAXED, 0.8
        elif score <= 0.4:
            return StressLevel.LOW, 0.7
        elif score <= 0.6:
            return StressLevel.NORMAL, 0.6
        elif score <= 0.8:
            return StressLevel.STRESS, 0.7
        else:
            return StressLevel.HIGH, 0.8

    def get_confidence(self) -> float:
        """
        Get confidence of last prediction (expected by main script)
        
        Returns:
            Confidence value (0.0 to 1.0)
        """
        if self.prediction_history:
            return self.prediction_history[-1].confidence
        return 0.5

    def set_baseline(self, baseline_data: Dict[str, Dict[str, float]]):
        """
        Set baseline data for feature normalization
        
        Args:
            baseline_data: Dictionary containing baseline statistics
        """
        self.baseline_data = baseline_data
        logger.info("Baseline data updated for stress prediction")

    def is_loaded(self) -> bool:
        """
        Check if model is loaded (expected by main script)
        
        Returns:
            True if model is loaded and ready
        """
        return self.loaded and self.ready

    def get_prediction_history(self, count: int = 100) -> List[PredictionResult]:
        """
        Get recent prediction history
        
        Args:
            count: Number of recent predictions to return
            
        Returns:
            List of recent PredictionResult objects
        """
        return self.prediction_history[-count:] if self.prediction_history else []

    def get_prediction_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recent predictions
        
        Returns:
            Dictionary with prediction statistics
        """
        if not self.prediction_history:
            return {'count': 0, 'error': 'No predictions available'}
        
        recent_predictions = self.prediction_history[-100:]  # Last 100 predictions
        
        # Count stress levels
        stress_counts = {}
        for pred in recent_predictions:
            level = pred.stress_level.value
            stress_counts[level] = stress_counts.get(level, 0) + 1
        
        # Calculate average confidence
        avg_confidence = np.mean([p.confidence for p in recent_predictions])
        
        return {
            'count': len(recent_predictions),
            'stress_distribution': stress_counts,
            'average_confidence': avg_confidence,
            'most_common_stress': max(stress_counts, key=stress_counts.get) if stress_counts else 'neutral'
        }

    def _log_prediction(self, prediction: PredictionResult):
        """Log prediction to file"""
        try:
            with open(self.config['log_file'], "a") as f:
                timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp_str},{prediction.stress_level.value},{prediction.confidence:.3f}\n")
        except Exception as e:
            logger.warning(f"Failed to log prediction: {e}")

    def save_model(self, file_path: str):
        """
        Save current model to file
        
        Args:
            file_path: Path to save model file
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.model, f, indent=2)
            logger.info(f"Model saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def update_model_parameters(self, parameters: Dict[str, Any]):
        """
        Update model parameters
        
        Args:
            parameters: New model parameters
        """
        try:
            if 'parameters' in self.model:
                self.model['parameters'].update(parameters)
            else:
                self.model['parameters'] = parameters
            
            logger.info("Model parameters updated")
        except Exception as e:
            logger.error(f"Failed to update model parameters: {e}")

# Standalone testing function
def test_stress_predictor(duration: int = 30):
    """
    Test function for standalone operation
    
    Args:
        duration: Duration in seconds to test predictor
    """
    print('Stress predictor starting...')
    
    predictor = StressPredictor()
    
    if not predictor.is_loaded():
        print("Failed to initialize stress predictor!")
        return
    
    try:
        start_time = time.time()
        test_count = 0
        
        while time.time() - start_time < duration:
            test_count += 1
            
            # Generate test features
            gsr = 10.0 + np.random.normal(0, 5)  # Simulate GSR data
            hr = 75.0 + np.random.normal(0, 10)  # Simulate heart rate data
            
            features = {
                'gsr_conductance': max(0, gsr),
                'heart_rate': max(40, hr)
            }
            
            # Make prediction
            stress_level = predictor.predict(features)
            confidence = predictor.get_confidence()
            
            print(f"Test {test_count}: GSR={features['gsr_conductance']:.1f}μS, HR={features['heart_rate']:.1f}BPM")
            print(f"  Prediction: {stress_level} (confidence: {confidence:.2f})")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, exiting...')
    
    finally:
        # Show statistics
        stats = predictor.get_prediction_statistics()
        print(f"\nPrediction Statistics:")
        print(f"  Total predictions: {stats['count']}")
        print(f"  Average confidence: {stats['average_confidence']:.2f}")
        print(f"  Most common stress level: {stats['most_common_stress']}")
        print('Stress predictor test completed!')

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test stress predictor functionality")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duration in seconds to test predictor, default 30")
    args = parser.parse_args()
    
    # Run standalone test
    test_stress_predictor(duration=args.time)
