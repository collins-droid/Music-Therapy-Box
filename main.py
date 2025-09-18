#!/usr/bin/env python3
"""
Music Therapy Box - Main Controller
Modular design with USB serial communication for button inputs
"""

import time
import queue
import logging
from enum import Enum
from dataclasses import dataclass

# Import sensor and other modules
from sensors.gsr_module import GSRSensor
from sensors.hr_module import HRSensor  
from display.lcd_module import LCDDisplay
from audio.music_player import MusicPlayer
from model.stress_predictor import StressPredictor
from utils.data_collector import DataCollector
from utils.feature_extractor import FeatureExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemState(Enum):
    IDLE = "idle"
    CALIBRATING = "calibrating" 
    SESSION_ACTIVE = "session_active"
    STOPPING = "stopping"

class ButtonType(Enum):
    START = "START"
    STOP = "STOP"

@dataclass
class ButtonEvent:
    button: ButtonType
    timestamp: float

class MusicTherapyBox:
    def __init__(self):
        # System state
        self.state = SystemState.IDLE
        self.session_active = False
        
        # Threading and communication
        self.button_queue = queue.Queue()
        self.running = True
        
        # Hardware modules
        self.gsr_sensor = None
        self.hr_sensor = None
        self.lcd = None
        self.music_player = None
        self.stress_predictor = None
        self.data_collector = None
        self.feature_extractor = None
        
        # Serial communication handled by GSR sensor only
        # No separate Arduino serial connection needed
        
        # Configuration
        self.config = {
            'calibration_duration': 10,  # seconds
            'sensor_window': 60,         # seconds
            'sampling_rate': 10,         # Hz (100ms intervals)
            'serial_port': self._get_serial_port(),
            'serial_baudrate': 9600,
            'music_folders': {
                'stress_relief': 'music/stress_relief/',
                'calming': 'music/calming/'
            }
        }

    def _get_serial_port(self) -> str:
        """Get appropriate serial port based on operating system"""
        import platform
        if platform.system() == "Windows":
            return "COM3"  # Default Windows COM port
        else:
            return "/dev/ttyUSB0"  # Default Linux port

    def initialize_hardware(self) -> bool:
        """Initialize all hardware modules"""
        try:
            logger.info("Initializing hardware modules...")
            
            # Initialize sensor modules
            logger.info("Initializing GSR sensor...")
            self.gsr_sensor = GSRSensor(button_callback=self._handle_arduino_button_event, 
                                       message_callback=self._handle_arduino_message)
            logger.info(f"GSR sensor initialized - Connected: {self.gsr_sensor.connected}, Port: {self.gsr_sensor.port}")
            self.hr_sensor = HRSensor()
            
            # Initialize display module (LCD only - LEDs controlled by Arduino)
            self.lcd = LCDDisplay()
           
            # Initialize audio module
            self.music_player = MusicPlayer(self.config['music_folders'])
            
            # Initialize ML module
            self.stress_predictor = StressPredictor()
            
            # Initialize utility modules
            self.data_collector = DataCollector(sampling_rate=self.config['sampling_rate'])
            self.feature_extractor = FeatureExtractor()
            
            # Start sensor modules
            logger.info("Starting sensor modules...")
            if not self.gsr_sensor.start_sensor():
                logger.warning("Failed to start GSR sensor")
            if not self.hr_sensor.start_sensor():
                logger.warning("Failed to start HR sensor")
            
            # Give sensors time to collect data
            import time
            time.sleep(5)
            
            # Test all modules
            logger.info("Testing hardware module readiness...")
            gsr_ready = self.gsr_sensor.is_connected()
            hr_ready = self.hr_sensor.is_connected()
            lcd_ready = self.lcd.is_ready()
            music_ready = self.music_player.is_ready()
            model_ready = self.stress_predictor.is_loaded()
            
            logger.info(f"GSR sensor ready: {gsr_ready}")
            logger.info(f"HR sensor ready: {hr_ready}")
            logger.info(f"LCD ready: {lcd_ready}")
            logger.info(f"Music player ready: {music_ready}")
            logger.info(f"Stress predictor ready: {model_ready}")
            
            if not all([gsr_ready, hr_ready, lcd_ready, music_ready, model_ready]):
                raise Exception("One or more hardware modules failed initialization")
            
            logger.info("Hardware initialization successful")
            self.lcd.display("System Ready")
            return True
            
        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}")
            return False

    def initialize_serial(self) -> bool:
        """Initialize USB serial communication with Arduino"""
        # Arduino communication is now handled by GSR sensor
        # No need for separate serial connection in main.py
        logger.info("Arduino communication handled by GSR sensor")
        return True

    def _serial_reader(self):
        """Background thread to read messages from Arduino"""
        # Arduino communication is now handled by GSR sensor
        # This method is disabled to prevent serial port conflicts
        logger.info("Serial reader disabled - Arduino communication handled by GSR sensor")
        while self.running:
            time.sleep(1)  # Just sleep to keep thread alive

    def _handle_lcd_message(self, message: str):
        """Handle LCD display messages from Arduino"""
        try:
            # Use the LCD module's Arduino command handler
            self.lcd.handle_arduino_lcd_command(message)
        except Exception as e:
            logger.error(f"Error handling LCD message: {e}")

    def _handle_baseline_data(self, message: str):
        """Handle baseline data from Arduino - now handled by GSR sensor"""
        # Baseline data is now handled directly by GSR sensor
        # This method is kept for compatibility but does nothing
        pass

    def _handle_baseline_progress(self, message: str):
        """Handle baseline collection progress"""
        try:
            # Format: "BASELINE_PROGRESS:10/50"
            progress_part = message.split(":")[1]  # "10/50"
            current, total = progress_part.split("/")
            current = int(current)
            total = int(total)
            
            logger.debug(f"Baseline progress: {current}/{total}")
            
            # Show progress on LCD
            self.lcd.show_baseline_collection(current, total)
            
        except Exception as e:
            logger.error(f"Error handling baseline progress: {e}")

    def _handle_calibration_status(self, message: str):
        """Handle calibration status messages"""
        try:
            if message == "CALIBRATION:STARTED":
                logger.info("Arduino calibration started")
            elif message == "CALIBRATION:COMPLETE":
                logger.info("Arduino calibration completed")
            else:
                logger.debug(f"Calibration status: {message}")
        except Exception as e:
            logger.error(f"Error handling calibration status: {e}")

    def _handle_session_status(self, message: str):
        """Handle session status messages"""
        try:
            if message == "SESSION:STARTED":
                logger.info("Arduino session started")
            else:
                logger.debug(f"Session status: {message}")
        except Exception as e:
            logger.error(f"Error handling session status: {e}")

    def _handle_status_message(self, message: str):
        """Handle general status messages"""
        try:
            # Clean the message string - remove null bytes and other control characters
            cleaned_message = message.replace('\x00', '').replace('\r', '').replace('\n', '').strip()
            
            if cleaned_message == "STATUS:IDLE":
                # Only log IDLE status changes, not every occurrence
                if not hasattr(self, '_last_status') or self._last_status != "IDLE":
                    logger.info("Arduino status: IDLE")
                    self._last_status = "IDLE"
            elif cleaned_message == "STATUS:CALIBRATING":
                if not hasattr(self, '_last_status') or self._last_status != "CALIBRATING":
                    logger.info("Arduino status: CALIBRATING")
                    self._last_status = "CALIBRATING"
            elif cleaned_message == "STATUS:SESSION_ACTIVE":
                if not hasattr(self, '_last_status') or self._last_status != "SESSION_ACTIVE":
                    logger.info("Arduino status: SESSION_ACTIVE")
                    self._last_status = "SESSION_ACTIVE"
            elif cleaned_message.startswith("STATUS:CALIBRATING,REMAINING:"):
                # Just log calibration progress, no LCD updates needed
                logger.debug(f"Calibration progress: {cleaned_message}")
            else:
                logger.debug(f"Status message: {cleaned_message}")
        except Exception as e:
            logger.error(f"Error handling status message: '{message}' -> '{cleaned_message}' - {e}")

    def _handle_arduino_button_event(self, button_type: str):
        """Handle button events from Arduino"""
        try:
            logger.info(f"Arduino button event: {button_type}")
            
            if button_type == "START":
                button_event = ButtonEvent(ButtonType.START, time.time())
                self.button_queue.put(button_event)
            elif button_type == "STOP":
                button_event = ButtonEvent(ButtonType.STOP, time.time())
                self.button_queue.put(button_event)
            else:
                logger.warning(f"Unknown button type: {button_type}")
                
        except Exception as e:
            logger.error(f"Error handling Arduino button event: {e}")

    def _handle_arduino_message(self, message: str):
        """Handle Arduino status and control messages"""
        try:
            # Clean the message string - remove null bytes and other control characters
            cleaned_message = message.replace('\x00', '').replace('\r', '').replace('\n', '').strip()
            
            logger.debug(f"Arduino message: '{message}' -> cleaned: '{cleaned_message}'")
            
            if cleaned_message.startswith("BASELINE:"):
                self._handle_baseline_data(cleaned_message)
            elif cleaned_message.startswith("BASELINE_PROGRESS:"):
                self._handle_baseline_progress(cleaned_message)
            elif cleaned_message.startswith("CALIBRATION:"):
                self._handle_calibration_status(cleaned_message)
            elif cleaned_message.startswith("SESSION:"):
                self._handle_session_status(cleaned_message)
            elif cleaned_message.startswith("STATUS:"):
                self._handle_status_message(cleaned_message)
            elif cleaned_message.startswith("LCD:"):
                self._handle_lcd_message(cleaned_message)
            else:
                logger.debug(f"Unhandled Arduino message: '{cleaned_message}'")
                
        except Exception as e:
            logger.error(f"Error handling Arduino message: '{message}' -> '{cleaned_message}' - {e}")

    def run_calibration(self) -> bool:
        """Run sensor calibration sequence"""
        try:
            logger.info("Starting calibration...")
            self.state = SystemState.CALIBRATING
            
            # Wait for Arduino to complete calibration and send baseline data
            # The Arduino will handle the actual calibration process
            calibration_timeout = 18  # seconds (Arduino takes 10s + 8s buffer for serial delays)
            start_time = time.time()
            
            logger.info("Waiting for Arduino calibration to complete...")
            self.lcd.show_waiting_for_arduino()
            
            # Debug: Log when we start waiting
            logger.info("DEBUG: Starting calibration wait loop...")
            
            while time.time() - start_time < calibration_timeout:
                # Check if GSR sensor has baseline data
                if self.gsr_sensor.has_baseline_data():
                    logger.info("Baseline data received from Arduino")
                    break
                
                # Log progress every 2 seconds
                elapsed = time.time() - start_time
                if int(elapsed) % 2 == 0 and elapsed > 0:
                    logger.debug(f"Calibration wait: {elapsed:.1f}s elapsed, has_baseline={self.gsr_sensor.has_baseline_data()}")
                    # Check GSR sensor status
                    if self.gsr_sensor:
                        logger.debug(f"GSR sensor status - Connected: {self.gsr_sensor.connected}, Running: {self.gsr_sensor.running}")
                        latest_reading = self.gsr_sensor.get_reading()
                        if latest_reading:
                            logger.debug(f"Latest GSR reading: {latest_reading.conductance:.2f}μS")
                
                time.sleep(0.1)
            
            if not self.gsr_sensor.has_baseline_data():
                # Use default GSR values when Arduino baseline data is not received
                logger.warning("Arduino baseline data not received - using default values")
                self.gsr_sensor.set_default_baseline(gsr_baseline=0.0, hr_baseline=70.0)
                logger.info("Using default baseline values - GSR: 0.0, HR: 70.0")
            else:
                # Use Arduino baseline data
                baseline_data = self.gsr_sensor.get_baseline_data()
                logger.info(f"Using Arduino baseline - GSR: {baseline_data.gsr_baseline:.2f}, HR: {baseline_data.hr_baseline:.2f}")
            
            # Cleanup
            self.lcd.display("Calibration complete!\nStarting session...")
            
            # Add MAX30102 calibration after GSR calibration
            logger.info("Starting MAX30102 calibration...")
            self.lcd.display("Calibrating HR sensor...\nPress finger HARD on sensor")
            
            # Give HR sensor time to calibrate and collect baseline data
            calibration_start = time.time()
            calibration_duration = 10  # seconds for HR calibration
            
            while time.time() - calibration_start < calibration_duration:
                # Check if we have valid HR readings
                hr_reading = self.hr_sensor.get_reading()
                
                # Debug: Log HR sensor status
                if int(time.time() - calibration_start) % 2 == 0 and time.time() - calibration_start > 0:
                    logger.debug(f"HR calibration: reading={hr_reading is not None}, "
                               f"finger_detected={hr_reading.finger_detected if hr_reading else False}, "
                               f"valid_bpm={hr_reading.valid_bpm if hr_reading else False}")
                
                if hr_reading and hr_reading.finger_detected and hr_reading.valid_bpm:
                    # Calculate baseline from recent readings
                    baseline_bpm = self.hr_sensor.calculate_baseline(duration_seconds=5)
                    if baseline_bpm:
                        self.hr_sensor.set_baseline_data(baseline_bpm)
                        logger.info(f"HR sensor calibrated - Baseline BPM: {baseline_bpm:.1f}")
                        break
                
                elapsed = time.time() - calibration_start
                if int(elapsed) % 2 == 0 and elapsed > 0:
                    logger.debug(f"HR calibration wait: {elapsed:.1f}s elapsed")
                
                time.sleep(0.1)
            
            # If no baseline collected, use default
            if not self.hr_sensor.has_baseline_data():
                logger.warning("HR baseline data not collected - using default")
                self.hr_sensor.set_baseline_data(70.0)  # Default HR baseline
            
            logger.info("MAX30102 calibration completed")
            
            logger.info("Calibration completed successfully")
            time.sleep(2)  # Brief pause before session
            return True
            
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            # Use default values even if calibration fails
            logger.warning("Using fallback default baseline values")
            self.gsr_sensor.set_default_baseline(gsr_baseline=0.0, hr_baseline=70.0)
            self.lcd.display("Calibration complete!\nUsing default values")
            logger.info("Calibration completed with default values")
            time.sleep(2)
            return True

    def run_therapy_session(self):
        """Main therapy session loop"""
        logger.info("Starting therapy session...")
        self.state = SystemState.SESSION_ACTIVE
        self.session_active = True
        
        # Visual feedback (LEDs controlled by Arduino)
        self.lcd.display("Therapy session started\nAnalyzing your state...")
        
        try:
            while self.session_active and self.running:
                # Step 1: Collect sensor data window
                sensor_window = self.data_collector.collect_window(
                    gsr_sensor=self.gsr_sensor,
                    hr_sensor=self.hr_sensor,
                    window_size=self.config['sensor_window'],
                    baseline=self.gsr_sensor.get_baseline_data()
                )
                
                if not sensor_window:
                    logger.warning("Failed to collect sensor data")
                    continue
                
                # Step 2: Extract features
                features = self.feature_extractor.extract_features(sensor_window)
                
                if not features:
                    logger.warning("Feature extraction failed - using default prediction")
                    # Use default prediction when feature extraction fails
                    prediction = "no_stress"
                    confidence = 0.5
                else:
                    # Step 3: Predict stress level
                    prediction = self.stress_predictor.predict(features)
                    confidence = self.stress_predictor.get_confidence()
                
                logger.info(f"Stress prediction: {prediction} (confidence: {confidence:.2f})")
                
                # Step 4: Select appropriate music
                music_category = self._map_prediction_to_music(prediction)
                song_path = self.music_player.select_song(music_category)
                
                if not song_path:
                    logger.error(f"No songs available in category: {music_category}")
                    continue
                
                # Step 5: Display status and start playback
                self._update_display_for_prediction(prediction, confidence)
                self.music_player.play(song_path)
                
                # Step 6: Handle playback and user interactions
                self._handle_playback_loop()
                
        except Exception as e:
            logger.error(f"Session error: {e}")
        finally:
            self._cleanup_session()

    def _handle_playback_loop(self):
        """Handle music playback with button monitoring and re-evaluation"""
        re_evaluation_time = None
        
        while self.music_player.is_playing() and self.session_active:
            # Check for button events
            try:
                button_event = self.button_queue.get_nowait()
                
                if button_event.button == ButtonType.STOP:
                    self.stop_session()
                    return
                    
            except queue.Empty:
                pass
            
            # Schedule re-evaluation 60 seconds before song ends
            if re_evaluation_time is None:
                song_duration = self.music_player.get_duration()
                if song_duration and song_duration > 60:
                    re_evaluation_time = time.time() + (song_duration - 60)
            
            # Perform re-evaluation if needed
            if re_evaluation_time and time.time() >= re_evaluation_time:
                self._perform_re_evaluation()
                re_evaluation_time = None  # Prevent multiple re-evaluations
            
            time.sleep(0.1)

    def _perform_re_evaluation(self):
        """Re-evaluate stress level before current song ends"""
        logger.info("Re-evaluating stress level...")
        self.lcd.display("Re-evaluating your state...")
        
        try:
            # Quick sensor reading
            sensor_data = self.data_collector.collect_quick_sample(
                gsr_sensor=self.gsr_sensor,
                hr_sensor=self.hr_sensor,
                duration=10,  # Shorter sample
                baseline=self.gsr_sensor.get_baseline_data()
            )
            
            if sensor_data:
                features = self.feature_extractor.extract_features(sensor_data)
                new_prediction = self.stress_predictor.predict(features)
                confidence = self.stress_predictor.get_confidence()
                
                logger.info(f"Re-evaluation result: {new_prediction} (confidence: {confidence:.2f})")
                self._update_display_for_prediction(new_prediction, confidence)
                
        except Exception as e:
            logger.warning(f"Re-evaluation failed: {e}")

    def _map_prediction_to_music(self, prediction: str) -> str:
        """Map ML prediction to music category"""
        mapping = {
            'stress': 'stress_relief',
            'no_stress': 'calming'
        }
        return mapping.get(prediction.lower(), 'calming')  # Default to calming music

    def _update_display_for_prediction(self, prediction: str, confidence: float):
        """Update LCD display based on prediction"""
        status_messages = {
            'stress': f"Stress detected ({confidence:.1f})\nPlaying calming music",
            'no_stress': f"Relaxed state ({confidence:.1f})\nPlaying gentle music"
        }
        
        category = self._map_prediction_to_music(prediction)
        message = status_messages.get(category, f"State: {prediction}\nPlaying music...")
        self.lcd.display(message)

    def stop_session(self):
        """Stop the current therapy session"""
        logger.info("Stopping therapy session...")
        self.state = SystemState.STOPPING
        self.session_active = False
        
        self.music_player.stop()
        self._cleanup_session()

    def _cleanup_session(self):
        """Clean up session resources"""
        self.lcd.display("Session stopped.\nPress START for new session")
        self.state = SystemState.IDLE
        logger.info("Session cleanup completed")

    def handle_button_events(self):
        """Main button event handler"""
        try:
            button_event = self.button_queue.get_nowait()
            
            if button_event.button == ButtonType.START and self.state == SystemState.IDLE:
                # Start new session with calibration
                if self.run_calibration():
                    self.run_therapy_session()
                    
            elif button_event.button == ButtonType.STOP:
                if self.state in [SystemState.SESSION_ACTIVE, SystemState.CALIBRATING]:
                    self.stop_session()
            
        except queue.Empty:
            pass

    def main_loop(self):
        """Main application loop"""
        logger.info("Starting main application loop...")
        
        while self.running:
            try:
                # Handle button events
                self.handle_button_events()
                
                # Small delay to prevent CPU spinning
                time.sleep(0.05)
                
            except KeyboardInterrupt:
                logger.info("Shutdown requested by user")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(1)  # Prevent rapid error loops

    def shutdown(self):
        """Clean shutdown of the system"""
        logger.info("Shutting down system...")
        self.running = False
        self.session_active = False
        
        if self.music_player:
            self.music_player.stop()
            
        if self.lcd:
            self.lcd.display("System shutting down...")
            
        # Arduino serial communication is handled by GSR sensor
        # No need to close separate Arduino connection
            
        logger.info("Shutdown complete")

def main():
    """Main entry point"""
    therapy_box = MusicTherapyBox()
    
    try:
        # Initialize system
        if not therapy_box.initialize_hardware():
            logger.error("Hardware initialization failed. Exiting.")
            return 1
            
        if not therapy_box.initialize_serial():
            logger.error("Serial initialization failed. Exiting.")
            return 1
        
        # Show ready state
        therapy_box.lcd.display("Music Therapy Box\nPress START to begin")
        logger.info("System ready. Press START button to begin.")
        
        # Run main loop
        therapy_box.main_loop()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    finally:
        therapy_box.shutdown()
    
    return 0

if __name__ == "__main__":
    exit(main())

    