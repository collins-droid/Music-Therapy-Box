import smbus2
import time
import numpy as np

class MAX30102:
    # Register addresses
    REG_INTR_STATUS_1 = 0x00
    REG_INTR_STATUS_2 = 0x01
    REG_INTR_ENABLE_1 = 0x02
    REG_INTR_ENABLE_2 = 0x03
    REG_FIFO_WR_PTR = 0x04
    REG_OVF_COUNTER = 0x05
    REG_FIFO_RD_PTR = 0x06
    REG_FIFO_DATA = 0x07
    REG_FIFO_CONFIG = 0x08
    REG_MODE_CONFIG = 0x09
    REG_SPO2_CONFIG = 0x0A
    REG_LED1_PA = 0x0C  # Red LED
    REG_LED2_PA = 0x0D  # IR LED
    REG_PILOT_PA = 0x10
    REG_MULTI_LED_CTRL1 = 0x11
    REG_MULTI_LED_CTRL2 = 0x12
    REG_TEMP_INTR = 0x1F
    REG_TEMP_FRAC = 0x20
    REG_TEMP_CONFIG = 0x21
    REG_PROX_INT_THRESH = 0x30
    REG_REV_ID = 0xFE
    REG_PART_ID = 0xFF
    
    def __init__(self, i2c_bus=1, i2c_address=0x57):
        """
        Initialize MAX30102 sensor
        i2c_bus: I2C bus number (1 for Pi 4B)
        i2c_address: I2C address (0x57 is default)
        """
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self.bus = smbus2.SMBus(i2c_bus)
        
        # Check if sensor is connected
        try:
            part_id = self.bus.read_byte_data(self.i2c_address, self.REG_PART_ID)
            if part_id != 0x15:  # MAX30102 part ID
                raise Exception(f"Wrong part ID: {hex(part_id)}, expected 0x15")
            print("MAX30102 sensor detected successfully!")
        except Exception as e:
            raise Exception(f"Failed to initialize MAX30102: {e}")
            
        self.setup()
    
    def setup(self):
        """Configure the sensor"""
        # Reset the sensor
        self.bus.write_byte_data(self.i2c_address, self.REG_MODE_CONFIG, 0x40)
        time.sleep(0.1)
        
        # Configure FIFO
        self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_CONFIG, 0x4F)  # Sample averaging = 4, FIFO rollover = true, FIFO almost full = 15
        
        # Configure mode (SpO2 mode)
        self.bus.write_byte_data(self.i2c_address, self.REG_MODE_CONFIG, 0x03)
        
        # Configure SpO2 (ADC range = 4096nA, Sample rate = 100Hz, pulse width = 411μs)
        self.bus.write_byte_data(self.i2c_address, self.REG_SPO2_CONFIG, 0x27)
        
        # Configure LED pulse amplitudes
        self.bus.write_byte_data(self.i2c_address, self.REG_LED1_PA, 0x24)  # Red LED current
        self.bus.write_byte_data(self.i2c_address, self.REG_LED2_PA, 0x24)  # IR LED current
        
        # Clear FIFO
        self.clear_fifo()
        
    def clear_fifo(self):
        """Clear FIFO pointers"""
        self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_WR_PTR, 0x00)
        self.bus.write_byte_data(self.i2c_address, self.REG_OVF_COUNTER, 0x00)
        self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_RD_PTR, 0x00)
    
    def read_fifo(self):
        """Read data from FIFO"""
        # Read FIFO pointers
        wr_ptr = self.bus.read_byte_data(self.i2c_address, self.REG_FIFO_WR_PTR)
        rd_ptr = self.bus.read_byte_data(self.i2c_address, self.REG_FIFO_RD_PTR)
        
        # Calculate number of samples
        num_samples = (wr_ptr - rd_ptr) & 0x1F
        
        if num_samples == 0:
            return [], []
        
        red_data = []
        ir_data = []
        
        # Read samples
        for _ in range(num_samples):
            # Read 6 bytes (3 bytes red + 3 bytes IR)
            fifo_data = self.bus.read_i2c_block_data(self.i2c_address, self.REG_FIFO_DATA, 6)
            
            # Convert to 18-bit values
            red = (fifo_data[0] << 16) | (fifo_data[1] << 8) | fifo_data[2]
            red &= 0x3FFFF  # 18-bit mask
            
            ir = (fifo_data[3] << 16) | (fifo_data[4] << 8) | fifo_data[5]
            ir &= 0x3FFFF  # 18-bit mask
            
            red_data.append(red)
            ir_data.append(ir)
        
        return red_data, ir_data
    
    def read_temperature(self):
        """Read temperature from sensor"""
        # Enable temperature measurement
        self.bus.write_byte_data(self.i2c_address, self.REG_TEMP_CONFIG, 0x01)
        
        # Wait for measurement
        time.sleep(0.1)
        
        # Read temperature
        temp_int = self.bus.read_byte_data(self.i2c_address, self.REG_TEMP_INTR)
        temp_frac = self.bus.read_byte_data(self.i2c_address, self.REG_TEMP_FRAC)
        
        # Convert to Celsius
        temperature = temp_int + (temp_frac * 0.0625)
        
        return temperature
    
    def calculate_heart_rate(self, ir_data, sample_rate=100):
        """
        Simple heart rate calculation using peak detection
        ir_data: List of IR values
        sample_rate: Sampling rate in Hz
        """
        if len(ir_data) < 20:
            return None
            
        # Convert to numpy array and normalize
        signal = np.array(ir_data, dtype=float)
        signal = (signal - np.mean(signal)) / np.std(signal)
        
        # Simple peak detection
        peaks = []
        threshold = 0.5
        
        for i in range(1, len(signal) - 1):
            if signal[i] > threshold and signal[i] > signal[i-1] and signal[i] > signal[i+1]:
                peaks.append(i)
        
        if len(peaks) < 2:
            return None
            
        # Calculate heart rate
        peak_intervals = np.diff(peaks)
        if len(peak_intervals) == 0:
            return None
            
        avg_interval = np.mean(peak_intervals)
        heart_rate = (sample_rate * 60) / avg_interval
        
        # Filter unrealistic values
        if 40 <= heart_rate <= 200:
            return heart_rate
        else:
            return None
    
    def read_sensor_data(self, duration=5):
        """
        Read sensor data for specified duration
        duration: Time in seconds to collect data
        """
        print(f"Collecting data for {duration} seconds...")
        
        red_buffer = []
        ir_buffer = []
        start_time = time.time()
        
        while (time.time() - start_time) < duration:
            red_data, ir_data = self.read_fifo()
            red_buffer.extend(red_data)
            ir_buffer.extend(ir_data)
            time.sleep(0.01)  # 10ms delay
        
        return red_buffer, ir_buffer
    
    def get_measurement(self, duration=10):
        """Get a complete measurement including heart rate"""
        red_data, ir_data = self.read_sensor_data(duration)
        
        if not ir_data:
            return None
            
        heart_rate = self.calculate_heart_rate(ir_data)
        temperature = self.read_temperature()
        
        return {
            'heart_rate': heart_rate,
            'temperature': temperature,
            'red_samples': len(red_data),
            'ir_samples': len(ir_data),
            'red_avg': np.mean(red_data) if red_data else 0,
            'ir_avg': np.mean(ir_data) if ir_data else 0
        }

# Example usage
if __name__ == "__main__":
    try:
        sensor = MAX30102()
        print("Place your finger on the sensor...")
        time.sleep(2)
        
        # Take measurement
        measurement = sensor.get_measurement(duration=15)
        
        if measurement:
            print("\nMeasurement Results:")
            print(f"Heart Rate: {measurement['heart_rate']:.1f} BPM" if measurement['heart_rate'] else "Heart Rate: Unable to detect")
            print(f"Temperature: {measurement['temperature']:.1f}°C")
            print(f"Red LED samples: {measurement['red_samples']}")
            print(f"IR LED samples: {measurement['ir_samples']}")
            print(f"Average Red: {measurement['red_avg']:.0f}")
            print(f"Average IR: {measurement['ir_avg']:.0f}")
        else:
            print("No valid measurement obtained")
            
    except Exception as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nStopping...")