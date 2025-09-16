#!/usr/bin/env python3
"""
Music Therapy Box - Main Controller
Modular design with USB serial communication for button inputs
"""

import time
import threading
import queue
import serial
import logging
from enum import Enum
from dataclasses import dataclass

# Import sensor and other modules (to be implemented separately)
from sensors.gsr_module import GSRSensor
from sensors.hr_module import HRSensor  
from display.oled_module import OLEDDisplay
from display.led_module import LEDController
from audio.music_player import MusicPlayer
from ml.stress_predictor import StressPredictor
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
    NEXT = "NEXT"

@dataclass
class ButtonEvent:
    button: ButtonType
    timestamp: float

class MusicTherapyBox:
    def __init__(self):
        # System state
        self.state = SystemState.IDLE
        self.session_active = False
        self.baseline_data = None
        
        # Threading and communication
        self.button_queue = queue.Queue()
        self.running = True
        
        # Hardware modules
        self.gsr_sensor = None
        self.hr_sensor = None
        self.oled = None
        self.leds = None
        self.music_player = None
        self.stress_predictor = None
        self.data_collector = None
        self.feature_extractor = None
        
        # Serial communication for buttons
        self.arduino_serial = None
        self.serial_thread = None
        
        # Configuration
        self.config = {
            'calibration_duration': 10,  # seconds
            'sensor_window': 60,         # seconds
            'sampling_rate': 10,         # Hz (100ms intervals)
            'serial_port': '/dev/ttyUSB0',
            'serial_baudrate': 9600,
            'music_folders': {
                'stress': 'music/stress_relief/',
                'no_stress': 'music/calming/',
                'neutral': 'music/neutral/'
            }
        }

    def initialize_hardware(self) -> bool:
        """Initialize all hardware modules"""
        try:
            logger.info("Initializing hardware modules...")
            
            # Initialize sensor modules
            self.gsr_sensor = GSRSensor()
            self.hr_sensor = HRSensor()
            
            # Initialize display modules
            self.oled = OLEDDisplay()
            self.leds = LEDController()
            
            # Initialize audio module
            self.music_player = MusicPlayer(self.config['music_folders'])
            
            # Initialize ML module
            self.stress_predictor = StressPredictor()
            
            # Initialize utility modules
            self.data_collector = DataCollector(sampling_rate=self.config['sampling_rate'])
            self.feature_extractor = FeatureExtractor()
            
            # Test all modules
            if not all([
                self.gsr_sensor.is_connected(),
                self.hr_sensor.is_connected(),
                self.oled.is_ready(),
                self.leds.test(),
                self.music_player.is_ready(),
                self.stress_predictor.is_loaded()
            ]):
                raise Exception("One or more hardware modules failed initialization")
            
            logger.info("Hardware initialization successful")
            self.oled.display("System Ready")
            return True
            
        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}")
            return False

    def initialize_serial(self) -> bool:
        """Initialize USB serial communication with Arduino"""
        try:
            self.arduino_serial = serial.Serial(
                self.config['serial_port'], 
                self.config['serial_baudrate'],
                timeout=1
            )
            
            # Start serial reading thread
            self.serial_thread = threading.Thread(target=self._serial_reader, daemon=True)
            self.serial_thread.start()
            
            logger.info(f"Serial communication initialized on {self.config['serial_port']}")
            return True
            
        except Exception as e:
            logger.error(f"Serial initialization failed: {e}")
            return False

    def _serial_reader(self):
        """Background thread to read button events from Arduino"""
        while self.running:
            try:
                if self.arduino_serial and self.arduino_serial.in_waiting > 0:
                    line = self.arduino_serial.readline().decode('utf-8').strip()
                    
                    if line:
                        # Expected format: "BUTTON:START" or "BUTTON:STOP" or "BUTTON:NEXT"
                        if line.startswith("BUTTON:"):
                            button_name = line.split(":")[1]
                            
                            if button_name in [b.value for b in ButtonType]:
                                button_event = ButtonEvent(
                                    button=ButtonType(button_name),
                                    timestamp=time.time()
                                )
                                self.button_queue.put(button_event)
                                logger.debug(f"Button event received: {button_name}")
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logger.warning(f"Serial read error: {e}")
                time.sleep(0.1)

    def run_calibration(self) -> bool:
        """Run sensor calibration sequence"""
        try:
            logger.info("Starting calibration...")
            self.state = SystemState.CALIBRATING
            
            # Visual feedback
            self.leds.turn_on('yellow')
            self.oled.display("Calibration in progress...\nRemain still for 10s")
            
            # Collect calibration data
            calibration_data = self.data_collector.collect_baseline(
                gsr_sensor=self.gsr_sensor,
                hr_sensor=self.hr_sensor,
                duration=self.config['calibration_duration']
            )
            
            if not calibration_data or len(calibration_data) < 10:
                raise Exception("Insufficient calibration data collected")
            
            # Compute baseline
            self.baseline_data = self.feature_extractor.compute_baseline(calibration_data)
            
            # Cleanup
            self.leds.turn_off('yellow')
            self.oled.display("Calibration complete!\nStarting session...")
            
            logger.info("Calibration completed successfully")
            time.sleep(2)  # Brief pause before session
            return True
            
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            self.leds.turn_off('yellow')
            self.oled.display("Calibration failed!\nPlease try again.")
            self.state = SystemState.IDLE
            return False

    def run_therapy_session(self):
        """Main therapy session loop"""
        logger.info("Starting therapy session...")
        self.state = SystemState.SESSION_ACTIVE
        self.session_active = True
        
        # Visual feedback
        self.leds.turn_on('red')
        self.oled.display("Therapy session started\nAnalyzing your state...")
        
        try:
            while self.session_active and self.running:
                # Step 1: Collect sensor data window
                sensor_window = self.data_collector.collect_window(
                    gsr_sensor=self.gsr_sensor,
                    hr_sensor=self.hr_sensor,
                    window_size=self.config['sensor_window'],
                    baseline=self.baseline_data
                )
                
                if not sensor_window:
                    logger.warning("Failed to collect sensor data")
                    continue
                
                # Step 2: Extract features
                features = self.feature_extractor.extract_features(sensor_window)
                
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
                elif button_event.button == ButtonType.NEXT:
                    self.music_player.stop()
                    return  # Exit to select next song
                    
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
        self.oled.display("Re-evaluating your state...", line=2)
        
        try:
            # Quick sensor reading
            sensor_data = self.data_collector.collect_quick_sample(
                gsr_sensor=self.gsr_sensor,
                hr_sensor=self.hr_sensor,
                duration=10,  # Shorter sample
                baseline=self.baseline_data
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
            'stress': 'stress',
            'high_stress': 'stress',
            'no_stress': 'no_stress',
            'low_stress': 'no_stress',
            'relaxed': 'no_stress',
            'neutral': 'neutral'
        }
        return mapping.get(prediction.lower(), 'neutral')

    def _update_display_for_prediction(self, prediction: str, confidence: float):
        """Update OLED display based on prediction"""
        status_messages = {
            'stress': f"Stress detected ({confidence:.1f})\nPlaying calming music",
            'no_stress': f"Relaxed state ({confidence:.1f})\nPlaying gentle music",
            'neutral': f"Neutral state ({confidence:.1f})\nPlaying ambient music"
        }
        
        category = self._map_prediction_to_music(prediction)
        message = status_messages.get(category, f"State: {prediction}\nPlaying music...")
        self.oled.display(message)

    def stop_session(self):
        """Stop the current therapy session"""
        logger.info("Stopping therapy session...")
        self.state = SystemState.STOPPING
        self.session_active = False
        
        self.music_player.stop()
        self._cleanup_session()

    def _cleanup_session(self):
        """Clean up session resources"""
        self.leds.turn_off('red')
        self.oled.display("Session stopped.\nPress START for new session")
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
                    
            # NEXT button is handled within playback loop
            
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
            
        if self.leds:
            self.leds.turn_off_all()
            
        if self.oled:
            self.oled.display("System shutting down...")
            
        if self.arduino_serial:
            self.arduino_serial.close()
            
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
        therapy_box.oled.display("Music Therapy Box\nPress START to begin")
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

    