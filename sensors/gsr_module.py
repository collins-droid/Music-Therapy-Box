#!/usr/bin/env python3
"""
GSR Sensor Module for Music Therapy Box (Optimized)
Receives pre-computed GSR conductance data from Arduino via serial communication
"""

import serial
import time
import logging
import threading
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class GSRReading:
    conductance: float
    timestamp: float
    valid: bool

class GSRSensor:
    """Optimized GSR sensor class for Arduino communication"""
    
    def __init__(self, port: str = None, baudrate: int = 9600):
        # Auto-detect port
        if port is None:
            import platform
            port = "COM3" if platform.system() == "Windows" else "/dev/ttyUSB0"
        
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.connected = False
        self.running = False
        
        # Use deque for efficient data storage
        self.latest_reading = None
        self.readings_history = deque(maxlen=1000)
        
        # Threading
        self._thread = None
        self._stop_event = threading.Event()
        
        # Validation limits
        self.min_conductance = 0.1
        self.max_conductance = 100.0
        
        # Initialize connection
        self._connect()

    def _connect(self) -> bool:
        """Initialize serial connection to Arduino"""
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connected = True
            logger.info(f"GSR sensor connected on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to GSR sensor: {e}")
            self.connected = False
            return False

    def _sensor_loop(self):
        """Main sensor reading loop"""
        logger.info("GSR sensor thread started")
        
        while not self._stop_event.is_set():
            try:
                if self.serial_connection and self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    
                    if line.startswith("GSR_CONDUCTANCE:"):
                        self._process_data(line)
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"GSR sensor error: {e}")
                time.sleep(0.1)

    def _process_data(self, data_line: str):
        """Process GSR data from Arduino"""
        try:
            # Simple parsing: "GSR_CONDUCTANCE:25.45"
            conductance = float(data_line.split(':')[1])
            
            # Validate range
            valid = self.min_conductance <= conductance <= self.max_conductance
            
            # Create reading
            reading = GSRReading(
                conductance=conductance,
                timestamp=time.time(),
                valid=valid
            )
            
            # Update data
            self.latest_reading = reading
            self.readings_history.append(reading)
            
            logger.debug(f"GSR: {conductance:.2f}μS, Valid={valid}")
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse GSR data: {data_line} - {e}")

    def start_sensor(self) -> bool:
        """Start the GSR sensor"""
        if not self.connected and not self._connect():
            return False
        
        if self.running:
            return True
        
        try:
            self.running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._sensor_loop, daemon=True)
            self._thread.start()
            logger.info("GSR sensor started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start GSR sensor: {e}")
            self.running = False
            return False

    def stop_sensor(self, timeout: float = 2.0):
        """Stop the GSR sensor"""
        if not self.running:
            return
        
        logger.info("Stopping GSR sensor...")
        self.running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)
        
        logger.info("GSR sensor stopped")

    def read_gsr(self) -> Optional[float]:
        """Get latest GSR conductance reading"""
        if self.latest_reading and self.latest_reading.valid:
            return self.latest_reading.conductance
        return None

    def get_reading(self) -> Optional[GSRReading]:
        """Get the latest complete GSR reading"""
        return self.latest_reading

    def get_readings(self, count: int = 100) -> List[GSRReading]:
        """Get recent GSR readings"""
        return list(self.readings_history)[-count:] if self.readings_history else []

    def get_readings_in_timeframe(self, duration_seconds: int) -> List[GSRReading]:
        """Get GSR readings from the last N seconds"""
        if not self.readings_history:
            return []
        
        cutoff_time = time.time() - duration_seconds
        return [r for r in self.readings_history if r.timestamp >= cutoff_time]

    def is_connected(self) -> bool:
        """Check if sensor is connected and receiving data"""
        if not self.connected or not self.running:
            return False
        
        if self.latest_reading:
            return (time.time() - self.latest_reading.timestamp) < 10.0
        
        return False

    def calculate_baseline(self, duration_seconds: int = 10) -> Optional[float]:
        """Calculate baseline conductance from recent readings"""
        readings = self.get_readings_in_timeframe(duration_seconds)
        valid_readings = [r.conductance for r in readings if r.valid]
        
        return np.mean(valid_readings) if len(valid_readings) >= 10 else None

    def detect_stress_change(self, baseline: float, threshold: float = 0.3) -> bool:
        """Detect significant change from baseline"""
        if not self.latest_reading or not self.latest_reading.valid:
            return False
        
        current = self.latest_reading.conductance
        relative_change = abs(current - baseline) / baseline
        
        return relative_change > threshold

    def get_statistics(self) -> dict:
        """Get GSR statistics for recent readings"""
        recent_readings = self.get_readings_in_timeframe(60)
        valid_readings = [r.conductance for r in recent_readings if r.valid]
        
        if not valid_readings:
            return {'count': 0, 'error': 'No valid readings'}
        
        return {
            'count': len(valid_readings),
            'conductance_min': min(valid_readings),
            'conductance_max': max(valid_readings),
            'conductance_avg': np.mean(valid_readings),
            'valid_rate': len(valid_readings) / len(recent_readings) if recent_readings else 0.0
        }

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_sensor()
        if self.serial_connection:
            self.serial_connection.close()

def test_gsr_sensor(duration: int = 30):
    """Test function for standalone operation"""
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
                print(f"GSR: Conductance={reading.conductance:.2f}μS, Valid={reading.valid}")
            
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
    
    test_gsr_sensor(duration=args.time)