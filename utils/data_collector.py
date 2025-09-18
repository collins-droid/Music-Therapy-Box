#!/usr/bin/env python3
"""
Data Collector Module for Music Therapy Box
Collects and manages sensor data from GSR and Heart Rate sensors
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class SensorReading:
    gsr_conductance: Optional[float]
    heart_rate: Optional[float]
    timestamp: float
    valid: bool

@dataclass
class DataWindow:
    readings: List[SensorReading]
    start_time: float
    end_time: float
    duration: float
    baseline: Optional[Dict[str, float]] = None

class DataCollector:
    """
    Data collector for Music Therapy Box
    Manages sensor data collection and windowing
    """
    
    def __init__(self, sampling_rate: float = 10.0):
        """
        Initialize data collector
        
        Args:
            sampling_rate: Sampling rate in Hz (samples per second)
        """
        self.sampling_rate = sampling_rate
        self.sample_interval = 1.0 / sampling_rate
        
        # Data storage
        self.readings_buffer = []
        self.max_buffer_size = 10000
        
        # Collection state
        self.collecting = False
        self._stop_event = threading.Event()
        self._collection_thread = None
        
        # Configuration
        self.config = {
            'log_data': True,
            'log_file': 'sensor_data.txt',
            'min_valid_readings': 5,  # Minimum valid readings for analysis
            'max_missing_samples': 3  # Maximum consecutive missing samples
        }

    def collect_baseline(self, gsr_sensor, hr_sensor, duration: int = 10) -> Optional[List[SensorReading]]:
        """
        Collect baseline data for calibration
        
        Args:
            gsr_sensor: GSR sensor instance
            hr_sensor: Heart rate sensor instance
            duration: Duration in seconds
            
        Returns:
            List of sensor readings or None if failed
        """
        try:
            logger.info(f"Starting baseline data collection for {duration} seconds...")
            
            readings = []
            start_time = time.time()
            last_sample_time = start_time
            
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # Ensure we don't sample too frequently
                if current_time - last_sample_time >= self.sample_interval:
                    # Collect sensor readings
                    gsr_reading = gsr_sensor.read_gsr() if gsr_sensor else None
                    hr_reading = hr_sensor.read_max30106_HR() if hr_sensor else None
                    
                    # Create reading object
                    reading = SensorReading(
                        gsr_conductance=gsr_reading,
                        heart_rate=hr_reading,
                        timestamp=current_time,
                        valid=(gsr_reading is not None or hr_reading is not None)
                    )
                    
                    readings.append(reading)
                    
                    # Log data if enabled
                    if self.config['log_data']:
                        self._log_reading(reading)
                    
                    last_sample_time = current_time
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            
            logger.info(f"Baseline collection completed: {len(readings)} readings collected")
            return readings
            
        except Exception as e:
            logger.error(f"Baseline data collection failed: {e}")
            return None

    def collect_window(self, gsr_sensor, hr_sensor, window_size: int, 
                      baseline: Optional[Dict[str, float]] = None) -> Optional[DataWindow]:
        """
        Collect a window of sensor data
        
        Args:
            gsr_sensor: GSR sensor instance
            hr_sensor: Heart rate sensor instance
            window_size: Window size in seconds
            baseline: Baseline data for normalization
            
        Returns:
            DataWindow object or None if failed
        """
        try:
            logger.info(f"Collecting sensor data window ({window_size}s)...")
            
            readings = []
            start_time = time.time()
            last_sample_time = start_time
            
            while time.time() - start_time < window_size:
                current_time = time.time()
                
                # Ensure we don't sample too frequently
                if current_time - last_sample_time >= self.sample_interval:
                    # Collect sensor readings
                    gsr_reading = gsr_sensor.read_gsr() if gsr_sensor else None
                    hr_reading = hr_sensor.read_max30106_HR() if hr_sensor else None
                    
                    # Create reading object
                    reading = SensorReading(
                        gsr_conductance=gsr_reading,
                        heart_rate=hr_reading,
                        timestamp=current_time,
                        valid=(gsr_reading is not None or hr_reading is not None)
                    )
                    
                    readings.append(reading)
                    last_sample_time = current_time
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            
            end_time = time.time()
            
            # Create data window
            window = DataWindow(
                readings=readings,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                baseline=baseline
            )
            
            # Calculate statistics
            valid_readings = [r for r in readings if r.valid]
            gsr_readings = [r for r in readings if r.gsr_conductance is not None]
            hr_readings = [r for r in readings if r.heart_rate is not None]
            
            logger.info(f"Data window collected: {len(readings)} readings over {window.duration:.1f}s")
            logger.info(f"Valid readings: {len(valid_readings)}")
            logger.info(f"GSR readings: {len(gsr_readings)}")
            logger.info(f"HR readings: {len(hr_readings)}")
            
            return window
            
        except Exception as e:
            logger.error(f"Data window collection failed: {e}")
            return None

    def collect_quick_sample(self, gsr_sensor, hr_sensor, duration: int = 10,
                           baseline: Optional[Dict[str, float]] = None) -> Optional[List[SensorReading]]:
        """
        Collect a quick sample of sensor data
        
        Args:
            gsr_sensor: GSR sensor instance
            hr_sensor: Heart rate sensor instance
            duration: Duration in seconds
            baseline: Baseline data for normalization
            
        Returns:
            List of sensor readings or None if failed
        """
        try:
            logger.info(f"Collecting quick sample ({duration}s)...")
            
            readings = []
            start_time = time.time()
            last_sample_time = start_time
            
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # Ensure we don't sample too frequently
                if current_time - last_sample_time >= self.sample_interval:
                    # Collect sensor readings
                    gsr_reading = gsr_sensor.read_gsr() if gsr_sensor else None
                    hr_reading = hr_sensor.read_max30106_HR() if hr_sensor else None
                    
                    # Create reading object
                    reading = SensorReading(
                        gsr_conductance=gsr_reading,
                        heart_rate=hr_reading,
                        timestamp=current_time,
                        valid=(gsr_reading is not None or hr_reading is not None)
                    )
                    
                    readings.append(reading)
                    last_sample_time = current_time
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            
            logger.info(f"Quick sample collected: {len(readings)} readings")
            return readings
            
        except Exception as e:
            logger.error(f"Quick sample collection failed: {e}")
            return None

    def start_continuous_collection(self):
        """Start continuous data collection in background thread"""
        if self.collecting:
            logger.warning("Data collection already running")
            return
        
        try:
            self.collecting = True
            self._stop_event.clear()
            self._collection_thread = threading.Thread(target=self._continuous_collection, daemon=True)
            self._collection_thread.start()
            
            logger.info("Continuous data collection started")
            
        except Exception as e:
            logger.error(f"Failed to start continuous collection: {e}")
            self.collecting = False

    def stop_continuous_collection(self):
        """Stop continuous data collection"""
        if not self.collecting:
            return
        
        try:
            self.collecting = False
            self._stop_event.set()
            
            if self._collection_thread and self._collection_thread.is_alive():
                self._collection_thread.join(timeout=2.0)
            
            logger.info("Continuous data collection stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop continuous collection: {e}")

    def _continuous_collection(self):
        """Background thread for continuous data collection"""
        logger.info("Continuous data collection thread started")
        
        while not self._stop_event.is_set() and self.collecting:
            try:
                # This would collect data continuously
                # For now, just sleep to prevent CPU spinning
                time.sleep(self.sample_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous collection: {e}")
                time.sleep(1)
        
        logger.info("Continuous data collection thread stopped")

    def get_recent_readings(self, count: int = 100) -> List[SensorReading]:
        """
        Get recent sensor readings
        
        Args:
            count: Number of recent readings to return
            
        Returns:
            List of recent SensorReading objects
        """
        return self.readings_buffer[-count:] if self.readings_buffer else []

    def get_readings_in_timeframe(self, duration_seconds: int) -> List[SensorReading]:
        """
        Get readings from the last N seconds
        
        Args:
            duration_seconds: Time window in seconds
            
        Returns:
            List of SensorReading objects within timeframe
        """
        if not self.readings_buffer:
            return []
        
        cutoff_time = time.time() - duration_seconds
        return [r for r in self.readings_buffer if r.timestamp >= cutoff_time]

    def calculate_statistics(self, readings: List[SensorReading]) -> Dict[str, float]:
        """
        Calculate statistics for a set of readings
        
        Args:
            readings: List of sensor readings
            
        Returns:
            Dictionary with statistical measures
        """
        if not readings:
            return {}
        
        # Separate valid readings
        valid_readings = [r for r in readings if r.valid]
        
        if not valid_readings:
            return {'count': 0, 'error': 'No valid readings'}
        
        # Extract values
        gsr_values = [r.gsr_conductance for r in valid_readings if r.gsr_conductance is not None]
        hr_values = [r.heart_rate for r in valid_readings if r.heart_rate is not None]
        
        stats = {
            'count': len(valid_readings),
            'valid_rate': len(valid_readings) / len(readings) if readings else 0.0
        }
        
        # GSR statistics
        if gsr_values:
            stats.update({
                'gsr_mean': np.mean(gsr_values),
                'gsr_std': np.std(gsr_values),
                'gsr_min': np.min(gsr_values),
                'gsr_max': np.max(gsr_values)
            })
        
        # Heart rate statistics
        if hr_values:
            stats.update({
                'hr_mean': np.mean(hr_values),
                'hr_std': np.std(hr_values),
                'hr_min': np.min(hr_values),
                'hr_max': np.max(hr_values)
            })
        
        return stats

    def _log_reading(self, reading: SensorReading):
        """Log sensor reading to file"""
        try:
            with open(self.config['log_file'], "a") as f:
                timestamp_str = datetime.fromtimestamp(reading.timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                gsr_str = f"{reading.gsr_conductance:.2f}" if reading.gsr_conductance is not None else "None"
                hr_str = f"{reading.heart_rate:.1f}" if reading.heart_rate is not None else "None"
                f.write(f"{timestamp_str},{gsr_str},{hr_str},{reading.valid}\n")
        except Exception as e:
            logger.warning(f"Failed to log sensor reading: {e}")

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_continuous_collection()

# Standalone testing function
def test_data_collector(duration: int = 30):
    """
    Test function for standalone operation
    
    Args:
        duration: Duration in seconds to test collector
    """
    print('Data collector starting...')
    
    collector = DataCollector()
    
    try:
        # Simulate sensor data collection
        start_time = time.time()
        test_count = 0
        
        while time.time() - start_time < duration:
            test_count += 1
            
            # Simulate sensor readings
            gsr_value = 15.0 + np.random.normal(0, 3)
            hr_value = 75.0 + np.random.normal(0, 5)
            
            reading = SensorReading(
                gsr_conductance=max(0, gsr_value),
                heart_rate=max(40, hr_value),
                timestamp=time.time(),
                valid=True
            )
            
            collector.readings_buffer.append(reading)
            
            # Calculate statistics every 10 readings
            if test_count % 10 == 0:
                stats = collector.calculate_statistics(collector.get_recent_readings(10))
                print(f"Sample {test_count}: GSR={stats.get('gsr_mean', 0):.1f}μS, HR={stats.get('hr_mean', 0):.1f}BPM")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, exiting...')
    
    finally:
        # Show final statistics
        final_stats = collector.calculate_statistics(collector.get_recent_readings())
        print(f"\nFinal Statistics:")
        print(f"  Total readings: {final_stats.get('count', 0)}")
        print(f"  Valid rate: {final_stats.get('valid_rate', 0):.2f}")
        print(f"  GSR mean: {final_stats.get('gsr_mean', 0):.1f}μS")
        print(f"  HR mean: {final_stats.get('hr_mean', 0):.1f}BPM")
        print('Data collector test completed!')

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test data collector functionality")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duration in seconds to test collector, default 30")
    args = parser.parse_args()
    
    # Run standalone test
    test_data_collector(duration=args.time)
