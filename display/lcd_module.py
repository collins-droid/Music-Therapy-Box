#!/usr/bin/env python3
"""
LCD Display Module for Music Therapy Box
Handles LCD display output using I2C communication
LCD is connected to I2C address 0x27
"""

import logging
import time
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DisplayMessage:
    text: str
    timestamp: float
    priority: int = 0  # Higher number = higher priority

class LCDDisplay:
    """
    LCD display controller for Music Therapy Box
    Uses I2C communication with LCD at address 0x27
    """
    
    def __init__(self, i2c_address: int = 0x27, width: int = 16, height: int = 2):
        """
        Initialize LCD display
        
        Args:
            i2c_address: I2C address of LCD (default 0x27)
            width: Display width in characters
            height: Display height in lines
        """
        self.i2c_address = i2c_address
        self.width = width
        self.height = height
        self.connected = False
        self.ready = False
        
        # Message queue for display updates
        self.message_queue = []
        self.current_message = None
        self.max_queue_size = 10
        
        # Display configuration
        self.config = {
            'auto_scroll': True,
            'scroll_delay': 2.0,  # seconds
            'log_display': True,
            'log_file': 'lcd_display_log.txt'
        }
        
        # Initialize display
        self._initialize_display()

    def _initialize_display(self) -> bool:
        """Initialize the LCD display hardware"""
        try:
            # Try to import and initialize I2C LCD
            try:
                import board
                from adafruit_character_lcd.character_lcd_i2c import Character_LCD_I2C
                
                # I2C setup
                i2c = board.I2C()
                self.lcd = Character_LCD_I2C(i2c, self.width, self.height, address=self.i2c_address)
                self.connected = True
                self.ready = True
                
                # Clear display and show ready message
                self.lcd.clear()
                self.lcd.message = "Music Therapy\nBox Ready"
                
                logger.info(f"LCD display initialized successfully at address 0x{self.i2c_address:02X}")
                return True
                
            except ImportError:
                logger.warning("Adafruit Character LCD library not available. Using simulation mode.")
                self._simulate_display()
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize LCD display: {e}")
            self._simulate_display()
            return False

    def _simulate_display(self):
        """Simulate display functionality when hardware is not available"""
        self.connected = False
        self.ready = True
        logger.info("LCD display running in simulation mode")

    def display(self, text: str, line: int = 0, clear: bool = True):
        """
        Display text on LCD screen
        
        Args:
            text: Text to display
            line: Line number (0-based)
            clear: Whether to clear display first
        """
        try:
            if not self.ready:
                logger.warning("LCD display not ready")
                return
            
            # Create display message
            message = DisplayMessage(
                text=text,
                timestamp=time.time(),
                priority=1
            )
            
            # Add to queue
            self._add_to_queue(message)
            
            if self.connected:
                # Hardware display
                self._display_hardware(text, line, clear)
            else:
                # Simulation mode
                self._display_simulation(text, line, clear)
            
            # Log display action
            if self.config['log_display']:
                self._log_display(text)
                
        except Exception as e:
            logger.error(f"Failed to display text: {e}")

    def handle_arduino_lcd_command(self, command: str):
        """
        Handle LCD commands received from Arduino via serial
        
        Args:
            command: LCD command from Arduino (e.g., "LCD:CALIBRATION_IN_PROGRESS")
        """
        try:
            if command == "LCD:CALIBRATION_IN_PROGRESS":
                self.show_calibration_start()
            elif command == "LCD:CALIBRATION_COMPLETE":
                self.show_calibration_complete()
            elif command == "LCD:SESSION_ACTIVE":
                self.show_session_active()
            elif command == "LCD:READY":
                self.show_system_ready()
            elif command.startswith("LCD:CALIBRATION_PROGRESS:"):
                remaining_seconds = int(command.split(":")[2])
                self.show_calibration_progress(remaining_seconds)
            else:
                logger.debug(f"Unknown Arduino LCD command: {command}")
                
        except Exception as e:
            logger.error(f"Error handling Arduino LCD command: {e}")

    def display_with_animation(self, text: str, animation_type: str = "none"):
        """
        Display text with optional animation effects
        
        Args:
            text: Text to display
            animation_type: Type of animation ("none", "blink", "scroll")
        """
        try:
            if animation_type == "blink":
                # Blink effect by clearing and redisplaying
                self.display("", clear=True)
                time.sleep(0.2)
                self.display(text)
            elif animation_type == "scroll":
                # Simple scroll effect by displaying character by character
                for i in range(len(text) + 1):
                    partial_text = text[:i]
                    self.display(partial_text)
                    time.sleep(0.1)
            else:
                # Normal display
                self.display(text)
                
        except Exception as e:
            logger.error(f"Error in animated display: {e}")

    def _display_hardware(self, text: str, line: int, clear: bool):
        """Display text on hardware LCD"""
        try:
            if clear:
                self.lcd.clear()
            
            # Split text into lines if it contains newlines
            lines = text.split('\n')
            
            # Display each line
            for i, line_text in enumerate(lines[:self.height]):
                if i == 0:
                    self.lcd.message = line_text
                else:
                    # For multi-line displays, we need to position cursor
                    self.lcd.cursor_position(0, i)
                    self.lcd.message = line_text
            
        except Exception as e:
            logger.error(f"Hardware LCD display error: {e}")

    def _display_simulation(self, text: str, line: int, clear: bool):
        """Simulate display output to console"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] LCD[{line}]: {text}")

    def _add_to_queue(self, message: DisplayMessage):
        """Add message to display queue"""
        self.message_queue.append(message)
        
        # Maintain queue size
        if len(self.message_queue) > self.max_queue_size:
            self.message_queue.pop(0)
        
        # Update current message
        self.current_message = message

    def _log_display(self, text: str):
        """Log display actions to file"""
        try:
            with open(self.config['log_file'], "a") as f:
                timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp_str}: {text}\n")
        except Exception as e:
            logger.warning(f"Failed to log display action: {e}")

    def clear(self):
        """Clear the LCD display"""
        try:
            if self.connected:
                self.lcd.clear()
            else:
                print("[LCD] Display cleared")
            
            self.current_message = None
            
        except Exception as e:
            logger.error(f"Failed to clear LCD display: {e}")

    def show_status(self, status: str, details: str = ""):
        """
        Show system status with details
        
        Args:
            status: Main status message
            details: Additional details
        """
        if details:
            full_text = f"{status}\n{details}"
        else:
            full_text = status
        
        self.display(full_text)

    def show_progress(self, title: str, current: int, total: int):
        """
        Show progress information
        
        Args:
            title: Progress title
            current: Current progress value
            total: Total progress value
        """
        if total > 0:
            percentage = (current / total) * 100
            progress_text = f"{title}\n{current}/{total} ({percentage:.1f}%)"
        else:
            progress_text = f"{title}\n{current}/?"
        
        self.display(progress_text)

    def show_error(self, error_message: str):
        """Show error message"""
        self.display(f"ERROR:\n{error_message}")

    def show_calibration_progress(self, remaining_seconds: int):
        """Show calibration progress with enhanced display"""
        if remaining_seconds > 0:
            # Create progress bar visualization
            progress_chars = min(15, int((10 - remaining_seconds) * 1.5))
            progress_bar = "█" * progress_chars + "░" * (15 - progress_chars)
            
            self.display(f"Calibrating...\n[{progress_bar}] {remaining_seconds}s")
        else:
            self.display("Calibration\nComplete!")

    def show_session_status(self, stress_level: str, confidence: float):
        """Show therapy session status"""
        self.display(f"Session Active\nStress: {stress_level}\nConf: {confidence:.1f}%")

    def show_baseline_data(self, gsr_baseline: float, hr_baseline: float):
        """Show collected baseline data"""
        self.display(f"Baseline Data\nGSR: {gsr_baseline:.1f}μS\nHR: {hr_baseline:.1f} BPM")

    def show_baseline_collection(self, samples_collected: int, total_samples: int):
        """Show baseline data collection progress"""
        if total_samples > 0:
            percentage = (samples_collected / total_samples) * 100
            progress_chars = min(15, int(percentage * 0.15))
            progress_bar = "█" * progress_chars + "░" * (15 - progress_chars)
            
            self.display(f"Collecting Data\n[{progress_bar}] {samples_collected}/{total_samples}")
        else:
            self.display(f"Collecting Data\nSamples: {samples_collected}")

    def show_arduino_status(self, status: str, details: str = ""):
        """Show Arduino communication status"""
        if details:
            self.display(f"Arduino: {status}\n{details}")
        else:
            self.display(f"Arduino: {status}")

    def show_calibration_start(self):
        """Show calibration start message"""
        self.display("Starting Calibration\nPlease remain still...")

    def show_calibration_complete(self):
        """Show calibration completion message"""
        self.display("Calibration Complete!\nStarting session...")

    def show_session_active(self, stress_level: str = "Monitoring"):
        """Show active session status"""
        self.display(f"Session Active\n{stress_level}")

    def show_system_ready(self):
        """Show system ready message"""
        self.display("System Ready\nPress START to begin")

    def show_arduino_connection_status(self, connected: bool):
        """Show Arduino connection status"""
        if connected:
            self.display("Arduino Connected\nSystem Ready")
        else:
            self.display("Arduino Disconnected\nCheck connection")

    def show_sensor_status(self, gsr_connected: bool, hr_connected: bool):
        """Show sensor connection status"""
        gsr_status = "✓" if gsr_connected else "✗"
        hr_status = "✓" if hr_connected else "✗"
        
        self.display(f"Sensors: GSR{gsr_status} HR{hr_status}\nSystem Ready")

    def show_error_with_recovery(self, error_message: str, recovery_action: str = ""):
        """Show error message with recovery instructions"""
        if recovery_action:
            self.display(f"ERROR:\n{error_message}\n{recovery_action}")
        else:
            self.display(f"ERROR:\n{error_message}")

    def show_countdown(self, title: str, seconds: int):
        """Show countdown timer"""
        self.display(f"{title}\n{seconds} seconds...")

    def show_waiting_for_arduino(self):
        """Show waiting for Arduino message"""
        self.display("Waiting for Arduino\nCalibration...")

    def show_baseline_received(self, gsr_value: float, hr_value: float):
        """Show received baseline data"""
        self.display(f"Baseline Received\nGSR: {gsr_value:.1f}μS\nHR: {hr_value:.1f} BPM")

    def is_ready(self) -> bool:
        """
        Check if LCD display is ready (expected by main script)
        
        Returns:
            True if display is ready
        """
        return self.ready

    def get_current_message(self) -> Optional[DisplayMessage]:
        """Get current display message"""
        return self.current_message

    def get_message_history(self) -> List[DisplayMessage]:
        """Get display message history"""
        return self.message_queue.copy()

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if self.connected:
                self.clear()
        except Exception as e:
            logger.warning(f"Error during LCD display cleanup: {e}")

# Standalone testing function
def test_lcd_display(duration: int = 30):
    """
    Test function for standalone operation
    
    Args:
        duration: Duration in seconds to test display
    """
    print('LCD display starting...')
    
    display = LCDDisplay()
    
    if not display.is_ready():
        print("Failed to initialize LCD display!")
        return
    
    try:
        start_time = time.time()
        test_count = 0
        
        while time.time() - start_time < duration:
            test_count += 1
            
            # Test different display functions
            if test_count % 4 == 1:
                display.display(f"Test Message {test_count}")
            elif test_count % 4 == 2:
                display.show_status("System Ready", "All sensors connected")
            elif test_count % 4 == 3:
                display.show_progress("Calibration", test_count, duration)
            else:
                display.show_session_status("Low", 85.5)
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, exiting...')
    
    finally:
        display.clear()
        print('LCD display test completed!')

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LCD display functionality")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duration in seconds to test display, default 30")
    args = parser.parse_args()
    
    # Run standalone test
    test_lcd_display(duration=args.time)
