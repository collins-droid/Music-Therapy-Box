#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Complete MAX30102 Heart Rate Monitor System
Combines all components into a single working script
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
        
        # Mode config (SpO2 mode)
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
# Heart Rate and SpO2 Calculation
# ============================================================================

# Algorithm constants
SAMPLE_FREQ = 25
MA_SIZE = 4
BUFFER_SIZE = 100


def calc_hr_and_spo2(ir_data, red_data):
    """
    Calculate heart rate and SpO2 from IR and Red LED data.
    """
    # Convert to numpy arrays
    ir_data = np.array(ir_data)
    red_data = np.array(red_data)
    
    # Get DC mean and remove it
    ir_mean = int(np.mean(ir_data))
    x = -1 * (ir_data - ir_mean)

    # 4 point moving average
    for i in range(x.shape[0] - MA_SIZE):
        x[i] = np.sum(x[i:i+MA_SIZE]) / MA_SIZE

    # Calculate threshold
    n_th = int(np.mean(x))
    n_th = max(30, min(60, n_th))  # Clamp between 30-60

    ir_valley_locs, n_peaks = find_peaks(x, BUFFER_SIZE, n_th, 4, 15)
    
    # Calculate heart rate
    if n_peaks >= 2:
        peak_interval_sum = 0
        for i in range(1, n_peaks):
            peak_interval_sum += (ir_valley_locs[i] - ir_valley_locs[i-1])
        peak_interval_sum = int(peak_interval_sum / (n_peaks - 1))
        hr = int(SAMPLE_FREQ * 60 / peak_interval_sum)
        hr_valid = True
    else:
        hr = -999
        hr_valid = False

    # Calculate SpO2
    exact_ir_valley_locs_count = n_peaks

    # Check if valley locations are within buffer
    for i in range(exact_ir_valley_locs_count):
        if ir_valley_locs[i] > BUFFER_SIZE:
            spo2 = -999
            spo2_valid = False
            return hr, hr_valid, spo2, spo2_valid

    i_ratio_count = 0
    ratio = []

    # Calculate ratio for SpO2
    for k in range(exact_ir_valley_locs_count-1):
        red_dc_max = -16777216
        ir_dc_max = -16777216
        red_dc_max_index = -1
        ir_dc_max_index = -1
        
        if ir_valley_locs[k+1] - ir_valley_locs[k] > 3:
            for i in range(ir_valley_locs[k], ir_valley_locs[k+1]):
                if ir_data[i] > ir_dc_max:
                    ir_dc_max = ir_data[i]
                    ir_dc_max_index = i
                if red_data[i] > red_dc_max:
                    red_dc_max = red_data[i]
                    red_dc_max_index = i

            # Calculate AC components
            red_ac = int((red_data[ir_valley_locs[k+1]] - red_data[ir_valley_locs[k]]) * 
                        (red_dc_max_index - ir_valley_locs[k]))
            red_ac = red_data[ir_valley_locs[k]] + int(red_ac / (ir_valley_locs[k+1] - ir_valley_locs[k]))
            red_ac = red_data[red_dc_max_index] - red_ac

            ir_ac = int((ir_data[ir_valley_locs[k+1]] - ir_data[ir_valley_locs[k]]) * 
                       (ir_dc_max_index - ir_valley_locs[k]))
            ir_ac = ir_data[ir_valley_locs[k]] + int(ir_ac / (ir_valley_locs[k+1] - ir_valley_locs[k]))
            ir_ac = ir_data[ir_dc_max_index] - ir_ac

            # Calculate ratio
            nume = red_ac * ir_dc_max
            denom = ir_ac * red_dc_max
            if (denom > 0 and i_ratio_count < 5) and nume != 0:
                ratio.append(int(((nume * 100) & 0xffffffff) / denom))
                i_ratio_count += 1

    # Calculate SpO2 from ratio
    if len(ratio) > 0:
        ratio = sorted(ratio)
        mid_index = int(i_ratio_count / 2)
        
        if mid_index > 1:
            ratio_ave = int((ratio[mid_index-1] + ratio[mid_index])/2)
        else:
            ratio_ave = ratio[mid_index]

        if 2 < ratio_ave < 184:
            spo2 = -45.060 * (ratio_ave**2) / 10000.0 + 30.054 * ratio_ave / 100.0 + 94.845
            spo2_valid = True
        else:
            spo2 = -999
            spo2_valid = False
    else:
        spo2 = -999
        spo2_valid = False

    return hr, hr_valid, spo2, spo2_valid


def find_peaks(x, size, min_height, min_dist, max_num):
    """Find peaks in signal."""
    ir_valley_locs, n_peaks = find_peaks_above_min_height(x, size, min_height, max_num)
    ir_valley_locs, n_peaks = remove_close_peaks(n_peaks, ir_valley_locs, x, min_dist)
    n_peaks = min([n_peaks, max_num])
    return ir_valley_locs, n_peaks


def find_peaks_above_min_height(x, size, min_height, max_num):
    """Find all peaks above minimum height."""
    i = 0
    n_peaks = 0
    ir_valley_locs = []
    
    while i < size - 1:
        if x[i] > min_height and x[i] > x[i-1]:
            n_width = 1
            while i + n_width < size - 1 and x[i] == x[i+n_width]:
                n_width += 1
            if x[i] > x[i+n_width] and n_peaks < max_num:
                ir_valley_locs.append(i)
                n_peaks += 1
                i += n_width + 1
            else:
                i += n_width
        else:
            i += 1
    return ir_valley_locs, n_peaks


def remove_close_peaks(n_peaks, ir_valley_locs, x, min_dist):
    """Remove peaks that are too close together."""
    sorted_indices = sorted(ir_valley_locs, key=lambda i: x[i])
    sorted_indices.reverse()

    i = -1
    while i < n_peaks:
        old_n_peaks = n_peaks
        n_peaks = i + 1
        j = i + 1
        while j < old_n_peaks:
            n_dist = (sorted_indices[j] - sorted_indices[i]) if i != -1 else (sorted_indices[j] + 1)
            if n_dist > min_dist or n_dist < -1 * min_dist:
                sorted_indices[n_peaks] = sorted_indices[j]
                n_peaks += 1
            j += 1
        i += 1

    sorted_indices[:n_peaks] = sorted(sorted_indices[:n_peaks])
    return sorted_indices, n_peaks


# ============================================================================
# Heart Rate Monitor Class
# ============================================================================

class HeartRateMonitor(object):
    """A class that encapsulates the MAX30102 device into a thread."""
    
    LOOP_TIME = 0.01

    def __init__(self, print_raw=False, print_result=False):
        self.bpm = 0
        if print_raw:
            print('IR, Red')
        self.print_raw = print_raw
        self.print_result = print_result

    def run_sensor(self):
        """Main sensor loop running in separate thread."""
        sensor = MAX30102()
        ir_data = []
        red_data = []
        bpms = []
        
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

                # Calculate HR and SpO2 when we have 100 samples
                if len(ir_data) == 100:
                    bpm, valid_bpm, spo2, valid_spo2 = calc_hr_and_spo2(ir_data, red_data)
                    if valid_bpm:
                        bpms.append(bpm)
                        while len(bpms) > 4:
                            bpms.pop(0)
                        self.bpm = np.mean(bpms)
                        
                        # Check if finger is detected
                        if (np.mean(ir_data) < 50000 and np.mean(red_data) < 50000):
                            self.bpm = 0
                            if self.print_result:
                                print("Finger not detected")
                        else:
                            if self.print_result:
                                print("BPM: {0:.1f}, SpO2: {1:.1f}".format(self.bpm, spo2))
            
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
    parser = argparse.ArgumentParser(description="Read and print data from MAX30102")
    parser.add_argument("-r", "--raw", action="store_true",
                        help="print raw data instead of calculation result")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duration in seconds to read from sensor, default 30")
    args = parser.parse_args()

    print('Sensor starting...')
    
    try:
        hrm = HeartRateMonitor(print_raw=args.raw, print_result=(not args.raw))
        hrm.start_sensor()
        
        print(f'Reading for {args.time} seconds. Place your finger on the sensor...')
        time.sleep(args.time)
        
    except KeyboardInterrupt:
        print('\nKeyboard interrupt detected, exiting...')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        if 'hrm' in locals():
            hrm.stop_sensor()
        print('Sensor stopped!')