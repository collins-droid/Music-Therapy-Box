/*
Music Therapy Box - Arduino UNO Controller (Optimized)
@file music_therapy_arduino.ino
@date 2025
GSR sensor with conductance conversion, button control, and LED feedback
*/

// Pin definitions
const int GSR_PIN = A0;
const int START_BUTTON = 2;
const int STOP_BUTTON = 3;
const int LED1_PIN = 4; // Calibration indicator
const int LED2_PIN = 5; // Session indicator

// System states
enum SystemState {
  IDLE,
  CALIBRATING, 
  SESSION_ACTIVE
};

SystemState currentState = IDLE;

// Button variables
bool lastStartState = HIGH;
bool lastStopState = HIGH;

// Timing variables
unsigned long stateStartTime = 0;
const unsigned long CALIBRATION_DURATION = 10000; // 10 seconds

// Baseline collection
float gsrBaselineSum = 0.0;
float hrBaselineSum = 0.0;
int baselineReadings = 0;
const int BASELINE_SAMPLES = 50;

// GSR configuration
const float VCC = 5.0;
const float ADC_RESOLUTION = 1024.0;
const float VOLTAGE_DIVIDER_RATIO = 2.0;

void setup() {
  Serial.begin(9600);
  
  pinMode(START_BUTTON, INPUT_PULLUP);
  pinMode(STOP_BUTTON, INPUT_PULLUP);
  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  
  digitalWrite(LED1_PIN, LOW);
  digitalWrite(LED2_PIN, LOW);
  
  analogReference(DEFAULT);
  
  Serial.println("Music Therapy Box Arduino Ready");
  Serial.println("Press START button to begin calibration");
}

void loop() {
  handleButtons();
  
  switch(currentState) {
    case IDLE:
      handleIdleState();
      break;
    case CALIBRATING:
      handleCalibrationState();
      break;
    case SESSION_ACTIVE:
      handleSessionState();
      break;
  }
  
  delay(100);
}

void handleButtons() {
  bool currentStartState = digitalRead(START_BUTTON);
  bool currentStopState = digitalRead(STOP_BUTTON);
  
  // Start button pressed
  if (lastStartState == HIGH && currentStartState == LOW) {
    if (currentState == IDLE) {
      startCalibration();
    }
  }
  
  // Stop button pressed
  if (lastStopState == HIGH && currentStopState == LOW) {
    if (currentState != IDLE) {
      stopOperation();
    }
  }
  
  lastStartState = currentStartState;
  lastStopState = currentStopState;
}

void startCalibration() {
  currentState = CALIBRATING;
  stateStartTime = millis();
  
  // Reset baseline variables
  gsrBaselineSum = 0.0;
  hrBaselineSum = 0.0;
  baselineReadings = 0;
  
  // Turn on both LEDs during calibration
  digitalWrite(LED1_PIN, HIGH);
  digitalWrite(LED2_PIN, HIGH);
  
  Serial.println("BUTTON:START");
  Serial.println("CALIBRATION:STARTED");
  Serial.println("LCD:CALIBRATION_IN_PROGRESS");
}

void stopOperation() {
  currentState = IDLE;
  
  digitalWrite(LED1_PIN, LOW);
  digitalWrite(LED2_PIN, LOW);
  
  Serial.println("BUTTON:STOP");
  Serial.println("OPERATION:STOPPED");
}

void handleIdleState() {
  // Send idle status only occasionally to avoid flooding logs
  static unsigned long lastIdleMessage = 0;
  unsigned long currentTime = millis();
  
  // Send IDLE status only every 5 seconds
  if (currentTime - lastIdleMessage > 5000) {
    Serial.println("STATUS:IDLE");
    Serial.println("LCD:READY");
    lastIdleMessage = currentTime;
  }
}

void handleCalibrationState() {
  unsigned long elapsed = millis() - stateStartTime;
  unsigned long remaining = CALIBRATION_DURATION - elapsed;
  
  if (remaining > 0) {
    // Read GSR and collect baseline data
    float conductance = readGSRSensor();
    collectBaselineData(conductance);
    
    // Send data
    Serial.print("GSR_CONDUCTANCE:");
    Serial.println(conductance, 2);
  } else {
    // Calibration complete
    finishCalibration();
  }
}

void handleSessionState() {
  // Read GSR during active session
  float conductance = readGSRSensor();
  
  Serial.print("GSR_CONDUCTANCE:");
  Serial.println(conductance, 2);
  Serial.println("STATUS:SESSION_ACTIVE");
  
  // Only send LCD command occasionally to avoid flooding serial
  static unsigned long lastLcdMessage = 0;
  unsigned long currentTime = millis();
  if (currentTime - lastLcdMessage > 5000) { // Every 5 seconds
    Serial.println("LCD:SESSION_ACTIVE");
    lastLcdMessage = currentTime;
  }
}

float readGSRSensor() {
  // Average 10 readings for stability
  long sum = 0;
  for(int i = 0; i < 10; i++) {
    sum += analogRead(GSR_PIN);
    delay(2);
  }
  int average = sum / 10;
  
  // Convert to conductance
  float voltage = (average * VCC) / ADC_RESOLUTION;
  float gsrVoltage = voltage * VOLTAGE_DIVIDER_RATIO;
  
  if (gsrVoltage <= 0) return 0.0;
  
  float knownResistor = 10000.0; // 10k ohm
  float resistance = (VCC - gsrVoltage) * knownResistor / gsrVoltage;
  
  return (resistance > 0) ? (1000000.0 / resistance) : 0.0; // microsiemens
}

void collectBaselineData(float conductance) {
  if (baselineReadings < BASELINE_SAMPLES) {
    gsrBaselineSum += conductance;
    float simulatedHR = 70.0 + (conductance / 1000.0) * 10.0;
    hrBaselineSum += simulatedHR;
    baselineReadings++;
    
    if (baselineReadings % 10 == 0) {
      Serial.print("BASELINE_PROGRESS:");
      Serial.print(baselineReadings);
      Serial.print("/");
      Serial.println(BASELINE_SAMPLES);
    }
    
    // Finish calibration as soon as we have enough samples
    if (baselineReadings >= BASELINE_SAMPLES) {
      finishCalibration();
    }
  }
}

void finishCalibration() {
  // Calculate and send baseline averages
  if (baselineReadings > 0) {
    float gsrBaseline = gsrBaselineSum / baselineReadings;
    float hrBaseline = hrBaselineSum / baselineReadings;
    
    Serial.print("BASELINE:GSR:");
    Serial.print(gsrBaseline, 2);
    Serial.print(",HR:");
    Serial.println(hrBaseline, 2);
  }
  
  // Transition to session
  currentState = SESSION_ACTIVE;
  digitalWrite(LED1_PIN, LOW);  // Turn off calibration LED
  digitalWrite(LED2_PIN, HIGH); // Keep session LED on
  
  Serial.println("CALIBRATION:COMPLETE");
  Serial.println("SESSION:STARTED");
  Serial.println("LCD:CALIBRATION_COMPLETE");
}