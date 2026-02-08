#include <math.h>

// --- Pin Assignments ---
const int fuelPin         = A15;  // Using A15 for fuel sensor
const int oilPressurePin  = A1;
const int coolantTempPin  = A2;  // FIXED: Added missing coolant temperature pin
const int oilTempPin      = A3;
const int batteryVoltPin  = A4;  // Battery voltage measurement (0-20V via voltage divider)
const int dimmerPin       = A9;  // Screen brightness dimmer (6-14.5V via voltage divider) - TESTING DIFFERENT PIN
const int tachometerPin   = A7;  // LM2907N tachometer voltage output (0-5V analog) - MOVED FROM A6
const int speedometerPin  = A8;  // LM2907N speedometer voltage output (0-5V analog) - NEW APPROACH (A6 had issues)
const int ecuSerialPin    = 19;  // ECU ALDL serial data (Pin 19/A5) - 160 baud

#include <SoftwareSerial.h>
SoftwareSerial ecuSerial(ecuSerialPin, -1); // Pin 19 RX, no TX needed

// --- ALDL Fuel Consumption Integration ---
const int ALDL_PIN = 19;  // Same as ecuSerialPin - direct digital read for timing precision

// ALDL Message structure for fuel consumption
struct ALDLMessage {
  unsigned long timestamp;
  unsigned char modeWord2;
  unsigned char fuelCounter;
  unsigned char distanceCounter;
  unsigned char fuelConstant;
  unsigned char reserved;
};

// ALDL variables - LIGHTWEIGHT APPROACH
ALDLMessage lastALDLMessage;
bool hasLastALDLMessage = false;
float currentFuelConsumptionLbHr = 0.0;  // Current fuel consumption in lb/hr
unsigned long lastALDLAttempt = 0;
const unsigned long ALDL_ATTEMPT_INTERVAL = 5000;  // Try ALDL reading every 5 seconds (much less frequent)

// ALDL State Machine for non-blocking operation
enum ALDLState {
  ALDL_IDLE,
  ALDL_LISTENING,
  ALDL_PROCESSING
};
ALDLState aldlState = ALDL_IDLE;
unsigned long aldlStateStartTime = 0;
const unsigned long ALDL_LISTEN_TIMEOUT = 100;  // Maximum 100ms listening time
const int VSS_PIN         = 2;  // External interrupt for speedometer (OLD APPROACH - COMMENTED OUT)
const int ODOMETER_PIN    = 3;  // Odometer stepper motor pulse output
// Pin 3 now used for odometer stepper motor control

// --- New Digital Input Pins (with internal pull-up) ---
const int PIN_AVG_MPG_SWITCH      = 34;  // Average MPG gauge switch
const int PIN_INST_MPG_SWITCH     = 40;  // Instant MPG gauge switch
const int PIN_AVG_FUEL_RESET      = 21;  // Average fuel reset button (moved to pin 21 - pin 6 has hardware issue)
const int PIN_TRIP_ODO_SWITCH     = 16;  // Trip odometer gauge switch (moved from pin 7)
const int PIN_FUEL_RANGE_SWITCH   = 8;   // Fuel range gauge switch
const int PIN_TRIP_ODO_RESET      = 22;  // Trip odometer reset button (moved from 7 to 22 - pin 7 has hardware issue)
const int PIN_VOLTS_SWITCH        = 10;  // Volts gauge switch
const int PIN_COOLANT_TEMP_SWITCH = 11;  // Coolant temp gauge switch
const int PIN_OIL_PRESSURE_SWITCH = 12;  // Oil pressure gauge switch
const int PIN_OIL_TEMP_SWITCH     = 13;  // Oil temp gauge switch
const int PIN_METRIC_SWITCH       = 14;  // Metric system switch

// --- Constants ---
const float VCC = 5.0;  // 5V for all sensors except fuel (fuel uses separate calibration)
const float SERIES_RESISTOR = 1000.0;  // 1kΩ pull-up resistor (changed from 10kΩ to fix ground loop issues)
const float ADC_RESOLUTION = 1023.0;

// --- Fuel Sensor Ground Loop Compensation Flag ---
const bool ENABLE_FUEL_GROUND_LOOP_COMPENSATION = true;  // Set to false to disable compensation
// Temperature sensor constants removed - using lookup table instead
const float PULSES_PER_MILE = 4000.0;  // 0.9 MPH/Hz = 4000 pulses/mile
const float MILES_PER_HOUR_CONV = 3600000.0 / PULSES_PER_MILE; // = 900.0 (ms-based conversion)

// --- Variables ---
volatile unsigned long pulseCount = 0;
unsigned long lastPrintTime = 0;
unsigned long lastPulseCount = 0;
float currentSpeed = 0.0;
float currentRPM = 0.0;

// --- Fuel Level Smoothing Variables (RC Filtered) ---
float displayFuelLevel = 50.0;      // Smoothed fuel level for display
const float FUEL_SMOOTHING = 0.02;  // Very heavy smoothing for sloshing resistance (2% new, 98% old)
const float FUEL_DEADBAND = 1.0;    // Ignore small changes under 1% (reduces sloshing noise)

// --- RPM Smoothing Variables ---
float displayRPM = 0.0;              // Smoothed RPM for display
const float RPM_FAST_SMOOTHING = 0.8;   // Fast response for large RPM changes (>100 RPM)
const float RPM_SLOW_SMOOTHING = 0.4;   // Moderate response for medium changes (50-100 RPM)
const float RPM_DEADBAND = 30;          // Ignore changes smaller than 30 RPM (eliminates idle oscillation)

// --- Oil Pressure Smoothing Variables ---
float displayOilPressure = 0.0;      // Smoothed oil pressure for display
const float OIL_PRESSURE_SMOOTHING = 0.3;  // Moderate smoothing for oil pressure (30% new, 70% old)
const float OIL_PRESSURE_DEADBAND = 2.0;   // Ignore changes smaller than 2 PSI

// --- Voltage Smoothing Variables ---
float displayVoltage = 12.0;         // Smoothed battery voltage for display
const float VOLTAGE_SMOOTHING = 0.2; // Gentle smoothing for voltage (20% new, 80% old)
const float VOLTAGE_DEADBAND = 0.1;  // Ignore changes smaller than 0.1V

// --- Speedometer Smoothing Variables ---
float displaySpeed = 0.0;           // Smoothed speed for display
float lastRawSpeed = 0.0;           // Previous raw speed reading
bool speedIsZero = false;           // Track if we're currently showing zero speed
const float SPEED_NOISE_FILTER = 2.5;     // Ignore changes smaller than 2.5 MPH (reduces noise)
const float SPEED_SMOOTHING = 0.7;        // Moderate smoothing (30% new, 70% old) - responsive but stable

// --- Acceleration Detection Variables ---
float previousRawSpeed = 0.0;       // RAW speed from previous cycle (not smoothed)
float smoothedAcceleration = 0.0;   // Smoothed acceleration to prevent erratic corrections
float currentAcceleration = 0.0;   // Current acceleration (MPH/second)
unsigned long lastSpeedTime = 0;   // Timestamp for acceleration calculation
unsigned long startupTime = 0;     // Time when we left zero speed (for startup spike prevention)

// --- Style Change Combo Detection Variables ---
unsigned long comboStartTime = 0;   // When both buttons were first pressed together
bool comboDetected = false;         // Flag to prevent multiple style change triggers
const unsigned long COMBO_HOLD_TIME = 1000;  // 1 second hold required for style change (reduced from 2s)

// --- Temperature Smoothing Variables ---
float displayCoolantTemp = 180.0;   // Smoothed coolant temperature for display
float displayOilTemp = 180.0;       // Smoothed oil temperature for display
const float TEMP_SMOOTHING = 0.15;  // Moderate smoothing for temperature readings (15% new, 85% old) - faster response
const float TEMP_DEADBAND = 2.0;    // Ignore changes smaller than 2°F (eliminates more sensor noise)

// --- Trip/MPG Calculation Variables ---
// Note: totalDistance and tripDistance moved to Raspberry Pi for better persistence
// Arduino only tracks fuel consumption for MPG calculations
float fuelUsed = 0.0;             // Estimated fuel used (gallons)
float fuelUsedBPW = 0.0;          // Real-time fuel used based on BPW calculations (gallons)
float lastFuelLevel = 0.0;        // Previous fuel level for consumption calculation
float instantMPG = 0.0;           // Current instant MPG
float averageMPG = 0.0;           // Average MPG since last reset
float fuelRange = 0.0;            // Estimated range with current fuel (miles)
float currentFuelFlowGPH = 0.0;   // Current fuel flow in gallons per hour
unsigned long lastMPGCalculation = 0;  // Timing for MPG calculations
bool fuelLevelInitialized = false;     // Flag to initialize fuel level tracking

// --- Odometer Stepper Motor Variables ---
float odometerPulsesAccumulated = 0.0;  // Accumulated fractional pulses
const float ODOMETER_PULSES_PER_MILE = 2002.0;  // Factory specification: 2002 pulses per mile
unsigned long lastOdometerPulse = 0;    // Timing for odometer pulse generation
bool odometerPulseState = false;        // Current state of odometer pulse output

// --- Critical Warning System Variables ---
bool criticalWarningActive = false;     // Flag indicating if any critical warning is active
int criticalWarningType = 0;           // Type of critical warning (1=oil, 2=coolant, 3=battery, 4=fuel)
unsigned long warningStartTime = 0;    // When the warning started (for timing)

// Warning thresholds (production values)
const float CRITICAL_OIL_PRESSURE = 10.0;     // PSI - below this is critical
const float CRITICAL_COOLANT_TEMP = 230.0;    // °F - above this is critical
const float CRITICAL_BATTERY_VOLTAGE = 11.0;  // V - below this is critical
const float CRITICAL_FUEL_LEVEL = 5.0;        // % - below this is critical (reserve)
const float CRITICAL_OIL_TEMP = 280.0;        // °F - above this is critical

// --- Persistent Data Communication ---
// Arduino will send persistent data to Raspberry Pi for storage
// Raspberry Pi will send initialization data back to Arduino on startup
bool persistentDataInitialized = false;
unsigned long lastDataRequest = 0;
const unsigned long DATA_REQUEST_INTERVAL = 5000;  // Request initialization data every 5 seconds until received

// --- Utility Functions ---
float analogToVoltage(int value) {
  // Manual ADC calculation with explicit values
  return (float)value * 5.0 / 1023.0;
}

// Simplified fuel consumption calculation without MAF sensor
// Uses RPM and speed-based estimation for L98 TPI engine

int analogReadAverage(int pin) {
  // Take multiple readings and average them to reduce ADC noise
  const int numSamples = 10;  // Increased from 5 to 10 for smoother readings
  long sum = 0;
  
  for (int i = 0; i < numSamples; i++) {
    sum += analogRead(pin);
    delayMicroseconds(200);  // Increased delay for more stable readings
  }
  
  return sum / numSamples;
}

float voltageToResistance(float voltage) {
  // Temperature sensors with 1kΩ pull-up resistor (changed from 10kΩ to fix ground loop issues)
  // Circuit: +5V -> 1kΩ -> Arduino_Pin -> Sensor -> GND
  // Voltage divider: Vmeasured = Vcc * Rsensor / (Rpullup + Rsensor)
  // Rearranged: Rsensor = Rpullup * Vmeasured / (Vcc - Vmeasured)
  
  if (voltage <= 0.005) return 0.0;       // Very low voltage = very low resistance
  if (voltage >= 4.95) return 1000000.0;  // Very high voltage = open circuit
  
  // Calculate sensor resistance using 1kΩ pull-up value
  float sensorResistance = SERIES_RESISTOR * voltage / (VCC - voltage);
  
  // Temperature calibration factor based on original cluster comparison:
  // Dashboard shows 198°F, Original cluster shows 183°F
  // Need to reduce by factor of 0.92 (183/198 = 0.92)
  sensorResistance = sensorResistance * 1.47;  // Reduced from 1.6 to 1.47 (0.92x total)
  
  return sensorResistance;
}

float voltageToResistanceFuel(float voltage) {
  // Fuel sensor with RC filter: 1kΩ pull-up + 1kΩ series + 100µF capacitor
  // Circuit: +5V -> 1kΩ (pull-up) -> Arduino_Pin -> 1kΩ (series) -> 100µF || Fuel_Sender -> GND
  // This creates a voltage divider: Max voltage = 2.5V when fuel sender = 0Ω
  
  const float FUEL_PULLUP_RESISTOR = 1000.0;  // 1kΩ pull-up for fuel sensor
  
  // Note: This function is now bypassed by fuelLevelPercent() which uses direct voltage calibration
  // The 1kΩ series resistor creates a voltage divider, so max voltage is ~2.5V
  
  if (voltage <= 0.005) return 0.0;        // Very low voltage = very low resistance
  if (voltage >= 2.45) return 150.0;       // Very high voltage = maximum fuel level (adjusted for voltage divider)
  
  // Calculate sensor resistance accounting for voltage divider effect
  float sensorResistance = FUEL_PULLUP_RESISTOR * voltage / (VCC - voltage);
  
  return sensorResistance;
}

float voltageToResistanceOilPressure(float voltage) {
  // Oil pressure sensor with 1kΩ pull-up resistor (changed from 10kΩ to fix ground loop issues)
  // Circuit: +5V -> 1kΩ -> Arduino_Pin -> Sensor -> GND
  // Voltage divider: Vmeasured = Vcc * Rsensor / (Rpullup + Rsensor)
  // Rearranged: Rsensor = Rpullup * Vmeasured / (Vcc - Vmeasured)
  
  if (voltage <= 0.005) return 0.0;       // Very low voltage = very low resistance
  if (voltage >= 4.95) return 1000000.0;  // Very high voltage = open circuit
  
  // Calculate sensor resistance using 1kΩ pull-up value
  float sensorResistance = SERIES_RESISTOR * voltage / (VCC - voltage);
  
  // Oil pressure calibration factor - Non-linear correction based on original cluster comparison:
  // Low pressure: Dashboard 10 PSI, Original 32 PSI (need +220%)
  // High pressure: Dashboard 70 PSI, Original 63 PSI (need -10%)
  // This suggests non-linear sensor response
  sensorResistance = sensorResistance * 0.8;  // Base calculation (back to original)
  
  return sensorResistance;
}

float oilTemperatureFahrenheit(float resistance) {
  // C4 Corvette Oil Temperature Sensor - Original Factory Specifications
  // 185Ω @ 210°F, 3400Ω @ 68°F, 7500Ω @ 39°F
  
  // Very high resistance indicates sensor disconnected or very cold
  if (resistance > 10000) {
    return -999.0;  // Special value indicating "LO" temperature (disconnected)
  }
  
  // Original factory resistance vs temperature table (high to low resistance)
  const float resistanceTable[] = {7500, 3400, 185};
  const float temperatureTable[] = {39, 68, 210};
  const int tableSize = 3;
  
  // Handle out of range values
  if (resistance >= resistanceTable[0]) return temperatureTable[0];  // 39°F (very cold)
  if (resistance <= resistanceTable[tableSize-1]) return temperatureTable[tableSize-1];  // 210°F (hot)
  
  // Find the two points to interpolate between
  for (int i = 0; i < tableSize - 1; i++) {
    if (resistance <= resistanceTable[i] && resistance >= resistanceTable[i + 1]) {
      // Linear interpolation between two points
      float r1 = resistanceTable[i];
      float r2 = resistanceTable[i + 1];
      float t1 = temperatureTable[i];
      float t2 = temperatureTable[i + 1];
      
      // Interpolate (note: resistance decreases as temperature increases)
      float ratio = (r1 - resistance) / (r1 - r2);
      return t1 + ratio * (t2 - t1);
    }
  }
  
  // Fallback
  return 68.0;  // Default to room temperature
}

float coolantTemperatureFahrenheit(float resistance) {
  // C4 Corvette Coolant Temperature Sensor - Original Factory Specifications
  // 185Ω @ 210°F, 3400Ω @ 68°F, 7500Ω @ 39°F
  
  // Very high resistance indicates sensor disconnected or very cold
  if (resistance > 10000) {
    return -999.0;  // Special value indicating "LO" temperature (disconnected)
  }
  
  // Original factory resistance vs temperature table (high to low resistance)
  const float resistanceTable[] = {7500, 3400, 185};
  const float temperatureTable[] = {39, 68, 210};
  const int tableSize = 3;
  
  // Handle out of range values
  if (resistance >= resistanceTable[0]) return temperatureTable[0];  // 39°F (very cold)
  if (resistance <= resistanceTable[tableSize-1]) return temperatureTable[tableSize-1];  // 210°F (hot)
  
  // Find the two points to interpolate between
  for (int i = 0; i < tableSize - 1; i++) {
    if (resistance <= resistanceTable[i] && resistance >= resistanceTable[i + 1]) {
      // Linear interpolation between two points
      float r1 = resistanceTable[i];
      float r2 = resistanceTable[i + 1];
      float t1 = temperatureTable[i];
      float t2 = temperatureTable[i + 1];
      
      // Interpolate (note: resistance decreases as temperature increases)
      float ratio = (r1 - resistance) / (r1 - r2);
      return t1 + ratio * (t2 - t1);
    }
  }
  
  // Fallback
  return 68.0;  // Default to room temperature
}

float fuelLevelPercent(float resistance) {
  // MAXIMUM RANGE FUEL SENSOR CALIBRATION - 470Ω pull-up + capacitor only
  // Circuit: +5V -> 470Ω (pull-up) -> Arduino_Pin -> 100µF || Fuel_Sender -> GND
  // MAXIMUM voltage range: 0.804V - best possible ground loop immunity!
  
  // Get the actual voltage (bypass resistance calculation for RC filtered sensor)
  float voltage = analogToVoltage(analogReadAverage(fuelPin));
  

  
  // GROUND LOOP COMPENSATION based on actual measurements
  // Engine stopped: 0.18V, Engine running: 0.58V = +0.40V increase
  extern float currentRPM;  // Access RPM from main loop
  if (ENABLE_FUEL_GROUND_LOOP_COMPENSATION && currentRPM > 100) {
    // Engine running (RPM > 100) - compensate for 0.40V ground loop increase
    voltage = voltage - 0.40;  // Subtract the voltage increase
  }
  
  // ACTUAL VOLTAGE CALIBRATION based on your correct measurements:
  // Full tank (0Ω): 4.99V
  // Current fuel (26Ω): 0.18V = 45% fuel (matches factory cluster)
  // Empty tank (100Ω): 0.78V
  // Excellent range: 0.60V (0.78V - 0.18V)
  
  if (voltage > 3.0) {
    // Disconnected sensor or very full tank
    return 100.0;
  } else if (voltage > 0.85) {
    // Above empty threshold
    return 0.0;
  } else {
    // CALIBRATION based on your actual measurements:
    // Current fuel: 0.18V = 45%, Empty: 0.78V = 0%, Full: ~0V = 100%
    
    float fuel_percent;  // Declare the variable
    
    // CORRECTED: Higher voltage = Higher fuel level (inverted from previous logic)
    if (voltage >= 0.78) {
      fuel_percent = 100.0;  // Full tank (high voltage)
    } else if (voltage <= 0.05) {
      fuel_percent = 0.0;    // Empty tank (low voltage)
    } else if (voltage >= 0.18) {
      // At or above current level: 0.78V (100%) to 0.18V (45%)
      fuel_percent = 45.0 + ((voltage - 0.18) / (0.78 - 0.18)) * 55.0;
    } else {
      // Below current level: 0.18V (45%) to 0.05V (0%)
      fuel_percent = (voltage / 0.18) * 45.0;
    }
    
    // Clamp to valid range
    if (fuel_percent < 0.0) fuel_percent = 0.0;
    if (fuel_percent > 100.0) fuel_percent = 100.0;
    
    return fuel_percent;
  }
}

float oilPressurePSI(float resistance) {
  // C4 Corvette Oil Pressure Sensor - Original Factory Specifications
  // 1Ω @ 0 PSI, 43Ω @ 30 PSI, 86Ω @ 60 PSI
  
  // Very high resistance indicates sensor disconnected - show 0 PSI (warning condition)
  if (resistance > 200) {
    return 0.0;  // Disconnected sensor = 0 PSI (triggers warning)
  }
  
  // Extended factory resistance vs pressure table (based on real car data)
  // Real car shows 115.8Ω when running - extend calibration range to factory 80 PSI max
  const float resistanceTable[] = {1, 43, 86, 120};
  const float pressureTable[] = {0, 30, 60, 80};  // Factory maximum 80 PSI
  const int tableSize = 4;
  
  // Handle out of range values
  if (resistance <= resistanceTable[0]) return pressureTable[0];  // 0 PSI
  if (resistance >= resistanceTable[tableSize-1]) return pressureTable[tableSize-1];  // 60 PSI
  
  // Find the two points to interpolate between
  for (int i = 0; i < tableSize - 1; i++) {
    if (resistance >= resistanceTable[i] && resistance <= resistanceTable[i + 1]) {
      // Linear interpolation between two points
      float r1 = resistanceTable[i];
      float r2 = resistanceTable[i + 1];
      float p1 = pressureTable[i];
      float p2 = pressureTable[i + 1];
      
      // Interpolate (note: resistance increases as pressure increases)
      float ratio = (resistance - r1) / (r2 - r1);
      float pressure = p1 + ratio * (p2 - p1);
      
      // Apply non-linear calibration correction based on real-world testing:
      // Oil pressure sensors are non-linear, especially at low pressures
      if (pressure < 10) {
        // Low pressure range: was showing 5 PSI, should show ~20 PSI
        pressure = pressure * 4.0;  // Higher correction for low pressure
      } else if (pressure < 30) {
        // Mid pressure range: moderate correction
        pressure = pressure * 2.5;
      } else {
        // High pressure range: minimal correction
        pressure = pressure * 1.5;
      }
      
      return pressure;
    }
  }
  
  // Fallback - apply same non-linear correction
  float pressure = 0.0;  // Default to 0 PSI (safe fallback)
  
  // Apply non-linear calibration correction for fallback case too
  if (pressure < 10) {
    pressure = pressure * 4.0;
  } else if (pressure < 30) {
    pressure = pressure * 2.5;
  } else {
    pressure = pressure * 1.5;
  }
  
  return pressure;
}

float batteryVoltage(float voltage) {
  // Convert voltage divider reading back to actual battery voltage
  // Updated calibration based on multimeter comparison:
  // Dashboard was reading 2-4% high with factor 3.9
  // Corrected factor: 3.79 (3.9 × 0.97 = 3.79)
  // Measured resistors: R1=14.7kΩ, R2=5.5kΩ
  // Voltage divider ratio: 5.5/(14.7+5.5) = 0.272
  return voltage * 3.79;
}

float dimmerBrightness(float voltage) {
  // Convert voltage divider reading back to actual dimmer voltage
  // Measured resistors: R1=14.7kΩ, R2=5.5kΩ
  // Voltage divider ratio: 5.5/(14.7+5.5) = 0.272
  // Multiply by 3.676 to get original voltage
  float actualVoltage = voltage * 3.676;
  
  // If voltage is very low (floating input), return default brightness
  if (actualVoltage < 3.0) {
    return 90.0;  // Default 90% brightness when dimmer not connected
  }
  
  // Convert 6V-14.5V range to 20-100% brightness (never completely dark)
  actualVoltage = constrain(actualVoltage, 6.0, 14.5);
  float brightness = ((actualVoltage - 6.0) / (14.5 - 6.0)) * 80.0 + 20.0;
  return brightness;
}

// --- Interrupts ---
void countPulse() {
  pulseCount++;
}

// --- Trip/MPG Calculation Functions ---
void updateDistanceAndMPG(float deltaTime, float speed, float fuelLevel) {
  // Note: Distance calculation moved to Raspberry Pi for better persistence
  // Arduino only handles fuel consumption and MPG calculations now
  
  // Calculate distance traveled this interval (in miles) - for odometer stepper motor only
  float distanceIncrement = (speed * deltaTime) / 3600000.0; // speed in MPH, time in ms
  
  // Update odometer stepper motor (physical hardware still needs Arduino control)
  updateOdometer(distanceIncrement);
  
  // Initialize fuel level tracking on first run
  if (!fuelLevelInitialized) {
    lastFuelLevel = fuelLevel;
    fuelLevelInitialized = true;
    return; // Skip MPG calculation on first run
  }
  
  // Calculate fuel consumption (only if fuel level decreased)
  float fuelLevelChange = lastFuelLevel - fuelLevel;
  if (fuelLevelChange > 0.1) { // Only count significant fuel level drops (> 0.1%)
    // Convert fuel level percentage to gallons (C4 Corvette has ~20 gallon tank)
    float fuelConsumed = (fuelLevelChange / 100.0) * 20.0;
    fuelUsed += fuelConsumed;
    lastFuelLevel = fuelLevel;
  }
  
  // Calculate instant MPG and fuel flow - let Raspberry Pi handle display logic
  // ESP32 ALDL calculation is already in GPH (not lb/hr as originally thought)
  currentFuelFlowGPH = currentFuelConsumptionLbHr;  // Direct assignment - no conversion needed
  
  if (currentRPM > 500) { // Engine running
    if (speed > 1.0 && currentFuelFlowGPH > 0.01) { 
      // Car moving and consuming fuel - calculate MPG
      instantMPG = speed / currentFuelFlowGPH;
      
      // Limit to reasonable range
      if (instantMPG > 50.0) instantMPG = 50.0;
      if (instantMPG < 1.0) instantMPG = 1.0;
      
      // Accumulate real-time fuel consumption for average MPG
      fuelUsedBPW += (currentFuelFlowGPH * deltaTime) / 3600000.0; // Convert ms to hours
    } else {
      // Engine running but not moving (idling) - Pi will show GPH
      instantMPG = 0.0; // Special value for idling (Pi will use FUEL_FLOW_GPH instead)
    }
  } else {
    // Engine off - no fuel consumption
    instantMPG = -1.0; // Special value for "OFF" display
    currentFuelFlowGPH = 0.0; // No fuel flow when engine off
  }
  
  // Note: Average MPG calculation moved to Raspberry Pi
  // Arduino only calculates instant MPG, Pi calculates average MPG using trip distance
  
  // Calculate fuel range (miles remaining with current fuel)
  float currentFuelGallons = (fuelLevel / 100.0) * 20.0; // Convert % to gallons
  if (averageMPG > 0) {
    fuelRange = currentFuelGallons * averageMPG;
  } else if (instantMPG > 0 && instantMPG < 50.0) {
    // Only use positive instant MPG values (not special -1.0 or -2.0 values)
    fuelRange = currentFuelGallons * instantMPG;
  } else {
    fuelRange = currentFuelGallons * 15.0; // Conservative 15 MPG estimate
  }
  
  // Limit range to reasonable maximum
  if (fuelRange > 500.0) fuelRange = 500.0;
}

void resetTripOdometer() {
  // Note: Trip distance now reset by Raspberry Pi
  fuelUsed = 0.0;
  fuelUsedBPW = 0.0; // Reset real-time fuel consumption too
  averageMPG = 0.0;
  // Note: Don't reset lastFuelLevel - keep tracking continuous
  
  // Send reset command to Raspberry Pi
  Serial.println("RESET_TRIP:");
  sendPersistentDataUpdate();
}

void resetAverageFuel() {
  fuelUsed = 0.0;
  fuelUsedBPW = 0.0; // Reset real-time fuel consumption too
  averageMPG = 0.0;
  // Reset the baseline for fuel consumption tracking
  // This allows recalculating average MPG from this point forward
  
  // Immediately send reset values to Raspberry Pi
  sendPersistentDataUpdate();
}

// --- Odometer Stepper Motor Functions ---
void updateOdometer(float distanceIncrement) {
  // Add distance to accumulated pulses
  odometerPulsesAccumulated += distanceIncrement * ODOMETER_PULSES_PER_MILE;
  
  // Generate pulses when we have accumulated at least 1 pulse worth of distance
  while (odometerPulsesAccumulated >= 1.0) {
    generateOdometerPulse();
    odometerPulsesAccumulated -= 1.0;
  }
}

void generateOdometerPulse() {
  // Generate a square wave pulse for the odometer stepper motor
  // Factory spec: 2002 pulses per mile in square wave form
  // Pulse width should be appropriate for stepper motor (typically 1-10ms)
  
  unsigned long now = millis();
  
  // Generate 5ms pulse (high for 5ms, then low)
  if (!odometerPulseState) {
    digitalWrite(ODOMETER_PIN, HIGH);
    odometerPulseState = true;
    lastOdometerPulse = now;
  } else if (now - lastOdometerPulse >= 5) {
    digitalWrite(ODOMETER_PIN, LOW);
    odometerPulseState = false;
  }
}

// --- Persistent Data Communication Functions ---
void requestPersistentData() {
  // Request initialization data from Raspberry Pi
  Serial.println("INIT_REQUEST:PERSISTENT_DATA");
}

void processPersistentDataResponse() {
  // Check for incoming persistent data from Raspberry Pi
  if (Serial.available()) {
    String response = Serial.readStringUntil('\n');
    response.trim();
    
    if (response.startsWith("AVG_MPG_UPDATE:")) {
      // Receive calculated average MPG from Raspberry Pi
      String data = response.substring(15); // Remove "AVG_MPG_UPDATE:" prefix
      averageMPG = data.toFloat();
      return;
    }
    
    if (response.startsWith("INIT_DATA:")) {
      // Parse initialization data: INIT_DATA:fuel_used,fuel_used_bpw
      String data = response.substring(10); // Remove "INIT_DATA:" prefix
      
      int firstComma = data.indexOf(',');
      int secondComma = data.indexOf(',', firstComma + 1);
      int thirdComma = data.indexOf(',', secondComma + 1);
      
      if (firstComma > 0) {
        // New format: only fuel consumption data (distance handled by Pi)
        fuelUsed = data.substring(0, firstComma).toFloat();
        
        // Parse real-time fuel consumption if available
        if (secondComma > firstComma) {
          fuelUsedBPW = data.substring(firstComma + 1).toFloat();
        }
        
        // Note: Average MPG calculation moved to Raspberry Pi
        
        persistentDataInitialized = true;
      }
    }
  }
}

void sendPersistentDataUpdate() {
  // Send current persistent data to Raspberry Pi for storage
  // Only fuel consumption data (distance now calculated by Pi)
  Serial.print("SAVE_DATA:");
  Serial.print(fuelUsed, 4); Serial.print(",");
  Serial.print(fuelUsedBPW, 4);
  Serial.println();
}

// --- Critical Warning System Functions ---
void checkCriticalWarnings(float oilPSI, float coolantTemp, float batteryVolts, float fuelPct, float oilTemp) {
  bool warningDetected = false;
  int newWarningType = 0;
  
  // Check each critical parameter (in order of severity)
  if (oilPSI < CRITICAL_OIL_PRESSURE) {
    warningDetected = true;
    newWarningType = 1; // Oil pressure critical
  } else if (coolantTemp > CRITICAL_COOLANT_TEMP) {
    warningDetected = true;
    newWarningType = 2; // Coolant temperature critical
  } else if (oilTemp > CRITICAL_OIL_TEMP) {
    warningDetected = true;
    newWarningType = 5; // Oil temperature critical
  } else if (batteryVolts < CRITICAL_BATTERY_VOLTAGE) {
    warningDetected = true;
    newWarningType = 3; // Battery voltage critical
  } else if (fuelPct < CRITICAL_FUEL_LEVEL) {
    warningDetected = true;
    newWarningType = 4; // Fuel level critical
  }
  
  // Update warning state
  if (warningDetected && !criticalWarningActive) {
    // New warning detected
    criticalWarningActive = true;
    criticalWarningType = newWarningType;
    warningStartTime = millis();
  } else if (warningDetected && criticalWarningActive && newWarningType != criticalWarningType) {
    // Different warning detected - switch to new one
    criticalWarningType = newWarningType;
    warningStartTime = millis();
  } else if (!warningDetected && criticalWarningActive) {
    // Warning condition cleared
    criticalWarningActive = false;
    criticalWarningType = 0;
  }
}

// --- LM2907N Tachometer Functions ---
float readTachometerRPM() {
  // Read voltage from LM2907N frequency-to-voltage converter
  int analog_value = analogRead(tachometerPin);
  float voltage = analog_value * (5.0 / 1023.0);
  
  // UPDATED CALIBRATION based on real car testing:
  // Your readings: 0.64-0.66V = 700-750 RPM idle
  // Calibration factor adjusted for your specific LM2907N circuit
  
  if (voltage < 0.1) {
    return 0.0; // Engine off or very low signal
  }
  
  // REAL CAR CALIBRATION - Non-linear correction based on original cluster comparison:
  // Low RPM: Dashboard 600, Original 700 (need +17%)
  // High RPM: Dashboard 1200, ECU 1100 (need -8%)
  // This suggests non-linear LM2907N response
  
  float rpm = (voltage / 0.65) * 660.0;  // Base calculation (back to original)
  
  // Apply non-linear correction based on RPM range
  if (rpm < 1000) {
    // Low RPM range - increase by 17%
    rpm = rpm * 1.17;
  } else {
    // High RPM range - apply graduated correction
    // At 1000 RPM: +17%, At 1200+ RPM: -8%
    // Linear interpolation between correction factors
    float correctionFactor = 1.17 - ((rpm - 1000) / 200.0) * 0.25;  // Gradually reduce correction
    correctionFactor = constrain(correctionFactor, 0.92, 1.17);  // Limit between -8% and +17%
    rpm = rpm * correctionFactor;
  }
  
  // Final offset correction: was showing 500, should show 550
  rpm = rpm + 50;
  
  // Reasonable limits for C4 Corvette
  if (rpm > 6500) rpm = 6500;  // Redline limit
  if (rpm < 0) rpm = 0;
  
  return rpm;
}

float readSpeedometerMPH() {
  // NEW LM2907N SPEEDOMETER APPROACH
  // Read voltage from LM2907N speedometer frequency-to-voltage converter
  int analog_value = analogRead(speedometerPin);
  float voltage = analog_value * (5.0 / 1023.0);
  
  // VOLTAGE DEBUG OUTPUT (uncomment for hardware testing)
  // Serial.print("V:"); Serial.print(voltage, 3); Serial.print(",");
  
  // Threshold to ignore noise and accidental touching
  if (voltage < 0.15) {  // Increased from 0.05V to 0.15V to reduce sensitivity to touching
    return 0.0; // Vehicle stopped or very low signal
  }
  
  // Handle zener diode clamping at high speeds (above ~92 MPH)
  float calibrated_voltage = voltage;
  if (voltage >= 5.0) {
    // Voltage is clamped by 5.1V zener diode at high speeds
    // Use special calibration for clamped region (above ~92 MPH)
    // This is a non-linear region, but we can estimate
    float excess_current = (voltage - 5.1) / 47000.0;  // Current through zener
    calibrated_voltage = 5.1 + (excess_current * 22000.0);  // Estimate unclamped voltage
  }
  
  // UPDATED CALIBRATION for 47kΩ load resistor (was 22kΩ):
  // Load resistor change: 22kΩ → 47kΩ = 2.14x higher voltage output
  // Original: 15Hz - 0.45V, 39Hz - 1.02V, 61Hz - 1.53V, 85Hz - 2.04V, 90Hz - 2.10V
  // New with 47kΩ: 15Hz - 0.96V, 39Hz - 2.18V, 61Hz - 3.27V, 85Hz - 4.37V, 90Hz - 4.49V
  // Updated approximation: ~0.051 V/Hz (voltage = frequency * 0.051)
  // So: frequency = voltage / 0.051
  
  // CORRECTED: Based on oscilloscope measurements
  // User data: 24Hz->33MPH, 42Hz->45MPH, 15Hz->30MPH, 57Hz->52MPH
  // Current calibration is reading WAY too high
  
  // VOLTAGE-TO-FREQUENCY conversion based on latest oscilloscope data:
  // User measured: 88Hz produces 3.34V on Arduino
  // Therefore: 88Hz ÷ 3.34V = 26.3 Hz/V
  // Conversion: frequency = voltage ÷ 0.038 (or voltage × 26.3)
  
  // NEW LM2907 CALIBRATION - REDESIGNED PCB WITH STABLE TACHOMETER ARCHITECTURE
  // User bench test data with new stable design:
  // 0 Hz → 0V, 7 Hz → 0.34V, 37 Hz → 0.91V, 55 Hz → 1.36V, 68 Hz → 1.65V, 86 Hz → 2.06V
  // Linear response: ~41.7 Hz/V or 0.024 V/Hz
  // Assuming VSS: ~1.5 Hz per MPH, this gives: MPH = Voltage × 41.7 ÷ 1.5 = Voltage × 27.8
  
  float mph;
  if (voltage < 0.1) {
    mph = 0.0;  // Below 0.1V = zero speed (noise threshold)
  } else {
    mph = voltage * 37.5;  // Updated calibration based on real GPS correlation data
  }
  
  // Reasonable limits for vehicle speed
  if (mph > 200) mph = 200;  // Speed limit
  if (mph < 0) mph = 0;
  
  return mph;
}

// --- ALDL Fuel Consumption Functions - LIGHTWEIGHT NON-BLOCKING ---
void tryALDLReading() {
  // Read fuel data from dedicated ESP32 ALDL board on Pin 19 (Serial1)
  if (Serial1.available()) {
    String line = Serial1.readStringUntil('\n');
    line.trim();
    
    // Debug: Show ALL received data
    Serial.print("ARDUINO_DEBUG: Received from ESP32: '");
    Serial.print(line);
    Serial.println("'");
    
    if (line.startsWith("ALDL_FUEL:")) {
      float receivedFuel = line.substring(10).toFloat();
      if (receivedFuel >= 0.0 && receivedFuel <= 50.0) {  // Sanity check
        currentFuelConsumptionLbHr = receivedFuel;
        Serial.print("ESP32_FUEL (Pin 19): ");
        Serial.print(currentFuelConsumptionLbHr, 3);
        Serial.println(" lb/hr - SUCCESS!");
      } else {
        Serial.print("ESP32_FUEL: Invalid value ");
        Serial.println(receivedFuel);
      }
    }
    else if (line.startsWith("ESP32_ALDL:READY")) {
      Serial.println("ESP32 ALDL board connected (Pin 19)");
    }
    else if (line.startsWith("ESP32_ALDL:HEARTBEAT")) {
      Serial.println("ESP32 ALDL heartbeat received (Pin 19)");
    }
    else {
      Serial.print("ESP32_UNKNOWN: ");
      Serial.println(line);
    }
  }
  
  // Debug: Show connection status every 10 seconds
  static unsigned long lastStatusCheck = 0;
  if (millis() - lastStatusCheck > 10000) {
    lastStatusCheck = millis();
    Serial.print("ARDUINO_STATUS: Waiting for ESP32 on Pin 19, Current fuel = ");
    Serial.println(currentFuelConsumptionLbHr, 3);
  }
}

void estimateFuelConsumptionFromRPM() {
  // FALLBACK: Estimate fuel consumption from RPM when ALDL is not available
  // This provides reasonable fuel consumption estimates without blocking
  
  if(currentRPM < 500) {
    currentFuelConsumptionLbHr = 0.0;  // Engine off
    return;
  }
  
  // RPM-based fuel consumption estimation (lb/hr)
  // Based on typical L98 TPI fuel consumption patterns
  float estimatedLbHr;
  
  if(currentRPM < 800) {
    // Idle
    estimatedLbHr = 4.8;  // ~0.8 GPH * 6 lb/gal = 4.8 lb/hr
  } else if(currentRPM < 1500) {
    // Low RPM cruise
    float rpmRatio = (currentRPM - 800) / 700.0;
    estimatedLbHr = 4.8 + (rpmRatio * 7.2);  // 4.8 to 12.0 lb/hr
  } else if(currentRPM < 2500) {
    // Normal cruise - factor in speed
    float baseConsumption = 12.0 + (currentRPM - 1500) * 0.006;  // 12.0-18.0 lb/hr
    float speedFactor = (currentSpeed > 0) ? (currentSpeed / 60.0) : 1.0;
    estimatedLbHr = baseConsumption * speedFactor;
  } else if(currentRPM < 4000) {
    // Highway/acceleration
    float baseConsumption = 18.0 + (currentRPM - 2500) * 0.012;  // 18.0-36.0 lb/hr
    float speedFactor = (currentSpeed > 0) ? (currentSpeed / 60.0) : 1.0;
    estimatedLbHr = baseConsumption * speedFactor;
  } else {
    // High RPM
    estimatedLbHr = 48.0 + (currentRPM - 4000) * 0.018;  // 48.0+ lb/hr
  }
  
  // Apply reasonable limits
  if(estimatedLbHr < 0.0) estimatedLbHr = 0.0;
  if(estimatedLbHr > 120.0) estimatedLbHr = 120.0;  // 20 GPH max
  
  // Smooth the estimate to prevent jumps
  currentFuelConsumptionLbHr = (currentFuelConsumptionLbHr * 0.8) + (estimatedLbHr * 0.2);
}

// --- Setup ---
void setup() {
  Serial.begin(115200);  // 12x faster serial communication for ultra-low latency
  ecuSerial.begin(160);  // ECU ALDL serial communication at 160 baud (not used since ALDL goes to ESP32)
  Serial1.begin(9600);   // ESP32 ALDL communication on Pin 19 (hardware serial)
  
  Serial.println("=== ARDUINO READY - WAITING FOR ESP32 ON PIN 19 ===");
  Serial.println("=== ESP32 COMMUNICATION DEBUG MODE ACTIVE ===");
  
  // Set ADC reference to external 5V (default, but make it explicit)
  analogReference(DEFAULT);  // Use 5V as ADC reference
  
  // Setup new digital inputs with internal pull-up resistors
  pinMode(PIN_AVG_MPG_SWITCH, INPUT_PULLUP);
  pinMode(PIN_INST_MPG_SWITCH, INPUT_PULLUP);
  pinMode(PIN_AVG_FUEL_RESET, INPUT_PULLUP);
  pinMode(PIN_TRIP_ODO_SWITCH, INPUT_PULLUP);
  pinMode(PIN_FUEL_RANGE_SWITCH, INPUT_PULLUP);
  pinMode(PIN_TRIP_ODO_RESET, INPUT_PULLUP);
  pinMode(PIN_VOLTS_SWITCH, INPUT_PULLUP);
  pinMode(PIN_COOLANT_TEMP_SWITCH, INPUT_PULLUP);
  pinMode(PIN_OIL_PRESSURE_SWITCH, INPUT_PULLUP);
  pinMode(PIN_OIL_TEMP_SWITCH, INPUT_PULLUP);
  pinMode(PIN_METRIC_SWITCH, INPUT_PULLUP);
  
  // Setup odometer stepper motor output
  pinMode(ODOMETER_PIN, OUTPUT);
  digitalWrite(ODOMETER_PIN, LOW);
  
  // OLD PULSE-COUNTING SPEEDOMETER INTERRUPT (COMMENTED OUT)
  // attachInterrupt(digitalPinToInterrupt(VSS_PIN), countPulse, RISING);
  
  // NEW: Both tachometer and speedometer use LM2907N analog inputs - no interrupts needed
  
  // Initialize fuel/MPG variables to prevent random startup values
  // Note: Distance variables moved to Raspberry Pi
  fuelUsed = 0.0;
  fuelUsedBPW = 0.0;
  averageMPG = 0.0;  // Will be received from Pi
  instantMPG = -2.0; // Start with "OFF" display
  fuelRange = 0.0;
  fuelLevelInitialized = false;
  
  // Initialize ALDL fuel consumption system - LIGHTWEIGHT
  pinMode(ALDL_PIN, INPUT);  // Set ALDL pin as input for quick digital reading
  currentFuelConsumptionLbHr = 0.0;
  hasLastALDLMessage = false;
  aldlState = ALDL_IDLE;
  lastALDLAttempt = 0;
  aldlStateStartTime = 0;
  
  Serial.println("=== ARDUINO CODE VERSION 2.5 - LIGHTWEIGHT ALDL INTEGRATION ===");
  Serial.println("=== DATA RATE: 20 Hz (50ms intervals) - PERFORMANCE OPTIMIZED ===");
  Serial.println("=== RASPBERRY PI OPTIMIZED FOR HIGH-SPEED PROCESSING ===");
  Serial.println("=== ALDL + RPM-BASED FUEL CONSUMPTION (NON-BLOCKING) ===");
  Serial.println("  A4 = Battery Voltage (via voltage divider)");
  Serial.println("  A5 = Dimmer (via voltage divider)");
  Serial.println("  A7 = Tachometer (LM2907N output) - MOVED FROM A6");
  Serial.println("  Pin 2 = VSS (Vehicle Speed Sensor)");
  Serial.println("  Pin 19 = ALDL ECU Data (160 baud + direct timing)");
  Serial.println("Requesting persistent data from Raspberry Pi...");
}

// ECU Serial Data Reading (1988 Corvette ALDL Protocol)
void readECUData() {
  static byte ecuBuffer[5];
  static int bufferIndex = 0;
  static unsigned long lastECUData = 0;
  
  // Read available ECU data
  while (ecuSerial.available()) {
    byte incomingByte = ecuSerial.read();
    
    // Store in buffer
    ecuBuffer[bufferIndex] = incomingByte;
    bufferIndex++;
    
    // When we have 5 bytes (complete ECU packet)
    if (bufferIndex >= 5) {
      // Parse ECU data packet
      parseECUPacket(ecuBuffer);
      bufferIndex = 0; // Reset for next packet
      lastECUData = millis();
    }
  }
  
  // Reset buffer if no data for too long (prevent stuck buffer)
  if (millis() - lastECUData > 5000 && bufferIndex > 0) {
    bufferIndex = 0;
  }
}

void parseECUPacket(byte packet[5]) {
  // 1988 Corvette ECU Protocol:
  // Byte 0: MW2 (status bits)
  // Bytes 1-4: Data addresses ($C009, $011A, $011E, $C712)
  
  byte statusByte = packet[0]; // MW2 status byte
  
  // Extract status bits (1988 format)
  bool overdriveOn = (statusByte & 0x01) != 0;  // Bit 0: Overdrive
  bool shiftLight = (statusByte & 0x80) != 0;   // Bit 7: Shift light
  
  // Data bytes (need to decode based on addresses)
  // This is raw data - will need to interpret based on ECU documentation
  byte numCylinders = packet[1];    // $C009: Number of cylinders
  byte fuelData = packet[2];        // $011A: Fuel supplied data
  byte distanceData = packet[3];    // $011E: Distance traveled data
  byte scaleData = packet[4];       // $C712: Scale factor data
  
  // Send ECU data to Raspberry Pi for processing
  Serial.print("ECU_DATA:");
  Serial.print("OD="); Serial.print(overdriveOn ? 1 : 0);
  Serial.print(",SHIFT="); Serial.print(shiftLight ? 1 : 0);
  Serial.print(",CYL="); Serial.print(numCylinders, HEX);
  Serial.print(",FUEL="); Serial.print(fuelData, HEX);
  Serial.print(",DIST="); Serial.print(distanceData, HEX);
  Serial.print(",SCALE="); Serial.print(scaleData, HEX);
  Serial.println();
  
  // Debug: Print raw packet in hex
  Serial.print("ECU_RAW:");
  for (int i = 0; i < 5; i++) {
    if (packet[i] < 16) Serial.print("0");
    Serial.print(packet[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
}

// --- Main Loop ---
void loop() {
  unsigned long now = millis();
  
  // Read ECU data continuously
  readECUData();
  
  // Try ALDL fuel consumption reading (non-blocking, timing-critical)
  tryALDLReading();
  
  if (now - lastPrintTime >= 100) {  // Reduced to 100ms (10 Hz) to balance with switch data
    // Read sensors with multiple samples for stability (ADC noise reduction)
    // Using 1kΩ pull-up resistors to eliminate ground loop issues
    float fuelR     = voltageToResistanceFuel(analogToVoltage(analogReadAverage(fuelPin)));        // 1kΩ pull-up
    float oilR      = voltageToResistanceOilPressure(analogToVoltage(analogReadAverage(oilPressurePin))); // 1kΩ pull-up
    float coolantR  = voltageToResistance(analogToVoltage(analogReadAverage(coolantTempPin)));     // 1kΩ pull-up
    float oilTempR  = voltageToResistance(analogToVoltage(analogReadAverage(oilTempPin)));        // 1kΩ pull-up
    
    // Read voltage measurements
    float batteryV  = analogToVoltage(analogRead(batteryVoltPin));
    float dimmerV   = analogToVoltage(analogRead(dimmerPin));

    // Convert to values
    float rawFuelPct = fuelLevelPercent(fuelR);
    float rawOilPSI = oilPressurePSI(oilR);
    float rawCoolantF  = coolantTemperatureFahrenheit(coolantR);
    float rawOilTempF  = oilTemperatureFahrenheit(oilTempR);
    float rawBatteryVolts = batteryVoltage(batteryV);
    float brightness = dimmerBrightness(dimmerV);

    // Adaptive Fuel Level Smoothing - heavier smoothing when engine running
    // Note: Hardware RC filter (1kΩ + 100µF) should significantly reduce noise
    // Software smoothing can be reduced if hardware filter is effective
    float fuelLevelDiff = abs(rawFuelPct - displayFuelLevel);
    
    // Enhanced fuel smoothing to handle sloshing during acceleration/turning
    // More aggressive smoothing when engine running (acceleration/braking/turning)
    float adaptiveFuelSmoothing = (currentRPM > 500) ? 0.01 : FUEL_SMOOTHING; // Extra heavy smoothing when driving
    float adaptiveDeadband = (currentRPM > 500) ? 1.5 : FUEL_DEADBAND; // Larger deadband when driving
    
    if (rawFuelPct >= 99.5) {
      // Disconnected sensor or very full tank - bypass smoothing for immediate 100% display
      displayFuelLevel = 100.0;
    } else if (fuelLevelDiff > adaptiveDeadband) {
      // Apply heavy smoothing for fuel level changes (anti-sloshing)
      displayFuelLevel = displayFuelLevel * (1.0 - adaptiveFuelSmoothing) + rawFuelPct * adaptiveFuelSmoothing;
    }
    // If difference is within deadband, keep current value (no change)
    
    // Use smoothed fuel level for output
    float fuelPct = displayFuelLevel;

    // Oil Pressure Smoothing - reduce erratic readings from fast updates
    float oilPressureDiff = abs(rawOilPSI - displayOilPressure);
    
    if (oilPressureDiff > OIL_PRESSURE_DEADBAND) {
      // Apply moderate smoothing for oil pressure changes
      displayOilPressure = displayOilPressure * (1.0 - OIL_PRESSURE_SMOOTHING) + rawOilPSI * OIL_PRESSURE_SMOOTHING;
    }
    // If difference is within deadband, keep current value (no change)
    
    // Use smoothed oil pressure for output
    float oilPSI = displayOilPressure;

    // Battery Voltage Smoothing - reduce erratic readings from alternator noise
    float voltageDiff = abs(rawBatteryVolts - displayVoltage);
    
    if (voltageDiff > VOLTAGE_DEADBAND) {
      // Apply gentle smoothing for voltage changes
      displayVoltage = displayVoltage * (1.0 - VOLTAGE_SMOOTHING) + rawBatteryVolts * VOLTAGE_SMOOTHING;
    }
    // If difference is within deadband, keep current value (no change)
    
    // Use smoothed voltage for output
    float batteryVolts = displayVoltage;



    // Temperature Smoothing - reduce erratic readings
    float coolantTempDiff = abs(rawCoolantF - displayCoolantTemp);
    float oilTempDiff = abs(rawOilTempF - displayOilTemp);
    
    // Handle special "LO" temperature values (-999.0)
    if (rawCoolantF <= -999) {
      displayCoolantTemp = rawCoolantF;  // Pass through "LO" immediately
    } else if (coolantTempDiff > TEMP_DEADBAND) {
      // Apply smoothing for normal temperature changes
      displayCoolantTemp = displayCoolantTemp * (1.0 - TEMP_SMOOTHING) + rawCoolantF * TEMP_SMOOTHING;
    }
    // If difference is within deadband, keep current value (no change)
    
    if (rawOilTempF <= -999) {
      displayOilTemp = rawOilTempF;  // Pass through "LO" immediately
    } else if (oilTempDiff > TEMP_DEADBAND) {
      // Apply smoothing for normal temperature changes
      displayOilTemp = displayOilTemp * (1.0 - TEMP_SMOOTHING) + rawOilTempF * TEMP_SMOOTHING;
    }
    // If difference is within deadband, keep current value (no change)
    
    // Use smoothed temperatures for output
    float coolantF = displayCoolantTemp;
    float oilTempF = displayOilTemp;

    // Read new digital input states (LOW = pressed/active due to pull-up)
    int avgMpgSwitch      = !digitalRead(PIN_AVG_MPG_SWITCH);
    int instMpgSwitch     = !digitalRead(PIN_INST_MPG_SWITCH);
    int avgFuelReset      = !digitalRead(PIN_AVG_FUEL_RESET);
    int tripOdoSwitch     = !digitalRead(PIN_TRIP_ODO_SWITCH);
    int fuelRangeSwitch   = !digitalRead(PIN_FUEL_RANGE_SWITCH);
    int tripOdoReset      = !digitalRead(PIN_TRIP_ODO_RESET);
    int voltsSwitch       = !digitalRead(PIN_VOLTS_SWITCH);
    int coolantTempSwitch = !digitalRead(PIN_COOLANT_TEMP_SWITCH);
    int oilPressureSwitch = !digitalRead(PIN_OIL_PRESSURE_SWITCH);
    int oilTempSwitch     = !digitalRead(PIN_OIL_TEMP_SWITCH);
    int metricSwitch      = !digitalRead(PIN_METRIC_SWITCH);

    // TEMPORARY DEBUG: Print MPG switch states every 2 seconds
    static unsigned long lastDebugPrint = 0;
    if (now - lastDebugPrint >= 2000) {
      Serial.print("DEBUG_MPG - Pin34_RAW:");
      Serial.print(digitalRead(PIN_AVG_MPG_SWITCH));
      Serial.print(" Pin40_RAW:");
      Serial.print(digitalRead(PIN_INST_MPG_SWITCH));
      Serial.print(" AvgMpgSW:");
      Serial.print(avgMpgSwitch);
      Serial.print(" InstMpgSW:");
      Serial.print(instMpgSwitch);
      Serial.println();
      
      // Debug button states
      Serial.print("DEBUG_BUTTONS - Pin21_RAW:");
      Serial.print(digitalRead(PIN_AVG_FUEL_RESET));
      Serial.print(" Pin22_RAW:");
      Serial.print(digitalRead(PIN_TRIP_ODO_RESET));
      Serial.print(" AvgResetBtn:");
      Serial.print(avgFuelReset);
      Serial.print(" TripResetBtn:");
      Serial.print(tripOdoReset);
      Serial.println();
      
      lastDebugPrint = now;
    }

    // Button states are sent to Raspberry Pi in the regular data stream
    // No timing logic needed in Ardu

    // Calculate deltaTime for trip/MPG calculations
    float deltaTime = now - lastPrintTime;
    
    // NEW: Calculate speed from LM2907N analog voltage
    float rawSpeed = readSpeedometerMPH();
    
    // SAFETY: Prevent extreme speed values that could cause issues
    if (rawSpeed > 250.0) rawSpeed = 250.0;  // Cap at reasonable maximum
    if (rawSpeed < 0.0) rawSpeed = 0.0;      // Prevent negative speed
    
    // ACCELERATION DETECTION AND CORRECTION (TEMPORARILY DISABLED)
    // Calculate acceleration for monitoring (but don't apply correction yet)
    if (lastSpeedTime > 0 && deltaTime > 0 && deltaTime < 1000) {  // Ignore huge time gaps
      float timeDelta = deltaTime / 1000.0;  // Convert to seconds
      
      // Calculate raw acceleration using unsmoothed speed values
      currentAcceleration = (rawSpeed - previousRawSpeed) / timeDelta;  // MPH/second
      
      // Smooth the acceleration to prevent erratic corrections
      smoothedAcceleration = smoothedAcceleration * 0.7 + currentAcceleration * 0.3;  // 30% new, 70% old
      
      // CORRECTION TEMPORARILY DISABLED - was over-correcting at higher speeds
      // Need to analyze the acceleration patterns first before applying corrections
      /*
      if (smoothedAcceleration > 4.0) {
        // Strong acceleration detected - apply gentle correction
        float correctionFactor = 1.0 - (smoothedAcceleration - 4.0) * 0.05;  // Reduce by 5% per MPH/s above 4
        if (correctionFactor < 0.85) correctionFactor = 0.85;  // Max 15% reduction (much gentler)
        rawSpeed = rawSpeed * correctionFactor;
      }
      */
    }
    
    // Update previous values for next acceleration calculation
    previousRawSpeed = rawSpeed;  // Use RAW speed, not smoothed
    lastSpeedTime = now;
    
    // Adaptive Speed Smoothing - similar to RPM smoothing but tuned for speedometer
    float speedDifference = abs(rawSpeed - lastRawSpeed);
    
    // SAFETY: Prevent extreme speed differences that could cause issues
    if (speedDifference > 100.0) speedDifference = 100.0;  // Cap large jumps
    
    // Hysteresis for zero speed detection (prevents oscillation at low speeds)
    // Use the already-calculated rawSpeed instead of reading voltage again
    
    if (!speedIsZero) {
      // Currently showing speed - use threshold to go to zero FAST
      if (rawSpeed < 2.0) {  // Simple speed-based zero detection
        displaySpeed = 0.0;
        currentSpeed = 0.0;
        speedIsZero = true;
      }
    } else {
      // Currently showing zero - use higher threshold to show speed
      if (rawSpeed > 4.0) {  // Leave zero when speed is clearly above zero
        speedIsZero = false;
        startupTime = now;  // Record when we started moving
        // STARTUP SPIKE PREVENTION: Start with gentle speed, not raw reading
        displaySpeed = min(rawSpeed * 0.3, 8.0);  // Start with 30% of raw speed, max 8 MPH
        currentSpeed = displaySpeed;
      } else {
        // Stay at zero
        displaySpeed = 0.0;
        currentSpeed = 0.0;
      }
    }
    
    // NOISE FILTERING - reduces ±3 MPH fluctuations without delays
    if (!speedIsZero) {
      if (speedDifference <= SPEED_NOISE_FILTER) {
        // Small change - likely noise, ignore it
        currentSpeed = displaySpeed;
      } else if (speedDifference > 10.0) {
        // Large change - use immediately (acceleration/deceleration)
        displaySpeed = rawSpeed;
        currentSpeed = rawSpeed;
      } else {
        // Medium change - apply light smoothing to reduce noise
        displaySpeed = displaySpeed * (1.0 - SPEED_SMOOTHING) + rawSpeed * SPEED_SMOOTHING;
        currentSpeed = displaySpeed;
      }
    }
    

    
    lastRawSpeed = rawSpeed;
    

    
    // OLD PULSE-COUNTING SPEEDOMETER APPROACH (COMMENTED OUT)
    /*
    // Calculate speed from pulses
    unsigned long pulsesNow = pulseCount;
    unsigned long deltaPulses = pulsesNow - lastPulseCount;
    currentSpeed = (deltaPulses * MILES_PER_HOUR_CONV) / deltaTime;
    

    
    lastPulseCount = pulsesNow;
    */

    // Read RPM from LM2907N tachometer with adaptive smoothing
    float rawRPM = readTachometerRPM();
    
    // Adaptive RPM smoothing - fast response for revving, smooth for idle
    float rpmDifference = abs(rawRPM - displayRPM);
    
    if (rpmDifference > 100) {
      // Large RPM change (revving) - fast response
      displayRPM = displayRPM * (1.0 - RPM_FAST_SMOOTHING) + rawRPM * RPM_FAST_SMOOTHING;
    } else if (rpmDifference > RPM_DEADBAND) {
      // Medium RPM change - moderate response
      displayRPM = displayRPM * (1.0 - RPM_SLOW_SMOOTHING) + rawRPM * RPM_SLOW_SMOOTHING;
    }
    // If difference is within deadband, keep current value (eliminates idle oscillation)
    
    currentRPM = displayRPM;

    // Update trip/MPG calculations always (handles all engine states)
    updateDistanceAndMPG(deltaTime, currentSpeed, fuelPct);
    


    // Check for critical warnings
    checkCriticalWarnings(oilPSI, coolantF, batteryVolts, fuelPct, oilTempF);

    // Handle persistent data communication
    if (!persistentDataInitialized) {
      // Keep requesting initialization data until received
      unsigned long now = millis();
      if (now - lastDataRequest >= DATA_REQUEST_INTERVAL) {
        requestPersistentData();
        lastDataRequest = now;
      }
      processPersistentDataResponse();
    }

    // DIAGNOSTIC OUTPUT: Disabled for performance - enable only when needed for troubleshooting
    // Serial.print("RAW PINS - A0:"); Serial.print(analogRead(fuelPin));
    // Serial.print(" A1:"); Serial.print(analogRead(oilPressurePin));
    // Serial.print(" A2:"); Serial.print(analogRead(coolantTempPin));
    // Serial.print(" A3:"); Serial.print(analogRead(oilTempPin));
    // Serial.print(" A4:"); Serial.print(analogRead(batteryVoltPin));
    // Serial.print(" A5:"); Serial.print(analogRead(dimmerPin));
    // Serial.print(" A7:"); Serial.print(analogRead(tachometerPin));
    // Serial.print(" A8:"); Serial.print(analogRead(speedometerPin));
    // Serial.println();
    

    // Serial.print(" ADC:"); Serial.print(oilR, 1);
    // Serial.print(" PSI:"); Serial.print(oilPSI, 1);
    // Serial.print(" Coolant V:"); Serial.print(analogToVoltage(analogRead(coolantTempPin)), 3);
    // Serial.print(" R:"); Serial.print(coolantR, 1);
    // Serial.print(" OilTemp V:"); Serial.print(analogToVoltage(analogRead(oilTempPin)), 3);
    // Serial.print(" R:"); Serial.print(oilTempR, 1);
    // Serial.println();

    // Output essential data with optimized Pi processing
    Serial.print("SPEED:"); Serial.print(currentSpeed, 1); Serial.print(",");
    Serial.print("FUEL:"); Serial.print(fuelPct, 1); Serial.print(",");
    Serial.print("OIL:"); Serial.print(oilPSI, 1); Serial.print(",");
    Serial.print("COOLANT:"); Serial.print(coolantF, 1); Serial.print(",");
    Serial.print("OILTEMP:"); Serial.print(oilTempF, 1); Serial.print(",");
    Serial.print("RPM:"); Serial.print(currentRPM, 0); Serial.print(",");
    Serial.print("BATTERY:"); Serial.print(batteryVolts, 1); Serial.print(",");
    Serial.print("BRIGHTNESS:"); Serial.print(brightness, 1); Serial.print(",");
    Serial.print("FUEL_CONSUMPTION:"); Serial.print(currentFuelConsumptionLbHr, 3);
    Serial.println();
    
    // Send switch states and other data more frequently (every 200ms for better responsiveness)
    static unsigned long lastSwitchUpdate = 0;
    if (now - lastSwitchUpdate >= 150) {  // Increased frequency for better responsiveness
      // IMPORTANT: Critical data FIRST so it's not truncated
      // Button data first (for style change)
      Serial.print("TRIP_BTN:"); Serial.print(tripOdoReset); Serial.print(",");
      Serial.print("AVG_BTN:"); Serial.print(avgFuelReset); Serial.print(",");
      // DSI gauge switches next (for display switching) - shortened names
      Serial.print("OIL_P_SW:"); Serial.print(oilPressureSwitch); Serial.print(",");
      Serial.print("OIL_T_SW:"); Serial.print(oilTempSwitch); Serial.print(",");
      Serial.print("COOL_SW:"); Serial.print(coolantTempSwitch); Serial.print(",");
      Serial.print("VOLT_SW:"); Serial.print(voltsSwitch); Serial.print(",");
      // Then other data - shortened names
      Serial.print("FUELRNG:"); Serial.print(fuelRange, 1); Serial.print(",");
      Serial.print("IMPG:"); Serial.print(instantMPG, 1); Serial.print(",");
      Serial.print("AMPG:"); Serial.print(averageMPG, 1); Serial.print(",");
      Serial.print("FLOW:"); Serial.print(currentFuelFlowGPH, 3); Serial.print(",");
      Serial.print("AMPG_SW:"); Serial.print(avgMpgSwitch); Serial.print(",");
      Serial.print("IMPG_SW:"); Serial.print(instMpgSwitch); Serial.print(",");
      Serial.print("TRIP_SW:"); Serial.print(tripOdoSwitch); Serial.print(",");
      Serial.print("FUELR_SW:"); Serial.print(fuelRangeSwitch); Serial.print(",");
      Serial.print("METR_SW:"); Serial.print(metricSwitch);
      Serial.println();
      lastSwitchUpdate = now;
    }

    lastPrintTime = now;
  }
  
  // Periodic odometer data saving every 10 seconds
  static unsigned long lastOdometerSave = 0;
  if (now - lastOdometerSave >= 10000) {  // 10 seconds = 10000 milliseconds
    sendPersistentDataUpdate();
    lastOdometerSave = now;
  }
}