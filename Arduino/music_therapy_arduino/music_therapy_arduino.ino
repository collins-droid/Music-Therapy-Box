/*
Music Therapy Box - Arduino UNO Controller
@file music_therapy_arduino.ino
@date 2025
GSR sensor with conductance conversion, button control, and LED feedback
*/

// Pin definitions
const int GSR_PIN = A0;        // GSR sensor connected to analog pin A0
const int START_BUTTON = 2;    // START button connected to digital pin 2
const int STOP_BUTTON = 3;      // STOP button connected to digital pin 3
const int LED1_PIN = 4;         // LED1 (calibration indicator) on digital pin 4
const int LED2_PIN = 5;         // LED2 (session indicator) on digital pin 5

// GSR sensor variables
int gsrValue = 0;
int gsr_average = 0;
float conductance = 0.0;

// Button state variables
bool startButtonPressed = false;
bool stopButtonPressed = false;
bool lastStartState = HIGH;
bool lastStopState = HIGH;

// System state variables
bool calibrationActive = false;
bool sessionActive = false;
unsigned long calibrationStartTime = 0;
const unsigned long CALIBRATION_DURATION = 10000; // 10 seconds in milliseconds

// Baseline data collection variables
float gsrBaselineSum = 0.0;
float hrBaselineSum = 0.0;
int baselineReadings = 0;
const int BASELINE_SAMPLES = 50; // Collect 50 samples during calibration
float gsrBaseline = 0.0;
float hrBaseline = 0.0;

// GSR sensor configuration
const float VCC = 5.0;           // Supply voltage
const float ADC_RESOLUTION = 1024.0; // 10-bit ADC resolution
const float VOLTAGE_DIVIDER_RATIO = 2.0; // GSR module 2 has built-in voltage divider

void setup() {
  Serial.begin(9600);
  
  // Configure pins
  pinMode(START_BUTTON, INPUT_PULLUP);
  pinMode(STOP_BUTTON, INPUT_PULLUP);
  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  
  // Initialize LEDs to OFF
  digitalWrite(LED1_PIN, LOW);
  digitalWrite(LED2_PIN, LOW);
  
  // Set analog reference to 5V
  analogReference(DEFAULT);
  
  Serial.println("Music Therapy Box Arduino Ready");
  Serial.println("Press START button to begin calibration");
}

void loop() {
  // Read button states
  readButtons();
  
  // Handle button events
  handleButtonEvents();
  
  // Read GSR sensor
  readGSRSensor();
  
  // Handle system states
  handleCalibration();
  handleSession();
  
  // Send data to Raspberry Pi
  sendDataToPi();
  
  delay(100); // Main loop delay
}

void readButtons() {
  // Read current button states
  bool currentStartState = digitalRead(START_BUTTON);
  bool currentStopState = digitalRead(STOP_BUTTON);
  
  // Detect button press (LOW when pressed due to INPUT_PULLUP)
  startButtonPressed = (lastStartState == HIGH && currentStartState == LOW);
  stopButtonPressed = (lastStopState == HIGH && currentStopState == LOW);
  
  // Update last states
  lastStartState = currentStartState;
  lastStopState = currentStopState;
}

void handleButtonEvents() {
  if (startButtonPressed) {
    if (!calibrationActive && !sessionActive) {
      // Start calibration
      startCalibration();
    }
  }
  
  if (stopButtonPressed) {
    if (calibrationActive || sessionActive) {
      // Stop current operation
      stopOperation();
    }
  }
}

void startCalibration() {
  calibrationActive = true;
  sessionActive = false;
  calibrationStartTime = millis();
  
  // Reset baseline collection variables
  gsrBaselineSum = 0.0;
  hrBaselineSum = 0.0;
  baselineReadings = 0;
  
  // Turn on LED1 (calibration indicator) and LED2 (session indicator)
  // LED2 remains ON during calibration as requested
  digitalWrite(LED1_PIN, HIGH);
  digitalWrite(LED2_PIN, HIGH);
  
  Serial.println("BUTTON:START");
  Serial.println("CALIBRATION:STARTED");
  Serial.println("LCD:CALIBRATION_IN_PROGRESS");
}

void stopOperation() {
  calibrationActive = false;
  sessionActive = false;
  
  // Turn off all LEDs
  digitalWrite(LED1_PIN, LOW);
  digitalWrite(LED2_PIN, LOW);
  
  Serial.println("BUTTON:STOP");
  Serial.println("OPERATION:STOPPED");
}

void handleCalibration() {
  if (calibrationActive) {
    unsigned long elapsed = millis() - calibrationStartTime;
    
    // Collect baseline data during calibration
    collectBaselineData();
    
    // Update LCD with progress
    unsigned long remaining = CALIBRATION_DURATION - elapsed;
    if (remaining > 0) {
      Serial.print("LCD:CALIBRATION_PROGRESS:");
      Serial.println(remaining / 1000); // Send remaining seconds
    }
    
    if (elapsed >= CALIBRATION_DURATION) {
      // Calculate baseline averages
      if (baselineReadings > 0) {
        gsrBaseline = gsrBaselineSum / baselineReadings;
        hrBaseline = hrBaselineSum / baselineReadings;
        
        // Send baseline data to Raspberry Pi
        Serial.print("BASELINE:GSR:");
        Serial.print(gsrBaseline, 2);
        Serial.print(",HR:");
        Serial.println(hrBaseline, 2);
      }
      
      // Calibration complete
      calibrationActive = false;
      sessionActive = true;
      
      // Keep LED2 ON (session indicator), turn off LED1
      digitalWrite(LED1_PIN, LOW);
      digitalWrite(LED2_PIN, HIGH);
      
      Serial.println("CALIBRATION:COMPLETE");
      Serial.println("SESSION:STARTED");
      Serial.println("LCD:CALIBRATION_COMPLETE");
    }
  }
}

void handleSession() {
  if (sessionActive) {
    // Session is active - LED2 remains ON
    //LEd 2 is the yellow led thus it should remain ON during the session
    // Additional session logic can be added here
  }
}

void readGSRSensor() {
  // Read GSR sensor with averaging
  long gsrSum = 0;
  for(int i = 0; i < 10; i++) {
    gsrValue = analogRead(GSR_PIN);
    gsrSum += gsrValue;
    delay(2);
  }
  gsr_average = gsrSum / 10;
  
  // Convert ADC reading to conductance
  conductance = calculateConductance(gsr_average);
}

void collectBaselineData() {
  // Collect baseline data during calibration
  if (calibrationActive && baselineReadings < BASELINE_SAMPLES) {
    // Add GSR conductance to baseline sum
    gsrBaselineSum += conductance;
    
    // MAX30102 Heart Rate Sensor is connected to Raspberry Pi via I2C
    // Arduino only collects GSR data and sends it to Pi
    // Pi will collect actual HR data from MAX30102 and combine with GSR baseline
    // For Arduino baseline collection, we simulate HR based on GSR patterns
    float simulatedHR = 70.0 + (conductance / 1000.0) * 10.0; // Simulate HR variation
    hrBaselineSum += simulatedHR;
    
    baselineReadings++;
    
    // Send progress update every 10 samples
    if (baselineReadings % 10 == 0) {
      Serial.print("BASELINE_PROGRESS:");
      Serial.print(baselineReadings);
      Serial.print("/");
      Serial.println(BASELINE_SAMPLES);
    }
  }
}

float calculateConductance(int adcValue) {
  // Convert ADC reading to voltage
  float voltage = (adcValue * VCC) / ADC_RESOLUTION;
  
  // Calculate resistance using voltage divider formula
  // Vout = Vin * R2 / (R1 + R2)
  // For GSR module 2 with built-in voltage divider
  float resistance = 0.0;
  
  if (voltage > 0) {
    // Assuming the voltage divider has equal resistors (R1 = R2)
    // Vout = Vin * R2 / (R1 + R2) = Vin * R / (R + R) = Vin / 2
    // So if we measure Vout, the actual voltage across GSR is 2 * Vout
    float gsrVoltage = voltage * VOLTAGE_DIVIDER_RATIO;
    
    // Calculate resistance: R = (VCC - Vgsr) / (Vgsr / R_known)
    // For GSR module 2, we need to account for the known resistor in the divider
    float knownResistor = 10000.0; // 10k ohm (typical value for GSR module 2)
    resistance = (VCC - gsrVoltage) * knownResistor / gsrVoltage;
  }
  
  // Convert resistance to conductance (microsiemens)
  float conductance_us = 0.0;
  if (resistance > 0) {
    conductance_us = 1000000.0 / resistance; // Convert to microsiemens
  }
  
  return conductance_us;
}

void sendDataToPi() {
  // Send GSR conductance data (Arduino already computed this)
  Serial.print("GSR_CONDUCTANCE:");
  Serial.println(conductance, 2);
  
  // Send system status
  if (calibrationActive) {
    unsigned long elapsed = millis() - calibrationStartTime;
    unsigned long remaining = CALIBRATION_DURATION - elapsed;
    Serial.print("STATUS:CALIBRATING,REMAINING:");
    Serial.println(remaining);
    
    // Send LCD update for calibration progress
    if (remaining > 0) {
      Serial.print("LCD:CALIBRATION_PROGRESS:");
      Serial.println(remaining / 1000);
    }
  } else if (sessionActive) {
    Serial.println("STATUS:SESSION_ACTIVE");
    Serial.println("LCD:SESSION_ACTIVE");
  } else {
    Serial.println("STATUS:IDLE");
    Serial.println("LCD:READY");
  }
  
  // Send baseline data if available
  if (gsrBaseline > 0 && hrBaseline > 0) {
    Serial.print("BASELINE_DATA:GSR:");
    Serial.print(gsrBaseline, 2);
    Serial.print(",HR:");
    Serial.println(hrBaseline, 2);
  }
}