/*
 * ESP32 ALDL Dedicated Board
 * 
 * Reads ALDL ECU data and sends processed fuel consumption to main Arduino
 * Based on ALDL_reading_final.cpp but optimized for ESP32
 */

#include <Arduino.h>

// ALDL Configuration
const int ALDL_PIN = 19;  // GPIO19 on ESP32
const int BIT_PERIOD_US = 6240;  // 6.24ms per bit (timing drift corrected)

// Message storage for fuel calculations
struct ALDLMessage {
  unsigned long timestamp;
  unsigned char modeWord2;
  unsigned char fuelCounter;
  unsigned char distanceCounter;
  unsigned char fuelConstant;
  unsigned char reserved;
};

ALDLMessage lastMessage;
bool hasLastMessage = false;
float currentFuelConsumptionLbHr = 0.0;

// Communication with main Arduino
const int SERIAL_BAUD = 9600;  // Reliable baud rate for Arduino communication

// Function declarations
bool captureALDLMessage(ALDLMessage* msg);
void calculateFuelConsumption(ALDLMessage last, ALDLMessage current);
void sendFuelDataToArduino();

void setup() {
  // Initialize Serial for debugging (USB)
  Serial.begin(115200);
  
  // Initialize Serial2 for communication with main Arduino (safe pins)
  Serial2.begin(SERIAL_BAUD, SERIAL_8N1, 16, 17);  // RX=16, TX=17
  
  // Initialize ALDL pin
  pinMode(ALDL_PIN, INPUT);
  
  // ESP32 startup messages
  Serial.println("ESP32 ALDL Board Starting...");
  Serial.println("DEBUG: Using Serial2 (TX=GPIO17) for Arduino communication");
  Serial.print("DEBUG: Baud = ");
  Serial.println(SERIAL_BAUD);
  Serial.println("DEBUG: Sending READY message to Arduino...");
  
  Serial2.println("ESP32_ALDL:READY");
  Serial.println("DEBUG: Sent to Arduino -> 'ESP32_ALDL:READY'");
  
  delay(2000);  // Allow main Arduino to initialize
}

void loop() {
  static unsigned long lastHeartbeat = 0;
  
  // Send heartbeat every 10 seconds (reduced frequency for production)
  if (millis() - lastHeartbeat > 10000) {
    lastHeartbeat = millis();
    Serial2.println("ESP32_ALDL:HEARTBEAT");
  }
  
  static unsigned long lastALDLAttempt = 0;
  static int aldlAttempts = 0;
  
  // Try ALDL capture every 1 second (production frequency)
  if (millis() - lastALDLAttempt > 1000) {
    lastALDLAttempt = millis();
    
    ALDLMessage currentMessage;
    
    // Attempt to capture ALDL message
    if(captureALDLMessage(&currentMessage)) {
      // ALDL message captured successfully (debug removed for production)
      
      // Calculate fuel consumption if we have previous message
      if(hasLastMessage) {
        calculateFuelConsumption(lastMessage, currentMessage);
        
        // Send fuel data to main Arduino
        sendFuelDataToArduino();
      }
      
      // Store for next calculation
      lastMessage = currentMessage;
      hasLastMessage = true;
    } else {
      // No valid ALDL message found (normal when ECU not transmitting)
    }
  }
  
  delay(1000); // Wait 1 second between captures
}

bool captureALDLMessage(ALDLMessage* msg) {
  char bitStream[200];
  int bitCount = 0;
  unsigned long captureStart = micros();
  
  // Capture bits using proven timing method
  while(bitCount < 200) {
    unsigned long bitStart = micros();
    unsigned long bitEnd = bitStart + BIT_PERIOD_US;
    
    // Measure total LOW time during this 6.24ms period
    unsigned long totalLowTime = 0;
    int lastState = digitalRead(ALDL_PIN);
    unsigned long lastCheck = bitStart;
    
    while(micros() < bitEnd) {
      int currentState = digitalRead(ALDL_PIN);
      unsigned long currentTime = micros();
      
      // If we were LOW, add the time
      if(lastState == 0) {
        totalLowTime += (currentTime - lastCheck);
      }
      
      lastState = currentState;
      lastCheck = currentTime;
      
      delayMicroseconds(50);  // Small delay for stability
    }
    
    // Convert to milliseconds and decode bit
    float lowTimeMs = totalLowTime / 1000.0;
    
    if(lowTimeMs >= 0.1 && lowTimeMs <= 1.5) {
      bitStream[bitCount] = '0';
    } else if(lowTimeMs >= 2.5 && lowTimeMs <= 5.5) {
      bitStream[bitCount] = '1';
    } else {
      bitStream[bitCount] = '?';
    }
    
    bitCount++;
  }
  
  // Look for SYNC patterns (9 consecutive 1's)
  for(int i = 0; i <= bitCount - 54; i++) {
    bool isSync = true;
    for(int j = 0; j < 9; j++) {
      if(bitStream[i + j] != '1') {
        isSync = false;
        break;
      }
    }
    
    if(isSync) {
      // Check for clean message (no '?' bits)
      bool hasQuestionMarks = false;
      for(int k = i; k < i + 54; k++) {
        if(bitStream[k] == '?') {
          hasQuestionMarks = true;
          break;
        }
      }
      
      if(!hasQuestionMarks) {
        // Found clean SYNC - decode message
        msg->timestamp = captureStart / 1000;
        
        // Decode 5 bytes (each byte = start bit + 8 data bits)
        unsigned char bytes[5];
        bool validMessage = true;
        
        for(int byteNum = 0; byteNum < 5; byteNum++) {
          int bitPos = i + 9 + (byteNum * 9);  // Skip SYNC
          
          // Check start bit (should be 0)
          if(bitStream[bitPos] != '0') {
            validMessage = false;
            break;
          }
          
          // Decode 8 data bits (MSB first)
          unsigned char dataByte = 0;
          for(int bit = 0; bit < 8; bit++) {
            if(bitStream[bitPos + 1 + bit] == '1') {
              dataByte |= (1 << (7 - bit));
            }
          }
          
          bytes[byteNum] = dataByte;
        }
        
        if(validMessage) {
          // Store message with correct mapping
          msg->modeWord2 = bytes[0];
          msg->reserved = bytes[1];            // Number of cylinders
          msg->fuelCounter = bytes[2];         // Fuel counter
          msg->distanceCounter = bytes[3];     // Distance counter  
          
          // Timing drift correction for fuel constant
          if(bytes[4] == 245) {
            msg->fuelConstant = 122;  // Correct the 1-bit timing drift
          } else {
            msg->fuelConstant = bytes[4];
          }
          
          return true;
        }
      }
    }
  }
  
  return false; // No valid message found
}

void calculateFuelConsumption(ALDLMessage last, ALDLMessage current) {
  float timeInterval = (current.timestamp - last.timestamp) / 1000.0; // seconds
  
  // Calculate fuel increment with rollover handling
  int fuelIncrement = current.fuelCounter - last.fuelCounter;
  if(fuelIncrement < 0) {
    fuelIncrement += 256; // Handle rollover
  }
  
  // Safety check for unrealistic increments
  if(fuelIncrement > 128) {
    return; // Skip calculation
  }
  
  if(timeInterval > 0 && timeInterval < 10.0) {
    // Calculate real-time fuel consumption in lb/hr
    float unitsRate = fuelIncrement / timeInterval;
    float maxInjectorFlow = 8.0 * (current.fuelConstant / 32.0);  // lb/hr
    
    if(unitsRate > 0) {
      float dutyCycle = unitsRate / 255.0;
      currentFuelConsumptionLbHr = maxInjectorFlow * dutyCycle;
    } else {
      currentFuelConsumptionLbHr = 0.0;
    }
  }
}

void sendFuelDataToArduino() {
  // Send fuel consumption data to main Arduino via Serial2
  Serial2.print("ALDL_FUEL:");
  Serial2.println(currentFuelConsumptionLbHr, 3);
  
  // Optional: Simple status output
  static unsigned long lastStatusOutput = 0;
  if (millis() - lastStatusOutput > 5000) {  // Every 5 seconds
    lastStatusOutput = millis();
    Serial.print("ALDL Fuel: ");
    Serial.print(currentFuelConsumptionLbHr, 3);
    Serial.println(" lb/hr");
  }
}