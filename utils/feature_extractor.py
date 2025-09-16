#!/usr/bin/env python3
"""
Feature Extractor Module for Music Therapy Box
Extracts the exact 15 features required by the Random Forest model
"""

import time
import logging
import numpy as np
from scipy import stats
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ExtractedFeatures:
    features: Dict[str, float]
    timestamp: float

class FeatureExtractor:
    """
    Feature extractor that produces the exact 15 features required by the Random Forest model
    """
    
    def __init__(self):
        """Initialize feature extractor"""
        # Feature names matching the Random Forest model
        self.hr_features = ['hr_mean', 'hr_std', 'hr_min', 'hr_max', 'hr_range', 'hr_skew', 'hr_kurtosis']
        self.eda_features = ['eda_mean', 'eda_std', 'eda_min', 'eda_max', 'eda_range', 'eda_skew', 'eda_kurtosis', 'eda_slope']
        self.all_features = self.hr_features + self.eda_features
        
        self.config = {
            'min_samples': 10,  # Minimum samples for reliable feature extraction
            'eda_fs': 4,        # EDA sampling frequency (Hz) - matching training
            'hr_fs': 1,         # HR sampling frequency (Hz) - matching training
            'log_features': True,
            'log_file': 'extracted_features.txt'
        }

    def extract_features(self, data_window) -> Optional[Dict[str, float]]:
        """
        Extract the exact 15 features required by the Random Forest model
        
        Args:
            data_window: DataWindow object containing sensor readings
            
        Returns:
            Dictionary with the 15 required features or None if failed
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
            
            # Separate GSR and HR data
            gsr_values = [r.gsr_conductance for r in valid_readings if r.gsr_conductance is not None]
            hr_values = [r.heart_rate for r in valid_readings if r.heart_rate is not None]
            
            # Extract features
            features = {}
            
            # Extract HR features (7 features)
            if hr_values:
                features.update(self._extract_hr_features(hr_values))
            else:
                # Use default values if no HR data
                features.update({feat: 0.0 for feat in self.hr_features})
            
            # Extract EDA features (8 features) - GSR conductance is treated as EDA
            if gsr_values:
                features.update(self._extract_eda_features(gsr_values))
            else:
                # Use default values if no GSR data
                features.update({feat: 0.0 for feat in self.eda_features})
            
            # Log features if enabled
            if self.config['log_features']:
                self._log_features(features)
            
            logger.debug(f"Extracted {len(features)} features from {len(valid_readings)} readings")
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    def _extract_hr_features(self, hr_values: List[float]) -> Dict[str, float]:
        """Extract HR features matching the training script exactly"""
        hr_array = np.array(hr_values)
        
        features = {
            'hr_mean': float(np.nanmean(hr_array)),
            'hr_std': float(np.nanstd(hr_array, ddof=1)),
            'hr_min': float(np.nanmin(hr_array)),
            'hr_max': float(np.nanmax(hr_array)),
            'hr_range': float(np.nanmax(hr_array) - np.nanmin(hr_array)),
            'hr_skew': float(stats.skew(hr_array)),
            'hr_kurtosis': float(stats.kurtosis(hr_array))
        }
        
        return features

    def _extract_eda_features(self, eda_values: List[float]) -> Dict[str, float]:
        """Extract EDA features matching the training script exactly"""
        eda_array = np.array(eda_values)
        
        features = {
            'eda_mean': float(np.nanmean(eda_array)),
            'eda_std': float(np.nanstd(eda_array, ddof=1)),
            'eda_min': float(np.nanmin(eda_array)),
            'eda_max': float(np.nanmax(eda_array)),
            'eda_range': float(np.nanmax(eda_array) - np.nanmin(eda_array)),
            'eda_skew': float(stats.skew(eda_array)),
            'eda_kurtosis': float(stats.kurtosis(eda_array))
        }
        
        # Calculate slope (linear fit over window) - matching training script
        if len(eda_array) >= 2:
            x = np.arange(len(eda_array)) / self.config['eda_fs']
            a, b = np.polyfit(x, eda_array, 1)
            features['eda_slope'] = float(a)  # μS per second
        else:
            features['eda_slope'] = 0.0
        
        return features

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
        """Get the list of feature names expected by the model"""
        return self.all_features.copy()

    def validate_features(self, features: Dict[str, float]) -> bool:
        """Validate that all required features are present"""
        return all(feat in features for feat in self.all_features)

    def compute_baseline(self, calibration_data: List) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Compute baseline statistics from calibration data
        
        Args:
            calibration_data: List of SensorReading objects from calibration
            
        Returns:
            Dictionary with baseline statistics or None if failed
        """
        try:
            if not calibration_data:
                logger.warning("No calibration data provided")
                return None
            
            valid_readings = [r for r in calibration_data if r.valid]
            
            if len(valid_readings) < 10:
                logger.warning(f"Insufficient calibration data: {len(valid_readings)}")
                return None
            
            # Extract GSR and HR values
            gsr_values = [r.gsr_conductance for r in valid_readings if r.gsr_conductance is not None]
            hr_values = [r.heart_rate for r in valid_readings if r.heart_rate is not None]
            
            baseline = {}
            
            # Compute GSR baseline
            if gsr_values:
                baseline['gsr_conductance'] = {
                    'mean': float(np.mean(gsr_values)),
                    'std': float(np.std(gsr_values)),
                    'min': float(np.min(gsr_values)),
                    'max': float(np.max(gsr_values))
                }
            
            # Compute HR baseline
            if hr_values:
                baseline['heart_rate'] = {
                    'mean': float(np.mean(hr_values)),
                    'std': float(np.std(hr_values)),
                    'min': float(np.min(hr_values)),
                    'max': float(np.max(hr_values))
                }
            
            logger.info(f"Computed baseline from {len(valid_readings)} calibration readings")
            return baseline
            
        except Exception as e:
            logger.error(f"Baseline computation failed: {e}")
            return None

# Test function
def test_feature_extractor():
    """Test the feature extractor with sample data"""
    print("Testing Feature Extractor...")
    
    extractor = FeatureExtractor()
    
    # Create sample data window
    from utils.data_collector import DataWindow, SensorReading
    
    # Sample sensor readings
    readings = []
    for i in range(60):  # 60 seconds of data
        reading = SensorReading(
            gsr_conductance=10.0 + np.random.normal(0, 2),  # Simulate GSR
            heart_rate=75.0 + np.random.normal(0, 5),      # Simulate HR
            timestamp=time.time() + i,
            valid=True
        )
        readings.append(reading)
    
    data_window = DataWindow(readings=readings, baseline=None)
    
    # Extract features
    features = extractor.extract_features(data_window)
    
    if features:
        print("Features extracted successfully:")
        for name, value in features.items():
            print(f"   {name}: {value:.3f}")
        
        # Validate features
        if extractor.validate_features(features):
            print("All required features present")
        else:
            print("Missing required features")
    else:
        print("Feature extraction failed")

if __name__ == "__main__":
    test_feature_extractor()