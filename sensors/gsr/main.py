#!/usr/bin/env python3
"""
Raspberry Pi GSR Data Receiver
Receives GSR sensor data from Arduino via serial communication
"""
import serial
import time
import RPi.GPIO as GPIO



# Serial configuration
ser = serial.Serial("/dev/ttyUSB0", 9600)  # Arduino connected via USB
ser.baudrate = 9600




def process_gsr_data(gsr_value):
    """Process the received GSR data"""
    print(f"GSR Value: {gsr_value}")
    
    # Add your processing logic here
    # For example:
    if gsr_value > 500:
        print("High GSR detected!")
      
    elif gsr_value < 200:
        print("Low GSR detected!")
    else:
        print("Normal GSR range")

try:
    print("Starting GSR data collection...")
    print("Press Ctrl+C to stop")
    
    while True:
        if ser.in_waiting > 0:
            # Read data from Arduino
            raw_data = ser.readline().decode('utf-8').strip()
            print(f"Raw data received: {raw_data}")
            
            # Parse GSR data
            if raw_data.startswith("GSR:"):
                try:
                    gsr_value = int(raw_data.split(":")[1])
                    process_gsr_data(gsr_value)
                    
                    # Optional: Save to file
                    with open("gsr_data.txt", "a") as f:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"{timestamp},{gsr_value}\n")
                        
                except ValueError:
                    print(f"Error parsing GSR value from: {raw_data}")
        
        time.sleep(0.1)  # Small delay to prevent excessive CPU usage

except KeyboardInterrupt:
    print("\nStopping GSR data collection...")

finally:
    # Clean up
    ser.close()
    GPIO.cleanup()
    print("Serial connection closed and GPIO cleaned up.")