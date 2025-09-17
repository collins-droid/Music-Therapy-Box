#!/usr/bin/env python3
"""
Hardware Diagnostic Script
Check hardware connections and troubleshoot issues
"""

import serial
import serial.tools.list_ports
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_serial_ports():
    """Check available serial ports"""
    print("=" * 60)
    print("SERIAL PORTS CHECK")
    print("=" * 60)
    
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("❌ No serial ports found!")
        return []
    
    print(f"Found {len(ports)} serial port(s):")
    for port in ports:
        print(f"  📍 {port.device} - {port.description}")
        print(f"     VID:PID = {port.vid}:{port.pid}")
        print(f"     Serial = {port.serial_number}")
    
    return ports

def test_serial_connection(port_name):
    """Test serial connection to a specific port"""
    print(f"\n🔍 Testing connection to {port_name}...")
    
    try:
        # Try to open the port
        ser = serial.Serial(port_name, 9600, timeout=2)
        print(f"✅ Successfully opened {port_name}")
        
        # Try to read some data
        print("📡 Reading data for 5 seconds...")
        start_time = time.time()
        data_received = False
        
        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"📨 Received: {line}")
                        data_received = True
                except Exception as e:
                    print(f"⚠️  Decode error: {e}")
            
            time.sleep(0.1)
        
        if not data_received:
            print("⚠️  No data received (Arduino might not be sending data)")
        
        ser.close()
        print(f"✅ Connection test completed for {port_name}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to {port_name}: {e}")
        return False

def check_i2c_devices():
    """Check I2C devices (for LCD and MAX30102)"""
    print("\n" + "=" * 60)
    print("I2C DEVICES CHECK")
    print("=" * 60)
    
    try:
        # Check if i2cdetect is available
        result = subprocess.run(['which', 'i2cdetect'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ i2cdetect not found. Install with: sudo apt install i2c-tools")
            return
        
        # Scan I2C bus
        print("🔍 Scanning I2C bus...")
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("📋 I2C Device Map:")
            print(result.stdout)
            
            # Check for expected devices
            output = result.stdout
            if '27' in output:
                print("✅ LCD Display found at address 0x27")
            else:
                print("❌ LCD Display not found at address 0x27")
            
            if '57' in output:
                print("✅ MAX30102 found at address 0x57")
            else:
                print("❌ MAX30102 not found at address 0x57")
        else:
            print(f"❌ I2C scan failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ I2C check failed: {e}")

def check_usb_devices():
    """Check USB devices"""
    print("\n" + "=" * 60)
    print("USB DEVICES CHECK")
    print("=" * 60)
    
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📋 USB Devices:")
            print(result.stdout)
        else:
            print(f"❌ USB check failed: {result.stderr}")
    except Exception as e:
        print(f"❌ USB check failed: {e}")

def main():
    """Main diagnostic function"""
    print("🔧 HARDWARE DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # Check serial ports
    ports = check_serial_ports()
    
    # Test each serial port
    if ports:
        for port in ports:
            test_serial_connection(port.device)
    
    # Check I2C devices
    check_i2c_devices()
    
    # Check USB devices
    check_usb_devices()
    
    print("\n" + "=" * 60)
    print("TROUBLESHOOTING TIPS")
    print("=" * 60)
    print("🔧 For GSR/Arduino issues:")
    print("   - Check USB cable connection")
    print("   - Try unplugging and reconnecting Arduino")
    print("   - Check if Arduino is programmed correctly")
    print("   - Verify Arduino is sending data")
    print("")
    print("🔧 For LCD issues:")
    print("   - Check I2C wiring (SDA, SCL, VCC, GND)")
    print("   - Verify LCD address (should be 0x27)")
    print("   - Check power supply")
    print("   - Try: sudo i2cdetect -y 1")
    print("")
    print("🔧 For MAX30102 issues:")
    print("   - Check I2C wiring")
    print("   - Verify sensor address (should be 0x57)")
    print("   - Check power supply")
    print("=" * 60)

if __name__ == "__main__":
    main()
