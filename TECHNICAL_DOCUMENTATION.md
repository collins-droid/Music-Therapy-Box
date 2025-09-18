# Music Therapy Box - Technical Documentation

## Main Entry Point (`main.py`)

### Overview

The `main.py` file serves as the central controller for the Music Therapy Box system. It orchestrates all hardware components, manages system state, handles user interactions, and implements the core therapy session logic using machine learning-based stress detection.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Music Therapy Box                        │
│                     (main.py)                              │
├─────────────────────────────────────────────────────────────┤
│  Hardware Modules          │  Software Components          │
│  ├─ GSR Sensor             │  ├─ Stress Predictor          │
│  ├─ HR Sensor (MAX30102)   │  ├─ Feature Extractor        │
│  ├─ LCD Display            │  ├─ Data Collector            │
│  ├─ Music Player           │  └─ Arduino Communication     │
│  └─ Arduino UNO            │                               │
└─────────────────────────────────────────────────────────────┘
```

### Core Classes and Data Structures

#### SystemState Enum
```python
class SystemState(Enum):
    IDLE = "idle"                    # System ready, waiting for user input
    CALIBRATING = "calibrating"      # Collecting baseline sensor data
    SESSION_ACTIVE = "session_active" # Active therapy session running
    STOPPING = "stopping"            # Session termination in progress
```

#### ButtonType Enum
```python
class ButtonType(Enum):
    START = "START"  # Begin therapy session
    STOP = "STOP"    # End current session
```

#### ButtonEvent Dataclass
```python
@dataclass
class ButtonEvent:
    button: ButtonType    # Type of button pressed
    timestamp: float      # When the event occurred
```

### Main Controller Class: MusicTherapyBox

#### Initialization (`__init__`)

The controller initializes with:
- **System State**: Starts in `IDLE` mode
- **Hardware Modules**: All sensors and components initialized as `None`
- **Communication**: Button event queue for Arduino communication
- **Configuration**: System parameters including calibration duration, sampling rates, and music folders

```python
def __init__(self):
    self.state = SystemState.IDLE
    self.session_active = False
    self.button_queue = queue.Queue()
    self.running = True
    
    # Hardware modules (initialized later)
    self.gsr_sensor = None
    self.hr_sensor = None
    self.lcd = None
    self.music_player = None
    self.stress_predictor = None
    self.data_collector = None
    self.feature_extractor = None
```

#### Configuration Parameters

```python
self.config = {
    'calibration_duration': 10,     # seconds for baseline collection
    'sensor_window': 60,            # seconds for data collection windows
    'sampling_rate': 10,            # Hz (100ms intervals)
    'serial_port': self._get_serial_port(),
    'serial_baudrate': 9600,
    'music_folders': {
        'stress_relief': 'music/stress_relief/',
        'calming': 'music/calming/'
    }
}
```

### Hardware Initialization Process

#### `initialize_hardware()` Method

This method performs a comprehensive hardware setup:

1. **Sensor Initialization**:
   - GSR Sensor: Connects to Arduino via serial communication
   - HR Sensor: Initializes MAX30102 heart rate sensor
   
2. **Display Module**: Sets up LCD display for user feedback

3. **Audio Module**: Initializes music player with configured folders

4. **ML Module**: Loads pre-trained Random Forest stress prediction model

5. **Utility Modules**: 
   - DataCollector: Manages sensor data collection
   - FeatureExtractor: Processes raw data into ML features

6. **Readiness Testing**: Verifies all modules are operational

```python
def initialize_hardware(self) -> bool:
    try:
        # Initialize all modules
        self.gsr_sensor = GSRSensor(button_callback=self._handle_arduino_button_event, 
                                   message_callback=self._handle_arduino_message)
        self.hr_sensor = HRSensor()
        self.lcd = LCDDisplay()
        self.music_player = MusicPlayer(self.config['music_folders'])
        self.stress_predictor = StressPredictor()
        self.data_collector = DataCollector(sampling_rate=self.config['sampling_rate'])
        self.feature_extractor = FeatureExtractor()
        
        # Start sensors and verify readiness
        # ... verification logic ...
        
        return True
    except Exception as e:
        logger.error(f"Hardware initialization failed: {e}")
        return False
```

### Arduino Communication System

#### Message Handling Architecture

The system uses a callback-based communication pattern:

```python
# GSR Sensor handles Arduino communication
self.gsr_sensor = GSRSensor(
    button_callback=self._handle_arduino_button_event,
    message_callback=self._handle_arduino_message
)
```

#### Message Types and Handlers

1. **Button Events** (`_handle_arduino_button_event`):
   - `START`: Initiates therapy session
   - `STOP`: Terminates current session

2. **Status Messages** (`_handle_status_message`):
   - `STATUS:IDLE`: Arduino in idle state
   - `STATUS:CALIBRATING`: Arduino collecting baseline
   - `STATUS:SESSION_ACTIVE`: Arduino session active

3. **Calibration Messages** (`_handle_calibration_status`):
   - `CALIBRATION:STARTED`: Calibration initiated
   - `CALIBRATION:COMPLETE`: Calibration finished

4. **Baseline Data** (`_handle_baseline_data`):
   - `BASELINE:GSR:25.45,HR:75.2`: Sensor baseline values

5. **LCD Commands** (`_handle_lcd_message`):
   - `LCD:message`: Display updates from Arduino

### Calibration Process

#### `run_calibration()` Method

The calibration process establishes baseline measurements for personalized stress detection:

1. **GSR Calibration** (Arduino-managed):
   - Arduino collects 10 seconds of GSR data
   - Calculates baseline conductance value
   - Transmits baseline data to Raspberry Pi

2. **HR Calibration** (Pi-managed):
   - MAX30102 sensor calibration
   - User places finger on sensor
   - Collects 10 seconds of heart rate data
   - Calculates baseline BPM

```python
def run_calibration(self) -> bool:
    self.state = SystemState.CALIBRATING
    
    # Wait for Arduino GSR calibration
    calibration_timeout = 18  # seconds
    while time.time() - start_time < calibration_timeout:
        if self.gsr_sensor.has_baseline_data():
            break
        time.sleep(0.1)
    
    # HR sensor calibration
    self.lcd.display("Calibrating HR sensor...\nPress finger HARD on sensor")
    calibration_duration = 10  # seconds
    
    while time.time() - calibration_start < calibration_duration:
        hr_reading = self.hr_sensor.get_reading()
        if hr_reading and hr_reading.finger_detected and hr_reading.valid_bpm:
            baseline_bpm = self.hr_sensor.calculate_baseline(duration_seconds=5)
            if baseline_bpm:
                self.hr_sensor.set_baseline_data(baseline_bpm)
                break
        time.sleep(0.1)
    
    return True
```

### Therapy Session Logic

#### `run_therapy_session()` Method

The core therapy session implements a continuous feedback loop:

```python
def run_therapy_session(self):
    self.state = SystemState.SESSION_ACTIVE
    self.session_active = True
    
    while self.session_active and self.running:
        # Step 1: Collect sensor data window (60 seconds)
        sensor_window = self.data_collector.collect_window(
            gsr_sensor=self.gsr_sensor,
            hr_sensor=self.hr_sensor,
            window_size=self.config['sensor_window'],
            baseline=self.gsr_sensor.get_baseline_data()
        )
        
        # Step 2: Extract features (15 statistical measures)
        features = self.feature_extractor.extract_features(sensor_window)
        
        # Step 3: Predict stress level using ML model
        prediction = self.stress_predictor.predict(features)
        confidence = self.stress_predictor.get_confidence()
        
        # Step 4: Select appropriate music category
        music_category = self._map_prediction_to_music(prediction)
        song_path = self.music_player.select_song(music_category)
        
        # Step 5: Update display and start playback
        self._update_display_for_prediction(prediction, confidence)
        self.music_player.play(song_path)
        
        # Step 6: Handle playback with re-evaluation
        self._handle_playback_loop()
```

#### Music Selection Logic

```python
def _map_prediction_to_music(self, prediction: str) -> str:
    mapping = {
        'stress': 'stress_relief',    # Calming music for stress
        'no_stress': 'calming'       # Gentle music for relaxed state
    }
    return mapping.get(prediction.lower(), 'calming')
```

### Playback Management

#### `_handle_playback_loop()` Method

Manages music playback with intelligent re-evaluation:

```python
def _handle_playback_loop(self):
    re_evaluation_time = None
    
    while self.music_player.is_playing() and self.session_active:
        # Check for STOP button events
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
            re_evaluation_time = None
        
        time.sleep(0.1)
```

#### Re-evaluation Process

```python
def _perform_re_evaluation(self):
    # Collect shorter sensor sample (10 seconds)
    sensor_data = self.data_collector.collect_quick_sample(
        gsr_sensor=self.gsr_sensor,
        hr_sensor=self.hr_sensor,
        duration=10,
        baseline=self.gsr_sensor.get_baseline_data()
    )
    
    if sensor_data:
        # Extract features and make new prediction
        features = self.feature_extractor.extract_features(sensor_data)
        new_prediction = self.stress_predictor.predict(features)
        confidence = self.stress_predictor.get_confidence()
        
        # Update display with new status
        self._update_display_for_prediction(new_prediction, confidence)
```

### User Interface Management

#### Display Updates

```python
def _update_display_for_prediction(self, prediction: str, confidence: float):
    status_messages = {
        'stress': f"Stress detected ({confidence:.1f})\nPlaying calming music",
        'no_stress': f"Relaxed state ({confidence:.1f})\nPlaying gentle music"
    }
    
    category = self._map_prediction_to_music(prediction)
    message = status_messages.get(category, f"State: {prediction}\nPlaying music...")
    self.lcd.display(message)
```

### Event Handling System

#### Button Event Processing

```python
def handle_button_events(self):
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
```

### Main Application Loop

#### `main_loop()` Method

The primary event loop manages system operation:

```python
def main_loop(self):
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
```

### System Shutdown

#### `shutdown()` Method

Ensures clean termination of all system components:

```python
def shutdown(self):
    logger.info("Shutting down system...")
    self.running = False
    self.session_active = False
    
    if self.music_player:
        self.music_player.stop()
        
    if self.lcd:
        self.lcd.display("System shutting down...")
        
    logger.info("Shutdown complete")
```

### Main Entry Point

#### `main()` Function

The application entry point:

```python
def main():
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
```

### Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Arduino UNO   │    │  Raspberry Pi   │    │   ML Pipeline   │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │GSR Sensor   │ │───▶│ │Data Collector│ │───▶│ │Feature      │ │
│ │Button Input │ │    │ │             │ │    │ │Extractor    │ │
│ │LED Control  │ │    │ └─────────────┘ │    │ └─────────────┘ │
│ └─────────────┘ │    │                 │    │         │       │
│                 │    │ ┌─────────────┐ │    │         ▼       │
│                 │    │ │HR Sensor    │ │    │ ┌─────────────┐ │
│                 │    │ │(MAX30102)   │ │    │ │Stress       │ │
│                 │    │ └─────────────┘ │    │ │Predictor    │ │
│                 │    │                 │    │ └─────────────┘ │
│                 │    │ ┌─────────────┐ │    │         │       │
│                 │    │ │LCD Display  │ │    │         ▼       │
│                 │    │ │Music Player │ │    │ ┌─────────────┐ │
│                 │    │ └─────────────┘ │    │ │Music        │ │
│                 │    └─────────────────┘    │ │Selection    │ │
└─────────────────┘                          │ └─────────────┘ │
                                             └─────────────────┘
```

### Error Handling Strategy

The system implements comprehensive error handling:

1. **Hardware Initialization**: Graceful fallback if modules fail
2. **Sensor Communication**: Timeout handling for Arduino communication
3. **ML Predictions**: Default to "no_stress" if prediction fails
4. **Music Playback**: Continue session if song selection fails
5. **Calibration**: Use default baseline values if calibration fails

### Performance Considerations

1. **Sampling Rate**: 10 Hz (100ms intervals) balances responsiveness with accuracy
2. **Data Windows**: 60-second windows provide sufficient data for reliable predictions
3. **Re-evaluation**: Smart timing prevents unnecessary computation
4. **Threading**: Non-blocking button event handling
5. **Memory Management**: Limited prediction history to prevent memory leaks

### Security and Safety

1. **Input Validation**: All Arduino messages are cleaned and validated
2. **Resource Management**: Proper cleanup of hardware resources
3. **Graceful Degradation**: System continues operation with reduced functionality
4. **User Control**: Always-available STOP button for emergency termination

### Dependencies

- **Hardware Modules**: GSR, HR sensors, LCD, Music player
- **ML Components**: Stress predictor, Feature extractor, Data collector
- **Communication**: Serial communication with Arduino
- **Utilities**: Logging, threading, queue management

### Configuration Management

The system uses a centralized configuration approach:
- Platform-specific serial port detection
- Configurable calibration and sampling parameters
- Music folder path management
- Hardware-specific settings

This technical documentation provides a comprehensive overview of the main entry point's architecture, functionality, and implementation details for the Music Therapy Box system.
