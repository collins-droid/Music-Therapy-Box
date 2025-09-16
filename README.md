# Music Therapy Box

A Raspberry Pi 4B-powered Music Therapy Box that uses machine learning and biosensors (MAX30102 + GSR) to detect stress levels and play curated music in real time. Features Arduino button control, calibration, LCD feedback, and adaptive music selection logic.

## System Architecture

![System Architecture](sys_arch.png)

*System Architecture Diagram - Shows the complete hardware and software components, data flow, and communication protocols between Arduino UNO and Raspberry Pi 4B.*

## System Startup Flow

1. Run: `python main.py`
   ↓
2. System initializes all hardware
   ↓
3. LCD: "Press START to begin"
   ↓
4. User presses START button (Arduino)
   ↓
5. Arduino → Pi: "BUTTON:START"
   ↓
6. Pi starts calibration (10 seconds)
   ↓
7. Arduino collects baseline data
   ↓
8. Arduino → Pi: "BASELINE:GSR:25.45,HR:75.2"
   ↓
9. Pi starts therapy session
   ↓
10. Pi collects 60-second sensor windows
    ↓
11. Pi extracts 15 features
    ↓
12. Pi predicts stress level
    ↓
13. Pi plays appropriate music
    ↓
14. User presses STOP → Session ends

## Complete Post-Prediction Flow

After the system predicts stress level, here's the detailed process:

### Step-by-Step Process:

```
1. STRESS PREDICTION
   ↓
2. MAP TO MUSIC CATEGORY
   ↓
3. SELECT SONG
   ↓
4. UPDATE LCD DISPLAY
   ↓
5. START MUSIC PLAYBACK
   ↓
6. MONITOR PLAYBACK LOOP
   ↓
7. RE-EVALUATION (if needed)
   ↓
8. CONTINUE OR STOP
```

### Detailed Code Flow:

**1. Prediction Made:**
```python
prediction = self.stress_predictor.predict(features)  # Returns "stress" or "no_stress"
confidence = self.stress_predictor.get_confidence()   # Returns 0.0 to 1.0
```

**2. Map to Music Category:**
```python
music_category = self._map_prediction_to_music(prediction)
# "stress" → "stress" → music/stress_relief/
# "no_stress" → "no_stress" → music/calming/
```

**3. Select Random Song:**
```python
song_path = self.music_player.select_song(music_category)
# Randomly picks a file from the appropriate folder
```

**4. Update LCD Display:**
```python
self._update_display_for_prediction(prediction, confidence)
# Shows: "Stress detected (0.85)\nPlaying calming music"
# OR: "Relaxed state (0.92)\nPlaying gentle music"
```

**5. Start Music Playback:**
```python
self.music_player.play(song_path)
# Begins playing the selected song
```

**6. Playback Monitoring Loop:**
```python
while self.music_player.is_playing() and self.session_active:
    # Monitor for STOP button presses
    # Schedule re-evaluation 60 seconds before song ends
    # Handle user interactions
```

**7. Re-evaluation (Smart Feature):**
- **Triggers**: 60 seconds before current song ends
- **Process**: Collects 10-second sensor sample
- **Action**: Makes new prediction and updates display
- **Purpose**: Ensures music matches current stress level

**8. Session Continuation:**
- **If STOP pressed**: Session ends
- **If song ends**: Collects new 60-second window → New prediction → New song
- **If re-evaluation**: Updates display with new status

### Key Features:

1. **Adaptive Music Selection**: Music changes based on real-time stress detection
2. **Continuous Monitoring**: System keeps checking stress levels
3. **Smart Re-evaluation**: Updates prediction before song ends
4. **User Control**: STOP button always available
5. **Visual Feedback**: LCD shows current state and confidence
6. **Seamless Experience**: Continuous loop until user stops

### Complete Cycle:

```
Collect 60s Data → Extract Features → Predict Stress → Select Music → Play Song → 
Monitor Playback → Re-evaluate (if needed) → Repeat...
```

## 🎵 Music Categories

The system uses **binary classification** with 2 music categories:

### Model Output:
- **Label 0** (518 samples) → `"no_stress"` → `music/calming/`
- **Label 1** (482 samples) → `"stress"` → `music/stress_relief/`

### Music Folders:
- **`music/stress_relief/`** - Calming music for stress detection
- **`music/calming/`** - Gentle music for relaxed state

## 🛠️ Hardware Components

### Arduino UNO:
- GSR sensor (A0)
- START button (Pin 2)
- STOP button (Pin 3)
- LED1 - Calibration indicator (Pin 4)
- LED2 - Session indicator (Pin 5)

### Raspberry Pi:
- MAX30102 Heart Rate sensor (I2C)
- LCD Display (I2C)
- Music playback system
- Machine Learning processing

## Machine Learning Model

- **Algorithm**: Random Forest Classifier
- **Features**: 15 features (7 HR + 8 EDA)
- **Training Data**: 1000 synthetic samples
- **Accuracy**: Binary stress/no-stress classification
- **Model File**: `model/random_forest/stress_random_forest.pkl`

### How Random Forest Works

Random Forest is an ensemble machine learning algorithm that combines multiple decision trees to make more accurate predictions. Here's how it works in our stress detection system:

**1. Multiple Decision Trees**
- Creates 200 individual decision trees (n_estimators=200)
- Each tree is trained on a random subset of the training data
- Each tree uses a random subset of features for each split

**2. Training Process**
- Each tree learns different patterns in the HR and EDA data
- Trees vote on the final prediction (stress vs no_stress)
- Majority vote determines the final classification

**3. Feature Importance**
- Random Forest calculates which features are most important
- HR features (mean, std, range) and EDA features (mean, slope) typically rank highest
- Helps understand what physiological signals indicate stress

**4. Confidence Scoring**
- Provides probability scores for each prediction
- Higher confidence indicates more certain classification
- Used to determine music selection reliability

**5. Advantages for Stress Detection**
- Handles noise well (important for sensor data)
- Reduces overfitting through ensemble averaging
- Provides interpretable feature importance
- Works well with small datasets (1000 samples)

**6. Binary Classification**
- Output: 0 (no_stress) or 1 (stress)
- Threshold-based decision making
- Maps directly to music categories

## Getting Started

1. **Hardware Setup**: Connect Arduino and Pi components
2. **Music Files**: Add music files to `music/stress_relief/` and `music/calming/`
3. **Dependencies**: Install required Python packages
4. **Run**: `python main.py`
5. **Use**: Press START button to begin therapy session

The system creates a **continuous feedback loop** where the music adapts to your changing stress levels in real-time.

## Glossary

### Technical Terminologies

**ADC (Analog-to-Digital Converter)**
- Converts analog sensor signals to digital values
- Arduino uses 10-bit ADC (0-1023 range)
- Used for reading GSR sensor voltage levels

**Arduino UNO**
- Microcontroller board used for hardware interface
- Handles GSR sensor reading, button inputs, and LED control
- Communicates with Raspberry Pi via USB serial

**BPM (Beats Per Minute)**
- Heart rate measurement unit
- Normal resting heart rate: 60-100 BPM
- Used to measure cardiovascular activity

**EDA (Electrodermal Activity)**
- Electrical conductance of the skin
- Measured in microsiemens (μS)
- Increases during stress due to sweat gland activity
- Also known as GSR (Galvanic Skin Response)

**Feature Extraction**
- Process of computing statistical measures from raw sensor data
- 15 features extracted: mean, std, min, max, range, skew, kurtosis, slope
- Converts time-series data into ML-ready format

**GSR (Galvanic Skin Response)**
- Same as EDA - measures skin conductance
- Connected to Arduino analog pin A0
- Conductance increases with stress/arousal

**HR (Heart Rate)**
- Number of heartbeats per minute
- Measured by MAX30102 sensor on Raspberry Pi
- Key indicator of stress and cardiovascular health

**I2C (Inter-Integrated Circuit)**
- Communication protocol for connecting devices
- Used for MAX30102 sensor and LCD display
- Allows multiple devices on same bus

**joblib**
- Python library for saving/loading machine learning models
- Used to save trained Random Forest model as .pkl file
- Efficient serialization for scikit-learn models

**LCD (Liquid Crystal Display)**
- 16x2 character display connected to Raspberry Pi
- Shows system status, progress, and user feedback
- Communicates via I2C protocol

**MAX30102**
- Heart rate and SpO2 sensor
- Uses infrared and red LEDs with photodetector
- Connected to Raspberry Pi via I2C
- Provides real-time heart rate data

**ML (Machine Learning)**
- Artificial intelligence technique for pattern recognition
- Random Forest algorithm used for stress classification
- Trained on synthetic HR and EDA data

**pkl (Pickle)**
- Python file format for serializing objects
- Used to save trained Random Forest model
- Contains complete model parameters and structure

**Random Forest**
- Ensemble machine learning algorithm
- Uses multiple decision trees for classification
- Provides confidence scores and handles overfitting well

**Raspberry Pi 4B**
- Single-board computer running main application
- Handles ML processing, music playback, and LCD control
- Communicates with Arduino via USB serial

**Serial Communication**
- USB connection between Arduino and Raspberry Pi
- Baud rate: 9600
- Transmits button events, sensor data, and status messages

**SpO2 (Peripheral Oxygen Saturation)**
- Blood oxygen saturation percentage
- Measured by MAX30102 sensor
- Normal range: 95-100%

**Stress Classification**
- Binary classification: stress (1) vs no_stress (0)
- Based on HR and EDA features
- Confidence score indicates prediction certainty

**μS (Microsiemens)**
- Unit of electrical conductance
- Used for EDA/GSR measurements
- Higher values indicate increased skin conductance

### System-Specific Terms

**Baseline Data**
- Reference measurements collected during calibration
- Used for normalizing individual differences
- Collected over 10-second calibration period

**Calibration**
- Initial 10-second period to establish user baseline
- Collects 50 samples of GSR and HR data
- Required before therapy session begins

**Feature Vector**
- Array of 15 numerical features
- Input to machine learning model
- Contains statistical measures of HR and EDA data

**Music Categories**
- **stress_relief**: Calming music for stress detection
- **calming**: Gentle music for relaxed state
- Binary mapping based on ML prediction

**Re-evaluation**
- Smart feature that updates stress prediction
- Triggers 60 seconds before song ends
- Ensures music matches current stress level

**Sensor Window**
- 60-second data collection period
- Used for feature extraction and prediction
- Balances accuracy with responsiveness

**Therapy Session**
- Active period where system monitors and responds
- Continuous loop of data collection → prediction → music selection
- Continues until user presses STOP button 