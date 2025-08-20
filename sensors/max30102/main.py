#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MAX30102 Heart Rate Monitor
This script reads heart rate data from the MAX30102 sensor using I2C.
It calculates heart rate based on the IR LED signal and prints the results.
It includes a simple peak detection algorithm to determine heart rate.
The sensor is initialized, calibrated, and runs in a separate thread.
"""

import smbus
import time
import threading
import numpy as np
import argparse

# ============================================================================
# MAX30102 Sensor Class
# ============================================================================

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
REG_LED1_PA = 0x0C
REG_LED2_PA = 0x0D
REG_PILOT_PA = 0x10
REG_MULTI_LED_CTRL1 = 0x11
REG_MULTI_LED_CTRL2 = 0x12
REG_TEMP_INTR = 0x1F
REG_TEMP_FRAC = 0x20
REG_TEMP_CONFIG = 0x21
REG_PROX_INT_THRESH = 0x30
REG_REV_ID = 0xFE
REG_PART_ID = 0xFF


class MAX30102:
    def __init__(self, channel=1, address=0x57):
        self.address = address
        self.channel = channel
        self.bus = smbus.SMBus(self.channel)
        self.reset()
        time.sleep(1)  # wait 1 sec
        
        # read & clear interrupt register (read 1 byte)
        reg_data = self.bus.read_i2c_block_data(self.address, REG_INTR_STATUS_1, 1)
        self.setup()

    def shutdown(self):
        """Shutdown the device."""
        self.bus.write_i2c_block_data(self.address, REG_MODE_CONFIG, [0x80])

    def reset(self):
        """Reset the device, this will clear all settings."""
        self.bus.write_i2c_block_data(self.address, REG_MODE_CONFIG, [0x40])

    def setup(self, led_mode=0x03):
        """Setup the device with default values."""
        # INTR setting
        self.bus.write_i2c_block_data(self.address, REG_INTR_ENABLE_1, [0xc0])
        self.bus.write_i2c_block_data(self.address, REG_INTR_ENABLE_2, [0x00])

        # FIFO pointers
        self.bus.write_i2c_block_data(self.address, REG_FIFO_WR_PTR, [0x00])
        self.bus.write_i2c_block_data(self.address, REG_OVF_COUNTER, [0x00])
        self.bus.write_i2c_block_data(self.address, REG_FIFO_RD_PTR, [0x00])

        # FIFO config
        self.bus.write_i2c_block_data(self.address, REG_FIFO_CONFIG, [0x4f])
        
        # Mode config (SpO2 mode for both red and IR)
        self.bus.write_i2c_block_data(self.address, REG_MODE_CONFIG, [led_mode])
        
        # SpO2 config
        self.bus.write_i2c_block_data(self.address, REG_SPO2_CONFIG, [0x27])

        # LED pulse amplitudes
        self.bus.write_i2c_block_data(self.address, REG_LED1_PA, [0x24])  # Red LED
        self.bus.write_i2c_block_data(self.address, REG_LED2_PA, [0x24])  # IR LED
        self.bus.write_i2c_block_data(self.address, REG_PILOT_PA, [0x7f])  # Pilot LED

    def get_data_present(self):
        """Get number of samples available in FIFO."""
        read_ptr = self.bus.read_byte_data(self.address, REG_FIFO_RD_PTR)
        write_ptr = self.bus.read_byte_data(self.address, REG_FIFO_WR_PTR)
        if read_ptr == write_ptr:
            return 0
        else:
            num_samples = write_ptr - read_ptr
            if num_samples < 0:
                num_samples += 32
            return num_samples

    def read_fifo(self):
        """Read data from FIFO."""
        # Read interrupt status (values are discarded)
        reg_INTR1 = self.bus.read_i2c_block_data(self.address, REG_INTR_STATUS_1, 1)
        reg_INTR2 = self.bus.read_i2c_block_data(self.address, REG_INTR_STATUS_2, 1)

        # Read 6-byte data from the device
        d = self.bus.read_i2c_block_data(self.address, REG_FIFO_DATA, 6)

        # Convert to 18-bit values and mask MSB [23:18]
        red_led = (d[0] << 16 | d[1] << 8 | d[2]) & 0x03FFFF
        ir_led = (d[3] << 16 | d[4] << 8 | d[5]) & 0x03FFFF

        return red_led, ir_led


# ============================================================================
# Simple Heart Rate Calculation
# ============================================================================

def calculate_heart_rate(ir_data, sample_rate=25):
    """
    Simple heart rate calculation using peak detection on IR signal.
    """
    if len(ir_data) < 50:
        return None, False
        
    # Convert to numpy array and normalize
    signal = np.array(ir_data, dtype=float)
    
    # Remove DC component
    signal = signal - np.mean(signal)
    
    # Simple peak detection
    peaks = []
    threshold = np.std(signal) * 0.3  # Adaptive threshold
    
    for i in range(1, len(signal) - 1):
        if (signal[i] > threshold and 
            signal[i] > signal[i-1] and 
            signal[i] > signal[i+1]):
            # Check if this peak is far enough from the last one
            if not peaks or (i - peaks[-1]) > 10:  # Minimum distance between peaks
                peaks.append(i)
    
    if len(peaks) < 2:
        return None, False
        
    # Calculate heart rate from peak intervals
    intervals = np.diff(peaks)
    if len(intervals) == 0:
        return None, False
        
    # Remove outlier intervals
    if len(intervals) > 2:
        intervals = intervals[intervals < np.mean(intervals) + 2 * np.std(intervals)]
        intervals = intervals[intervals > np.mean(intervals) - 2 * np.std(intervals)]
    
    if len(intervals) == 0:
        return None, False
        
    avg_interval = np.mean(intervals)
    heart_rate = (sample_rate * 60) / avg_interval
    
    # Filter unrealistic values
    if 40 <= heart_rate <= 200:
        return heart_rate, True
    else:
        return None, False


# ============================================================================
# Heart Rate Monitor Class
# ============================================================================

class HeartRateMonitor(object):
    """A simplified heart rate monitor class."""
    
    LOOP_TIME = 0.01

    def __init__(self, print_raw=False, print_result=False):
        self.bpm = 0
        if print_raw:
            print('IR, Red')
        self.print_raw = print_raw
        self.print_result = print_result
        self.calibrating = True
        self.calibration_start = None

    def run_sensor(self):
        """Main sensor loop running in separate thread."""
        sensor = MAX30102()
        ir_data = []
        red_data = []
        bpms = []
        self.calibration_start = time.time()
        
        # Run until told to stop
        while not self._thread.stopped:
            # Check if any data is available
            num_bytes = sensor.get_data_present()
            if num_bytes > 0:
                # Grab all the data and stash it into arrays
                while num_bytes > 0:
                    red, ir = sensor.read_fifo()
                    num_bytes -= 1
                    ir_data.append(ir)
                    red_data.append(red)
                    if self.print_raw:
                        print("{0}, {1}".format(ir, red))

                # Keep buffer size at 100
                while len(ir_data) > 100:
                    ir_data.pop(0)
                    red_data.pop(0)

                # Check calibration period
                if self.calibrating and time.time() - self.calibration_start > 5.0:
                    self.calibrating = False
                    if self.print_result:
                        print("Calibration complete. Reading heart rate...")

                # Calculate HR when we have enough samples and calibration is done
                if len(ir_data) >= 50 and not self.calibrating:
                    # Check if finger is detected
                    if (np.mean(ir_data) < 50000 and np.mean(red_data) < 50000):
                        self.bpm = 0
                        bpms.clear()  # Clear history when finger removed
                        if self.print_result:
                            print("Finger not detected")
                    else:
                        hr, valid = calculate_heart_rate(ir_data)
                        if valid:
                            bpms.append(hr)
                            while len(bpms) > 4:
                                bpms.pop(0)
                            
                            self.bpm = np.mean(bpms)
                            
                            if self.print_result:
                                print("BPM: {0:.1f}".format(self.bpm))
                elif self.calibrating and self.print_result:
                    remaining = 5.0 - (time.time() - self.calibration_start)
                    if remaining > 0 and int(remaining) != int(remaining + self.LOOP_TIME):
                        print("Calibrating... {0:.0f}s remaining".format(remaining))
            
            time.sleep(self.LOOP_TIME)
        
        sensor.shutdown()

    def start_sensor(self):
        """Start the sensor in a separate thread."""
        self._thread = threading.Thread(target=self.run_sensor)
        self._thread.stopped = False
        self._thread.start()

    def stop_sensor(self, timeout=2.0):
        """Stop the sensor thread."""
        self._thread.stopped = True
        self.bpm = 0
        self._thread.join(timeout)


# ============================================================================
# Main Script
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read heart rate from MAX30102")
    parser.add_argument("-r", "--raw", action="store_true",
                        help="print raw data instead of calculation result")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duration in seconds to read from sensor, default 30")
    args = parser.parse_args()

    print('Sensor starting...')
    
    try:
        hrm = HeartRateMonitor(print_raw=args.raw, print_result=(not args.raw))
        hrm.start_sensor()
        
        if not args.raw:
            print('Place your finger on the sensor...')
            print('Calibrating for 5 seconds...')
        
        time.sleep(args.time)
        
    except KeyboardInterrupt:
        print('\nKeyboard interrupt detected, exiting...')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        if 'hrm' in locals():
            hrm.stop_sensor()
        print('Sensor stopped!')