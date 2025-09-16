#!/usr/bin/env python3
"""
GSR Sensor Module for Music Therapy Box
Receives pre-computed GSR conductance data from Arduino via serial communication
Arduino handles ADC reading and conductance calculation, Pi only processes the results
"""

import serial
import time
import logging
import threading
import queue
from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class GSRReading:
    adc_value: int
    conductance: float
    timestamp: float
    valid: bool

class GSRSensor:
    """
    GSR sensor class that receives pre-computed conductance data from Arduino
    Arduino handles ADC reading and conductance calculation
    This class only processes the received conductance values
    """
    
    def __init__(self, port: str = None, baudrate: int = 9600):
        """
        Initialize GSR sensor
        
        Args:
            port: Serial port for Arduino communication (auto-detect if None)
            baudrate: Serial communication baud rate
        """
        if port is None:
            # Auto-detect port based on OS
            import platform
            if platform.system() == "Windows":
                port = "COM3"  # Default Windows COM port
            else:
                port = "/dev/ttyUSB0"  # Default Linux port
        
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.connected = False
        self.running = False
        
        # Data storage
        self.latest_reading = None
        self.readings_history = []
        self.max_history = 1000
        
        # Threading
        self._thread = None
        self._stop_event = threading.Event()
        self.data_queue = queue.Queue(maxsize=100)
        
        # Configuration
        self.config = {
            'log_data': True,
            'log_file': 'gsr_data.txt',
            'calibration_samples': 100,  # Samples for baseline calculation
            'min_conductance': 0.1,      # Minimum valid conductance (μS)
            'max_conductance': 100.0     # Maximum valid conductance (μS)
        }
        
        # Initialize connection
        self._initialize_connection()

    def _initialize_connection(self) -> bool:
        """Initialize serial connection to Arduino"""
        try:
            self.serial_connection = serial.Serial(
                self.port, 
                self.baudrate, 
                timeout=1
            )
            self.connected = True
            logger.info(f"GSR sensor connected on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to GSR sensor: {e}")
            self.connected = False
            return False

    def _run_sensor(self):
        """Main sensor reading loop (runs in background thread)"""
        logger.info("GSR sensor thread started")
        
        while not self._stop_event.is_set() and self.running:
            try:
                if self.serial_connection and self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    
                    if line and line.startswith("GSR_CONDUCTANCE:"):
                        self._parse_gsr_data(line)
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Error in GSR sensor thread: {e}")
                time.sleep(0.1)

    def _parse_gsr_data(self, data_line: str):
        """Parse GSR data from Arduino serial output"""
        try:
            # Expected format: "GSR_CONDUCTANCE:25.45"
            conductance_part = data_line.split(':')[1]
            conductance = float(conductance_part)
            
            # Validate conductance range
            valid = (self.config['min_conductance'] <= conductance <= self.config['max_conductance'])
            
            # Create reading object (ADC value not needed since Arduino computed conductance)
            reading = GSRReading(
                adc_value=0,  # Not used since Arduino computed conductance
                conductance=conductance,
                timestamp=time.time(),
                valid=valid
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
            
            logger.debug(f"GSR Conductance: {conductance:.2f}μS, Valid={valid}")
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse GSR data: {data_line} - {e}")

    def _log_reading(self, reading: GSRReading):
        """Log GSR reading to file"""
        try:
            with open(self.config['log_file'], "a") as f:
                timestamp_str = datetime.fromtimestamp(reading.timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                f.write(f"{timestamp_str},{reading.adc_value},{reading.conductance:.2f},{reading.valid}\n")
        except Exception as e:
            logger.warning(f"Failed to log GSR data: {e}")

    def start_sensor(self) -> bool:
        """
        Start the GSR sensor (expected by main script)
        
        Returns:
            True if sensor started successfully
        """
        if not self.connected:
            if not self._initialize_connection():
                return False
        
        if self.running:
            logger.warning("GSR sensor is already running")
            return True
        
        try:
            self.running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_sensor, daemon=True)
            self._thread.start()
            
            logger.info("GSR sensor started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start GSR sensor: {e}")
            self.running = False
            return False

    def stop_sensor(self, timeout: float = 2.0):
        """
        Stop the GSR sensor
        
        Args:
            timeout: Maximum time to wait for thread to stop
        """
        if not self.running:
            return
        
        logger.info("Stopping GSR sensor...")
        self.running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)
        
        logger.info("GSR sensor stopped")

    def read_gsr(self) -> Optional[float]:
        """
        Get the latest GSR conductance reading (expected by main script)
        
        Returns:
            Latest conductance value in microsiemens or None if no data available
        """
        if self.latest_reading and self.latest_reading.valid:
            return self.latest_reading.conductance
        return None

    def get_reading(self) -> Optional[GSRReading]:
        """
        Get the latest complete GSR reading
        
        Returns:
            Latest GSRReading object or None
        """
        return self.latest_reading

    def get_readings(self, count: int = 100) -> List[GSRReading]:
        """
        Get recent GSR readings
        
        Args:
            count: Number of recent readings to return
            
        Returns:
            List of recent GSRReading objects
        """
        return self.readings_history[-count:] if self.readings_history else []

    def get_readings_in_timeframe(self, duration_seconds: int) -> List[GSRReading]:
        """
        Get GSR readings from the last N seconds
        
        Args:
            duration_seconds: Time window in seconds
            
        Returns:
            List of GSRReading objects within timeframe
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
        
        # Check if we have recent data
        if self.latest_reading:
            return (time.time() - self.latest_reading.timestamp) < 10.0
        
        return False

    def calculate_baseline(self, duration_seconds: int = 10) -> Optional[float]:
        """
        Calculate baseline conductance from recent readings
        
        Args:
            duration_seconds: Duration to use for baseline calculation
            
        Returns:
            Average conductance value or None if insufficient data
        """
        readings = self.get_readings_in_timeframe(duration_seconds)
        valid_readings = [r for r in readings if r.valid]
        
        if len(valid_readings) < 10:  # Need at least 10 valid readings
            return None
        
        conductance_values = [r.conductance for r in valid_readings]
        return np.mean(conductance_values)

    def detect_stress_change(self, baseline: float, threshold: float = 0.3) -> bool:
        """
        Detect significant change from baseline
        
        Args:
            baseline: Baseline conductance value
            threshold: Relative change threshold (0.3 = 30% change)
            
        Returns:
            True if significant change detected
        """
        if not self.latest_reading or not self.latest_reading.valid:
            return False
        
        current = self.latest_reading.conductance
        relative_change = abs(current - baseline) / baseline
        
        return relative_change > threshold

    def get_statistics(self) -> dict:
        """
        Get GSR statistics for recent readings
        
        Returns:
            Dictionary with min, max, avg values for conductance
        """
        recent_readings = self.get_readings_in_timeframe(60)  # Last minute
        valid_readings = [r for r in recent_readings if r.valid]
        
        if not valid_readings:
            return {'count': 0, 'error': 'No valid readings'}
        
        conductance_values = [r.conductance for r in valid_readings]
        
        import statistics
        return {
            'count': len(valid_readings),
            'conductance_min': min(conductance_values),
            'conductance_max': max(conductance_values),
            'conductance_avg': statistics.mean(conductance_values),
            'valid_rate': len(valid_readings) / len(recent_readings) if recent_readings else 0.0
        }

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_sensor()
        if self.serial_connection:
            self.serial_connection.close()

# Standalone testing function
def test_gsr_sensor(duration: int = 30):
    """
    Test function for standalone operation
    
    Args:
        duration: Duration in seconds to read from sensor
    """
    print('GSR sensor starting...')
    
    sensor = GSRSensor()
    
    if not sensor.start_sensor():
        print("Failed to start GSR sensor!")
        return
    
    try:
        start_time = time.time()
        while time.time() - start_time < duration:
            reading = sensor.get_reading()
            if reading:
                print(f"GSR: ADC={reading.adc_value}, Conductance={reading.conductance:.2f}μS, Valid={reading.valid}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, exiting...')
    
    finally:
        sensor.stop_sensor()
        print('GSR sensor stopped!')

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Read and print data from GSR sensor")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duration in seconds to read from sensor, default 30")
    args = parser.parse_args()
    
    # Run standalone test
    test_gsr_sensor(duration=args.time)