#!/usr/bin/env python3
"""
Raspberry Pi Temperature Data Receiver
Receives HW498 temperature sensor data from Arduino via serial communication
"""
import serial
import time
import RPi.GPIO as GPIO

# Serial configuration
ser = serial.Serial("/dev/ttyUSB0", 9600)  # Arduino connected via USB
ser.baudrate = 9600



def process_temperature_data(temp_value):
    """Process the received temperature data"""
    print(f"Temperature: {temp_value:.2f}°C ({temp_value * 9/5 + 32:.2f}°F)")
    
    # Add your processing logic here
    if temp_value > 30.0:
        print(" High temperature detected!")
       
    elif temp_value < 15.0:
        print(" Low temperature detected!")
       
    else:
        print("🌡️  Normal temperature range")

try:
    print("Starting HW498 temperature data collection...")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    while True:
        if ser.in_waiting > 0:
            # Read data from Arduino
            raw_data = ser.readline().decode('utf-8').strip()
            
            # Parse temperature data
            if raw_data.startswith("TEMP:"):
                try:
                    temp_value = float(raw_data.split(":")[1])
                    process_temperature_data(temp_value)
                    
                    # Optional: Save to CSV file
                    with open("temperature_data.csv", "a") as f:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"{timestamp},{temp_value:.2f}\n")
                        
                except (ValueError, IndexError) as e:
                    print(f"Error parsing temperature value from: {raw_data} - {e}")
            else:
                print(f"Unknown data format: {raw_data}")
        
        time.sleep(0.1)  # Small delay to prevent excessive CPU usage

except KeyboardInterrupt:
    print("\n" + "="*50)
    print("Stopping temperature data collection...")

finally:
    # Clean up
    ser.close()
    GPIO.cleanup()
    print("Serial connection closed and GPIO cleaned up.")