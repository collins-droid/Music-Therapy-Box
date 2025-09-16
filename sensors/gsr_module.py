#!/usr/bin/env python3
"""
GSR Sensor Module for Music Therapy Box
Receives GSR sensor data from Arduino via serial communication
Compatible with the main script's expected interface
"""

import serial
import time
import threading
import queue
import logging
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class GSRReading:
    value: int
    timestamp: float
    raw_data: str

class GSRSensor:
    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600):
        """
        Initialize GSR sensor with serial communication
        
        Args:
            port: Serial port for Arduino connection
            baudrate: Serial communication speed
        """
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.connected = False
        self.running = False
        
        # Threading for continuous data collection
        self.read_thread = None
        self.data_queue = queue.Queue(maxsize=1000)
        
        # Data storage
        self.latest_reading = None
        self.readings_history = []
        self.max_history = 1000  # Keep last 1000 readings
        
        # Configuration
        self.config = {
            'timeout': 1,
            'retry_attempts': 3,
            'log_data': True,
            'log_file': 'gsr_data.txt'
        }
        
        # Initialize connection
        self._connect()

    def _connect(self) -> bool:
        """Establish serial connection to Arduino"""
        for attempt in range(self.config['retry_attempts']):
            try:
                logger.info(f"Attempting to connect to GSR sensor on {self.port} (attempt {attempt + 1})")
                
                self.serial_connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.config['timeout']
                )
                
                # Test connection by waiting for valid data
                test_timeout = time.time() + 5  # 5 second timeout
                while time.time() < test_timeout:
                    if self.serial_connection.in_waiting > 0:
                        test_data = self.serial_connection.readline().decode('utf-8').strip()
                        if test_data.startswith("GSR:"):
                            self.connected = True
                            logger.info("GSR sensor connected successfully")
                            self._start_reading_thread()
                            return True
                    time.sleep(0.1)
                
                # If we get here, no valid data received
                self.serial_connection.close()
                logger.warning(f"No valid GSR data received on attempt {attempt + 1}")
                
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                time.sleep(1)  # Wait before retry
        
        logger.error("Failed to connect to GSR sensor after all attempts")
        self.connected = False
        return False

    def _start_reading_thread(self):
        """Start background thread for continuous data reading"""
        if not self.read_thread or not self.read_thread.is_alive():
            self.running = True
            self.read_thread = threading.Thread(target=self._continuous_read, daemon=True)
            self.read_thread.start()
            logger.info("GSR reading thread started")

    def _continuous_read(self):
        """Background thread function for continuous data reading"""
        while self.running and self.connected:
            try:
                if self.serial_connection and self.serial_connection.in_waiting > 0:
                    raw_data = self.serial_connection.readline().decode('utf-8').strip()
                    
                    if raw_data.startswith("GSR:"):
                        try:
                            gsr_value = int(raw_data.split(":")[1])
                            timestamp = time.time()
                            
                            reading = GSRReading(
                                value=gsr_value,
                                timestamp=timestamp,
                                raw_data=raw_data
                            )
                            
                            # Update latest reading
                            self.latest_reading = reading
                            
                            # Add to history (maintain max size)
                            self.readings_history.append(reading)
                            if len(self.readings_history) > self.max_history:
                                self.readings_history.pop(0)
                            
                            # Add to queue for external consumers
                            try:
                                self.data_queue.put_nowait(reading)
                            except queue.Full:
                                # Remove oldest item and add new one
                                try:
                                    self.data_queue.get_nowait()
                                    self.data_queue.put_nowait(reading)
                                except queue.Empty:
                                    pass
                            
                            # Optional data logging
                            if self.config['log_data']:
                                self._log_reading(reading)
                                
                        except ValueError as e:
                            logger.warning(f"Error parsing GSR value from: {raw_data} - {e}")
                    
                    elif raw_data.startswith("BUTTON:"):
                        # Handle button data if received on same serial line
                        logger.debug(f"Button data received: {raw_data}")
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Error in GSR reading thread: {e}")
                # Try to reconnect
                if not self._reconnect():
                    break
                time.sleep(0.1)

    def _reconnect(self) -> bool:
        """Attempt to reconnect to the sensor"""
        logger.info("Attempting to reconnect to GSR sensor...")
        self.connected = False
        
        if self.serial_connection:
            try:
                self.serial_connection.close()
            except:
                pass
        
        return self._connect()

    def _log_reading(self, reading: GSRReading):
        """Log GSR reading to file"""
        try:
            with open(self.config['log_file'], "a") as f:
                timestamp_str = datetime.fromtimestamp(reading.timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                f.write(f"{timestamp_str},{reading.value}\n")
        except Exception as e:
            logger.warning(f"Failed to log GSR data: {e}")

    def read_gsr(self) -> Optional[int]:
        """
        Get the latest GSR reading (expected by main script)
        
        Returns:
            Latest GSR value or None if no data available
        """
        if self.latest_reading:
            return self.latest_reading.value
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
            True if sensor is connected and receiving data
        """
        # Check connection status and recent data
        if not self.connected:
            return False
        
        if self.latest_reading:
            # Consider connected if we have recent data (within last 5 seconds)
            return (time.time() - self.latest_reading.timestamp) < 5.0
        
        return False

    def get_data_rate(self) -> float:
        """
        Calculate current data reception rate
        
        Returns:
            Readings per second
        """
        if len(self.readings_history) < 2:
            return 0.0
        
        recent_readings = self.get_readings_in_timeframe(10)  # Last 10 seconds
        if len(recent_readings) < 2:
            return 0.0
        
        time_span = recent_readings[-1].timestamp - recent_readings[0].timestamp
        return len(recent_readings) / time_span if time_span > 0 else 0.0

    def get_statistics(self) -> dict:
        """
        Get GSR statistics for recent readings
        
        Returns:
            Dictionary with min, max, avg, std values
        """
        recent_readings = self.get_readings_in_timeframe(60)  # Last minute
        
        if not recent_readings:
            return {'count': 0, 'min': 0, 'max': 0, 'avg': 0, 'std': 0}
        
        values = [r.value for r in recent_readings]
        
        import statistics
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0
        }

    def process_gsr_data(self, gsr_value: int):
        """
        Process GSR data with categorization (from your original script)
        
        Args:
            gsr_value: GSR sensor value
        """
        logger.info(f"GSR Value: {gsr_value}")
        
        if gsr_value > 500:
            logger.info("High GSR detected!")
        elif gsr_value < 200:
            logger.info("Low GSR detected!")
        else:
            logger.debug("Normal GSR range")

    def stop(self):
        """Stop the GSR sensor and clean up resources"""
        logger.info("Stopping GSR sensor...")
        self.running = False
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
        
        if self.serial_connection:
            try:
                self.serial_connection.close()
            except:
                pass
        
        self.connected = False
        logger.info("GSR sensor stopped")

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop()

# Standalone testing function
def test_gsr_sensor():
    """Test function for standalone operation (matches your original script)"""
    sensor = GSRSensor()
    
    if not sensor.is_connected():
        print("Failed to connect to GSR sensor!")
        return
    
    try:
        print("Starting GSR data collection...")
        print("Press Ctrl+C to stop")
        
        while True:
            reading = sensor.get_reading()
            if reading:
                sensor.process_gsr_data(reading.value)
                
                # Show statistics every 10 seconds
                if int(reading.timestamp) % 10 == 0:
                    stats = sensor.get_statistics()
                    print(f"Stats: {stats}")
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nStopping GSR data collection...")
    
    finally:
        sensor.stop()
        print("GSR sensor disconnected.")

if __name__ == "__main__":
    # Run standalone test
    test_gsr_sensor()