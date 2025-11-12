# C4 Corvette Digital Dashboard

A complete digital dashboard replacement for 1984-1996 Chevrolet Corvette (C4) featuring real-time sensor monitoring, fuel consumption tracking, and multiple display styles.

## 📁 **Required Files**

### **Core Application Files**
- **`arduino_code.cpp`** - Main Arduino firmware for sensor reading and data processing
- **`arduino_combined_dashboard.py`** - Raspberry Pi dashboard application with all display styles
- **`README.md`** - This comprehensive setup and usage guide

### **Symbol Images** (Required for dashboard display)
- **`coolant_temp_symbol.png`** - Coolant temperature gauge icon
- **`oil_symbol.png`** - Oil pressure gauge icon
- **`gas_pump_symbol.png`** - Fuel level gauge icon
- **`battery_symbol.png`** - Battery voltage gauge icon

### **Documentation Files** (Optional - for development reference)
- **`ALDL_INTEGRATION_FINAL_SUCCESS.md`** - ALDL fuel consumption integration details
- **`C4_DASHBOARD_COMPLETE_SETUP.md`** - Complete hardware setup guide
- **`FUEL_DISPLAY_IMPROVEMENT.md`** - Fuel display architecture improvements
- **`ALDL_PERFORMANCE_FIX.md`** - Performance optimization details
- **`debug_timing_analysis.py`** - Performance analysis tool (development use)

### **File Structure**
```
C4-Corvette-Dashboard/
├── arduino_code.cpp                    # Arduino firmware
├── arduino_combined_dashboard.py       # Main dashboard application
├── README.md                          # Setup guide
├── coolant_temp_symbol.png            # Required icon
├── oil_symbol.png                     # Required icon
├── gas_pump_symbol.png                # Required icon
├── battery_symbol.png                 # Required icon
├── docs/                              # Documentation (optional)
│   ├── ALDL_INTEGRATION_FINAL_SUCCESS.md
│   ├── C4_DASHBOARD_COMPLETE_SETUP.md
│   ├── FUEL_DISPLAY_IMPROVEMENT.md
│   └── ALDL_PERFORMANCE_FIX.md
└── tools/                             # Development tools (optional)
    └── debug_timing_analysis.py
```

### **Installation Priority**
1. **Essential**: `arduino_code.cpp`, `arduino_combined_dashboard.py`, symbol images
2. **Recommended**: `README.md` for setup instructions
3. **Optional**: Documentation files for advanced configuration and troubleshooting

## 🚗 **Project Overview**

This project replaces the original C4 Corvette dashboard with a modern digital system featuring:

### **🎯 Key Features**
- **Triple Display Setup**: Speedometer, Tachometer, and DSI gauges
- **5 Display Styles**: Synthwave, Citroën BX, Subaru XT, Nissan 300ZX, and C4 Classic
- **Real-time ALDL Integration**: Dedicated ESP32 board for ECU fuel consumption data
- **Comprehensive Sensor Monitoring**: Speed, RPM, fuel, oil, coolant, battery
- **Advanced Fuel Calculations**: Real-time MPG and GPH from ECU data with accurate display across all styles
- **Hardware Acceleration**: 20Hz refresh rate with optimized performance
- **Robust Error Handling**: Comprehensive safety checks and graceful degradation

### **🔧 Hardware Architecture**

![C4 Corvette Dashboard Schematic](corvette-c4-raspberry-dashboard/corvette_c4_dashboard.jpg)
*Complete system wiring diagram showing Arduino Mega, ESP32 ALDL board, Raspberry Pi, and all sensor connections*

#### **Main Arduino (Mega 2560)**
- **Primary dashboard control** and sensor reading
- **20Hz main loop** for smooth gauge updates
- **Switch monitoring** and user interface
- **Communication hub** for all components

#### **Dedicated ESP32 ALDL Board**
- **Real-time ALDL ECU data capture** from 1988 Corvette L98 TPI
- **Non-blocking fuel consumption calculation**
- **Serial communication** with main Arduino
- **Isolated processing** - zero impact on dashboard performance

#### **Raspberry Pi 4**
- **Triple display management** (1920x1080 + 800x480 + 800x480)
- **Advanced graphics rendering** with hardware acceleration
- **Style switching** and user interface
- **Data logging** and persistent storage

### **📡 ALDL Integration Details**

The system uses a **dedicated ESP32 board** for ALDL (Assembly Line Diagnostic Link) integration:

#### **ESP32 ALDL Board (ESP32_ALDL_Dedicated.ino)**
- **GPIO19**: ALDL ECU data input (160 baud, 6.24ms bit timing)
- **GPIO17**: Serial TX to Arduino (9600 baud)
- **Real-time ECU fuel consumption** calculation in lb/hr
- **Proven timing method** from ALDL_reading_final.cpp
- **Automatic fuel counter rollover** handling

#### **Communication Flow**
```
ECU → ESP32 (ALDL capture) → Arduino (Serial) → Raspberry Pi → Dashboard
```

#### **Fuel Data Processing**
- **ECU fuel counter** and fuel constant from ALDL stream
- **Real-time lb/hr calculation** using injector flow rates
- **Conversion to GPH** for dashboard display (lb/hr ÷ 6.0)
- **Instant MPG calculation** using Speed ÷ Fuel Flow

### **🔌 Wiring Connections**

> **📋 See the complete wiring diagram above for visual reference**

#### **ESP32 ALDL Board**
```
ESP32 GPIO17 → Arduino Pin 19 (Serial1 RX)
ESP32 GPIO19 → ALDL wire from ECU (Pin E on diagnostic connector)
ESP32 GND    → Arduino GND (common ground essential!)
ESP32 USB    → 5V Power supply
```

#### **Main Arduino Connections**
- **Analog Inputs**: Fuel (A15), Oil (A1), Coolant (A2), Oil Temp (A3), Battery (A4), Brightness (A9), Tach (A7), Speed (A8)
- **Digital Inputs**: Various switches (Pins 4-16) with internal pull-ups
- **Serial Communication**: ESP32 (Pin 19), Raspberry Pi (USB)

## 🚗 **Supported Vehicles**

This project replaces the traditional analog gauges with a modern digital dashboard system using Arduino Mega and Raspberry Pi. It provides real-time monitoring of all essential vehicle parameters with enhanced features like instant/average MPG calculation, fuel consumption tracking, and customizable display themes.

### **Key Features**
- **Real-time sensor monitoring**: Speed, RPM, fuel level, oil pressure, coolant temperature, oil temperature, battery voltage
- **Advanced fuel tracking**: Instant MPG, Average MPG, GPH consumption with accurate display across all styles
- **ALDL integration**: Real-time ECU data for precise fuel consumption calculations
- **Multiple display styles**: Synthwave, Citroën BX, Subaru XT, Nissan 300ZX, Corvette C4 themes
- **Triple display setup**: Left speedometer, center DSI gauges, right tachometer
- **Hardware acceleration**: Optimized for smooth 20Hz refresh rate with robust error handling
- **Ground loop compensation**: Software correction for electrical interference

## 🛠️ **Hardware Requirements**

### **Core Components**
- **Raspberry Pi 4** (recommended for performance)
- **Arduino Mega 2560** (main sensor interface and dashboard control)
- **ESP32 Development Board** (dedicated ALDL ECU data processing)
- **Triple Display Setup**:
  - Left: HDMI-1 (1024x768) - Speedometer
  - Center: DSI-1 (800x480) - Official Pi touchscreen with gauges
  - Right: HDMI-2 (1024x768) - Tachometer

### **Sensors and Connections**
- **Fuel Level**: Pin A15 (470Ω pull-up + 100µF filter)
- **Oil Pressure**: Pin A1 (1kΩ pull-up)
- **Coolant Temperature**: Pin A2 (1kΩ pull-up)
- **Oil Temperature**: Pin A3 (1kΩ pull-up)
- **Battery Voltage**: Pin A4 (voltage divider)
- **Brightness Dimmer**: Pin A5 (voltage divider)
- **Tachometer**: Pin A7 (LM2907N output)
- **Speedometer**: Pin A8 (LM2907N output)
- **ESP32 Communication**: Pin 19 (9600 baud serial from ESP32 ALDL board)

### **ESP32 ALDL Board**
- **ESP32 Development Board** (any ESP32 with GPIO17 and GPIO19)
- **ALDL ECU Connection**: GPIO19 (direct connection to ECU diagnostic port)
- **Arduino Communication**: GPIO17 (serial TX to Arduino Pin 19)
- **Power**: USB 5V (separate from Arduino)
- **Ground**: Common ground with Arduino (essential for serial communication)

### **Digital Switches** (Internal pull-up enabled)
- **Average MPG Switch**: Pin 15
- **Instant MPG Switch**: Pin 5
- **Average Fuel Reset**: Pin 4
- **Trip Odometer Switch**: Pin 16
- **Fuel Range Switch**: Pin 8
- **Trip Odometer Reset**: Pin 7
- **Volts Switch**: Pin 10
- **Coolant Temp Switch**: Pin 11
- **Oil Pressure Switch**: Pin 12
- **Oil Temp Switch**: Pin 13
- **Metric Switch**: Pin 14

## 📦 **Software Installation**

### **Raspberry Pi Setup**

1. **Install Raspberry Pi OS Lite** (for optimal performance)
```bash
sudo apt update
sudo apt install python3-pygame python3-serial python3-pip
sudo apt install xserver-xorg-core xinit x11-xserver-utils xrandr
```

2. **Configure GPU Memory** in `/boot/firmware/config.txt`:
```
gpu_mem=128
dtoverlay=vc4-kms-v3d
hdmi_force_hotplug=1
hdmi_drive=2
disable_overscan=1
```

3. **Setup Display Configuration**:
```bash
DISPLAY=:0 xrandr --output HDMI-1 --mode 1024x768 --pos 0x0 --rotate normal
DISPLAY=:0 xrandr --output HDMI-2 --mode 1024x768 --pos 1024x0 --rotate normal  
DISPLAY=:0 xrandr --output DSI-1 --mode 800x480 --pos 2048x0 --rotate normal
```

4. **Install Dashboard Files**:
   - Copy `arduino_combined_dashboard.py` to `/home/pi/`
   - Copy symbol images (`*.png`) to `/home/pi/`
   - Set up systemd service for auto-start

### **ESP32 ALDL Board Setup**

1. **Install ESP32 Board Support**:
   - Open Arduino IDE
   - Go to File → Preferences
   - Add to Additional Board Manager URLs: `https://dl.espressif.com/dl/package_esp32_index.json`
   - Go to Tools → Board → Boards Manager
   - Search for "ESP32" and install "ESP32 by Espressif Systems"

2. **Upload ESP32 Code**:
   - Select Board: "ESP32 Dev Module" (or your specific ESP32 board)
   - Select correct COM port for ESP32
   - Upload `ESP32_ALDL_Dedicated.ino`

3. **Verify ESP32 Operation**:
   - Open Serial Monitor at 115200 baud
   - Should see: `"ESP32 ALDL Board Starting..."`
   - With ALDL connected: `"ALDL Fuel: X.XXX lb/hr"`

4. **ESP32 Wiring**:
   ```
   ESP32 GPIO17 → Arduino Pin 19
   ESP32 GPIO19 → ALDL wire from ECU
   ESP32 GND    → Arduino GND
   ```

### **Arduino Setup**

1. **Install Arduino IDE**
2. **Upload `arduino_code.cpp`** to Arduino Mega
3. **Verify serial connection** at 115200 baud
4. **Connect ALDL wire** from ECU Pin E (19) to Arduino Pin 19

## ⚙️ **Configuration**

### **Ground Loop Compensation**

**Important**: This system includes software ground loop compensation specifically calibrated for electrical interference patterns. This may not be needed for all vehicles.

**To disable ground loop compensation:**
```cpp
const bool ENABLE_FUEL_GROUND_LOOP_COMPENSATION = false;
```

**To enable (default):**
```cpp
const bool ENABLE_FUEL_GROUND_LOOP_COMPENSATION = true;
```

### **Fuel Sensor Calibration**

The fuel sensor calibration is specific to the circuit design and may need adjustment for different vehicles:

**Current calibration** (470Ω pull-up + 100µF filter):
- **Full tank**: ~0V
- **Empty tank**: ~0.78V
- **Current example**: 0.18V = 45% fuel

**To recalibrate for your vehicle:**
1. Measure actual voltages at different fuel levels
2. Update the voltage thresholds in `fuelLevelPercent()` function
3. Adjust ground loop compensation values if needed

### **Sensor Calibration**

All sensors use lookup tables based on C4 Corvette specifications. For other vehicles, you may need to adjust these values:

#### **Temperature Sensors (Coolant & Oil)**
**C4 Corvette specifications:**
- **185Ω @ 210°F** (hot)
- **3400Ω @ 68°F** (room temperature)  
- **7500Ω @ 39°F** (cold)

**To calibrate for your vehicle:**
1. Measure sensor resistance at known temperatures
2. Update the resistance tables in `coolantTemperatureFahrenheit()` and `oilTemperatureFahrenheit()`
3. Adjust calibration factors if readings don't match original cluster

**Example calibration adjustment:**
```cpp
// Temperature calibration factor based on original cluster comparison
sensorResistance = sensorResistance * 1.47;  // Adjust this multiplier
```

#### **Oil Pressure Sensor**
**C4 Corvette specifications:**
- **1Ω @ 0 PSI** (no pressure)
- **43Ω @ 30 PSI** (normal idle)
- **86Ω @ 60 PSI** (driving)
- **120Ω @ 80 PSI** (maximum)

**Non-linear calibration applied:**
```cpp
if (pressure < 10) {
    pressure = pressure * 4.0;  // Higher correction for low pressure
} else if (pressure < 30) {
    pressure = pressure * 2.5;  // Moderate correction
} else {
    pressure = pressure * 1.5;  // Minimal correction for high pressure
}
```

**To calibrate for your vehicle:**
1. Compare readings with original cluster or known good gauge
2. Adjust the resistance table values in `oilPressurePSI()`
3. Modify the non-linear correction factors as needed

#### **Fuel Level Sensor**
**Circuit-specific calibration** (depends on your pull-up resistor and circuit design):

**Current setup (470Ω pull-up + 100µF filter):**
- **Full tank**: ~0V (0Ω resistance)
- **Current example**: 0.18V = 45% fuel (26Ω resistance)
- **Empty tank**: ~0.78V (90Ω resistance)

**To calibrate for different circuit or vehicle:**
1. Measure actual voltages at known fuel levels
2. Update voltage thresholds in `fuelLevelPercent()` function:
```cpp
if (voltage <= 0.05) {
    fuel_percent = 100.0;  // Full tank threshold
} else if (voltage >= 0.78) {
    fuel_percent = 0.0;    // Empty tank threshold
}
```

#### **Battery Voltage**
**Voltage divider calibration** (R1=14.7kΩ, R2=5.5kΩ):
```cpp
return voltage * 3.79;  // Calibration factor
```

**To calibrate:**
1. Compare Arduino reading with multimeter measurement
2. Adjust the multiplier (3.79) to match actual battery voltage

#### **Brightness Dimmer**
**Voltage range mapping** (6V-14.5V input to 20-100% brightness):
```cpp
float brightness = ((actualVoltage - 6.0) / (14.5 - 6.0)) * 80.0 + 20.0;
```

**To calibrate:**
1. Measure actual dimmer voltage range in your vehicle
2. Adjust the voltage range (6.0V to 14.5V) and brightness range (20% to 100%)

## 🔄 **Sensor Smoothing System**

The dashboard implements adaptive smoothing to eliminate sensor noise while maintaining responsiveness:

### **Smoothing Algorithm**
Each sensor uses a **weighted moving average** with configurable parameters:
```cpp
smoothed_value = (old_value * (1 - smoothing_factor)) + (new_value * smoothing_factor)
```

### **Adaptive Smoothing Parameters**

#### **Fuel Level Smoothing**
```cpp
const float FUEL_SMOOTHING = 0.05;      // 5% new, 95% old (heavy smoothing)
const float FUEL_DEADBAND = 0.5;        // Ignore changes < 0.5%
```
**Adaptive behavior:**
- **Engine running**: Even heavier smoothing (0.03) to reduce electrical noise
- **RC filter**: Hardware 100µF capacitor provides additional noise reduction

#### **RPM Smoothing**
```cpp
const float RPM_FAST_SMOOTHING = 0.8;   // Fast response for large changes (>100 RPM)
const float RPM_SLOW_SMOOTHING = 0.4;   // Moderate response for medium changes
const float RPM_DEADBAND = 30;          // Ignore changes < 30 RPM
```
**Adaptive behavior:**
- **Large changes**: Fast response for acceleration/deceleration
- **Small changes**: Moderate smoothing to eliminate idle oscillation

#### **Speed Smoothing**
```cpp
const float SPEED_FAST_SMOOTHING = 0.95; // Ultra-fast for large changes (>5 MPH)
const float SPEED_SLOW_SMOOTHING = 0.9;  // Very fast for medium changes
const float SPEED_DEADBAND = 0.5;        // Ignore changes < 0.5 MPH
```
**Special features:**
- **Zero speed detection**: Immediate drop to 0 when stopped
- **Acceleration compensation**: Monitors acceleration patterns (currently disabled)

#### **Temperature Smoothing**
```cpp
const float TEMP_SMOOTHING = 0.15;       // 15% new, 85% old
const float TEMP_DEADBAND = 2.0;         // Ignore changes < 2°F
```
**Handles special cases:**
- **"LO" temperature**: Immediate display for disconnected sensors
- **Gradual changes**: Smooth response to prevent erratic readings

#### **Oil Pressure & Voltage Smoothing**
```cpp
const float OIL_PRESSURE_SMOOTHING = 0.3;  // 30% new, 70% old
const float VOLTAGE_SMOOTHING = 0.2;       // 20% new, 80% old
```

### **Deadband System**
**Prevents unnecessary updates** when sensor values fluctuate within normal noise levels:

```cpp
if (abs(new_value - current_value) > DEADBAND_THRESHOLD) {
    // Apply smoothing and update display
    current_value = apply_smoothing(new_value);
} else {
    // Keep current value (no change)
}
```

### **Customizing Smoothing**

**To adjust smoothing for your vehicle:**

1. **Increase smoothing** (more stable, slower response):
```cpp
const float SENSOR_SMOOTHING = 0.1;  // 10% new, 90% old
```

2. **Decrease smoothing** (faster response, more noise):
```cpp
const float SENSOR_SMOOTHING = 0.5;  // 50% new, 50% old
```

3. **Adjust deadband** (sensitivity to changes):
```cpp
const float SENSOR_DEADBAND = 1.0;   // Smaller = more sensitive
```

### **Smoothing Benefits**
- ✅ **Eliminates sensor noise** without losing responsiveness
- ✅ **Adaptive behavior** based on change magnitude
- ✅ **Prevents display flicker** from minor fluctuations
- ✅ **Maintains accuracy** for significant changes
- ✅ **Configurable parameters** for different vehicle characteristics

## 🎨 **Display Styles**

The dashboard supports 5 different visual themes:

1. **Synthwave** (Default) - Retro neon aesthetic
2. **Citroën BX** - Futuristic green theme
3. **Subaru XT** - Amber/orange theme  
4. **Nissan 300ZX** - Turquoise theme
5. **Corvette C4** - Classic red theme

**Style switching**: Hold both trip reset and average fuel reset buttons for 1 second.

### **Recent Improvements (January 2025)**
- **✅ GPH Display Fix**: Resolved critical fuel consumption display bug across all styles
- **✅ Enhanced Error Handling**: Added comprehensive safety checks for sensor data
- **✅ Improved Stability**: Fixed RPM None value crashes and visual display issues
- **✅ Consistent Fuel Display**: All styles now accurately show GPH values (e.g., "0.8 GPH" when idling)

## 🔧 **Troubleshooting**

### **Common Issues**

**Fuel level shows incorrect readings:**
1. Check voltage at Arduino pin A15 with multimeter
2. Verify ground connections between fuel sender and Arduino
3. Confirm 470Ω pull-up resistor value
4. Test with known resistor values (26Ω, 68Ω, 100Ω)

**Ground loop interference:**
1. Ensure all sensor grounds connect to Arduino GND
2. Avoid using chassis ground for precision measurements
3. Adjust ground loop compensation values if needed
4. Consider using shielded cables for long sensor runs

**Display issues:**
1. Check display configuration with `DISPLAY=:0 xrandr`
2. Verify X11 server is running: `ps aux | grep X`
3. Restart display setup script if screens are mirrored
4. Ensure GPU memory is set to 128MB

**Arduino communication:**
1. Verify serial connection: `ls /dev/ttyACM*`
2. Check baud rate (115200)
3. Monitor serial output for sensor data
4. Test individual sensor readings

### **Performance Optimization**

**For best performance:**
- Use Raspberry Pi OS Lite (not desktop version)
- Disable unnecessary services (bluetooth, wifi-powersave)
- Enable hardware acceleration (kmsdrm driver)
- Use quality SD card (Class 10 or better)
- Ensure adequate power supply (3A+ for Pi 4)

## 📊 **Technical Specifications**

### **Performance Metrics**
- **Dashboard refresh rate**: 20Hz
- **Serial communication**: 115200 baud
- **Boot time**: <15 seconds (optimized)
- **Switch response**: <1 second
- **Memory usage**: ~100MB RAM

### **Fuel Consumption Accuracy**
- **ALDL integration**: Real-time ECU data when available
- **RPM fallback**: Accurate estimation based on engine load
- **MPG calculation**: Speed ÷ Fuel Flow Rate (GPH)
- **Range estimation**: Current fuel × Average MPG

### **Electrical Specifications**
- **Operating voltage**: 12V automotive
- **Current consumption**: <500mA total
- **Sensor pull-up resistors**: 470Ω (fuel), 1kΩ (others)
- **ADC resolution**: 10-bit (1024 levels)
- **Voltage dividers**: 3.79:1 (battery), 3.676:1 (dimmer)

## 🤝 **Contributing**

This project is open source and welcomes contributions:

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-feature`
3. **Commit changes**: `git commit -am 'Add new feature'`
4. **Push to branch**: `git push origin feature/new-feature`
5. **Create Pull Request**

### **Areas for Contribution**
- Additional display themes
- Enhanced ALDL protocol support
- Data logging functionality
- Mobile app integration
- Additional vehicle compatibility

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 **Acknowledgments**

- C4 Corvette community for technical specifications
- Original dashboard design inspiration from various automotive manufacturers
- Contributors to the Arduino and Raspberry Pi ecosystems
- ALDL protocol documentation and reverse engineering efforts

## 📞 **Support**

For technical support and questions:
- **GitHub Issues**: Report bugs and feature requests
- **Forum Discussion**: Share experiences and modifications
- **Documentation**: Refer to included markdown files for detailed setup guides

---

**⚠️ Important Safety Notice**: This system is intended for off-road and track use. Ensure all safety systems remain functional and comply with local regulations when modifying vehicle instrumentation.