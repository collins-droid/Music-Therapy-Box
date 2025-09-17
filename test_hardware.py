#!/usr/bin/env python3
"""
Test script to check individual hardware components
"""

import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gsr_sensor():
    """Test GSR sensor initialization"""
    try:
        from sensors.gsr_module import GSRSensor
        logger.info("Testing GSR sensor...")
        gsr = GSRSensor()
        connected = gsr.is_connected()
        logger.info(f"GSR sensor: {'✓ Connected' if connected else '✗ Failed'}")
        return connected
    except Exception as e:
        logger.error(f"GSR sensor failed: {e}")
        return False

def test_hr_sensor():
    """Test HR sensor initialization"""
    try:
        from sensors.hr_module import HRSensor
        logger.info("Testing HR sensor...")
        hr = HRSensor()
        connected = hr.is_connected()
        logger.info(f"HR sensor: {'✓ Connected' if connected else '✗ Failed'}")
        return connected
    except Exception as e:
        logger.error(f"HR sensor failed: {e}")
        return False

def test_lcd_display():
    """Test LCD display initialization"""
    try:
        from display.lcd_module import LCDDisplay
        logger.info("Testing LCD display...")
        lcd = LCDDisplay()
        ready = lcd.is_ready()
        logger.info(f"LCD display: {'✓ Ready' if ready else '✗ Failed'}")
        return ready
    except Exception as e:
        logger.error(f"LCD display failed: {e}")
        return False

def test_music_player():
    """Test music player initialization"""
    try:
        from audio.music_player import MusicPlayer
        logger.info("Testing music player...")
        music = MusicPlayer(['music/calming', 'music/stress_relief'])
        ready = music.is_ready()
        logger.info(f"Music player: {'✓ Ready' if ready else '✗ Failed'}")
        return ready
    except Exception as e:
        logger.error(f"Music player failed: {e}")
        return False

def test_stress_predictor():
    """Test stress predictor initialization"""
    try:
        from model.stress_predictor import StressPredictor
        logger.info("Testing stress predictor...")
        predictor = StressPredictor()
        loaded = predictor.is_loaded()
        logger.info(f"Stress predictor: {'✓ Loaded' if loaded else '✗ Failed'}")
        return loaded
    except Exception as e:
        logger.error(f"Stress predictor failed: {e}")
        return False

def main():
    """Run all hardware tests"""
    logger.info("Starting hardware component tests...")
    
    results = {
        'GSR Sensor': test_gsr_sensor(),
        'HR Sensor': test_hr_sensor(),
        'LCD Display': test_lcd_display(),
        'Music Player': test_music_player(),
        'Stress Predictor': test_stress_predictor()
    }
    
    logger.info("\n" + "="*50)
    logger.info("HARDWARE TEST RESULTS:")
    logger.info("="*50)
    
    all_passed = True
    for component, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{component:20} {status}")
        if not result:
            all_passed = False
    
    logger.info("="*50)
    if all_passed:
        logger.info("All hardware components passed!")
        return 0
    else:
        logger.error("One or more hardware components failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
