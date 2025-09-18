#!/usr/bin/env python3
"""
Test script for MAX30102 Heart Rate Sensor
Based on the original HeartRateMonitor implementation
"""

import logging
import time
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_heartrate_sensor():
    """Test the heart rate sensor using the original implementation"""
    try:
        logger.info("Testing Heart Rate Sensor...")
        
        # Import the original HeartRateMonitor
        from sensors.heartrate_monitor import HeartRateMonitor
        
        # Create sensor instance
        hrm = HeartRateMonitor(print_raw=False, print_result=True)
        
        logger.info("Starting heart rate sensor...")
        hrm.start_sensor()
        
        logger.info("Heart rate sensor started. Place finger on MAX30102 sensor...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            # Run for 30 seconds by default
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        logger.info("Stopping heart rate sensor...")
        hrm.stop_sensor()
        logger.info("Heart rate sensor stopped!")
        
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import HeartRateMonitor: {e}")
        return False
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

def test_enhanced_hr_sensor():
    """Test the enhanced HR sensor implementation"""
    try:
        logger.info("Testing Enhanced HR Sensor...")
        
        # Import the enhanced HRSensor
        from sensors.hr_module import HRSensor
        
        # Create sensor instance
        hr_sensor = HRSensor(print_raw=False, print_result=True)
        
        logger.info("Starting enhanced HR sensor...")
        if not hr_sensor.start_sensor():
            logger.error("Failed to start enhanced HR sensor")
            return False
        
        logger.info("Enhanced HR sensor started. Place finger on MAX30102 sensor...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            # Run for 30 seconds
            start_time = time.time()
            while time.time() - start_time < 30:
                reading = hr_sensor.get_reading()
                if reading:
                    logger.info(f"HR Reading: BPM={reading.bpm:.1f}, "
                              f"Finger={reading.finger_detected}, "
                              f"Valid={reading.valid_bpm}, "
                              f"IR={reading.ir_value}, Red={reading.red_value}")
                else:
                    logger.debug("No HR reading available")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        logger.info("Stopping enhanced HR sensor...")
        hr_sensor.stop_sensor()
        logger.info("Enhanced HR sensor stopped!")
        
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import HRSensor: {e}")
        return False
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

def test_baseline_calculation():
    """Test baseline calculation functionality"""
    try:
        logger.info("Testing Baseline Calculation...")
        
        from sensors.hr_module import HRSensor
        
        hr_sensor = HRSensor(print_raw=False, print_result=True)
        
        if not hr_sensor.start_sensor():
            logger.error("Failed to start HR sensor for baseline test")
            return False
        
        logger.info("Collecting baseline data for 10 seconds...")
        logger.info("Place finger FIRMLY on MAX30102 sensor!")
        
        time.sleep(10)  # Collect data for 10 seconds
        
        # Calculate baseline
        baseline_bpm = hr_sensor.calculate_baseline(duration_seconds=10)
        
        if baseline_bpm:
            logger.info(f"✅ Baseline calculated: {baseline_bpm:.1f} BPM")
            hr_sensor.set_baseline_data(baseline_bpm)
            logger.info(f"✅ Baseline stored: {hr_sensor.get_baseline_data():.1f} BPM")
        else:
            logger.warning("❌ No baseline data collected - finger may not be detected")
        
        hr_sensor.stop_sensor()
        return baseline_bpm is not None
        
    except Exception as e:
        logger.error(f"Baseline test failed: {e}")
        return False

def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test MAX30102 Heart Rate Sensor")
    parser.add_argument("-t", "--test", choices=["original", "enhanced", "baseline", "all"], 
                       default="all", help="Which test to run")
    parser.add_argument("-d", "--duration", type=int, default=30,
                       help="Test duration in seconds")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("MAX30102 Heart Rate Sensor Test Suite")
    logger.info("=" * 60)
    
    results = {}
    
    if args.test in ["original", "all"]:
        logger.info("\n1. Testing Original HeartRateMonitor...")
        results["original"] = test_heartrate_sensor()
    
    if args.test in ["enhanced", "all"]:
        logger.info("\n2. Testing Enhanced HRSensor...")
        results["enhanced"] = test_enhanced_hr_sensor()
    
    if args.test in ["baseline", "all"]:
        logger.info("\n3. Testing Baseline Calculation...")
        results["baseline"] = test_baseline_calculation()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name.upper()}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n🎉 All tests PASSED! MAX30102 sensor is working correctly.")
    else:
        logger.info("\n⚠️  Some tests FAILED. Check finger placement and sensor connection.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
