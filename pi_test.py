#!/usr/bin/env python3
"""
Simple Pi Hardware Test
Test Arduino and I2C devices on Raspberry Pi
"""

import serial
import time
import subprocess

def test_arduino():
    """Test Arduino serial communication"""
    print("🔍 Testing Arduino at /dev/ttyUSB0...")
    
    try:
        ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=2)
        print("✅ Arduino port opened successfully")
        
        print("📡 Reading Arduino data for 10 seconds...")
        start_time = time.time()
        data_count = 0
        
        while time.time() - start_time < 10:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"📨 {line}")
                        data_count += 1
                except Exception as e:
                    print(f"⚠️  Decode error: {e}")
            
            time.sleep(0.1)
        
        ser.close()
        
        if data_count > 0:
            print(f"✅ Arduino is working! Received {data_count} messages")
        else:
            print("❌ Arduino not sending data")
            
    except Exception as e:
        print(f"❌ Arduino test failed: {e}")

def test_i2c():
    """Test I2C devices"""
    print("\n🔍 Testing I2C devices...")
    
    try:
        # Check if i2cdetect is available
        result = subprocess.run(['which', 'i2cdetect'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ i2cdetect not found. Install with: sudo apt install i2c-tools")
            return
        
        # Scan I2C bus
        print("📋 Scanning I2C bus...")
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("I2C Device Map:")
            print(result.stdout)
            
            # Check for expected devices
            output = result.stdout
            if '27' in output:
                print("✅ LCD Display found at address 0x27")
            else:
                print("❌ LCD Display NOT found at address 0x27")
            
            if '57' in output:
                print("✅ MAX30102 found at address 0x57")
            else:
                print("❌ MAX30102 NOT found at address 0x57")
        else:
            print(f"❌ I2C scan failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ I2C test failed: {e}")

def main():
    """Main test function"""
    print("🔧 PI HARDWARE TEST")
    print("=" * 50)
    
    test_arduino()
    test_i2c()
    
    print("\n" + "=" * 50)
    print("QUICK FIXES:")
    print("=" * 50)
    print("If Arduino not working:")
    print("  - Check USB cable")
    print("  - Reconnect Arduino")
    print("  - Check Arduino code")
    print("")
    print("If I2C devices missing:")
    print("  - Check wiring (SDA=GPIO2, SCL=GPIO3)")
    print("  - Check power supply")
    print("  - Enable I2C: sudo raspi-config")
    print("=" * 50)

if __name__ == "__main__":
    main()
