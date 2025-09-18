#!/usr/bin/env python3
"""
GSR Sensor Module for Music Therapy Box (Optimized)
Receives pre-computed GSR conductance data from Arduino via serial communication
"""
import re
import serial
import time
import logging
import threading
from typing import Optional, List
from dataclasses import dataclass
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class GSRReading:
    conductance: float
    timestamp: float
    valid: bool

@dataclass
class BaselineData:
    gsr_baseline: float
    hr_baseline: float
    timestamp: float
    source: str  # 'arduino' or 'default'

class GSRSensor:
    """Optimized GSR sensor class for Arduino communication"""
    
    def __init__(self, port: str = None, baudrate: int = 9600, button_callback=None, message_callback=None):
        # Auto-detect port
        if port is None:
            import platform
            if platform.system() == "Windows":
                port = "COM3"
            else:
                # Try common Linux ports
                import glob
                possible_ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
                if possible_ports:
                    port = possible_ports[0]  # Use first available port
                    print(f"Auto-detected Arduino port: {port}")
                else:
                    port = "/dev/ttyUSB0"  # Default fallback
        
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.connected = False
        self.running = False
        
        # Use deque for efficient data storage
        self.latest_reading = None
        self.readings_history = deque(maxlen=1000)
        
        # Baseline data storage
        self.baseline_data = None
        
        # Threading
        self._thread = None
        self._stop_event = threading.Event()
        
        # Validation limits
        self.min_conductance = 0.1
        self.max_conductance = 100.0
        
        # Callbacks
        self.button_callback = button_callback
        self.message_callback = message_callback
        
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
                    try:
                        raw_data = self.serial_connection.readline()
                        
                        # Enhanced character cleaning and encoding handling
                        try:
                            # Try UTF-8 first, fallback to latin-1 for problematic characters
                            line = raw_data.decode('utf-8', errors='replace').strip()
                        except UnicodeDecodeError:
                            # Fallback to latin-1 if UTF-8 fails completely
                            line = raw_data.decode('latin-1', errors='replace').strip()
                        
                        # Debug: Show raw data with enhanced character inspection
                        if line:
                            logger.debug(f"Raw Arduino data: {repr(raw_data)} -> decoded: {repr(line)}")
                        
                        # Comprehensive character cleaning - remove all control characters except essential ones
                        import re
                        # Remove null bytes, carriage returns, line feeds, and other control characters
                        line = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', line)
                        line = line.strip()
                        
                        # Skip empty lines
                        if not line:
                            continue
                        
                        # Handle potential message concatenation by splitting on known message prefixes
                        messages = []
                        prefixes = ["GSR_CONDUCTANCE:", "BUTTON:", "BASELINE:", "BASELINE_PROGRESS:", 
                                  "CALIBRATION:", "SESSION:", "STATUS:", "LCD:"]
                        
                        # Check if line contains multiple messages
                        current_message = line
                        for prefix in prefixes:
                            if prefix in current_message and current_message.count(prefix) > 1:
                                # Split on the prefix (except first occurrence)
                                parts = current_message.split(prefix)
                                if len(parts) > 1:
                                    messages.append(parts[0] + prefix)  # First message
                                    for i in range(1, len(parts)):
                                        if parts[i]:  # Non-empty part
                                            messages.append(prefix + parts[i])
                                break
                        else:
                            # Single message
                            messages = [current_message]
                        
                        # Process each message
                        for message in messages:
                            message = message.strip()
                            if not message:
                                continue
                                
                            if message.startswith("GSR_CONDUCTANCE:"):
                                self._process_data(message)
                            elif message.startswith("BUTTON:"):
                                self._process_button_event(message)
                            elif (message.startswith("BASELINE:") or message.startswith("BASELINE_PROGRESS:") or 
                                  message.startswith("CALIBRATION:") or message.startswith("SESSION:") or 
                                  message.startswith("STATUS:") or message.startswith("LCD:")):
                                self._process_arduino_message(message)
                            else:
                                logger.debug(f"Unrecognized Arduino message: {message}")
                    except UnicodeDecodeError:
                        # Skip invalid data and continue
                        continue
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"GSR sensor error: {e}")
                time.sleep(0.1)

    def _process_data(self, data_line: str):
        """Process GSR data from Arduino"""
        try:
            # Clean the data line - remove any carriage returns, newlines, and extra whitespace
            cleaned_line = data_line.strip().replace('\r', '').replace('\n', '')
            
            # Handle case where data might be concatenated (e.g., "GSR_CONDUCTANCE:7.34\r37431")
            # Extract only the GSR_CONDUCTANCE part up to the first non-numeric character after the colon
            if cleaned_line.startswith("GSR_CONDUCTANCE:"):
                # Find the colon position
                colon_pos = cleaned_line.find(':')
                if colon_pos != -1:
                    # Extract the value part and clean it
                    value_part = cleaned_line[colon_pos + 1:]
                    # Remove any non-numeric characters except decimal point and minus sign
                    import re
                    numeric_part = re.match(r'^[-+]?[0-9]*\.?[0-9]+', value_part)
                    if numeric_part:
                        conductance_str = numeric_part.group()
                        conductance = float(conductance_str)
                    else:
                        logger.warning(f"Could not extract numeric value from: {value_part}")
                        return
                else:
                    logger.warning(f"Invalid GSR data format - no colon found: {cleaned_line}")
                    return
            else:
                logger.warning(f"Invalid GSR data format - doesn't start with GSR_CONDUCTANCE: {cleaned_line}")
                return
            
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
            logger.warning(f"Failed to parse GSR data: '{data_line}' -> '{cleaned_line}' - {e}")

    def _process_button_event(self, data_line: str):
        """Process button events from Arduino"""
        try:
            # Parse button event: "BUTTON:START" or "BUTTON:STOP"
            button_type = data_line.split(':')[1]
            
            logger.info(f"Button event received: {button_type}")
            
            # Forward button event to callback if available
            if self.button_callback:
                self.button_callback(button_type)
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse button event: {data_line} - {e}")

    def _process_arduino_message(self, data_line: str):
        """Process Arduino status and control messages"""
        try:
            logger.debug(f"Arduino message: {data_line}")
            
            # Special handling for baseline messages
            if data_line.startswith("BASELINE:"):
                logger.info(f"BASELINE message received: {data_line}")
                self._parse_and_store_baseline_data(data_line)
            elif data_line.startswith("BASELINE_PROGRESS:"):
                logger.info(f"BASELINE_PROGRESS message received: {data_line}")
            elif data_line.startswith("CALIBRATION:"):
                logger.info(f"CALIBRATION message received: {data_line}")
            elif data_line.startswith("SESSION:"):
                logger.info(f"SESSION message received: {data_line}")
            
            # Forward message to callback if available
            if self.message_callback:
                self.message_callback(data_line)
            else:
                logger.warning("No message callback set - baseline data may be lost!")
            
        except Exception as e:
            logger.warning(f"Failed to process Arduino message: {data_line} - {e}")
    
    def _parse_and_store_baseline_data(self, message: str):
        """Parse and store baseline data from Arduino message"""
        try:
            # Parse baseline data: "BASELINE:GSR:123.45,HR:75.2"
            data_part = message.split(":", 1)[1]  # "GSR:123.45,HR:75.2"
            parts = data_part.split(",")
            
            gsr_value = None
            hr_value = None
            
            for part in parts:
                part = part.strip()  # Clean each part
                if part.startswith("GSR:"):
                    gsr_value = float(part.split(":")[1])
                elif part.startswith("HR:"):
                    hr_value = float(part.split(":")[1])
            
            if gsr_value is not None and hr_value is not None:
                self.baseline_data = BaselineData(
                    gsr_baseline=gsr_value,
                    hr_baseline=hr_value,
                    timestamp=time.time(),
                    source='arduino'
                )
                logger.info(f"Baseline data stored - GSR: {gsr_value:.2f}, HR: {hr_value:.2f}")
            else:
                logger.warning(f"Failed to parse baseline data from: {message}")
                
        except Exception as e:
            logger.error(f"Error parsing baseline data: {e}")

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
        
        # If we have recent readings, check if they're fresh
        if self.latest_reading:
            return (time.time() - self.latest_reading.timestamp) < 10.0
        
        # If no readings yet but sensor is running, consider it connected
        # (during initialization, sensor might not have data yet)
        return True

    def calculate_baseline(self, duration_seconds: int = 10) -> Optional[float]:
        """Calculate baseline conductance from recent readings"""
        readings = self.get_readings_in_timeframe(duration_seconds)
        valid_readings = [r.conductance for r in readings if r.valid]
        
        return np.mean(valid_readings) if len(valid_readings) >= 10 else None
    
    def has_baseline_data(self) -> bool:
        """Check if baseline data is available"""
        return self.baseline_data is not None
    
    def get_baseline_data(self) -> Optional[BaselineData]:
        """Get stored baseline data"""
        return self.baseline_data
    
    def set_default_baseline(self, gsr_baseline: float = 0.0, hr_baseline: float = 70.0):
        """Set default baseline data when Arduino data is not available"""
        self.baseline_data = BaselineData(
            gsr_baseline=gsr_baseline,
            hr_baseline=hr_baseline,
            timestamp=time.time(),
            source='default'
        )
        logger.info(f"Default baseline data set - GSR: {gsr_baseline:.2f}, HR: {hr_baseline:.2f}")

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
    
    print(f"Sensor connected: {sensor.connected}")
    print(f"Sensor port: {sensor.port}")
    
    if not sensor.start_sensor():
        print("Failed to start GSR sensor!")
        print(f"Connection status: {sensor.connected}")
        return
    
    print(f"Sensor started successfully. Running for {duration} seconds...")
    
    try:
        start_time = time.time()
        while time.time() - start_time < duration:
            reading = sensor.get_reading()
            if reading:
                print(f"GSR: Conductance={reading.conductance:.2f}μS, Valid={reading.valid}")
            else:
                print("No GSR reading available")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, exiting...')
    except Exception as e:
        print(f'Error during test: {e}')
    
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