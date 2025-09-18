#!/usr/bin/env python3
"""
Quick test script to check MAX30102 sensor functionality
"""

import logging
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_max30102():
    """Test MAX30102 sensor directly"""
    try:
        logger.info("Testing MAX30102 sensor...")
        
        # Try to import MAX30102
        try:
            from sensors.max30102 import MAX30102
            logger.info("MAX30102 library imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import MAX30102: {e}")
            return False
        
        # Try to initialize sensor
        try:
            sensor = MAX30102()
            logger.info("MAX30102 sensor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MAX30102 sensor: {e}")
            return False
        
        # Test data reading
        logger.info("Testing data reading for 10 seconds...")
        start_time = time.time()
        data_count = 0
        
        while time.time() - start_time < 10:
            try:
                num_bytes = sensor.get_data_present()
                if num_bytes > 0:
                    logger.info(f"Data available: {num_bytes} bytes")
                    red, ir = sensor.read_fifo()
                    logger.info(f"IR: {ir}, Red: {red}")
                    data_count += 1
                else:
                    logger.debug("No data available")
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error reading sensor data: {e}")
                break
        
        logger.info(f"Test completed. Data readings: {data_count}")
        
        # Shutdown sensor
        try:
            sensor.shutdown()
            logger.info("MAX30102 sensor shutdown")
        except Exception as e:
            logger.warning(f"Error shutting down sensor: {e}")
        
        return data_count > 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_max30102()
    if success:
        print("✅ MAX30102 test PASSED")
    else:
        print("❌ MAX30102 test FAILED")
