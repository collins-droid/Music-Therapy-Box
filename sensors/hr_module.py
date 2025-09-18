#!/usr/bin/env python3
"""
HR Sensor Module for Music Therapy Box
Based on MAX30102 sensor with enhanced functionality
Compatible with the main script's expected interface
"""

import threading
import time
import logging
import queue
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
import numpy as np

try:
    from .max30102 import MAX30102
    from . import hrcalc
    MAX30102_AVAILABLE = True
except ImportError:
    MAX30102_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class HRReading:
    bpm: float

    ir_value: int
    red_value: int
    timestamp: float
    valid_bpm: bool
    finger_detected: bool

class HRSensor:
    """
    Enhanced HR sensor class compatible with Music Therapy Box main script
    Based on MAX30102 sensor with thread-safe operation
    """
    
    LOOP_TIME = 0.01
    DETECTION_THRESHOLD = 50000  # Original threshold for finger detection
    
    def __init__(self, print_raw: bool = False, print_result: bool = False):
        """
        Initialize HR sensor
        
        Args:
            print_raw: Print raw IR/Red values
           
        """
        # Check if MAX30102 library is available
        if not MAX30102_AVAILABLE:
            logger.error("MAX30102 library not available. Install with: pip install max30102")
            raise ImportError("MAX30102 library not found")
        
        # Sensor state
        self.bpm = 0.0
        self.connected = False
        self.running = False
        self.finger_detected = False
        
        # Configuration
        self.print_raw = print_raw
        self.print_result = print_result
        
        # Threading
        self._thread = None
        self._stop_event = threading.Event()
        
        # Data storage
        self.ir_data = []
        self.red_data = []
        self.bpm_history = []
        self.latest_reading = None
        self.readings_history = []
        self.max_history = 1000
        
        # Baseline data storage
        self.baseline_bpm = None
        self.baseline_timestamp = None
        
        # Data queue for external consumers
        self.data_queue = queue.Queue(maxsize=100)
        
        # Configuration
        self.config = {
            'window_size': 100,      # Data points for calculation
            'bpm_smoothing': 4,      # Number of BPM values to average
            'log_data': True,
            'log_file': 'hr_data.txt',
            'detection_threshold': self.DETECTION_THRESHOLD
        }
        
        # Initialize sensor
        self._initialize_sensor()

    def _initialize_sensor(self) -> bool:
        """Initialize the MAX30102 sensor"""
        try:
            self.sensor = MAX30102()
            self.connected = True
            logger.info("MAX30102 HR sensor initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MAX30102 sensor: {e}")
            self.connected = False
            return False

    def _run_sensor(self):
        """Main sensor reading loop (runs in background thread)"""
        logger.info("HR sensor thread started")
        
        while not self._stop_event.is_set() and self.running:
            try:
                # Check if any data is available
                num_bytes = self.sensor.get_data_present()
                
                if num_bytes > 0:
                    logger.debug(f"MAX30102 data available: {num_bytes} bytes")
                    # Read all available data
                    while num_bytes > 0:
                        red, ir = self.sensor.read_fifo()
                        num_bytes -= 1
                        
                        # Store raw data
                        self.ir_data.append(ir)
                        self.red_data.append(red)
                        
                        if self.print_raw:
                            print(f"IR: {ir}, Red: {red}")
                        
                        # Maintain window size
                        while len(self.ir_data) > self.config['window_size']:
                            self.ir_data.pop(0)
                            self.red_data.pop(0)
                        
                        # Calculate HR and SpO2 when we have enough data
                        if len(self.ir_data) == self.config['window_size']:
                            self._calculate_vitals()
                else:
                    # Log occasionally when no data is available
                    if hasattr(self, '_no_data_count'):
                        self._no_data_count += 1
                    else:
                        self._no_data_count = 1
                    
                    if self._no_data_count % 1000 == 0:  # Log every 1000 iterations (10 seconds)
                        logger.debug(f"MAX30102: No data available (iteration {self._no_data_count})")
                
                time.sleep(self.LOOP_TIME)
                
            except Exception as e:
                logger.error(f"Error in HR sensor thread: {e}")
                time.sleep(0.1)
        
        # Shutdown sensor when thread exits
        try:
            self.sensor.shutdown()
            logger.info("MAX30102 sensor shutdown")
        except Exception as e:
            logger.warning(f"Error shutting down sensor: {e}")

    def _calculate_vitals(self):
        """Calculate heart rate  from collected data"""
        try:
            # Calculate HR (ignore SpO2 since we don't use it for ML)
            bpm, valid_bpm, _, _ = hrcalc.calc_hr_and_spo2(
                self.ir_data, self.red_data
            )
            
            # Check finger detection
            mean_ir = np.mean(self.ir_data)
            mean_red = np.mean(self.red_data)
            
            # Log finger detection status occasionally
            if hasattr(self, '_finger_log_count'):
                self._finger_log_count += 1
            else:
                self._finger_log_count = 1
            
            if self._finger_log_count % 100 == 0:  # Log every 100 calculations
                logger.debug(f"Finger detection: IR={mean_ir:.0f}, Red={mean_red:.0f}, "
                           f"Threshold=50000")
            
            # Check finger detection using original logic
            if (mean_ir < 50000 and mean_red < 50000):
                # No finger detected - set BPM to 0
                self.bpm = 0.0
                self.finger_detected = False
                valid_bpm = False
                
                if self.print_result:
                    print("Finger not detected")
            else:
                self.finger_detected = True
                
                # Smooth BPM using history (original logic)
                if valid_bpm:
                    self.bpm_history.append(bpm)
                    while len(self.bpm_history) > 4:  # Original uses 4, not config
                        self.bpm_history.pop(0)
                    
                    self.bpm = np.mean(self.bpm_history)
                    
                    if self.print_result:
                        print(f"BPM: {self.bpm:.1f}")
            
            # Create reading object
            reading = HRReading(
                bpm=self.bpm,
              
                ir_value=int(mean_ir),
                red_value=int(mean_red),
                timestamp=time.time(),
                valid_bpm=valid_bpm,
                finger_detected=self.finger_detected
            )
            
            # Update latest reading
            self.latest_reading = reading
            
            # Add to history
            self.readings_history.append(reading)
            if len(self.readings_history) > self.max_history:
                self.readings_history.pop(0)
            
            # Add to queue for external consumers
            try:
                self.data_queue.put_nowait(reading)
            except queue.Full:
                # Remove oldest and add new
                try:
                    self.data_queue.get_nowait()
                    self.data_queue.put_nowait(reading)
                except queue.Empty:
                    pass
            
            # Optional data logging
            if self.config['log_data']:
                self._log_reading(reading)
                
        except Exception as e:
            logger.error(f"Error calculating vitals: {e}")

    def _log_reading(self, reading: HRReading):
        """Log HR reading to file"""
        try:
            with open(self.config['log_file'], "a") as f:
                timestamp_str = datetime.fromtimestamp(reading.timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                f.write(f"{timestamp_str},{reading.bpm:.1f},{reading.finger_detected}\n")
        except Exception as e:
            logger.warning(f"Failed to log HR data: {e}")

    def start_sensor(self) -> bool:
        """
        Start the HR sensor (expected by main script)
        
        Returns:
            True if sensor started successfully
        """
        if not self.connected:
            if not self._initialize_sensor():
                return False
        
        if self.running:
            logger.warning("HR sensor is already running")
            return True
        
        try:
            self.running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_sensor, daemon=True)
            self._thread.start()
            
            logger.info("HR sensor started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start HR sensor: {e}")
            self.running = False
            return False

    def stop_sensor(self, timeout: float = 2.0):
        """
        Stop the HR sensor
        
        Args:
            timeout: Maximum time to wait for thread to stop
        """
        if not hasattr(self, 'running') or not self.running:
            return
        
        logger.info("Stopping HR sensor...")
        self.running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)
        
        self.bpm = 0.0
      
        self.finger_detected = False
        logger.info("HR sensor stopped")

    def read_max30106_HR(self) -> Optional[float]:
        """
        Get the latest heart rate reading (expected by main script)
        
        Returns:
            Latest BPM value or None if no data available
        """
        if self.latest_reading and self.latest_reading.finger_detected:
            return self.latest_reading.bpm
        return None

    def read_hr(self) -> Optional[float]:
        """Alias for read_max30106_HR for consistency"""
        return self.read_max30106_HR()

    def get_bpm(self) -> float:
        """Get current BPM value"""
        return self.bpm

    def is_finger_detected(self) -> bool:
        """Check if finger is currently detected"""
        return self.finger_detected

    def get_reading(self) -> Optional[HRReading]:
        """
        Get the latest complete HR reading
        
        Returns:
            Latest HRReading object or None
        """
        return self.latest_reading

    def get_readings(self, count: int = 100) -> List[HRReading]:
        """
        Get recent HR readings
        
        Args:
            count: Number of recent readings to return
            
        Returns:
            List of recent HRReading objects
        """
        return self.readings_history[-count:] if self.readings_history else []

    def get_readings_in_timeframe(self, duration_seconds: int) -> List[HRReading]:
        """
        Get HR readings from the last N seconds
        
        Args:
            duration_seconds: Time window in seconds
            
        Returns:
            List of HRReading objects within timeframe
        """
        if not self.readings_history:
            return []
        
        cutoff_time = time.time() - duration_seconds
        return [r for r in self.readings_history if r.timestamp >= cutoff_time]

    def is_connected(self) -> bool:
        """
        Check if sensor is connected (expected by main script)
        
        Returns:
            True if sensor is connected and running
        """
        if not self.connected or not self.running:
            return False
        
        # If sensor is running and connected, consider it connected
        # (HR sensor may not have data without finger, but hardware is working)
        return True

    def get_statistics(self) -> dict:
        """
        Get HR statistics for recent readings
        
        Returns:
            Dictionary with min, max, avg values for BPM
        """
        recent_readings = self.get_readings_in_timeframe(60)  # Last minute
        valid_readings = [r for r in recent_readings if r.valid_bpm and r.finger_detected]
        
       
        
        bpm_values = [r.bpm for r in valid_readings]
       
        
        detection_rate = len(valid_readings) / len(recent_readings) if recent_readings else 0.0
        
        import statistics
        return {
            'count': len(valid_readings),
            'bpm_min': min(bpm_values),
            'bpm_max': max(bpm_values),
            'bpm_avg': statistics.mean(bpm_values),
            'finger_detection_rate': detection_rate
        }
    
    def has_baseline_data(self) -> bool:
        """Check if baseline data is available"""
        return self.baseline_bpm is not None
    
    def get_baseline_data(self) -> Optional[float]:
        """Get stored baseline BPM"""
        return self.baseline_bpm
    
    def set_baseline_data(self, bpm: float):
        """Set baseline BPM data"""
        self.baseline_bpm = bpm
        self.baseline_timestamp = time.time()
        logger.info(f"HR baseline data set - BPM: {bpm:.1f}")
    
    def calculate_baseline(self, duration_seconds: int = 10) -> Optional[float]:
        """Calculate baseline BPM from recent readings"""
        readings = self.get_readings_in_timeframe(duration_seconds)
        valid_readings = [r for r in readings if r.valid_bpm and r.finger_detected]
        
        if len(valid_readings) >= 5:  # Need at least 5 valid readings
            bpm_values = [r.bpm for r in valid_readings]
            import statistics
            return statistics.mean(bpm_values)
        return None

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_sensor()

# Standalone testing function (matches your original script functionality)
def test_hr_sensor(duration: int = 30, print_raw: bool = False):
    """
    Test function for standalone operation
    
    Args:
        duration: Duration in seconds to read from sensor
        print_raw: Print raw data instead of calculation results
    """
    print('HR sensor starting...')
    
    sensor = HRSensor(print_raw=print_raw, print_result=(not print_raw))
    
    if not sensor.start_sensor():
        print("Failed to start HR sensor!")
        return
    
    try:
        start_time = time.time()
        while time.time() - start_time < duration:
            reading = sensor.get_reading()
           
                
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, exiting...')
    
    finally:
        sensor.stop_sensor()
        print('HR sensor stopped!')

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Read and print data from MAX30102")
    parser.add_argument("-r", "--raw", action="store_true",
                        help="print raw data instead of calculation result")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duration in seconds to read from sensor, default 30")
    args = parser.parse_args()
    
    # Run standalone test
    test_hr_sensor(duration=args.time, print_raw=args.raw)