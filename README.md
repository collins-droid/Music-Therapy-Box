# Music Therapy Box
A Raspberry Pi 4B-powered Music Therapy Box that uses machine learning and biosensors (MAX30102 + GSR+MLX90614) to detect stress levels and play curated music in real time. Features user login via keypad, calibration, SQLite session tracking, LCD feedback, and adaptive music selection logic.
1. Run: python main.py
   ↓
2. System initializes all hardware
   ↓
3. LCD: "Press START to begin"
   ↓
4. User presses START button (Arduino)
   ↓
5. Arduino → Pi: "BUTTON:START"
   ↓
6. Pi starts calibration (10 seconds)
   ↓
7. Arduino collects baseline data
   ↓
8. Arduino → Pi: "BASELINE:GSR:25.45,HR:75.2"
   ↓
9. Pi starts therapy session
   ↓
10. Pi collects 60-second sensor windows
    ↓
11. Pi extracts 15 features
    ↓
12. Pi predicts stress level
    ↓
13. Pi plays appropriate music
    ↓
14. User presses STOP → Session ends