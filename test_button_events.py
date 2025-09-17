#!/usr/bin/env python3
"""
Test script to verify Arduino button events are being received
"""

import time
import logging
from sensors.gsr_module import GSRSensor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def button_callback(button_type):
    """Callback function to handle button events"""
    logger.info(f"*** BUTTON EVENT RECEIVED: {button_type} ***")

def main():
    """Test button event detection"""
    logger.info("Starting button event test...")
    
    # Initialize GSR sensor with button callback
    gsr_sensor = GSRSensor(button_callback=button_callback)
    
    if not gsr_sensor.start_sensor():
        logger.error("Failed to start GSR sensor")
        return
    
    logger.info("GSR sensor started. Press START or STOP button on Arduino...")
    logger.info("Press Ctrl+C to exit")
    
    try:
        while True:
            # Check for GSR readings
            reading = gsr_sensor.get_reading()
            if reading:
                logger.debug(f"GSR: {reading.conductance:.2f}μS")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    finally:
        gsr_sensor.stop_sensor()
        logger.info("Test completed")

if __name__ == "__main__":
    main()
