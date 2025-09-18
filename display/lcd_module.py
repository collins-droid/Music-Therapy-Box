#!/usr/bin/env python3
"""
LCD Display Module for Music Therapy Box (Optimized)
Handles LCD display output using I2C communication at address 0x27
Uses RPi_I2C_driver for direct hardware control
"""

import logging
import time
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DisplayMessage:
    text: str
    timestamp: float

class LCDDisplay:
    """Optimized LCD display controller for Music Therapy Box using RPi_I2C_driver"""
    
    def __init__(self, i2c_address: int = 0x27, width: int = 16, height: int = 2):
        self.i2c_address = i2c_address
        self.width = width
        self.height = height
        self.connected = False
        self.ready = False
        self.lcd = None
        
        # Current state tracking
        self.current_message = None
        
        # Initialize display
        self._initialize()

    def _initialize(self) -> bool:
        """Initialize the LCD display hardware using RPi_I2C_driver"""
        try:
            # Import the custom I2C driver - handle both relative and absolute imports
            try:
                from .RPi_I2C_driver import lcd
            except ImportError:
                # Fallback for when running as main module
                import RPi_I2C_driver
                lcd = RPi_I2C_driver.lcd
            
            self.lcd = lcd()
            self.connected = True
            self.ready = True
            
            # Show initial message
            self.lcd_clear()
            self.lcd_display_string("Music Therapy", 1)
            self.lcd_display_string("Box Ready", 2)
            
            logger.info(f"LCD initialized at 0x{self.i2c_address:02X}")
            return True
            
        except ImportError as e:
            logger.error(f"RPi_I2C_driver not available: {e}")
            self.connected = False
            self.ready = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize LCD: {e}")
            self.connected = False
            self.ready = False
            return False


    def display(self, text: str, clear: bool = True):
        """Display text on LCD screen"""
        try:
            if not self.ready or not self.connected:
                logger.warning("LCD not connected - cannot display text")
                return
            
            # Update current message
            self.current_message = DisplayMessage(text=text, timestamp=time.time())
            
            if clear:
                self.lcd_clear()
            
            # Split text into lines and display
            lines = text.split('\n')
            for i, line in enumerate(lines[:self.height]):
                self.lcd_display_string(line[:self.width], i + 1)
                
        except Exception as e:
            logger.error(f"Display error: {e}")

    def lcd_display_string(self, text: str, line: int):
        """Display string on specific line using RPi_I2C_driver method"""
        try:
            if not self.ready or not self.connected:
                logger.warning("LCD not connected - cannot display string")
                return
                
            self.lcd.lcd_display_string(text, line)
        except Exception as e:
            logger.error(f"LCD display string error: {e}")

    def lcd_display_string_pos(self, text: str, line: int, pos: int):
        """Display string at specific position using RPi_I2C_driver method"""
        try:
            if not self.ready or not self.connected:
                logger.warning("LCD not connected - cannot display string at position")
                return
                
            self.lcd.lcd_display_string_pos(text, line, pos)
        except Exception as e:
            logger.error(f"LCD display string position error: {e}")

    def lcd_clear(self):
        """Clear LCD display using RPi_I2C_driver method"""
        try:
            if not self.ready or not self.connected:
                logger.warning("LCD not connected - cannot clear display")
                return
                
            self.lcd.lcd_clear()
            self.current_message = None
        except Exception as e:
            logger.error(f"LCD clear error: {e}")

    def backlight(self, state: int):
        """Control LCD backlight using RPi_I2C_driver method"""
        try:
            if not self.ready or not self.connected:
                logger.warning("LCD not connected - cannot control backlight")
                return
                
            self.lcd.backlight(state)
        except Exception as e:
            logger.error(f"LCD backlight control error: {e}")

    def lcd_load_custom_chars(self, fontdata):
        """Load custom characters using RPi_I2C_driver method"""
        try:
            if not self.ready or not self.connected:
                logger.warning("LCD not connected - cannot load custom characters")
                return
                
            self.lcd.lcd_load_custom_chars(fontdata)
        except Exception as e:
            logger.error(f"LCD custom characters error: {e}")

    def handle_arduino_lcd_command(self, command: str):
        """Handle LCD commands from Arduino serial"""
        try:
            # Clean the command string - remove null bytes and other control characters
            cleaned_command = command.replace('\x00', '').replace('\r', '').replace('\n', '').strip()
            
            logger.debug(f"LCD command received: '{command}' -> cleaned: '{cleaned_command}'")
            
            if cleaned_command == "LCD:CALIBRATION_IN_PROGRESS":
                self.display("Calibrating...\nPlease wait")
            elif cleaned_command == "LCD:CALIBRATION_COMPLETE":
                self.display("Calibration\nComplete!")
            elif cleaned_command == "LCD:SESSION_ACTIVE":
                self.display("Session Active\nMonitoring...")
            elif cleaned_command == "LCD:READY":
                self.display("System Ready\nPress START")
            elif cleaned_command.startswith("LCD:CALIBRATION_PROGRESS:"):
                # LCD progress not needed - just log for debugging
                logger.debug(f"LCD progress command received (ignored): {cleaned_command}")
            else:
                logger.debug(f"Unknown LCD command: '{cleaned_command}'")
                
        except Exception as e:
            logger.error(f"Error handling LCD command: '{command}' -> '{cleaned_command}' - {e}")

    def show_calibration_progress(self, remaining_seconds: int):
        """Show calibration progress with countdown"""
        if remaining_seconds > 0:
            # Simple progress visualization
            elapsed = 10 - remaining_seconds
            progress = min(10, max(0, elapsed))
            bar = "█" * progress + "░" * (10 - progress)
            self.lcd_clear()
            self.lcd_display_string("Calibrating", 1)
            self.lcd_display_string(f"[{bar}] {remaining_seconds}s", 2)
        else:
            self.lcd_clear()
            self.lcd_display_string("Calibration", 1)
            self.lcd_display_string("Complete!", 2)

    def show_status(self, status: str, details: str = ""):
        """Show system status with optional details"""
        self.lcd_clear()
        self.lcd_display_string(status[:self.width], 1)
        if details:
            self.lcd_display_string(details[:self.width], 2)

    def show_progress(self, title: str, current: int, total: int):
        """Show progress information"""
        self.lcd_clear()
        self.lcd_display_string(title[:self.width], 1)
        if total > 0:
            percentage = int((current / total) * 100)
            progress_text = f"{current}/{total} ({percentage}%)"
        else:
            progress_text = str(current)
        self.lcd_display_string(progress_text[:self.width], 2)

    def show_error(self, error_message: str):
        """Show error message"""
        self.lcd_clear()
        self.lcd_display_string("ERROR:", 1)
        self.lcd_display_string(error_message[:self.width], 2)

    def show_session_status(self, stress_level: str, confidence: float = 0):
        """Show therapy session status"""
        self.lcd_clear()
        self.lcd_display_string("Session Active", 1)
        if confidence > 0:
            status_text = f"Stress: {stress_level}"
            conf_text = f"Conf: {confidence:.1f}%"
            self.lcd_display_string(status_text[:self.width], 2)
            # Note: For 3+ line displays, we could show confidence on line 3
        else:
            self.lcd_display_string(f"Stress: {stress_level}"[:self.width], 2)

    def show_baseline_data(self, gsr_baseline: float, hr_baseline: float):
        """Show baseline data"""
        self.lcd_clear()
        self.lcd_display_string("Baseline Set", 1)
        baseline_text = f"GSR:{gsr_baseline:.1f} HR:{hr_baseline:.1f}"
        self.lcd_display_string(baseline_text[:self.width], 2)

    def show_arduino_status(self, connected: bool):
        """Show Arduino connection status"""
        self.lcd_clear()
        self.lcd_display_string("Arduino", 1)
        status = "Connected" if connected else "Disconnected"
        self.lcd_display_string(status[:self.width], 2)

    def show_sensor_status(self, gsr_ok: bool, hr_ok: bool):
        """Show sensor status"""
        self.lcd_clear()
        self.lcd_display_string("Sensors", 1)
        gsr_icon = "✓" if gsr_ok else "✗"
        hr_icon = "✓" if hr_ok else "✗"
        sensor_text = f"GSR{gsr_icon} HR{hr_icon}"
        self.lcd_display_string(sensor_text[:self.width], 2)

    def show_waiting_for_arduino(self):
        """Show waiting for Arduino calibration message"""
        self.display("Waiting for Arduino\nto complete calibration...")

    def show_baseline_received(self, gsr_value: float, hr_value: float):
        """Show baseline data received from Arduino"""
        self.display(f"Baseline received!\nGSR: {gsr_value:.1f}, HR: {hr_value:.1f}")

    def show_baseline_collection(self, current: int, total: int):
        """Show baseline collection progress"""
        progress = int((current / total) * 100)
        self.display(f"Collecting baseline...\n{current}/{total} ({progress}%)")

    def clear(self):
        """Clear the display"""
        self.lcd_clear()

    def is_ready(self) -> bool:
        """Check if LCD is ready"""
        return self.ready

    def get_current_message(self) -> Optional[DisplayMessage]:
        """Get current display message"""
        return self.current_message

    def __del__(self):
        """Cleanup on destruction"""
        try:
            if self.connected:
                self.lcd_clear()
        except:
            pass

    # Additional utility methods using RPi_I2C_driver capabilities
    def display_multiline(self, lines: list):
        """Display multiple lines of text"""
        self.lcd_clear()
        for i, line in enumerate(lines[:self.height]):
            self.lcd_display_string(line[:self.width], i + 1)

    def display_at_position(self, text: str, line: int, position: int):
        """Display text at specific line and position"""
        self.lcd_display_string_pos(text, line, position)

    def set_backlight_on(self):
        """Turn on LCD backlight"""
        self.backlight(1)

    def set_backlight_off(self):
        """Turn off LCD backlight"""
        self.backlight(0)

    def load_custom_characters(self, fontdata):
        """Load custom characters for special symbols"""
        self.lcd_load_custom_chars(fontdata)

def test_lcd_display(duration: int = 30):
    """Test LCD display functionality using RPi_I2C_driver methods"""
    print('LCD display test starting...')
    
    display = LCDDisplay()
    
    if not display.is_ready():
        print("Failed to initialize LCD!")
        return
    
    try:
        start_time = time.time()
        test_count = 0
        
        while time.time() - start_time < duration:
            test_count += 1
            
            # Cycle through different display types
            if test_count % 5 == 1:
                display.display(f"Test {test_count}")
            elif test_count % 5 == 2:
                display.show_status("System Ready", "All OK")
            elif test_count % 5 == 3:
                display.show_progress("Calibration", test_count, 20)
            elif test_count % 5 == 4:
                display.show_session_status("Low", 85.5)
            else:
                # Test new methods
                display.display_multiline(["Custom Test", f"Count: {test_count}"])
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print('Test interrupted')
    
    finally:
        display.clear()
        print('LCD test completed')

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LCD display")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="Test duration in seconds")
    args = parser.parse_args()
    
    test_lcd_display(duration=args.time)