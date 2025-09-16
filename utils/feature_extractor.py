#!/usr/bin/env python3
"""
Feature Extractor Module for Music Therapy Box
Extracts meaningful features from sensor data for stress prediction
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class ExtractedFeatures:
    gsr_conductance: float
    heart_rate: float
    gsr_variability: float
    hr_variability: float
    gsr_trend: float
    hr_trend: float
    stress_indicator: float
    timestamp: float

class FeatureExtractor:
    """
    Feature extractor for Music Therapy Box
    Extracts meaningful features from sensor data for ML prediction
    """
    
    def __init__(self):
        """Initialize feature extractor"""
        self.config = {
            'min_samples': 5,  # Minimum samples for feature extraction
            'trend_window': 10,  # Window size for trend calculation
            'variability_threshold': 0.1,  # Threshold for variability calculation
            'log_features': True,
            'log_file': 'extracted_features.txt'
        }

    def extract_features(self, data_window) -> Optional[Dict[str, float]]:
        """
        Extract features from sensor data window
        
        Args:
            data_window: DataWindow object containing sensor readings
            
        Returns:
            Dictionary of extracted features or None if failed
        """
        try:
            if not data_window or not data_window.readings:
                logger.warning("No data available for feature extraction")
                return None
            
            readings = data_window.readings
            valid_readings = [r for r in readings if r.valid]
            
            if len(valid_readings) < self.config['min_samples']:
                logger.warning(f"Insufficient valid readings: {len(valid_readings)}")
                return None
            
            # Extract basic features
            features = self._extract_basic_features(valid_readings)
            
            # Extract variability features
            variability_features = self._extract_variability_features(valid_readings)
            features.update(variability_features)
            
            # Extract trend features
            trend_features = self._extract_trend_features(valid_readings)
            features.update(trend_features)
            
            # Extract derived features
            derived_features = self._extract_derived_features(features)
            features.update(derived_features)
            
            # Normalize features if baseline is available
            if data_window.baseline:
                features = self._normalize_features(features, data_window.baseline)
            
            # Log features if enabled
            if self.config['log_features']:
                self._log_features(features)
            
            logger.debug(f"Extracted {len(features)} features from {len(valid_readings)} readings")
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    def _extract_basic_features(self, readings: List) -> Dict[str, float]:
        """Extract basic statistical features"""
        features = {}
        
        # GSR features
        gsr_values = [r.gsr_conductance for r in readings if r.gsr_conductance is not None]
        if gsr_values:
            features.update({
                'gsr_conductance': np.mean(gsr_values),
                'gsr_min': np.min(gsr_values),
                'gsr_max': np.max(gsr_values),
                'gsr_range': np.max(gsr_values) - np.min(gsr_values)
            })
        else:
            features['gsr_conductance'] = 0.0
        
        # Heart rate features
        hr_values = [r.heart_rate for r in readings if r.heart_rate is not None]
        if hr_values:
            features.update({
                'heart_rate': np.mean(hr_values),
                'hr_min': np.min(hr_values),
                'hr_max': np.max(hr_values),
                'hr_range': np.max(hr_values) - np.min(hr_values)
            })
        else:
            features['heart_rate'] = 0.0
        
        return features

    def _extract_variability_features(self, readings: List) -> Dict[str, float]:
        """Extract variability features"""
        features = {}
        
        # GSR variability
        gsr_values = [r.gsr_conductance for r in readings if r.gsr_conductance is not None]
        if len(gsr_values) > 1:
            gsr_std = np.std(gsr_values)
            gsr_mean = np.mean(gsr_values)
            features['gsr_variability'] = gsr_std / gsr_mean if gsr_mean > 0 else 0.0
            features['gsr_std'] = gsr_std
        else:
            features['gsr_variability'] = 0.0
            features['gsr_std'] = 0.0
        
        # Heart rate variability
        hr_values = [r.heart_rate for r in readings if r.heart_rate is not None]
        if len(hr_values) > 1:
            hr_std = np.std(hr_values)
            hr_mean = np.mean(hr_values)
            features['hr_variability'] = hr_std / hr_mean if hr_mean > 0 else 0.0
            features['hr_std'] = hr_std
        else:
            features['hr_variability'] = 0.0
            features['hr_std'] = 0.0
        
        return features

    def _extract_trend_features(self, readings: List) -> Dict[str, float]:
        """Extract trend features"""
        features = {}
        
        # GSR trend
        gsr_values = [r.gsr_conductance for r in readings if r.gsr_conductance is not None]
        if len(gsr_values) >= self.config['trend_window']:
            features['gsr_trend'] = self._calculate_trend(gsr_values)
        else:
            features['gsr_trend'] = 0.0
        
        # Heart rate trend
        hr_values = [r.heart_rate for r in readings if r.heart_rate is not None]
        if len(hr_values) >= self.config['trend_window']:
            features['hr_trend'] = self._calculate_trend(hr_values)
        else:
            features['hr_trend'] = 0.0
        
        return features

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend using least squares"""
        try:
            if len(values) < 2:
                return 0.0
            
            x = np.arange(len(values))
            y = np.array(values)
            
            # Calculate slope using least squares
            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x * x)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            return slope
            
        except Exception as e:
            logger.warning(f"Trend calculation failed: {e}")
            return 0.0

    def _extract_derived_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Extract derived features"""
        derived = {}
        
        # Stress indicator (combined metric)
        gsr_conductance = features.get('gsr_conductance', 0.0)
        heart_rate = features.get('heart_rate', 0.0)
        gsr_variability = features.get('gsr_variability', 0.0)
        hr_variability = features.get('hr_variability', 0.0)
        
        # Normalize values (simplified normalization)
        gsr_norm = min(gsr_conductance / 50.0, 1.0)  # Assume max GSR of 50 μS
        hr_norm = min((heart_rate - 60) / 40.0, 1.0)  # Assume HR range 60-100 BPM
        
        # Combined stress indicator
        stress_indicator = (gsr_norm * 0.6 + hr_norm * 0.4) * (1 + gsr_variability + hr_variability)
        derived['stress_indicator'] = min(stress_indicator, 1.0)
        
        # Variability ratio
        if hr_variability > 0:
            derived['variability_ratio'] = gsr_variability / hr_variability
        else:
            derived['variability_ratio'] = 0.0
        
        # Range ratio
        gsr_range = features.get('gsr_range', 0.0)
        hr_range = features.get('hr_range', 0.0)
        if hr_range > 0:
            derived['range_ratio'] = gsr_range / hr_range
        else:
            derived['range_ratio'] = 0.0
        
        return derived

    def _normalize_features(self, features: Dict[str, float], baseline: Dict[str, float]) -> Dict[str, float]:
        """Normalize features using baseline data"""
        normalized = {}
        
        for feature_name, value in features.items():
            if feature_name in baseline:
                baseline_mean = baseline[feature_name].get('mean', 0.0)
                baseline_std = baseline[feature_name].get('std', 1.0)
                
                if baseline_std > 0:
                    normalized[feature_name] = (value - baseline_mean) / baseline_std
                else:
                    normalized[feature_name] = value - baseline_mean
            else:
                normalized[feature_name] = value
        
        return normalized

    def compute_baseline(self, readings: List) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Compute baseline statistics from calibration data
        
        Args:
            readings: List of sensor readings from calibration
            
        Returns:
            Dictionary with baseline statistics or None if failed
        """
        try:
            if not readings:
                logger.warning("No readings available for baseline computation")
                return None
            
            valid_readings = [r for r in readings if r.valid]
            
            if len(valid_readings) < self.config['min_samples']:
                logger.warning(f"Insufficient valid readings for baseline: {len(valid_readings)}")
                return None
            
            # Extract features from calibration data
            features = self._extract_basic_features(valid_readings)
            variability_features = self._extract_variability_features(valid_readings)
            features.update(variability_features)
            
            # Compute baseline statistics
            baseline = {}
            for feature_name, value in features.items():
                baseline[feature_name] = {
                    'mean': value,
                    'std': 0.0  # For now, we'll use the current value as mean
                }
            
            logger.info(f"Baseline computed from {len(valid_readings)} readings")
            return baseline
            
        except Exception as e:
            logger.error(f"Baseline computation failed: {e}")
            return None

    def _log_features(self, features: Dict[str, float]):
        """Log extracted features to file"""
        try:
            with open(self.config['log_file'], "a") as f:
                timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
                feature_str = ",".join([f"{k}:{v:.3f}" for k, v in features.items()])
                f.write(f"{timestamp_str},{feature_str}\n")
        except Exception as e:
            logger.warning(f"Failed to log features: {e}")

    def get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        return [
            'gsr_conductance', 'heart_rate',
            'gsr_variability', 'hr_variability',
            'gsr_trend', 'hr_trend',
            'stress_indicator', 'variability_ratio', 'range_ratio'
        ]

    def validate_features(self, features: Dict[str, float]) -> bool:
        """
        Validate extracted features
        
        Args:
            features: Dictionary of features
            
        Returns:
            True if features are valid
        """
        try:
            required_features = ['gsr_conductance', 'heart_rate']
            
            for feature in required_features:
                if feature not in features:
                    logger.warning(f"Missing required feature: {feature}")
                    return False
                
                value = features[feature]
                if not isinstance(value, (int, float)) or np.isnan(value) or np.isinf(value):
                    logger.warning(f"Invalid feature value: {feature}={value}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Feature validation failed: {e}")
            return False

# Standalone testing function
def test_feature_extractor():
    """Test function for standalone operation"""
    print('Feature extractor starting...')
    
    extractor = FeatureExtractor()
    
    try:
        # Create test data
        from utils.data_collector import SensorReading
        
        test_readings = []
        for i in range(20):
            gsr_value = 15.0 + np.random.normal(0, 2)
            hr_value = 75.0 + np.random.normal(0, 3)
            
            reading = SensorReading(
                gsr_conductance=max(0, gsr_value),
                heart_rate=max(40, hr_value),
                timestamp=time.time() + i,
                valid=True
            )
            test_readings.append(reading)
        
        # Test feature extraction
        from utils.data_collector import DataWindow
        
        data_window = DataWindow(
            readings=test_readings,
            start_time=time.time(),
            end_time=time.time() + 20,
            duration=20.0
        )
        
        features = extractor.extract_features(data_window)
        
        if features:
            print("Extracted features:")
            for name, value in features.items():
                print(f"  {name}: {value:.3f}")
        else:
            print("Feature extraction failed!")
        
        # Test baseline computation
        baseline = extractor.compute_baseline(test_readings)
        if baseline:
            print("\nBaseline statistics:")
            for name, stats in baseline.items():
                print(f"  {name}: mean={stats['mean']:.3f}, std={stats['std']:.3f}")
        
    except Exception as e:
        print(f"Test failed: {e}")
    
    finally:
        print('Feature extractor test completed!')

if __name__ == "__main__":
    # Run standalone test
    test_feature_extractor()
