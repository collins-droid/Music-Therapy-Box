#!/usr/bin/env python3
"""
LCD Display Module for Music Therapy Box (Optimized)
Handles LCD display output using I2C communication at address 0x27
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
    """Optimized LCD display controller for Music Therapy Box"""
    
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
        """Initialize the LCD display hardware"""
        try:
            # Try hardware initialization
            import board
            from adafruit_character_lcd.character_lcd_i2c import Character_LCD_I2C
            
            i2c = board.I2C()
            self.lcd = Character_LCD_I2C(i2c, self.width, self.height, address=self.i2c_address)
            self.connected = True
            self.ready = True
            
            # Show initial message
            self.lcd.clear()
            self.lcd.message = "Music Therapy\nBox Ready"
            
            logger.info(f"LCD initialized at 0x{self.i2c_address:02X}")
            return True
            
        except ImportError:
            logger.warning("LCD library not available. Using simulation mode.")
            self._enable_simulation()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LCD: {e}")
            self._enable_simulation()
            return False

    def _enable_simulation(self):
        """Enable simulation mode when hardware unavailable"""
        self.connected = False
        self.ready = True
        logger.info("LCD running in simulation mode")

    def display(self, text: str, clear: bool = True):
        """Display text on LCD screen"""
        try:
            if not self.ready:
                return
            
            # Update current message
            self.current_message = DisplayMessage(text=text, timestamp=time.time())
            
            if self.connected:
                if clear:
                    self.lcd.clear()
                self.lcd.message = text
            else:
                # Simulation mode
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] LCD: {text}")
                
        except Exception as e:
            logger.error(f"Display error: {e}")

    def handle_arduino_lcd_command(self, command: str):
        """Handle LCD commands from Arduino serial"""
        try:
            if command == "LCD:CALIBRATION_IN_PROGRESS":
                self.display("Calibrating...\nPlease wait")
            elif command == "LCD:CALIBRATION_COMPLETE":
                self.display("Calibration\nComplete!")
            elif command == "LCD:SESSION_ACTIVE":
                self.display("Session Active\nMonitoring...")
            elif command == "LCD:READY":
                self.display("System Ready\nPress START")
            elif command.startswith("LCD:CALIBRATION_PROGRESS:"):
                remaining = int(command.split(":")[2])
                self.show_calibration_progress(remaining)
            else:
                logger.debug(f"Unknown LCD command: {command}")
                
        except Exception as e:
            logger.error(f"Error handling LCD command: {e}")

    def show_calibration_progress(self, remaining_seconds: int):
        """Show calibration progress with countdown"""
        if remaining_seconds > 0:
            # Simple progress visualization
            elapsed = 10 - remaining_seconds
            progress = min(10, max(0, elapsed))
            bar = "█" * progress + "░" * (10 - progress)
            self.display(f"Calibrating\n[{bar}] {remaining_seconds}s")
        else:
            self.display("Calibration\nComplete!")

    def show_status(self, status: str, details: str = ""):
        """Show system status with optional details"""
        text = f"{status}\n{details}" if details else status
        self.display(text)

    def show_progress(self, title: str, current: int, total: int):
        """Show progress information"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.display(f"{title}\n{current}/{total} ({percentage}%)")
        else:
            self.display(f"{title}\n{current}")

    def show_error(self, error_message: str):
        """Show error message"""
        self.display(f"ERROR:\n{error_message}")

    def show_session_status(self, stress_level: str, confidence: float = 0):
        """Show therapy session status"""
        if confidence > 0:
            self.display(f"Session Active\nStress: {stress_level}\nConf: {confidence:.1f}%")
        else:
            self.display(f"Session Active\nStress: {stress_level}")

    def show_baseline_data(self, gsr_baseline: float, hr_baseline: float):
        """Show baseline data"""
        self.display(f"Baseline Set\nGSR:{gsr_baseline:.1f} HR:{hr_baseline:.1f}")

    def show_arduino_status(self, connected: bool):
        """Show Arduino connection status"""
        status = "Connected" if connected else "Disconnected"
        self.display(f"Arduino\n{status}")

    def show_sensor_status(self, gsr_ok: bool, hr_ok: bool):
        """Show sensor status"""
        gsr_icon = "✓" if gsr_ok else "✗"
        hr_icon = "✓" if hr_ok else "✗"
        self.display(f"Sensors\nGSR{gsr_icon} HR{hr_icon}")

    def clear(self):
        """Clear the display"""
        try:
            if self.connected:
                self.lcd.clear()
            else:
                print("[LCD] Display cleared")
            
            self.current_message = None
            
        except Exception as e:
            logger.error(f"Clear error: {e}")

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
                self.clear()
        except:
            pass

def test_lcd_display(duration: int = 30):
    """Test LCD display functionality"""
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
            if test_count % 4 == 1:
                display.display(f"Test {test_count}")
            elif test_count % 4 == 2:
                display.show_status("System Ready", "All OK")
            elif test_count % 4 == 3:
                display.show_progress("Calibration", test_count, 20)
            else:
                display.show_session_status("Low", 85.5)
            
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