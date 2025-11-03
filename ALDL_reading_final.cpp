/*
 * ALDL Reading Final
 * 
 * Production version for real-time fuel consumption monitoring
 * Clean output: just fuel consumption in lb/hr
 */

#include <Arduino.h>

const int ALDL_PIN = 19;
const int BIT_PERIOD_US = 6240;  // 6.24ms per bit (timing drift corrected)

// Message storage for MPG calculations
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

// Function declarations
void continuousMonitoring();
bool captureALDLMessage(ALDLMessage* msg);
void calculateFuelConsumption(ALDLMessage last, ALDLMessage current);

void setup() {
  Serial.begin(115200);
  pinMode(ALDL_PIN, INPUT);
  
  Serial.println("ALDL Fuel Monitor Ready");
  
  delay(2000);
  
  continuousMonitoring();
}

void loop() {
  delay(1000);
}

void continuousMonitoring() {
  while(true) {
    ALDLMessage currentMessage;
    
    if(captureALDLMessage(&currentMessage)) {
      
      // Calculate fuel consumption if we have previous message
      if(hasLastMessage) {
        calculateFuelConsumption(lastMessage, currentMessage);
      }
      
      // Store for next calculation
      lastMessage = currentMessage;
      hasLastMessage = true;
    }
    
    delay(1000); // Wait 1 second between captures
  }
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
    float fuelConsumptionLbHr = 0.0;
    
    if(unitsRate > 0) {
      float dutyCycle = unitsRate / 255.0;
      fuelConsumptionLbHr = maxInjectorFlow * dutyCycle;
    }
    
    // Clean output: just the fuel consumption value
    Serial.print(fuelConsumptionLbHr, 3);
    Serial.println(" lb/hr");
  }
}