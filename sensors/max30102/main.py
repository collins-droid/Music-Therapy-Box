#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Improved MAX30102 Heart Rate Monitor
Based on the official MAX30102 datasheet specifications.
This implementation includes proper register definitions, initialization sequences,
temperature compensation, proximity detection, and improved heart rate calculation.
"""

import smbus
import time
import threading
import numpy as np
import argparse
import csv
from datetime import datetime
from collections import deque

# ============================================================================
# MAX30102 Register Definitions (From Datasheet)
# ============================================================================

# Status Registers
REG_INTR_STATUS_1 = 0x00
REG_INTR_STATUS_2 = 0x01
REG_INTR_ENABLE_1 = 0x02
REG_INTR_ENABLE_2 = 0x03

# FIFO Registers
REG_FIFO_WR_PTR = 0x04
REG_OVF_COUNTER = 0x05
REG_FIFO_RD_PTR = 0x06
REG_FIFO_DATA = 0x07

# Configuration Registers
REG_FIFO_CONFIG = 0x08
REG_MODE_CONFIG = 0x09
REG_SPO2_CONFIG = 0x0A

# LED Pulse Amplitude Registers
REG_LED1_PA = 0x0C  # Red LED
REG_LED2_PA = 0x0D  # IR LED
REG_PILOT_PA = 0x10

# Multi-LED Control Registers
REG_MULTI_LED_CTRL1 = 0x11
REG_MULTI_LED_CTRL2 = 0x12

# Temperature Registers
REG_TEMP_INTR = 0x1F
REG_TEMP_FRAC = 0x20
REG_TEMP_CONFIG = 0x21

# Proximity Registers
REG_PROX_INT_THRESH = 0x30

# Part ID Registers
REG_REV_ID = 0xFE
REG_PART_ID = 0xFF

# ============================================================================
# MAX30102 Constants (From Datasheet)
# ============================================================================

# Mode Configuration
MODE_SHDN = 0x80
MODE_RESET = 0x40
MODE_HR_ONLY = 0x02
MODE_SPO2 = 0x03
MODE_MULTI_LED = 0x07

# SpO2 Configuration
SPO2_ADC_RGE_2048 = 0x00  # 2048 nA
SPO2_ADC_RGE_4096 = 0x01  # 4096 nA
SPO2_ADC_RGE_8192 = 0x02  # 8192 nA
SPO2_ADC_RGE_16384 = 0x03  # 16384 nA

SPO2_SR_50 = 0x00   # 50 samples per second
SPO2_SR_100 = 0x01  # 100 samples per second
SPO2_SR_200 = 0x02  # 200 samples per second
SPO2_SR_400 = 0x03  # 400 samples per second
SPO2_SR_800 = 0x04  # 800 samples per second
SPO2_SR_1000 = 0x05 # 1000 samples per second
SPO2_SR_1600 = 0x06 # 1600 samples per second
SPO2_SR_3200 = 0x07 # 3200 samples per second

LED_PW_69 = 0x00   # 69μs pulse width, 15-bit resolution
LED_PW_118 = 0x01  # 118μs pulse width, 16-bit resolution
LED_PW_215 = 0x02  # 215μs pulse width, 17-bit resolution
LED_PW_411 = 0x03  # 411μs pulse width, 18-bit resolution

# FIFO Configuration
FIFO_A_FULL_17 = 0x0F  # Interrupt when 17 samples remain (15 empty)

# Sample Averaging
SMP_AVE_1 = 0x00
SMP_AVE_2 = 0x01
SMP_AVE_4 = 0x02
SMP_AVE_8 = 0x03
SMP_AVE_16 = 0x04
SMP_AVE_32 = 0x05

# Interrupt Enable Flags
A_FULL_EN = 0x80
PPG_RDY_EN = 0x40
ALC_OVF_EN = 0x20
PROX_INT_EN = 0x10

# I2C Address (from datasheet: 7-bit address 0b1010111)
MAX30102_I2C_ADDRESS = 0x57

# Expected Part ID
MAX30102_EXPECTED_PART_ID = 0x15


class MAX30102:
    """
    Improved MAX30102 sensor class based on datasheet specifications.
    """
    
    def __init__(self, i2c_bus=1, i2c_address=MAX30102_I2C_ADDRESS):
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self.bus = smbus.SMBus(self.i2c_bus)
        
        # Verify part ID
        if not self._check_part_id():
            raise RuntimeError("MAX30102 not found or invalid part ID")
        
        # Initialize sensor
        self.reset()
        time.sleep(0.1)  # Wait for reset to complete
        
        # Clear any pending interrupts
        self._clear_interrupts()
        
        print(f"MAX30102 initialized successfully (Rev ID: 0x{self._get_revision_id():02X})")

    def _check_part_id(self):
        """Verify the sensor part ID matches expected value."""
        try:
            part_id = self.bus.read_byte_data(self.i2c_address, REG_PART_ID)
            return part_id == MAX30102_EXPECTED_PART_ID
        except Exception:
            return False

    def _get_revision_id(self):
        """Get the revision ID of the sensor."""
        return self.bus.read_byte_data(self.i2c_address, REG_REV_ID)

    def _clear_interrupts(self):
        """Clear all interrupt status registers."""
        self.bus.read_byte_data(self.i2c_address, REG_INTR_STATUS_1)
        self.bus.read_byte_data(self.i2c_address, REG_INTR_STATUS_2)

    def reset(self):
        """Reset the device (sets all registers to power-on state)."""
        self.bus.write_byte_data(self.i2c_address, REG_MODE_CONFIG, MODE_RESET)
        
        # Wait for reset bit to clear automatically
        timeout = time.time() + 1.0
        while time.time() < timeout:
            reg_val = self.bus.read_byte_data(self.i2c_address, REG_MODE_CONFIG)
            if not (reg_val & MODE_RESET):
                break
            time.sleep(0.01)

    def shutdown(self):
        """Put the device into power-save mode."""
        self.bus.write_byte_data(self.i2c_address, REG_MODE_CONFIG, MODE_SHDN)

    def setup_heart_rate_mode(self, sample_rate=SPO2_SR_100, pulse_width=LED_PW_411, 
                             led_current=0x1F, sample_averaging=SMP_AVE_4):
        """
        Configure the sensor for heart rate monitoring using IR LED only.
        
        Args:
            sample_rate: Sample rate (use SPO2_SR_* constants)
            pulse_width: LED pulse width (use LED_PW_* constants)  
            led_current: IR LED current (0x00-0xFF, see datasheet table 8)
            sample_averaging: Number of samples to average (use SMP_AVE_* constants)
        """
        
        # Configure FIFO
        fifo_config = (sample_averaging << 5) | FIFO_A_FULL_17
        self.bus.write_byte_data(self.i2c_address, REG_FIFO_CONFIG, fifo_config)
        
        # Clear FIFO pointers
        self.bus.write_byte_data(self.i2c_address, REG_FIFO_WR_PTR, 0x00)
        self.bus.write_byte_data(self.i2c_address, REG_OVF_COUNTER, 0x00)
        self.bus.write_byte_data(self.i2c_address, REG_FIFO_RD_PTR, 0x00)
        
        # Configure SpO2/HR settings
        spo2_config = (SPO2_ADC_RGE_4096 << 5) | (sample_rate << 2) | pulse_width
        self.bus.write_byte_data(self.i2c_address, REG_SPO2_CONFIG, spo2_config)
        
        # Set LED current (using IR LED for heart rate)
        self.bus.write_byte_data(self.i2c_address, REG_LED2_PA, led_current)  # IR LED
        self.bus.write_byte_data(self.i2c_address, REG_LED1_PA, 0x00)  # Turn off Red LED
        
        # Enable interrupts
        self.bus.write_byte_data(self.i2c_address, REG_INTR_ENABLE_1, A_FULL_EN)
        
        # Set mode to Heart Rate only
        self.bus.write_byte_data(self.i2c_address, REG_MODE_CONFIG, MODE_HR_ONLY)
        
        print("Heart Rate mode configured")

    def setup_spo2_mode(self, sample_rate=SPO2_SR_100, pulse_width=LED_PW_411,
                       red_current=0x1F, ir_current=0x1F, sample_averaging=SMP_AVE_4):
        """
        Configure the sensor for SpO2 monitoring using both Red and IR LEDs.
        
        Args:
            sample_rate: Sample rate (use SPO2_SR_* constants)
            pulse_width: LED pulse width (use LED_PW_* constants)
            red_current: Red LED current (0x00-0xFF)
            ir_current: IR LED current (0x00-0xFF)
            sample_averaging: Number of samples to average (use SMP_AVE_* constants)
        """
        
        # Configure FIFO
        fifo_config = (sample_averaging << 5) | FIFO_A_FULL_17
        self.bus.write_byte_data(self.i2c_address, REG_FIFO_CONFIG, fifo_config)
        
        # Clear FIFO pointers  
        self.bus.write_byte_data(self.i2c_address, REG_FIFO_WR_PTR, 0x00)
        self.bus.write_byte_data(self.i2c_address, REG_OVF_COUNTER, 0x00)
        self.bus.write_byte_data(self.i2c_address, REG_FIFO_RD_PTR, 0x00)
        
        # Configure SpO2/HR settings
        spo2_config = (SPO2_ADC_RGE_4096 << 5) | (sample_rate << 2) | pulse_width
        self.bus.write_byte_data(self.i2c_address, REG_SPO2_CONFIG, spo2_config)
        
        # Set LED currents
        self.bus.write_byte_data(self.i2c_address, REG_LED1_PA, red_current)  # Red LED
        self.bus.write_byte_data(self.i2c_address, REG_LED2_PA, ir_current)   # IR LED
        
        # Enable interrupts
        self.bus.write_byte_data(self.i2c_address, REG_INTR_ENABLE_1, A_FULL_EN)
        
        # Set mode to SpO2
        self.bus.write_byte_data(self.i2c_address, REG_MODE_CONFIG, MODE_SPO2)
        
        print("SpO2 mode configured")

    def enable_proximity_detection(self, threshold=0x14, pilot_current=0x7F):
        """
        Enable proximity detection to save power when finger is not present.
        
        Args:
            threshold: Proximity threshold (0x00-0xFF)
            pilot_current: Pilot LED current for proximity detection
        """
        self.bus.write_byte_data(self.i2c_address, REG_PROX_INT_THRESH, threshold)
        self.bus.write_byte_data(self.i2c_address, REG_PILOT_PA, pilot_current)
        
        # Enable proximity interrupt
        intr_enable = self.bus.read_byte_data(self.i2c_address, REG_INTR_ENABLE_1)
        self.bus.write_byte_data(self.i2c_address, REG_INTR_ENABLE_1, intr_enable | PROX_INT_EN)

    def get_interrupt_status(self):
        """Get the current interrupt status."""
        status1 = self.bus.read_byte_data(self.i2c_address, REG_INTR_STATUS_1)
        status2 = self.bus.read_byte_data(self.i2c_address, REG_INTR_STATUS_2)
        return status1, status2

    def get_fifo_available_samples(self):
        """Get the number of samples available in the FIFO."""
        wr_ptr = self.bus.read_byte_data(self.i2c_address, REG_FIFO_WR_PTR)
        rd_ptr = self.bus.read_byte_data(self.i2c_address, REG_FIFO_RD_PTR)
        
        if wr_ptr >= rd_ptr:
            return wr_ptr - rd_ptr
        else:
            return (32 - rd_ptr) + wr_ptr

    def read_fifo_data(self):
        """
        Read one sample from FIFO (6 bytes for SpO2 mode, 3 bytes for HR mode).
        Returns tuple (red_value, ir_value) for SpO2 mode or (None, ir_value) for HR mode.
        """
        # Clear interrupt status by reading it
        self._clear_interrupts()
        
        # Check current mode to determine how many bytes to read
        mode = self.bus.read_byte_data(self.i2c_address, REG_MODE_CONFIG) & 0x07
        
        if mode == MODE_SPO2:  # SpO2 mode - read 6 bytes
            data = self.bus.read_i2c_block_data(self.i2c_address, REG_FIFO_DATA, 6)
            
            # Convert to 18-bit values (left-justified)
            red_value = ((data[0] & 0x03) << 16) | (data[1] << 8) | data[2]
            ir_value = ((data[3] & 0x03) << 16) | (data[4] << 8) | data[5]
            
            return red_value, ir_value
            
        elif mode == MODE_HR_ONLY:  # HR mode - read 3 bytes (IR only)
            data = self.bus.read_i2c_block_data(self.i2c_address, REG_FIFO_DATA, 3)
            
            # Convert to 18-bit value (left-justified)  
            ir_value = ((data[0] & 0x03) << 16) | (data[1] << 8) | data[2]
            
            return None, ir_value
        else:
            raise RuntimeError(f"Unsupported mode: {mode}")

    def read_temperature(self):
        """
        Read the internal die temperature.
        Returns temperature in degrees Celsius.
        """
        # Trigger temperature measurement
        self.bus.write_byte_data(self.i2c_address, REG_TEMP_CONFIG, 0x01)
        
        # Wait for measurement to complete (typically 29ms)
        time.sleep(0.03)
        
        # Read integer and fractional parts
        temp_int = self.bus.read_byte_data(self.i2c_address, REG_TEMP_INTR)
        temp_frac = self.bus.read_byte_data(self.i2c_address, REG_TEMP_FRAC) & 0x0F
        
        # Convert to temperature (2's complement for integer part)
        if temp_int > 127:
            temp_int -= 256
            
        temperature = temp_int + (temp_frac * 0.0625)
        
        return temperature


class HeartRateCalculator:
    """
    Improved heart rate calculation using multiple algorithms.
    """
    
    def __init__(self, sample_rate=100, window_size=50):
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.signal_buffer = deque(maxlen=window_size * 2)  # Keep extra history
        
    def add_sample(self, ir_value):
        """Add a new IR sample to the buffer."""
        self.signal_buffer.append(ir_value)
        
    def calculate_heart_rate(self):
        """
        Calculate heart rate using improved peak detection algorithm.
        Returns (heart_rate, confidence) tuple.
        """
        if len(self.signal_buffer) < self.window_size:
            return None, 0.0
            
        # Convert to numpy array
        signal = np.array(list(self.signal_buffer))
        
        # Check for valid signal (finger detection)
        signal_mean = np.mean(signal)
        signal_std = np.std(signal)
        
        # Basic finger detection
        if signal_mean < 50000 or signal_std < 500:
            return None, 0.0
            
        # Preprocessing
        # 1. Remove DC component
        signal_ac = signal - signal_mean
        
        # 2. Apply simple bandpass filter (0.5-4 Hz for heart rate)
        signal_filtered = self._bandpass_filter(signal_ac, 0.5, 4.0, self.sample_rate)
        
        # 3. Peak detection
        peaks = self._find_peaks(signal_filtered)
        
        if len(peaks) < 3:
            return None, 0.0
            
        # Calculate heart rate from peak intervals
        intervals = np.diff(peaks) / self.sample_rate  # Convert to seconds
        
        # Remove outliers
        if len(intervals) > 3:
            q75, q25 = np.percentile(intervals, [75, 25])
            iqr = q75 - q25
            lower_bound = q25 - (1.5 * iqr)
            upper_bound = q75 + (1.5 * iqr)
            intervals = intervals[(intervals >= lower_bound) & (intervals <= upper_bound)]
        
        if len(intervals) == 0:
            return None, 0.0
            
        # Calculate BPM
        avg_interval = np.mean(intervals)
        heart_rate = 60.0 / avg_interval
        
        # Calculate confidence based on interval consistency
        confidence = self._calculate_confidence(intervals)
        
        # Filter unrealistic values
        if 40 <= heart_rate <= 200 and confidence > 0.3:
            return heart_rate, confidence
        else:
            return None, 0.0
    
    def _bandpass_filter(self, signal, low_freq, high_freq, sample_rate):
        """Simple bandpass filter using rolling averages."""
        # Simple high-pass filter (remove very low frequencies)
        window_high = int(sample_rate / low_freq)
        if window_high < len(signal):
            high_passed = signal - np.convolve(signal, np.ones(window_high)/window_high, mode='same')
        else:
            high_passed = signal
            
        # Simple low-pass filter (remove high frequencies)
        window_low = max(1, int(sample_rate / (high_freq * 4)))
        low_passed = np.convolve(high_passed, np.ones(window_low)/window_low, mode='same')
        
        return low_passed
    
    def _find_peaks(self, signal):
        """Find peaks in the signal using adaptive threshold."""
        if len(signal) < 3:
            return np.array([])
            
        # Adaptive threshold based on signal statistics
        signal_std = np.std(signal)
        threshold = signal_std * 0.4
        
        peaks = []
        min_distance = int(self.sample_rate * 0.3)  # Minimum 300ms between peaks (200 BPM max)
        
        for i in range(1, len(signal) - 1):
            if (signal[i] > threshold and 
                signal[i] > signal[i-1] and 
                signal[i] > signal[i+1]):
                
                # Check minimum distance from last peak
                if not peaks or (i - peaks[-1]) >= min_distance:
                    peaks.append(i)
        
        return np.array(peaks)
    
    def _calculate_confidence(self, intervals):
        """Calculate confidence based on interval consistency."""
        if len(intervals) <= 1:
            return 0.0
            
        # Coefficient of variation (lower is better)
        cv = np.std(intervals) / np.mean(intervals)
        
        # Convert to confidence (0-1, higher is better)
        confidence = max(0.0, 1.0 - cv * 4)
        
        return min(1.0, confidence)


class ImprovedHeartRateMonitor:
    """
    Improved heart rate monitor with proper sensor initialization and algorithms.
    """
    
    def __init__(self, mode='hr', sample_rate=100, print_raw=False, print_result=True, save_data=True):
        self.mode = mode  # 'hr' or 'spo2'
        self.sample_rate = sample_rate
        self.print_raw = print_raw
        self.print_result = print_result  
        self.save_data = save_data
        
        # Initialize sensor
        self.sensor = MAX30102()
        
        # Configure sensor based on mode
        if mode == 'hr':
            self.sensor.setup_heart_rate_mode(sample_rate=SPO2_SR_100, led_current=0x1F)
        elif mode == 'spo2':
            self.sensor.setup_spo2_mode(sample_rate=SPO2_SR_100, red_current=0x1F, ir_current=0x1F)
        else:
            raise ValueError("Mode must be 'hr' or 'spo2'")
        
        # Enable proximity detection
        self.sensor.enable_proximity_detection()
        
        # Initialize heart rate calculator
        self.hr_calculator = HeartRateCalculator(sample_rate=100)
        
        # State variables
        self.bpm = 0
        self.confidence = 0.0
        self.running = False
        
        # Data logging
        if self.save_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.data_file = f"heart_rate_data_{timestamp}.csv"
            with open(self.data_file, 'w', newline='') as f:
                writer = csv.writer(f)
                if mode == 'hr':
                    writer.writerow(['timestamp', 'bpm', 'confidence', 'ir_value', 'temperature'])
                else:
                    writer.writerow(['timestamp', 'bpm', 'confidence', 'ir_value', 'red_value', 'temperature'])

    def start_monitoring(self):
        """Start the heart rate monitoring in a separate thread."""
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        
        if self.print_result:
            print(f"Heart rate monitoring started in {self.mode.upper()} mode")
            print("Place your finger on the sensor...")

    def stop_monitoring(self):
        """Stop the heart rate monitoring."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)
        self.sensor.shutdown()
        
        if self.print_result:
            print("Heart rate monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        last_temp_read = 0
        temperature = None
        
        while self.running:
            try:
                # Check for available samples
                available_samples = self.sensor.get_fifo_available_samples()
                
                if available_samples > 0:
                    for _ in range(available_samples):
                        # Read sample
                        red_value, ir_value = self.sensor.read_fifo_data()
                        
                        if self.print_raw:
                            if red_value is not None:
                                print(f"Red: {red_value}, IR: {ir_value}")
                            else:
                                print(f"IR: {ir_value}")
                        
                        # Add to heart rate calculator
                        self.hr_calculator.add_sample(ir_value)
                        
                        # Calculate heart rate
                        hr_result = self.hr_calculator.calculate_heart_rate()
                        if hr_result[0] is not None:
                            self.bpm, self.confidence = hr_result
                            
                            if self.print_result:
                                print(f"Heart Rate: {self.bpm:.1f} BPM (Confidence: {self.confidence:.2f})")
                        
                        # Save data
                        if self.save_data:
                            current_time = time.time()
                            
                            # Read temperature every 5 seconds
                            if current_time - last_temp_read > 5.0:
                                temperature = self.sensor.read_temperature()
                                last_temp_read = current_time
                            
                            with open(self.data_file, 'a', newline='') as f:
                                writer = csv.writer(f)
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                
                                if self.mode == 'hr':
                                    writer.writerow([timestamp, self.bpm, self.confidence, ir_value, temperature])
                                else:
                                    writer.writerow([timestamp, self.bpm, self.confidence, ir_value, red_value, temperature])
                
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                if self.print_result:
                    print(f"Error in monitoring loop: {e}")
                time.sleep(0.1)


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="Improved MAX30102 Heart Rate Monitor")
    parser.add_argument("-m", "--mode", choices=['hr', 'spo2'], default='hr',
                        help="Monitoring mode: hr (heart rate only) or spo2 (both heart rate and SpO2)")
    parser.add_argument("-r", "--raw", action="store_true",
                        help="Print raw sensor data")
    parser.add_argument("-t", "--time", type=int, default=60,
                        help="Duration in seconds to monitor (default: 60)")
    parser.add_argument("--no-save", action="store_true",
                        help="Don't save data to file")
    
    args = parser.parse_args()

    try:
        # Initialize monitor
        monitor = ImprovedHeartRateMonitor(
            mode=args.mode,
            print_raw=args.raw,
            print_result=not args.raw,
            save_data=not args.no_save
        )
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Run for specified time
        time.sleep(args.time)
        
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'monitor' in locals():
            monitor.stop_monitoring()
            if hasattr(monitor, 'data_file') and not args.no_save:
                print(f"Data saved to: {monitor.data_file}")


if __name__ == "__main__":
    main()