import pygame
import serial
import math
import time
import os
import subprocess
import json
import signal
import sys
from datetime import datetime

print("THIS IS A DEBUG MESSAGE 1")
# Remove window positioning to match temp_debug_with_grid.py
# os.environ['SDL_VIDEO_WINDOW_POS'] = '-1024,0'  # DISABLED - was preventing center screen access

# Configure SDL for Raspberry Pi displays
os.environ['DISPLAY'] = ':0'  # Use X11 display
os.environ['SDL_VIDEODRIVER'] = 'x11'  # Use X11 for multi-head support

pygame.init()
pygame.mixer.quit()  # Disable audio to stop ALSA errors

# Extended window to include all three screens side by side
TOTAL_WIDTH = 5000  # Increased width to prevent tachometer clipping
SCREEN_HEIGHT = 768  # Keep original height (DSI is 480 but we'll handle rotation)
SINGLE_SCREEN_WIDTH = 1024

# Dashboard style system
current_style_index = 0
STYLE_SYNTHWAVE = 0
STYLE_CITROEN_BX = 1
STYLE_SUBARU_XT = 2
STYLE_NISSAN_300ZX = 3
STYLE_CORVETTE_C4 = 4

# Citroën BX style colors (futuristic dark green)
BX_GREEN = (0, 255, 100)      # Bright futuristic green
BX_DARK_GREEN = (0, 150, 60)  # Darker green for backgrounds
BX_DIM_GREEN = (0, 100, 40)   # Dimmed green for inactive elements
BX_BLACK = (0, 20, 10)        # Very dark green-tinted black

# Subaru XT style colors (amber/orange theme)
XT_AMBER = (255, 191, 0)       # Bright amber
XT_DARK_AMBER = (200, 120, 0)  # Darker amber for backgrounds
XT_DIM_AMBER = (150, 90, 0)    # Dimmed amber for inactive elements
XT_BLACK = (20, 15, 0)         # Very dark amber-tinted black

# Nissan 300ZX style colors (futuristic glowing turquoise theme)
ZX_BLACK = (0, 10, 15)        # Dark blue-tinted black background
ZX_TURQUOISE = (0, 255, 255)  # Bright glowing turquoise
ZX_BRIGHT_TURQUOISE = (100, 255, 255)  # Even brighter for active elements
ZX_DIM_TURQUOISE = (0, 150, 150)      # Dimmed turquoise for inactive elements
ZX_DARK_TURQUOISE = (0, 100, 100)     # Darker turquoise for backgrounds
DSI_SCREEN_WIDTH = 800
DSI_SCREEN_HEIGHT = 480
DSI_X_OFFSET = 2048  # DSI screen starts after both HDMI screens

# Check if fullscreen mode is requested (default to fullscreen for dashboard)
fullscreen_mode = os.environ.get('COMBINED_FULLSCREEN', '1') == '1'  # Default to '1' (fullscreen)

if fullscreen_mode:
    # Use borderless window spanning all screens at position (0,0)
    screen = pygame.display.set_mode((TOTAL_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
    print("Combined dashboard started in BORDERLESS FULLSCREEN mode")
else:
    screen = pygame.display.set_mode((TOTAL_WIDTH, SCREEN_HEIGHT))
    print("Combined dashboard started in WINDOWED mode")
    print("Instructions: Press F11 for fullscreen")

pygame.display.set_caption("C4 Dual Dashboard - Combined")
pygame.mouse.set_visible(False)  # Hide mouse cursor for dashboard
clock = pygame.time.Clock()

# Track fullscreen state
is_fullscreen = fullscreen_mode

# Create surfaces for each dashboard (will be rotated)
speedometer_surface = pygame.Surface((1024, 768))
tachometer_surface = pygame.Surface((1024, 968))  # Increased height by 200px total for odometer space

# Load symbol images
try:
    coolant_temp_symbol = pygame.image.load("coolant_temp_symbol.png")
    oil_symbol = pygame.image.load("oil_symbol.png")
    gas_pump_symbol = pygame.image.load("gas_pump_symbol.png")
    battery_symbol = pygame.image.load("battery_symbol.png")
    print("Symbol images loaded successfully")
except Exception as e:
    print(f"Warning: Could not load symbol images: {e}")
    coolant_temp_symbol = None
    oil_symbol = None
    gas_pump_symbol = None
    battery_symbol = None

# Colors
BLACK = (0, 0, 0)
BRIGHT_GREEN = (0, 255, 0)
DULL_GREEN = (0, 100, 0)
YELLOW = (255, 255, 0)
NEON_PINK = (255, 20, 147)
NEON_CYAN = (0, 255, 255)
PURPLE = (138, 43, 226)
ORANGE = (255, 165, 0)
RED = (255, 0, 0)

# SPEEDOMETER PARAMETERS - ADJUSTED UP FOR BETTER SYNTHWAVE POSITIONING
SPEEDO_X_OFFSET = 350
SPEEDO_Y_OFFSET = 480  # Moved up for better Synthwave layout (was 550, now 480, -70px up)
SPEEDO_LENGTH = 350
SPEEDO_DIGITAL_X = 550
SPEEDO_DIGITAL_Y = 320  # Moved up for better Synthwave layout (was 390, now 320, -70px up)
SPEEDO_NUMBER_DISTANCE = 50
SPEEDO_GRID_X = 650
SPEEDO_GRID_Y = 180  # Moved up for better Synthwave layout (was 250, now 180, -70px up)

# TACHOMETER PARAMETERS - ADJUSTED FOR EXPANDED SURFACE (MOVED MORE DOWN)
TACHO_X_OFFSET = 350
TACHO_Y_OFFSET = 550  # Moved down more (was 520, now 550, +30px down)
TACHO_LENGTH = 350
TACHO_DIGITAL_X = 550
TACHO_DIGITAL_Y = 590  # Moved down more (was 560, now 590, +30px down)
TACHO_NUMBER_DISTANCE = 50
TACHO_GRID_X = 650
TACHO_GRID_Y = 430  # Moved down more (was 400, now 430, +30px down)

# Arduino Serial Configuration
SERIAL_BAUD = 115200  # 12x faster serial communication for ultra-low latency
SERIAL_TIMEOUT = 0.1  # Reliable timeout for stable connection

# Auto-detect Arduino port
def find_arduino_port():
    """Automatically find Arduino serial port"""
    import serial.tools.list_ports
    
    # Common Arduino ports to try first
    common_ports = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']
    
    # Get all available ports
    available_ports = [port.device for port in serial.tools.list_ports.comports()]
    
    # Try common ports first
    for port in common_ports:
        if port in available_ports:
            try:
                test_ser = serial.Serial(port, SERIAL_BAUD, timeout=1)
                test_ser.close()
                print(f"Found Arduino on {port}")
                return port
            except:
                continue
    
    # Try other available ports
    for port in available_ports:
        if port not in common_ports:
            try:
                test_ser = serial.Serial(port, SERIAL_BAUD, timeout=1)
                test_ser.close()
                print(f"Found Arduino on {port}")
                return port
            except:
                continue
    
    return None

SERIAL_PORT = find_arduino_port() or '/dev/ttyACM0'  # Fallback to default

# Persistent Data Management
PERSISTENT_DATA_FILE = "corvette_persistent_data.json"

class PersistentDataManager:
    def __init__(self):
        self.data = {
            "total_odometer": 89240.5,  # Current odometer reading
            "trip_odometer": 0.0,
            "fuel_used": 0.0,
            "fuel_used_bpw": 0.0,  # Real-time fuel consumption tracking
            "dashboard_style": 0,  # 0=Synthwave, 1=Citroën BX
            "last_updated": datetime.now().isoformat(),
            "save_count": 0
        }
        self.load_data()
    
    def load_data(self):
        """Load persistent data from JSON file"""
        try:
            if os.path.exists(PERSISTENT_DATA_FILE):
                with open(PERSISTENT_DATA_FILE, 'r') as f:
                    loaded_data = json.load(f)
                    self.data.update(loaded_data)
                print(f"Loaded persistent data: Total ODO: {self.data['total_odometer']:.1f} miles, "
                      f"Trip: {self.data['trip_odometer']:.1f} miles")
            else:
                print("No existing persistent data file found, starting with defaults")
                self.save_data()
        except Exception as e:
            print(f"Error loading persistent data: {e}")
    
    def save_data(self):
        """Save persistent data to JSON file"""
        try:
            self.data["last_updated"] = datetime.now().isoformat()
            self.data["save_count"] += 1
            
            # Create backup every 1000 saves
            if self.data["save_count"] % 1000 == 0:
                backup_file = f"{PERSISTENT_DATA_FILE}.backup_{int(time.time())}"
                if os.path.exists(PERSISTENT_DATA_FILE):
                    import shutil
                    shutil.copy2(PERSISTENT_DATA_FILE, backup_file)
                    print(f"Created backup: {backup_file}")
            
            with open(PERSISTENT_DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
            
        except Exception as e:
            print(f"Error saving persistent data: {e}")
    
    def update_data(self, total_odo, trip_odo, fuel_used, fuel_used_bpw=0.0):
        """Update and save persistent data"""
        # Check if data has changed significantly to avoid excessive disk writes
        odo_changed = abs(self.data["total_odometer"] - total_odo) >= 0.1  # Save if odometer changed by 0.1+ miles
        trip_changed = abs(self.data["trip_odometer"] - trip_odo) >= 0.1   # Save if trip changed by 0.1+ miles
        fuel_changed = abs(self.data["fuel_used"] - fuel_used) >= 0.01     # Save if fuel changed by 0.01+ gallons
        bpw_changed = abs(self.data["fuel_used_bpw"] - fuel_used_bpw) >= 0.01  # Save if BPW fuel changed by 0.01+ gallons
        
        # Always update the data in memory
        self.data["total_odometer"] = total_odo
        self.data["trip_odometer"] = trip_odo
        self.data["fuel_used"] = fuel_used
        self.data["fuel_used_bpw"] = fuel_used_bpw
        
        # Only save to disk if significant change occurred
        if odo_changed or trip_changed or fuel_changed or bpw_changed:
            self.save_data()
    
    def send_init_data(self, ser):
        """Send initialization data to Arduino"""
        if ser and ser.is_open:
            try:
                init_message = f"INIT_DATA:{self.data['fuel_used']:.4f},{self.data['fuel_used_bpw']:.4f}\n"
                ser.write(init_message.encode())
                # Init data sent to Arduino
                
                # Also send calculated average MPG
                total_fuel_used = self.data["fuel_used"] + self.data["fuel_used_bpw"]
                if total_fuel_used > 0.01 and self.data["trip_odometer"] > 0.01:
                    avg_mpg = self.data["trip_odometer"] / total_fuel_used
                    if avg_mpg > 50.0:
                        avg_mpg = 50.0
                    mpg_message = f"AVG_MPG_UPDATE:{avg_mpg:.1f}\n"
                    ser.write(mpg_message.encode())
                else:
                    ser.write(b"AVG_MPG_UPDATE:0.0\n")
            except Exception as e:
                print(f"Error sending init data: {e}")

# Initialize persistent data manager
persistent_data = PersistentDataManager()

# Button timing variables
button_trip_start_time = 0
button_avg_start_time = 0
button_combo_start_time = 0
button_trip_triggered = False
button_avg_triggered = False
button_combo_triggered = False
BUTTON_HOLD_TIME = 1000  # 1 second in milliseconds

def handle_button_timing(trip_pressed, avg_pressed):
    """Handle button timing logic in Raspberry Pi"""
    global button_trip_start_time, button_avg_start_time, button_combo_start_time
    global button_trip_triggered, button_avg_triggered, button_combo_triggered
    global current_style_index
    
    current_time = pygame.time.get_ticks()
    
    # Check for combo (both buttons pressed)
    if trip_pressed and avg_pressed:
        if button_combo_start_time == 0:
            button_combo_start_time = current_time
            button_combo_triggered = False
        elif current_time - button_combo_start_time >= BUTTON_HOLD_TIME and not button_combo_triggered:
            # Style change
            old_style = current_style_index
            current_style_index = (current_style_index + 1) % 5
            style_names = {STYLE_SYNTHWAVE: 'Synthwave', STYLE_CITROEN_BX: 'Citroën BX', STYLE_SUBARU_XT: 'Subaru XT', STYLE_NISSAN_300ZX: 'Nissan 300ZX', STYLE_CORVETTE_C4: 'Corvette C4'}
            print(f"🎨 STYLE CHANGE! Changed from {style_names[old_style]} to: {style_names[current_style_index]}")
            
            # Save the new style
            persistent_data.data["dashboard_style"] = current_style_index
            persistent_data.save_data()
            print(f"💾 Style saved: {current_style_index}")
            
            button_combo_triggered = True
    else:
        # Reset combo ONLY when BOTH buttons are released (not when only one is pressed)
        if not trip_pressed and not avg_pressed:
            if button_combo_start_time > 0:
                button_combo_start_time = 0
                button_combo_triggered = False
        
        # Handle individual buttons only when combo is not active
        
        # Trip reset button
        if trip_pressed:
            if button_trip_start_time == 0:
                button_trip_start_time = current_time
                button_trip_triggered = False
            elif current_time - button_trip_start_time >= BUTTON_HOLD_TIME and not button_trip_triggered:
                # Reset trip
                persistent_data.data["trip_odometer"] = 0.0
                persistent_data.save_data()
                print("🔄 TRIP RESET!")
                button_trip_triggered = True
        else:
            button_trip_start_time = 0
            button_trip_triggered = False
        
        # Average reset button
        if avg_pressed:
            if button_avg_start_time == 0:
                button_avg_start_time = current_time
                button_avg_triggered = False
            elif current_time - button_avg_start_time >= BUTTON_HOLD_TIME and not button_avg_triggered:
                # Reset average (would need to send command to Arduino)
                print("🔄 AVERAGE RESET!")
                button_avg_triggered = True
        else:
            button_avg_start_time = 0
            button_avg_triggered = False

# Load saved dashboard style
if "dashboard_style" in persistent_data.data:
    current_style_index = persistent_data.data["dashboard_style"]
    print(f"🎨 Loaded saved style: {'Synthwave' if current_style_index == STYLE_SYNTHWAVE else 'Citroën BX'}")
else:
    # Default to Synthwave if no saved style
    current_style_index = STYLE_SYNTHWAVE
    persistent_data.data["dashboard_style"] = current_style_index

# Initialize serial connection
try:
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
    print(f"Connected to Arduino on {SERIAL_PORT}")
    serial_connected = True
    # Send initialization data to Arduino
    persistent_data.send_init_data(ser)
except Exception as e:
    print(f"Failed to connect to Arduino: {e}")
    print("Running in demo mode...")
    serial_connected = False
    ser = None

# Simple connection tracking
was_ever_connected = serial_connected

# Current values
current_speed = 0.0
current_rpm = 0.0
demo_rpm_direction = 1

# Adaptive RPM smoothing - fast for large changes, smooth for small oscillations
display_rpm = 0.0  # Smoothed RPM for visual display
RPM_FAST_SMOOTHING = 0.9    # Even faster response for large changes (>50 RPM difference) - increased from 0.85
RPM_SLOW_SMOOTHING = 0.3    # Faster smoothing for small oscillations - increased from 0.25
RPM_DEADBAND = 50           # Much larger deadband for rock-solid idle stability - increased from 35
last_rpm_time = 0           # Track when we last received RPM data

# Speed aggregation system - rolling average for stability
display_speed = 0.0         # Smoothed speed for visual display
speed_samples = []          # Rolling buffer of speed samples
SPEED_SAMPLE_WINDOW = 500   # 500ms aggregation window
MAX_SAMPLES = 25            # Maximum samples in buffer (500ms / 20ms = 25 samples at 50Hz)
last_speed_update = 0       # Track when we last updated display speed
last_speed_time = 0         # Track when we last received speed data

# Software brightness control
software_brightness = 1.0  # 1.0 = full brightness, 0.2 = minimum
last_brightness_value = -1  # Track last brightness to avoid unnecessary updates

# Arduino sensor data (for 3rd dashboard)
current_fuel_level = 50.0
current_oil_pressure = 40.0
current_coolant_temp = 185.0
current_oil_temp = 200.0
current_battery_voltage = 12.6
current_brightness = 75.0
current_fuel_consumption_lbhr = 0.0  # Real-time fuel consumption from ALDL (lb/hr)

# Arduino trip/MPG data (MISSING - this was the bug!)
current_fuel_range = 0.0
current_inst_mpg = 0.0
current_avg_mpg = 0.0
current_fuel_flow_gph = 0.0  # Current fuel flow in gallons per hour

# Distance calculation now done by Raspberry Pi (better persistence)
last_speed_update_time = 0
distance_calculation_initialized = False

# Arduino switch states (for gauge switching)
switch_oil_pressure = False
switch_oil_temp = False
switch_coolant_temp = False
switch_volts = False
switch_fuel_range = False
switch_trip_odo = False
switch_inst_mpg = False
switch_avg_mpg = False
switch_metric = False

# Button states for visual feedback
button_trip_reset = False
button_avg_reset = False

# Speedometer configuration
max_speed = 85
speed_tick_count = 18
speed_numbers = [5, 15, 25, 35, 45, 55, 65, 75, 85]

# Tachometer configuration (matching original Corvette pattern)
max_rpm = 6000  # RPM x100 (60 = 6000 RPM)
rpm_numbers = [0, 1000, 2000, 3000, 4000, 5000, 6000]  # Major numbered ticks

# 7-segment display patterns
SEGMENTS = {
    0: [1,1,1,1,1,1,0],  # a,b,c,d,e,f,g
    1: [0,1,1,0,0,0,0],
    2: [1,1,0,1,1,0,1],
    3: [1,1,1,1,0,0,1],
    4: [0,1,1,0,0,1,1],
    5: [1,0,1,1,0,1,1],
    6: [1,0,1,1,1,1,1],
    7: [1,1,1,0,0,0,0],
    8: [1,1,1,1,1,1,1],
    9: [1,1,1,1,0,1,1]
}

# Metric conversion functions
def mph_to_kph(mph):
    """Convert MPH to KPH"""
    return mph * 1.60934

def fahrenheit_to_celsius(f):
    """Convert Fahrenheit to Celsius"""
    return (f - 32) * 5.0/9.0

def psi_to_kpa(psi):
    """Convert PSI to kPa"""
    return psi * 6.89476

def miles_to_km(miles):
    """Convert miles to kilometers"""
    return miles * 1.60934

def mpg_to_lp100km(mpg):
    """Convert MPG to L/100km (liters per 100 kilometers)"""
    if mpg <= 0:
        return 999.9  # Invalid/infinite consumption
    return 235.214 / mpg  # Standard conversion formula

def decode_instant_mpg_display(instant_mpg_value, fuel_flow_gph=0.0, apply_compensation=True):
    """Decode instant MPG value from Arduino and return display info"""
    if instant_mpg_value == 0.0:
        # Engine idling - show GPH using real fuel flow data
        gph_value = fuel_flow_gph if fuel_flow_gph > 0.01 else 0.8  # Use real data or fallback
        # Only apply division compensation for Synthwave and Corvette C4 styles
        final_value = gph_value / 10.0 if apply_compensation else gph_value
        return {
            'type': 'gph',
            'value': final_value,
            'label': 'GPH',
            'format_decimals': 1
        }
    elif instant_mpg_value == -1.0:
        # Engine off
        return {
            'type': 'off',
            'value': 0,
            'label': 'OFF',
            'format_decimals': 0
        }
    else:
        # Normal MPG display (positive values)
        return {
            'type': 'mpg',
            'value': instant_mpg_value,
            'label': 'MPG',
            'format_decimals': 1
        }

# Reconnection logic removed - was causing blocking issues

def apply_software_brightness(surface, brightness_factor):
    """Apply software brightness by creating a dark overlay"""
    if brightness_factor >= 1.0:
        return  # No dimming needed
    
    # Create a dark overlay
    overlay = pygame.Surface(surface.get_size())
    overlay.fill(BLACK)
    
    # Calculate alpha for overlay (higher alpha = darker)
    alpha = int((1.0 - brightness_factor) * 255)
    overlay.set_alpha(alpha)
    
    # Blit the overlay onto the surface
    surface.blit(overlay, (0, 0))

def set_screen_brightness(brightness_percent):
    """Set brightness for all three screens based on percentage (20-100, never completely dark)"""
    try:
        # Ensure minimum brightness of 20% for safety
        brightness_percent = max(brightness_percent, 20.0)
        
        # Convert percentage to brightness values for different display types
        # Wayland displays: 0.2 to 1.0 (gamma correction approach)
        wayland_brightness = 0.2 + ((brightness_percent - 20.0) / 80.0) * 0.8
        
        # DSI display: 51 to 255 (backlight range, minimum ~20%)
        dsi_brightness = int(51 + ((brightness_percent - 20.0) / 80.0) * 204)
        
        # Fast DSI brightness control (most reliable)
        backlight_paths = [
            '/sys/class/backlight/rpi_backlight/brightness',
            '/sys/class/backlight/10-0045/brightness',
            '/sys/class/backlight/backlight/brightness'
        ]
        
        for path in backlight_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'w') as f:
                        f.write(str(dsi_brightness))
                    break  # Success, no need to try other paths
                except (PermissionError, OSError):
                    continue
        
        # DISABLED: xrandr calls were causing dashboard freezing
        # Try xrandr for Wayland displays (skip if too slow)
        # wayland_outputs = ['XWAYLAND0', 'XWAYLAND1']  # Only try first two (speedometer/tachometer)
        # 
        # for output in wayland_outputs:
        #     try:
        #         # Quick xrandr call with minimal output
        #         subprocess.run(['xrandr', '--output', output, '--brightness', str(wayland_brightness)], 
        #                       capture_output=True, timeout=0.1, check=False)
        #     except (subprocess.TimeoutExpired, Exception):
        #         # Skip if too slow or fails
        #         continue
                    
    except Exception:
        # Silently ignore errors to avoid slowing down the main loop
        pass

def read_arduino_data():
    """Read speed, RPM, and sensor data from Arduino"""
    global current_speed, current_rpm, demo_rpm_direction
    global current_fuel_level, current_oil_pressure, current_coolant_temp, current_oil_temp
    global current_battery_voltage, current_brightness
    global display_rpm, last_rpm_time
    global display_speed, last_speed_time
    global switch_oil_pressure, switch_oil_temp, switch_coolant_temp, switch_volts
    global switch_fuel_range, switch_trip_odo, switch_inst_mpg, switch_avg_mpg, switch_metric
    global current_fuel_range, current_inst_mpg, current_avg_mpg, current_fuel_flow_gph
    global last_speed_update_time, distance_calculation_initialized
    global serial_connected, ser
    global speed_samples, last_speed_update  # Added missing global declarations
    
    # Debug timing removed for performance
    
    if not serial_connected:
            # Only show demo if Arduino was NEVER connected from the beginning
            if not was_ever_connected:
                # Demo mode - simulate both speed and RPM changes
                current_speed += 0.4
                if current_speed > 90:
                    current_speed = 0
                    
                current_rpm += 50 * demo_rpm_direction
                if current_rpm >= 6500:
                    demo_rpm_direction = -1
                elif current_rpm <= 800:
                    demo_rpm_direction = 1
                
                # Demo mode for sensor data (will be overridden by DSI demo animations)
                current_fuel_level = 65.0
                current_oil_pressure = 40.0
                current_coolant_temp = 185.0
                current_oil_temp = 200.0
                current_fuel_consumption_lbhr = 2.5  # Demo fuel consumption
                current_fuel_flow_gph = 0.8  # Demo fuel flow
            else:
                # Arduino was connected before but now disconnected - freeze last values
                # Don't update any values, just return current state
                pass
                
            return current_speed, current_rpm
    
    try:
        if ser is None or not ser.is_open:
            raise Exception("Serial connection is not open")
        
        # Simple, reliable serial processing - back to working version
        if ser.in_waiting > 0:
            # If buffer is getting full (>1000 bytes), clear old data
            if ser.in_waiting > 1000:
                ser.reset_input_buffer()  # Clear the buffer
                line = ""
            else:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
        else:
            line = ""  # No data available, don't block
        
        if not line:
            return current_speed, current_rpm
        

        
        # Parse Arduino data
        # Parse the actual format
        # Handle Arduino initialization requests
        if line.startswith("INIT_REQUEST:PERSISTENT_DATA"):
            # print("Arduino requesting persistent data")  # Disabled for performance
            persistent_data.send_init_data(ser)
            return current_speed, current_rpm
        
        # Handle Arduino reset commands
        if line.startswith("RESET_TRIP:"):
            # Reset trip odometer (distance calculation now done by Pi)
            persistent_data.data["trip_odometer"] = 0.0
            persistent_data.save_data()
            # Send reset average MPG to Arduino
            if ser and ser.is_open:
                try:
                    ser.write(b"AVG_MPG_UPDATE:0.0\n")
                except:
                    pass
            # Trip odometer reset by Arduino button
            return current_speed, current_rpm
        
        # Handle style change command (both buttons held for 2+ seconds)
        if line.startswith("STYLE_CHANGE:"):
            global current_style_index
            current_style_index = (current_style_index + 1) % 5  # Cycle between 0, 1, 2, 3, and 4
            
            # Save the new style to persistent data
            persistent_data.data["dashboard_style"] = current_style_index
            persistent_data.save_data()
            
            return current_speed, current_rpm
        

        
        # Handle Arduino save data commands
        if line.startswith("SAVE_DATA:"):
            data_part = line[10:]  # Remove "SAVE_DATA:" prefix
            parts = data_part.split(',')
            if len(parts) >= 1:  # New format: only fuel data (distance calculated by Pi)
                try:
                    fuel_used = float(parts[0])
                    fuel_used_bpw = float(parts[1]) if len(parts) > 1 else 0.0
                    # Update only fuel data, keep existing distance data
                    persistent_data.data["fuel_used"] = fuel_used
                    persistent_data.data["fuel_used_bpw"] = fuel_used_bpw
                    persistent_data.save_data()
                    # print(f"Saved fuel data: {fuel_used:.2f}, {fuel_used_bpw:.2f}")  # Disabled for performance
                except ValueError as e:
                    print(f"Error parsing save data: {e}")
            return current_speed, current_rpm
        
        if "SPEED:" in line or "FUELRNG:" in line or "AMPG_SW:" in line:
            
            # Split by comma and parse key:value pairs (handles both high and low frequency messages)
            pairs = line.split(",")
            data = {}
            for pair in pairs:
                if ":" in pair:
                    key, value = pair.split(":", 1)
                    try:
                        data[key.strip()] = float(value.strip())
                    except ValueError:
                        pass  # Skip non-numeric values
            

            
            # Update speed if available with essential processing restored
            if "SPEED" in data:
                current_speed = data["SPEED"]
                current_time = pygame.time.get_ticks()
                last_speed_time = current_time  # Update timestamp
                
                # Essential distance calculation (simplified from old version)
                if distance_calculation_initialized and last_speed_update_time > 0:
                    delta_time_ms = current_time - last_speed_update_time
                    if delta_time_ms > 0 and current_speed > 0.1:  # Only when moving
                        # Calculate distance increment in miles
                        distance_increment = (current_speed * delta_time_ms) / 3600000.0  # MPH * ms -> miles
                        
                        # Update odometer values
                        persistent_data.data["total_odometer"] += distance_increment
                        persistent_data.data["trip_odometer"] += distance_increment
                        
                        # Calculate average MPG (simplified)
                        total_fuel_used = persistent_data.data["fuel_used"] + persistent_data.data["fuel_used_bpw"]
                        if total_fuel_used > 0.01 and persistent_data.data["trip_odometer"] > 0.01:
                            calculated_avg_mpg = persistent_data.data["trip_odometer"] / total_fuel_used
                            if calculated_avg_mpg > 50.0:
                                calculated_avg_mpg = 50.0
                            current_avg_mpg = calculated_avg_mpg
                        else:
                            current_avg_mpg = 0.0
                
                last_speed_update_time = current_time
                distance_calculation_initialized = True
                
                # Essential speed processing (simplified from old working version)
                display_speed = current_speed  # Simple assignment for now
            else:
                # No speed data in this message - check if we should timeout
                current_time = pygame.time.get_ticks()
                if current_speed is not None and (current_time - last_speed_time) < 500:  # 500ms timeout
                    # Keep last good values - prevents brief gaps during fast serial updates
                    pass
                else:
                    # Timeout exceeded or first time - reset
                    display_speed = 0.0
            
            # Handle RPM data - no simulation when Arduino is connected
            if "RPM" in data:
                current_rpm = data["RPM"]  # Use actual RPM data (including 0 if that's the value)
                last_rpm_time = pygame.time.get_ticks()  # Update timestamp
                
                # Adaptive RPM smoothing - fast for big changes, stable for small ones
                if display_rpm == 0.0:  # First reading
                    display_rpm = current_rpm
                else:
                    rpm_difference = abs(current_rpm - display_rpm)
                    
                    # Deadband: ignore very small changes to prevent 6↔7 oscillation
                    if rpm_difference < RPM_DEADBAND:
                        # Keep current display value - no change for small oscillations
                        pass
                    elif rpm_difference > 50:
                        # Large change: fast response (revving up/down)
                        display_rpm = display_rpm + (current_rpm - display_rpm) * RPM_FAST_SMOOTHING
                    else:
                        # Medium change: normal smoothing
                        display_rpm = display_rpm + (current_rpm - display_rpm) * RPM_SLOW_SMOOTHING
                
                # Debug output disabled for maximum performance
                # print(f"RPM DEBUG: Arduino={data['RPM']}, Smooth={display_rpm:.0f}, Display_calc={int(display_rpm)//100}, Should_show={int(display_rpm)//100:02d}")
            else:
                # No RPM data in this message - check if we should timeout
                current_time = pygame.time.get_ticks()
                if current_rpm is not None and (current_time - last_rpm_time) < 500:  # 500ms timeout
                    # Keep last good values - prevents brief N/A flicker during fast serial updates
                    pass
                else:
                    # Timeout exceeded or first time - show N/A
                    current_rpm = None
                    display_rpm = 0.0
            
            # Update sensor data for 3rd dashboard
            if "FUEL" in data:
                current_fuel_level = data["FUEL"]
            if "OIL" in data:
                current_oil_pressure = data["OIL"]
            if "COOLANT" in data:
                # Arduino now sends Fahrenheit directly, handle special "LO" value
                current_coolant_temp = data["COOLANT"]
            if "OILTEMP" in data:
                # Arduino now sends Fahrenheit directly, handle special "LO" value
                current_oil_temp = data["OILTEMP"]
            if "BATTERY" in data:
                current_battery_voltage = data["BATTERY"]
            if "BRIGHTNESS" in data:
                current_brightness = data["BRIGHTNESS"]
            if "FUEL_CONSUMPTION" in data:
                current_fuel_consumption_lbhr = data["FUEL_CONSUMPTION"]
            
            # Update trip/MPG data (FIXED - this was missing!)
            if "TRIP_ODO" in data:
                current_trip_odo = data["TRIP_ODO"]
            if "TOTAL_ODO" in data:
                current_total_odo = data["TOTAL_ODO"]
            if "FUELRNG" in data:
                current_fuel_range = data["FUELRNG"]
            if "IMPG" in data:
                current_inst_mpg = data["IMPG"]
            if "AMPG" in data:
                current_avg_mpg = data["AMPG"]
            if "FLOW" in data:
                current_fuel_flow_gph = data["FLOW"]

            
            # Update switch states for gauge switching
            if "OIL_P_SW" in data:
                switch_oil_pressure = bool(int(data["OIL_P_SW"]))
            if "OIL_T_SW" in data:
                switch_oil_temp = bool(int(data["OIL_T_SW"]))
            if "COOL_SW" in data:
                switch_coolant_temp = bool(int(data["COOL_SW"]))
            if "VOLT_SW" in data:
                switch_volts = bool(int(data["VOLT_SW"]))
            if "FUELR_SW" in data:
                switch_fuel_range = bool(int(data["FUELR_SW"]))
            if "TRIP_SW" in data:
                switch_trip_odo = bool(int(data["TRIP_SW"]))
            if "IMPG_SW" in data:
                switch_inst_mpg = bool(int(data["IMPG_SW"]))
            if "AMPG_SW" in data:
                switch_avg_mpg = bool(int(data["AMPG_SW"]))
            if "METR_SW" in data:
                switch_metric = bool(int(data["METR_SW"]))
            
            # Handle button states with timing logic
            if "TRIP_BTN" in data and "AVG_BTN" in data:
                trip_btn = bool(int(data["TRIP_BTN"]))
                avg_btn = bool(int(data["AVG_BTN"]))
                
                handle_button_timing(trip_btn, avg_btn)
            
            # Update button states for visual feedback
            if "TRIP_BTN" in data:
                button_trip_reset = bool(int(data["TRIP_BTN"]))
            if "AVG_BTN" in data:
                button_avg_reset = bool(int(data["AVG_BTN"]))
            
            # Handle persistent data communication
            if "TOTAL_ODO" in data and "TRIP_ODO" in data and "FUEL_USED" in data:
                # Update persistent data from Arduino
                persistent_data.update_data(
                    data["TOTAL_ODO"],
                    data["TRIP_ODO"], 
                    data["FUEL_USED"]
                )
            
            # Clean console output
            rpm_display = "N/A" if current_rpm is None else f"{current_rpm:.0f}"
            #print(f"Arduino - Speed: {current_speed:.1f} MPH, RPM: {rpm_display}")
        # Silently ignore other message formats
    except Exception as e:
        if serial_connected:
            # Arduino connection lost - switch to demo mode
            serial_connected = False
            if ser:
                try:
                    ser.close()
                except:
                    pass
                    ser = None
        # print(f"Serial read error: {e}")  # Disabled - connectivity issue resolved
        pass  # Silent error handling for performance
    
    return current_speed, current_rpm

def draw_7_segment_digit(surface, x, y, digit, color, size=50, dim_factor=1.0):
    """Draw a single 7-segment digit with optional dimming for leading zeros"""
    if digit < 0 or digit > 9:
        return
    
    segments = SEGMENTS[digit]
    w, h = size, size * 1.5
    gap = max(2, size // 12)  # Proportional gap (4px for 50px size)
    thickness = max(4, size // 4)  # Proportional thickness (12px for 50px size, 7px for 30px)
    
    # Apply dimming factor to color
    if dim_factor < 1.0:
        dimmed_color = tuple(int(c * dim_factor) for c in color)
    else:
        dimmed_color = color
    
    def draw_horizontal_segment(start_x, start_y, width):
        points = [
            (start_x + thickness//2, start_y - thickness//2),
            (start_x + width - thickness//2, start_y - thickness//2),
            (start_x + width, start_y),
            (start_x + width - thickness//2, start_y + thickness//2),
            (start_x + thickness//2, start_y + thickness//2),
            (start_x, start_y)
        ]
        pygame.draw.polygon(surface, dimmed_color, points)
    
    def draw_vertical_segment(start_x, start_y, height):
        points = [
            (start_x - thickness//2, start_y + thickness//2),
            (start_x, start_y),
            (start_x + thickness//2, start_y + thickness//2),
            (start_x + thickness//2, start_y + height - thickness//2),
            (start_x, start_y + height),
            (start_x - thickness//2, start_y + height - thickness//2)
        ]
        pygame.draw.polygon(surface, dimmed_color, points)
    
    # Draw segments based on pattern
    if segments[0]:  # a (top)
        draw_horizontal_segment(x + gap, y, w - 2*gap)
    if segments[1]:  # b (top right)
        draw_vertical_segment(x + w, y + gap, h//2 - 2*gap)
    if segments[2]:  # c (bottom right)
        draw_vertical_segment(x + w, y + h//2 + gap, h//2 - 2*gap)
    if segments[3]:  # d (bottom)
        draw_horizontal_segment(x + gap, y + h, w - 2*gap)
    if segments[4]:  # e (bottom left)
        draw_vertical_segment(x, y + h//2 + gap, h//2 - 2*gap)
    if segments[5]:  # f (top left)
        draw_vertical_segment(x, y + gap, h//2 - 2*gap)
    if segments[6]:  # g (middle)
        draw_horizontal_segment(x + gap, y + h//2, w - 2*gap)

def draw_multi_digit_display(surface, value, num_digits, start_x, start_y, digit_width, color, size=50, leading_zero_dim=0.3):
    """Draw multi-digit display with dimmed leading zeros"""
    # Format the number with leading zeros
    format_str = f"{{:0{num_digits}d}}"
    value_str = format_str.format(int(value))
    
    # Find first non-zero digit
    first_non_zero = len(value_str)  # Default to end if all zeros
    for i, digit_char in enumerate(value_str):
        if digit_char != '0':
            first_non_zero = i
            break
    
    # Special case: if all digits are zero, dim all but the last one
    if first_non_zero == len(value_str):
        first_non_zero = len(value_str) - 1
    
    # Draw each digit
    for i, digit_char in enumerate(value_str):
        digit = int(digit_char)
        x = start_x + i * digit_width
        
        # Determine if this is a leading zero
        is_leading_zero = (i < first_non_zero and digit == 0)
        dim_factor = leading_zero_dim if is_leading_zero else 1.0
        
        draw_7_segment_digit(surface, x, start_y, digit, color, size, dim_factor)

def draw_speed_display(surface, speed):
    """Draw 3-digit speed in 7-segment style with MPH/KPH label"""
    # Convert to metric if metric switch is active (use aggregated display_speed, not raw speed)
    if switch_metric:
        display_speed_for_drawing = mph_to_kph(display_speed)
        unit_text = "KPH"
    else:
        display_speed_for_drawing = display_speed
        unit_text = "MPH"
    
    digit_width = 80
    start_x = SPEEDO_DIGITAL_X
    start_y = SPEEDO_DIGITAL_Y
    
    # Use multi-digit display with leading zero dimming
    draw_multi_digit_display(surface, display_speed, 3, start_x, start_y, digit_width, YELLOW, 50, 0.3)
    
    font_small = pygame.font.SysFont('Arial', 24, bold=True)
    unit_label = font_small.render(unit_text, True, YELLOW)
    unit_rect = unit_label.get_rect(center=(start_x + digit_width, start_y + 120))
    surface.blit(unit_label, unit_rect)

def draw_rpm_display(surface, rpm):
    """Draw 2-digit RPM in 7-segment style with RPM/100 label"""
    digit_width = 80  # Same spacing as speedometer
    start_x = TACHO_DIGITAL_X - 60   # Moved right for centering (was -100, now -60)
    start_y = TACHO_DIGITAL_Y - 170  # Moved up 70 pixels from previous position (-100 - 70 = -170)
    
    if rpm is None:
        # Show "N/A" when no RPM data is available
        font_na = pygame.font.SysFont('Arial', 40, bold=True)
        na_text = font_na.render("N/A", True, (128, 128, 128))  # Gray color for N/A
        na_rect = na_text.get_rect()
        na_x = start_x + digit_width - na_rect.width // 2  # Center where digits would be
        surface.blit(na_text, (na_x, start_y + 20))
    else:
        # Show RPM digits with leading zero dimming - display actual RPM/100 properly
        rpm_hundreds = int(rpm) // 100  # Convert to hundreds for display (e.g., 741 RPM -> 7, should show as "07")
        # Ensure we show the correct value: 741 RPM should show "07" (meaning 0700 RPM range)
        draw_multi_digit_display(surface, rpm_hundreds, 2, start_x, start_y, digit_width, YELLOW, 50, 0.3)
    
    font_small = pygame.font.SysFont('Arial', 24, bold=True)
    rpm_text = font_small.render("RPM/100", True, YELLOW)  # Changed from "RPM" to "RPM/100"
    rpm_rect = rpm_text.get_rect(center=(start_x + digit_width * 1 - 10, start_y + 105))  # Moved 10 pixels to the left
    surface.blit(rpm_text, rpm_rect)


def draw_odometer_separate(surface, total_miles):
    """Draw odometer on dedicated small surface for high positioning"""
    # Position within small surface (320x70) - WIDER SURFACE
    odo_x = 260  # Adjusted for wider surface (was 240, now 260)
    odo_y = 45   # Lower in surface to leave room for title
    
    # Compact styling for small surface
    digit_width = 28
    digit_height = 35
    digit_spacing = 30
    border_color = (100, 100, 100)
    bg_color = (20, 20, 20)
    digit_color = (255, 255, 255)
    decimal_color = (255, 200, 0)
    
    if total_miles is None or total_miles < 0:
        total_miles = 0.0
    
    # Format odometer
    integer_part = int(total_miles)
    decimal_part = int((total_miles - integer_part) * 10)
    integer_str = f"{integer_part:06d}"
    decimal_str = f"{decimal_part:01d}"
    
    # Draw title at top of surface
    font_title = pygame.font.SysFont('Arial', 14, bold=True)
    title_text = font_title.render("ODOMETER", True, (200, 200, 200))
    surface.blit(title_text, (odo_x - 60, 5))  # Top of surface
    
    # Draw digits
    font_digit = pygame.font.SysFont('Courier', 22, bold=True)
    
    for i, digit_char in enumerate(integer_str):
        x = odo_x - (6 - i) * digit_spacing
        y = odo_y
        
        # Draw digit background and border
        digit_rect = pygame.Rect(x - digit_width//2, y - digit_height//2, digit_width, digit_height)
        pygame.draw.rect(surface, border_color, digit_rect, 2)
        pygame.draw.rect(surface, bg_color, digit_rect.inflate(-4, -4))
        
        # Draw digit
        digit_surface = font_digit.render(digit_char, True, digit_color)
        digit_rect_center = digit_surface.get_rect(center=(x, y))
        surface.blit(digit_surface, digit_rect_center)
    
    # Draw decimal point and digit
    decimal_x = odo_x + digit_spacing
    decimal_y = odo_y + digit_height//4
    pygame.draw.circle(surface, decimal_color, (decimal_x, decimal_y), 3)
    
    decimal_digit_x = odo_x + digit_spacing * 1.3
    decimal_digit_rect = pygame.Rect(decimal_digit_x - digit_width//2, odo_y - digit_height//2, digit_width, digit_height)
    pygame.draw.rect(surface, border_color, decimal_digit_rect, 2)
    pygame.draw.rect(surface, bg_color, decimal_digit_rect.inflate(-4, -4))
    
    decimal_surface = font_digit.render(decimal_str, True, decimal_color)
    decimal_rect_center = decimal_surface.get_rect(center=(decimal_digit_x, odo_y))
    surface.blit(decimal_surface, decimal_rect_center)

def draw_odometer_display(surface, total_miles):
    """Draw 7-digit odometer display in top right corner, similar to original C4 cluster"""
    # Optimized position for all dashboard styles (no title, expanded surface)
    odo_x = 800  # Right side positioning - moved right more (+50 total)
    odo_y = 10   # Top area with expanded surface space - moved up more (-30 total)
    
    # Odometer styling - similar to original C4
    digit_width = 32
    digit_height = 45
    digit_spacing = 35
    border_color = (100, 100, 100)  # Gray border
    bg_color = (20, 20, 20)         # Dark background
    digit_color = (255, 255, 255)   # White digits
    decimal_color = (255, 200, 0)   # Yellow/orange for decimal digit
    
    # Ensure we have a valid number
    if total_miles is None or total_miles < 0:
        total_miles = 0.0
    
    # Format odometer reading: 089240.5 -> "089240" + "5"
    # Split into integer and decimal parts
    integer_part = int(total_miles)
    decimal_part = int((total_miles - integer_part) * 10)  # Get first decimal place
    
    # Format as 6 digits + 1 decimal: "089240" + "5"
    integer_str = f"{integer_part:06d}"  # 6 digits with leading zeros
    decimal_str = f"{decimal_part:01d}"  # 1 decimal digit
    
    # Title removed for cleaner appearance
    
    # Use regular font instead of 7-segment for reliability
    font_digit = pygame.font.SysFont('Courier', 28, bold=True)  # Monospace font
    
    # Draw integer digits (6 digits)
    for i, digit_char in enumerate(integer_str):
        # Calculate position for this digit
        x = odo_x - (6 - i) * digit_spacing  # Right to left positioning
        y = odo_y
        
        # Draw border rectangle
        border_rect = pygame.Rect(x - 2, y - 2, digit_width + 4, digit_height + 4)
        pygame.draw.rect(surface, border_color, border_rect, 2)
        
        # Draw background
        bg_rect = pygame.Rect(x, y, digit_width, digit_height)
        pygame.draw.rect(surface, bg_color, bg_rect)
        
        # Draw the digit using regular font
        digit_text = font_digit.render(digit_char, True, digit_color)
        digit_rect = digit_text.get_rect(center=(x + digit_width//2, y + digit_height//2))
        surface.blit(digit_text, digit_rect)
    
    # Draw decimal point
    decimal_x = odo_x + 5
    decimal_y = odo_y + digit_height - 10
    pygame.draw.circle(surface, decimal_color, (decimal_x, decimal_y), 4)
    
    # Draw decimal digit (1 digit)
    x = odo_x + 15
    y = odo_y
    
    # Draw border rectangle for decimal digit
    border_rect = pygame.Rect(x - 2, y - 2, digit_width + 4, digit_height + 4)
    pygame.draw.rect(surface, border_color, border_rect, 2)
    
    # Draw background for decimal digit
    bg_rect = pygame.Rect(x, y, digit_width, digit_height)
    pygame.draw.rect(surface, bg_color, bg_rect)
    
    # Draw the decimal digit in different color
    decimal_digit_text = font_digit.render(decimal_str, True, decimal_color)
    decimal_digit_rect = decimal_digit_text.get_rect(center=(x + digit_width//2, y + digit_height//2))
    surface.blit(decimal_digit_text, decimal_digit_rect)

def draw_synthwave_mountains(surface, rpm):
    """Draw minimalist mountain and sunset scene with color based on RPM"""
    # Scale down by 30% and position at top left of dashboard
    scale_factor = 0.7  # 30% smaller
    center_x = 275      # Moved right from 250 to 275
    center_y = 200      # Moved down significantly - 2.5x mountain height (~125px * 2.5 = ~312, using 200 for balance)
    scene_width = int(280 * scale_factor)  # Scaled width
    scene_height = int(120 * scale_factor)  # Scaled height
    
    def interpolate_color(color1, color2, factor):
        return tuple(int(c1 + (c2 - c1) * factor) for c1, c2 in zip(color1, color2))
    
    # Handle None RPM case
    if rpm is None:
        # No RPM data - use default colors
        mountain_color = NEON_CYAN  # Default cyan color
        sun_color = BLACK  # Invisible sun
    else:
        # Mountain color (same progression as grid)
        if rpm <= 3000:
            factor = rpm / 3000.0
            mountain_color = interpolate_color(NEON_CYAN, PURPLE, factor)
        else:
            factor = min((rpm - 3000) / 4000.0, 1.0)
            mountain_color = interpolate_color(PURPLE, RED, factor)
        
        # Sun color progression (black -> cyan -> yellow)
        if rpm <= 1500:
            # Low RPM: black (invisible)
            sun_factor = rpm / 1500.0
            sun_color = interpolate_color(BLACK, NEON_CYAN, sun_factor)
        elif rpm <= 4500:
            # Mid RPM: cyan -> yellow
            sun_factor = (rpm - 1500) / 3000.0
            sun_color = interpolate_color(NEON_CYAN, YELLOW, sun_factor)
        else:
            # High RPM: bright yellow
            sun_color = YELLOW
    
    # Draw simple geometric mountains and sun like in the image
    import math
    
    # Base line for mountains (scaled)
    base_y = center_y + scene_height - int(10 * scale_factor)
    
    # Right mountain (background, scaled)
    right_base_left = center_x - int(20 * scale_factor)
    right_base_right = center_x + int(120 * scale_factor)
    right_peak_x = center_x + int(50 * scale_factor)
    right_peak_y = center_y + int(10 * scale_factor)
    
    # Left mountain (foreground, scaled)
    left_base_left = center_x - int(130 * scale_factor)
    left_base_right = center_x + int(30 * scale_factor)
    left_peak_x = center_x - int(50 * scale_factor)
    left_peak_y = center_y - int(10 * scale_factor)
    
    # Create duller colors for fills (reduce intensity by ~40%)
    def make_duller(color):
        return tuple(int(c * 0.6) for c in color)
    
    mountain_fill_color = make_duller(mountain_color)
    sun_fill_color = make_duller(sun_color) if sun_color != BLACK else BLACK
    
    # Draw bigger sun (behind both mountains) - stretched horizontally and scaled
    sun_center_x = center_x
    sun_center_y = center_y + int(30 * scale_factor)
    sun_radius_x = 87.5 * scale_factor  # Scaled horizontal radius
    sun_radius_y = 70 * scale_factor    # Scaled vertical radius
    
    # Draw filled sun ellipse with gradient (behind mountains)
    if sun_color != BLACK:  # Only draw if visible
        # Draw gradient fill by drawing horizontal lines from top to bottom
        sun_top = sun_center_y - sun_radius_y
        sun_bottom = sun_center_y + sun_radius_y
        
        for y in range(int(sun_top), int(sun_bottom) + 1):
            # Calculate how far down we are (0.0 at top, 1.0 at bottom)
            gradient_factor = (y - sun_top) / (sun_bottom - sun_top)
            
            # Create 8-bit style bands (quantize the gradient into discrete steps)
            num_bands = 6  # Number of color bands for 8-bit effect
            band_index = int(gradient_factor * num_bands)
            if band_index >= num_bands:
                band_index = num_bands - 1
            
            # Use the band index to create discrete color steps
            band_factor = band_index / (num_bands - 1)
            
            # Interpolate between bright sun color at top and darker at bottom
            bright_color = sun_color
            dark_color = make_duller(make_duller(sun_color))  # Extra dark (36% of original)
            
            gradient_color = tuple(
                int(bright_color[i] * (1 - band_factor) + dark_color[i] * band_factor)
                for i in range(3)
            )
            
            # Calculate the width of the ellipse at this y position
            if abs(y - sun_center_y) <= sun_radius_y:
                # Ellipse equation: (x-cx)²/rx² + (y-cy)²/ry² = 1
                # Solve for x: x = cx ± rx * sqrt(1 - (y-cy)²/ry²)
                y_offset = y - sun_center_y
                width_factor = math.sqrt(1 - (y_offset / sun_radius_y) ** 2)
                half_width = sun_radius_x * width_factor
                
                start_x = int(sun_center_x - half_width)
                end_x = int(sun_center_x + half_width)
                
                # Draw horizontal line with gradient color
                if start_x <= end_x:
                    pygame.draw.line(surface, gradient_color, (start_x, y), (end_x, y), 1)
        
        # Draw sun outline
        for angle in range(0, 360, 3):
            start_angle = math.radians(angle)
            end_angle = math.radians(angle + 3)
            
            start_x = sun_center_x + sun_radius_x * math.cos(start_angle)
            start_y = sun_center_y + sun_radius_y * math.sin(start_angle)
            end_x = sun_center_x + sun_radius_x * math.cos(end_angle)
            end_y = sun_center_y + sun_radius_y * math.sin(end_angle)
            
            pygame.draw.line(surface, sun_color, (start_x, start_y), (end_x, end_y), 2)
    
    # Draw mountains in correct order (back to front)
    # Right mountain first (background)
    right_mountain_points = [
        (right_base_left, base_y),
        (right_peak_x, right_peak_y),
        (right_base_right, base_y)
    ]
    
    # Draw filled right mountain
    pygame.draw.polygon(surface, mountain_fill_color, right_mountain_points)
    
    # Draw right mountain outline
    pygame.draw.line(surface, mountain_color, (right_base_left, base_y), (right_peak_x, right_peak_y), 2)  # Left side
    pygame.draw.line(surface, mountain_color, (right_peak_x, right_peak_y), (right_base_right, base_y), 2)  # Right side
    pygame.draw.line(surface, mountain_color, (right_base_left, base_y), (right_base_right, base_y), 2)  # Base
    
    # Left mountain second (foreground, covers part of right mountain)
    left_mountain_points = [
        (left_base_left, base_y),
        (left_peak_x, left_peak_y),
        (left_base_right, base_y)
    ]
    
    # Draw filled left mountain
    pygame.draw.polygon(surface, mountain_fill_color, left_mountain_points)
    
    # Draw left mountain outline
    pygame.draw.line(surface, mountain_color, (left_base_left, base_y), (left_peak_x, left_peak_y), 2)  # Left side
    pygame.draw.line(surface, mountain_color, (left_peak_x, left_peak_y), (left_base_right, base_y), 2)  # Right side
    pygame.draw.line(surface, mountain_color, (left_base_left, base_y), (left_base_right, base_y), 2)  # Base

def draw_diagonal_speedometer(surface, current_speed):
    """Draw curved diagonal speedometer with horizontal ticks"""
    line_start_x = SPEEDO_X_OFFSET
    line_start_y = SPEEDO_Y_OFFSET
    line_length = SPEEDO_LENGTH
    angle_deg = 60
    angle_rad = math.radians(angle_deg)
    
    line_end_x = line_start_x + line_length * math.cos(angle_rad)
    line_end_y = line_start_y - line_length * math.sin(angle_rad)
    
    # Convert speed and scale for metric if needed (use aggregated display_speed, not raw current_speed)
    if switch_metric:
        display_speed_for_drawing = mph_to_kph(display_speed)
        max_display_speed = mph_to_kph(max_speed)  # ~137 KPH
        display_numbers = [int(mph_to_kph(mph)) for mph in speed_numbers]  # Convert speed numbers to KPH
    else:
        display_speed_for_drawing = display_speed
        max_display_speed = max_speed
        display_numbers = speed_numbers
    
    for i in range(speed_tick_count):
        mph = (i / (speed_tick_count - 1)) * max_speed  # Always use original MPH for tick positioning
        display_mph = (i / (speed_tick_count - 1)) * max_display_speed  # Display value (MPH or KPH)
        ratio = i / (speed_tick_count - 1)
        
        curve_intensity = 80
        curve_offset = math.sin(ratio * math.pi) * curve_intensity
        
        base_tick_x = line_start_x + ratio * (line_end_x - line_start_x)
        base_tick_y = line_start_y + ratio * (line_end_y - line_start_y)
        
        tick_x = base_tick_x - curve_offset
        tick_y = base_tick_y
        
        is_numbered_tick = any(abs(mph - num) < 2.5 for num in speed_numbers)
        
        # Horizontal tick line
        if is_numbered_tick:
            tick_length = 120
            tick_x1 = tick_x - tick_length/2 - 40
            tick_x2 = tick_x + tick_length/2
        else:
            tick_length = 120
            tick_x1 = tick_x - tick_length/2
            tick_x2 = tick_x + tick_length/2
        
        tick_y1 = tick_y
        tick_y2 = tick_y
        
        color = BRIGHT_GREEN if mph < current_speed else DULL_GREEN
        pygame.draw.line(surface, color, (tick_x1, tick_y1), (tick_x2, tick_y2), 16)
        
        if is_numbered_tick:
            closest_num = min(speed_numbers, key=lambda x: abs(x - mph))
            if abs(mph - closest_num) < 2.5:
                font_number = pygame.font.SysFont('Arial', 30, bold=True)
                # Display the converted number
                if switch_metric:
                    display_num = int(mph_to_kph(closest_num))
                else:
                    display_num = closest_num
                
                # Dim numbers when not reached, bright when reached (like tachometer)
                if closest_num <= current_speed:
                    number_color = YELLOW  # Bright when reached
                else:
                    number_color = (100, 100, 0)  # Dimmed yellow when not reached
                
                number_text = font_number.render(str(display_num), True, number_color)
                number_x = tick_x1 - SPEEDO_NUMBER_DISTANCE
                number_y = tick_y - 12
                surface.blit(number_text, (number_x, number_y))

def get_modified_tachometer_position(rpm):
    """Calculate position along smoothed mountain-shaped RPM line with linear x-spacing"""
    
    # Starting point (bottom left)
    line_start_x = TACHO_X_OFFSET - 120
    line_start_y = TACHO_Y_OFFSET
    
    # End point (bottom right) - extended length for wider ticks spacing
    line_end_x = TACHO_X_OFFSET + 400  # Extended from 350 to 400 for wider tick spacing
    line_end_y = TACHO_Y_OFFSET
    
    # Peak at 4500 RPM (75% along the line)
    peak_rpm = 4500
    peak_ratio = peak_rpm / max_rpm  # 0.75
    
    # Linear x-coordinate progression (equal spacing)
    ratio = rpm / max_rpm
    tick_x = line_start_x + ratio * (line_end_x - line_start_x)
    
    # Y-coordinate follows mountain shape with peak at 4500 RPM - more vertical stretch
    if rpm <= peak_rpm:
        # Rising part: 0 to peak at 4500 RPM
        segment_ratio = rpm / peak_rpm
        # Sharper rise to peak with more height
        peak_height = 280  # Increased from 200 for more vertical stretch
        # Use a sharper curve (power function instead of sine)
        tick_y = line_start_y - (segment_ratio ** 0.7 * peak_height)
    else:
        # Falling part: 4500 to 6000 RPM
        segment_ratio = (rpm - peak_rpm) / (max_rpm - peak_rpm)
        # Sharper fall from peak
        peak_height = 280
        fall_height = 60  # Increased fall for more dramatic curve
        # Use sharper curve for the fall
        tick_y = line_start_y - peak_height + (segment_ratio ** 0.8 * fall_height)
    
    return tick_x, tick_y

def draw_modified_tachometer(surface, current_rpm):
    """Draw modified tachometer following exact original Corvette C4 pattern"""
    
    # Generate ticks with equal spacing along the RPM line
    # Total of 26 ticks based on your pattern, equally spaced from 0 to 6000 RPM
    
    all_ticks = []
    total_ticks = 26
    
    for i in range(total_ticks):
        # Equal RPM spacing from 0 to 6000
        rpm = (i / (total_ticks - 1)) * max_rpm
        
        # Determine color based on RPM ranges from your specification
        if rpm <= 4000:  # 0-40 (0-4000 RPM): green
            active_color = BRIGHT_GREEN
            inactive_color = DULL_GREEN
        elif rpm <= 4500:  # 40-45 (4000-4500 RPM): green (starting to fall)
            active_color = BRIGHT_GREEN
            inactive_color = DULL_GREEN
        elif rpm <= 5000:  # 45-50 (4500-5000 RPM): yellow
            active_color = YELLOW
            inactive_color = (100, 100, 0)
        else:  # 50-60 (5000-6000 RPM): mix of yellow and red
            if rpm <= 5400:  # First part yellow
                active_color = YELLOW
                inactive_color = (100, 100, 0)
            else:  # Last part red
                active_color = RED
                inactive_color = (100, 0, 0)
        
        all_ticks.append((rpm, active_color, inactive_color))
    
    # Draw all ticks
    for i, (rpm, active_color, inactive_color) in enumerate(all_ticks):
        # Stop at 6000 RPM exactly
        if rpm > 6000:
            continue
            
        tick_x, tick_y = get_modified_tachometer_position(rpm)
        
        # Determine if this is a major numbered tick (0, 1000, 2000, 3000, 4000, 5000, 6000)
        # Calculate which ticks should be numbered based on exact positions
        numbered_tick_indices = []
        for target_rpm in rpm_numbers:
            target_index = round((target_rpm / max_rpm) * (total_ticks - 1))
            numbered_tick_indices.append(target_index)
        
        is_numbered_tick = i in numbered_tick_indices
        
        # All ticks have same length (constant thickness and spacing) - 20% longer
        base_tick_length = 72  # Increased from 60 to 72 (20% longer)
        
        # Adjust length based on curve geometry to maintain visual consistency
        curve_position = rpm / max_rpm
        if curve_position <= 0.2:  # Start of curve
            tick_length = base_tick_length + 24  # Increased from 20 to 24 (20% longer)
        elif curve_position <= 0.75:  # Middle ascending part (up to peak at 4500)
            tick_length = base_tick_length + 12  # Increased from 10 to 12 (20% longer)
        else:  # Descending part after peak
            tick_length = base_tick_length - 6  # Increased from -5 to -6 (20% longer)
        
        # All ticks same length - no longer ticks for numbered points
        tick_y1 = tick_y - tick_length/2
        tick_y2 = tick_y + tick_length/2
        
        # Color based on current RPM (handle None case)
        if current_rpm is None:
            # No RPM data - show all ticks as inactive
            color = inactive_color
        else:
            # Normal RPM comparison
            if rpm <= current_rpm:
                color = active_color
            else:
                color = inactive_color
        
        # Draw tick with increased thickness (15% wider than speedometer)
        pygame.draw.line(surface, color, (tick_x, tick_y1), (tick_x, tick_y2), 18)  # 15% wider than speedometer (16 * 1.15 = 18)
        
        # Draw small square and RPM numbers for major ticks
        if is_numbered_tick:
            # Draw small square on top of tick - same width as tick (18 pixels)
            square_size = 18  # Same as new tick thickness (15% wider)
            square_x = tick_x - square_size // 2
            square_y = tick_y1 - square_size - 3  # Above the tick
            
            square_color = color  # Same color as the tick
            pygame.draw.rect(surface, square_color, (square_x, square_y, square_size, square_size))
            
            # Draw RPM number above the square
            font_number = pygame.font.SysFont('Arial', 24, bold=True)
            
            # Find which numbered RPM this tick represents based on tick index
            target_rpm = rpm_numbers[numbered_tick_indices.index(i)]
            display_num = str(int(target_rpm // 1000))
            
            # Show numbers based on current RPM (handle None case)
            if current_rpm is None:
                number_color = (80, 80, 0)  # Dim when no data
            else:
                number_color = YELLOW if rpm <= current_rpm else (80, 80, 0)
            
            number_text = font_number.render(display_num, True, number_color)
            number_rect = number_text.get_rect()
            number_x = square_x + square_size // 2 - number_rect.width // 2  # Center above square
            number_y = square_y - number_rect.height - 5  # Above the square
            surface.blit(number_text, (number_x, number_y))

def draw_synthwave_grid(surface, value, is_speed=True, grid_x=650, grid_y=180):
    """Draw synthwave grid with color based on speed or RPM"""
    max_width = 280
    min_width = 60
    
    def interpolate_color(color1, color2, factor):
        return tuple(int(c1 + (c2 - c1) * factor) for c1, c2 in zip(color1, color2))
    
    if is_speed:
        # Speed-based colors (0-40 mph: cyan->purple, 40-85 mph: purple->red)
        if value <= 40:
            factor = value / 40.0
            color = interpolate_color(NEON_CYAN, PURPLE, factor)
        else:
            factor = min((value - 40) / 45.0, 1.0)
            color = interpolate_color(PURPLE, RED, factor)
    else:
        # RPM-based colors (0-3000 rpm: cyan->purple, 3000-7000 rpm: purple->red)
        if value <= 3000:
            factor = value / 3000.0
            color = interpolate_color(NEON_CYAN, PURPLE, factor)
        else:
            factor = min((value - 3000) / 4000.0, 1.0)
            color = interpolate_color(PURPLE, RED, factor)
    
    # Horizontal perspective lines
    for i in range(8):
        y_pos = grid_y + (i * 15)
        width_factor = (i + 1) / 8.0
        line_width = int(min_width + (max_width - min_width) * width_factor)
        
        start_x = grid_x - line_width // 2
        end_x = grid_x + line_width // 2
        
        pygame.draw.line(surface, color, (start_x, y_pos), (end_x, y_pos), 2)
    
    # Vertical perspective lines
    for i in range(-3, 4):
        if i == 0:
            continue
        
        start_x = grid_x + i * 8
        start_y = grid_y - 15
        end_x = grid_x + i * 35
        end_y = grid_y + 120
        
        pygame.draw.line(surface, color, (start_x, start_y), (end_x, end_y), 2)

def draw_connection_status(surface, x_offset=10):
    """Draw connection status indicator"""
    status_font = pygame.font.SysFont('Arial', 16, bold=True)
    if serial_connected:
        # No status display when connected (user doesn't want distraction)
        pass
    else:
        if was_ever_connected:
            status_text = status_font.render("ARDUINO DISCONNECTED", True, RED)
        else:
            status_text = status_font.render("DEMO MODE", True, YELLOW)
        surface.blit(status_text, (x_offset, 10))

def draw_diagonal_speedometer_smooth(surface, current_speed):
    """Draw curved diagonal line with smooth bar filling - Corvette C4 version"""
    # Calculated geometry (same as original speedometer)
    line_start_x = SPEEDO_X_OFFSET
    line_start_y = SPEEDO_Y_OFFSET
    line_length = SPEEDO_LENGTH
    angle_deg = 60
    angle_rad = math.radians(angle_deg)
    
    line_end_x = line_start_x + line_length * math.cos(angle_rad)
    line_end_y = line_start_y - line_length * math.sin(angle_rad)
    
    # Draw the curved path as a thick smooth filled bar with flat ends
    bar_thickness = 80  # Even thicker for speedometer (was 60, now 80)
    
    # Calculate how much of the bar to fill based on current speed
    speed_ratio = min(current_speed / max_speed, 1.0)
    
    # Draw the background curve (full length, dimmed)
    for i in range(speed_tick_count * 8):  # More points for smoother curve
        ratio = i / (speed_tick_count * 8 - 1)
        
        # Create a curved path
        curve_intensity = 80
        curve_offset = math.sin(ratio * math.pi) * curve_intensity
        
        # Position along the diagonal line with curve
        base_x = line_start_x + ratio * (line_end_x - line_start_x)
        base_y = line_start_y + ratio * (line_end_y - line_start_y)
        
        # Apply curve offset
        center_x = base_x - curve_offset
        center_y = base_y
        
        # Draw background segment as horizontal rectangle following curve direction
        rect_width = bar_thickness
        rect_height = bar_thickness // 5  # Even thinner height for less boxy appearance
        rect = pygame.Rect(int(center_x - rect_width//2), int(center_y - rect_height//2), 
                          rect_width, rect_height)
        pygame.draw.rect(surface, DULL_GREEN, rect)
    
    # Draw the filled portion (up to current speed)
    fill_points = int(speed_tick_count * 8 * speed_ratio)
    for i in range(fill_points):
        ratio = i / (speed_tick_count * 8 - 1)
        
        # Create a curved path
        curve_intensity = 80
        curve_offset = math.sin(ratio * math.pi) * curve_intensity
        
        # Position along the diagonal line with curve
        base_x = line_start_x + ratio * (line_end_x - line_start_x)
        base_y = line_start_y + ratio * (line_end_y - line_start_y)
        
        # Apply curve offset
        center_x = base_x - curve_offset
        center_y = base_y
        
        # Draw filled segment as horizontal rectangle following curve direction
        rect_width = bar_thickness
        rect_height = bar_thickness // 5  # Even thinner height for less boxy appearance
        rect = pygame.Rect(int(center_x - rect_width//2), int(center_y - rect_height//2), 
                          rect_width, rect_height)
        pygame.draw.rect(surface, BRIGHT_GREEN, rect)
    
    # Draw horizontal black grid lines - milestone positions + intermediate lines
    # First draw milestone grid lines (matching milestone positions)
    for speed_num in speed_numbers:
        # Calculate position along the curve (same as milestone calculation)
        ratio = speed_num / max_speed
        curve_intensity = 80
        curve_offset = math.sin(ratio * math.pi) * curve_intensity
        
        base_x = line_start_x + ratio * (line_end_x - line_start_x)
        base_y = line_start_y + ratio * (line_end_y - line_start_y)
        
        grid_x = base_x - curve_offset
        grid_y = base_y
        
        # Draw horizontal black grid line through the whole bar at milestone level
        grid_line_left = grid_x - bar_thickness  # Extend beyond bar left
        grid_line_right = grid_x + bar_thickness  # Extend beyond bar right
        pygame.draw.line(surface, BLACK, 
                        (int(grid_line_left), int(grid_y)), 
                        (int(grid_line_right), int(grid_y)), 2)
    
    # Add intermediate grid lines (2 lines between each milestone)
    for i in range(len(speed_numbers) - 1):
        current_speed_num = speed_numbers[i]
        next_speed_num = speed_numbers[i + 1]
        
        # Add 2 intermediate lines between current and next milestone
        for j in range(1, 3):  # j = 1, 2 (two intermediate lines)
            intermediate_speed = current_speed_num + (next_speed_num - current_speed_num) * (j / 3.0)
            
            # Calculate position for intermediate grid line
            ratio = intermediate_speed / max_speed
            curve_intensity = 80
            curve_offset = math.sin(ratio * math.pi) * curve_intensity
            
            base_x = line_start_x + ratio * (line_end_x - line_start_x)
            base_y = line_start_y + ratio * (line_end_y - line_start_y)
            
            grid_x = base_x - curve_offset
            grid_y = base_y
            
            # Draw intermediate grid line (slightly thinner)
            grid_line_left = grid_x - bar_thickness  # Extend beyond bar left
            grid_line_right = grid_x + bar_thickness  # Extend beyond bar right
            pygame.draw.line(surface, BLACK, 
                            (int(grid_line_left), int(grid_y)), 
                            (int(grid_line_right), int(grid_y)), 1)  # Thinner line for intermediate
    
    # Draw horizontal milestone lines and speed numbers at key positions
    for speed_num in speed_numbers:
        # Calculate position along the curve
        ratio = speed_num / max_speed
        curve_intensity = 80
        curve_offset = math.sin(ratio * math.pi) * curve_intensity
        
        base_x = line_start_x + ratio * (line_end_x - line_start_x)
        base_y = line_start_y + ratio * (line_end_y - line_start_y)
        
        tick_x = base_x - curve_offset
        tick_y = base_y
        
        # Draw horizontal milestone line starting to the left of the bar with spacing
        line_start_x_pos = tick_x - bar_thickness // 2 - 15  # Reduced gap from bar (was 30px, now 15px)
        line_end_x_pos = tick_x - 80  # Extend leftward
        pygame.draw.line(surface, YELLOW if speed_num <= current_speed else (100, 100, 0), 
                        (int(line_start_x_pos), int(tick_y)), (int(line_end_x_pos), int(tick_y)), 3)
        
        # Draw speed numbers (both reached and dimmed unreached)
        # Position number with much more spacing from milestone line
        number_x = tick_x - 150  # Much more spacing from milestone line (was 130, now 150)
        number_y = tick_y - 12
        
        font_number = pygame.font.SysFont('Arial', 30, bold=True)
        
        # Color based on whether speed is reached (like tachometer)
        if speed_num <= current_speed:
            number_color = YELLOW  # Bright when reached
        else:
            number_color = (100, 100, 0)  # Dimmed yellow when not reached
        
        number_text = font_number.render(str(speed_num), True, number_color)
        surface.blit(number_text, (number_x, number_y))

def draw_modified_tachometer_smooth(surface, rpm):
    """Draw RPM-to-power curve tachometer with smooth bar filling - Corvette C4 version"""
    # Use the same mountain-shaped curve as original Synthwave tachometer
    bar_thickness = 60  # Much thicker (was 20, now 60)
    
    # Calculate how much of the curve to fill based on current RPM
    # Safety check for None values
    if rpm is None or rpm == 0:
        rpm = 0
    rpm_ratio = min(rpm / max_rpm, 1.0)
    
    # Draw the background curve (full length, dimmed)
    total_points = 500  # Much more points for smoother curve (was 200, now 500)
    for i in range(total_points):
        point_rpm = (i / (total_points - 1)) * max_rpm
        tick_x, tick_y = get_modified_tachometer_position(point_rpm)
        
        # Draw background segment as vertical rectangle following curve direction
        rect_width = bar_thickness // 5  # Even thinner width for less boxy appearance (was //3, now //5)
        rect_height = bar_thickness
        rect = pygame.Rect(int(tick_x - rect_width//2), int(tick_y - rect_height//2), 
                          rect_width, rect_height)
        
        # Color background to match filled bar progression but dimmed
        if point_rpm <= 4000:
            bg_color = DULL_GREEN  # Dimmed green
        elif point_rpm <= 4500:
            bg_color = DULL_GREEN  # Dimmed green
        elif point_rpm <= 5000:
            bg_color = (100, 100, 0)  # Dimmed yellow
        else:
            if point_rpm <= 5400:
                bg_color = (100, 100, 0)  # Dimmed yellow
            else:
                bg_color = (100, 0, 0)  # Dimmed red
        
        pygame.draw.rect(surface, bg_color, rect)
    
    # Draw the filled portion (up to current RPM)
    fill_points = int(total_points * rpm_ratio)
    for i in range(fill_points):
        point_rpm = (i / (total_points - 1)) * max_rpm
        tick_x, tick_y = get_modified_tachometer_position(point_rpm)
        
        # Choose color based on RPM (same as original)
        if point_rpm <= 4000:
            fill_color = BRIGHT_GREEN
        elif point_rpm <= 4500:
            fill_color = BRIGHT_GREEN
        elif point_rpm <= 5000:
            fill_color = YELLOW
        else:
            if point_rpm <= 5400:
                fill_color = YELLOW
            else:
                fill_color = RED
        
        # Draw filled segment as vertical rectangle following curve direction
        rect_width = bar_thickness // 5  # Even thinner width for less boxy appearance (was //3, now //5)
        rect_height = bar_thickness
        rect = pygame.Rect(int(tick_x - rect_width//2), int(tick_y - rect_height//2), 
                          rect_width, rect_height)
        pygame.draw.rect(surface, fill_color, rect)
    
    # Draw vertical black grid lines on the bar for visual separation
    grid_spacing = 20  # Grid line every 20 points along the curve
    for i in range(0, total_points, grid_spacing):
        grid_rpm = (i / (total_points - 1)) * max_rpm
        grid_x, grid_y = get_modified_tachometer_position(grid_rpm)
        
        # Draw vertical black grid line through the whole bar
        grid_line_top = grid_y - bar_thickness  # Extend beyond bar top
        grid_line_bottom = grid_y + bar_thickness  # Extend beyond bar bottom
        pygame.draw.line(surface, BLACK, 
                        (int(grid_x), int(grid_line_top)), 
                        (int(grid_x), int(grid_line_bottom)), 2)
    
    # Draw milestone vertical lines and numbers at key positions
    for rpm_num in rpm_numbers:
        tick_x, tick_y = get_modified_tachometer_position(rpm_num)
        
        # Draw vertical milestone line starting above the bar with more spacing
        line_start_y = tick_y - bar_thickness // 2 - 20  # Start above curve with 20px spacing (was 10px)
        line_end_y = tick_y - 80  # Extend upward (shorter line)
        pygame.draw.line(surface, YELLOW if rpm_num <= rpm else (100, 100, 0), 
                        (int(tick_x), int(line_start_y)), (int(tick_x), int(line_end_y)), 3)
        
        # Draw RPM numbers (both reached and dimmed unreached)
        # Position number higher above the curve
        number_x = tick_x
        number_y = tick_y - 100  # Moved up from -40 to -100
        
        # Draw number (show as x1000 format)
        display_num = int(rpm_num / 1000)
        font_number = pygame.font.SysFont('Arial', 24, bold=True)
        
        # Color based on whether RPM is reached (like other styles)
        if rpm_num <= rpm:
            number_color = YELLOW  # Bright when reached
        else:
            number_color = (100, 100, 0)  # Dimmed yellow when not reached
        
        number_text = font_number.render(str(display_num), True, number_color)
        text_rect = number_text.get_rect(center=(number_x, number_y))
        surface.blit(number_text, text_rect)

def draw_redline_warning(surface, rpm):
    """Draw redline warning positioned under RPM/100 with 80s style font"""
    if rpm is not None and rpm > 4500:  # Show warning after 4500 RPM (only if RPM data available)
        # Position under RPM/100 label
        # Calculate position based on RPM display positioning
        start_x = TACHO_DIGITAL_X - 60
        start_y = TACHO_DIGITAL_Y - 170 + 105 + 40  # Below RPM/100 label
        
        # 80s style font - use a bold, blocky font (50% larger)
        warning_font = pygame.font.SysFont('Courier', 42, bold=True)  # Increased from 28 to 42 (50% larger)
        
        # Color based on RPM level
        if rpm > 5500:
            # Red after 5500 RPM with pulsing effect
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.015)) * 0.3 + 0.7  # Faster pulse, less dramatic
            warning_color = (int(255 * pulse), 0, 0)
        else:
            # Yellow after 4500 RPM
            warning_color = YELLOW
        
        warning_text = warning_font.render("REDLINE", True, warning_color)
        
        # Position the text (moved 25 pixels to the right)
        text_rect = warning_text.get_rect()
        text_x = start_x + 40 - text_rect.width // 2 + 25  # Moved 25 pixels to the right
        
        surface.blit(warning_text, (text_x, start_y))

def draw_rounded_rect_border(surface, color, rect, radius, thickness=3):
    """Draw a simple rectangular border"""
    pygame.draw.rect(surface, color, rect, thickness)

def draw_dsi_7_segment_digit(surface, x, y, digit, color, size=30, dim_factor=1.0):
    """Draw a 7-segment digit specifically sized for DSI gauges with optional dimming"""
    if digit < 0 or digit > 9:
        return
    
    segments = SEGMENTS[digit]
    w, h = size, size * 1.5
    gap = 2
    thickness = max(6, size // 6)  # Increased thickness for bolder digits (was size//8, now size//6)
    
    # Apply dimming factor to color
    if dim_factor < 1.0:
        dimmed_color = tuple(int(c * dim_factor) for c in color)
    else:
        dimmed_color = color
    
    def draw_horizontal_segment(start_x, start_y, width):
        points = [
            (start_x + thickness//2, start_y - thickness//2),
            (start_x + width - thickness//2, start_y - thickness//2),
            (start_x + width, start_y),
            (start_x + width - thickness//2, start_y + thickness//2),
            (start_x + thickness//2, start_y + thickness//2),
            (start_x, start_y)
        ]
        pygame.draw.polygon(surface, dimmed_color, points)
    
    def draw_vertical_segment(start_x, start_y, height):
        points = [
            (start_x - thickness//2, start_y + thickness//2),
            (start_x, start_y),
            (start_x + thickness//2, start_y + thickness//2),
            (start_x + thickness//2, start_y + height - thickness//2),
            (start_x, start_y + height),
            (start_x - thickness//2, start_y + height - thickness//2)
        ]
        pygame.draw.polygon(surface, dimmed_color, points)
    
    # Draw segments based on pattern
    if segments[0]:  # a (top)
        draw_horizontal_segment(x + gap, y, w - 2*gap)
    if segments[1]:  # b (top right)
        draw_vertical_segment(x + w, y + gap, h//2 - 2*gap)
    if segments[2]:  # c (bottom right)
        draw_vertical_segment(x + w, y + h//2 + gap, h//2 - 2*gap)
    if segments[3]:  # d (bottom)
        draw_horizontal_segment(x + gap, y + h, w - 2*gap)
    if segments[4]:  # e (bottom left)
        draw_vertical_segment(x, y + h//2 + gap, h//2 - 2*gap)
    if segments[5]:  # f (top left)
        draw_vertical_segment(x, y + gap, h//2 - 2*gap)
    if segments[6]:  # g (middle)
        draw_horizontal_segment(x + gap, y + h//2, w - 2*gap)

def draw_dsi_multi_digit_display(surface, value, num_digits, start_x, start_y, digit_spacing, color, size=30, leading_zero_dim=0.3, decimal_pos=None):
    """Draw multi-digit display for DSI gauges with dimmed leading zeros and optional decimal point"""
    
    # Input validation: Handle negative values and special cases
    if value < 0:
        # For negative values, just display zeros (or handle specially)
        value = 0
    
    # Format the number with leading zeros
    try:
        if decimal_pos is not None:
            # Handle decimal formatting (e.g., 000.0 format)
            format_str = f"{{:0{num_digits + 1}.1f}}"
            value_str = format_str.format(float(value)).replace('.', '')
        else:
            # Integer formatting
            format_str = f"{{:0{num_digits}d}}"
            value_str = format_str.format(int(value))
    except (ValueError, TypeError):
        # Fallback: display zeros if formatting fails
        value_str = '0' * num_digits
    
    # Find first non-zero digit
    first_non_zero = len(value_str)  # Default to end if all zeros
    for i, digit_char in enumerate(value_str):
        if digit_char != '0':
            first_non_zero = i
            break
    
    # Special case: if all digits are zero, show the last digit at full brightness
    if first_non_zero == len(value_str):
        first_non_zero = len(value_str) - 1
    
    # Draw each digit
    for i, digit_char in enumerate(value_str):
        try:
            digit = int(digit_char)
        except ValueError:
            # Skip non-numeric characters (shouldn't happen with our validation above)
            continue
        x = start_x + i * digit_spacing
        
        # Add extra space after decimal point position
        if decimal_pos is not None and i >= decimal_pos:
            x += 15
        
        # Determine if this is a leading zero
        is_leading_zero = (i < first_non_zero and digit == 0)
        dim_factor = leading_zero_dim if is_leading_zero else 1.0
        
        draw_dsi_7_segment_digit(surface, x, start_y, digit, color, size, dim_factor)
    
    # Draw decimal point if specified
    if decimal_pos is not None:
        decimal_x = start_x + decimal_pos * digit_spacing + size // 8  # Fine-tuned position between digits
        decimal_y = start_y + int(size * 1.5) - 8
        pygame.draw.circle(surface, color, (decimal_x, decimal_y), 4)

def draw_dsi_screen_content(surface, speed, rpm):
    """Draw C4 Corvette style dashboard for the 3rd DSI screen (800x480)"""
    global current_fuel_level, current_oil_pressure, current_coolant_temp, current_oil_temp
    global switch_oil_pressure, switch_oil_temp, switch_coolant_temp, switch_volts
    global switch_fuel_range, switch_trip_odo, switch_inst_mpg, switch_avg_mpg, switch_metric
    

    # Use the passed surface directly (should be 800x480 landscape)
    dsi_surface = surface
    
    # Fonts matching the main dashboard
    font_large = pygame.font.SysFont('Arial', 32, bold=True)  # For titles
    font_medium = pygame.font.SysFont('Arial', 24, bold=True)  # For labels
    font_small = pygame.font.SysFont('Arial', 18, bold=True)   # For small text
    font_digits = pygame.font.SysFont('Arial', 36, bold=True)  # For digital displays
    
    # Colors matching main dashboard
    border_color = YELLOW
    text_color = YELLOW
    digit_color = YELLOW
    
    # Layout dimensions (scaled up by 30% + 15% more = 49.5% total)
    gauge_width = int(180 * 1.495)  # 269
    gauge_height = int(120 * 1.495)  # 179
    margin = 20
    corner_radius = 10
    
    # Adjusted margins to bring gauges closer to center for physical window fit
    top_margin = 70    # Original working position for Synthwave style (reverted to original)
    bottom_margin = 80  # Increased to move bottom gauges UP and prevent cutoff
    
    # === 1. GAUGE 1 (Top Left) - Oil Pressure or Oil Temperature ===
    oil_rect = (margin, top_margin, gauge_width, gauge_height)
    draw_rounded_rect_border(dsi_surface, border_color, oil_rect, corner_radius, 3)
    
    # Determine which gauge to show based on switch states
    time_ms = pygame.time.get_ticks()
    
    if switch_oil_pressure:
        # Show Oil Pressure Gauge
        if serial_connected:
            oil_pressure = current_oil_pressure  # Use real Arduino data
        elif not was_ever_connected:
            oil_pressure = 40 + math.sin(time_ms * 0.0003) * 40  # Demo: 0-80 PSI (only if never connected)
        else:
            oil_pressure = current_oil_pressure  # Use last known value when disconnected
        
        # Convert pressure for metric display and warning logic
        pressure_kpa = psi_to_kpa(oil_pressure)
        
        # Determine display pressure and unit
        if switch_metric:
            display_pressure = pressure_kpa
            pressure_unit = "kPa"
        else:
            display_pressure = oil_pressure
            pressure_unit = "PSI"
        
        # Warning light for low oil pressure (between PSI/kPa and digits)
        if switch_metric:
            warning_light_active = pressure_kpa < psi_to_kpa(5)  # Convert 5 PSI threshold to kPa
        else:
            warning_light_active = oil_pressure < 5
        if warning_light_active:
            # Blinking red rectangular warning light - same height as digits
            # Stay on most of the time, off briefly
            blink_time = pygame.time.get_ticks() // 200  # Faster cycle (200ms)
            if blink_time % 5 != 0:  # Show light 4 out of 5 cycles (80% on, 20% off)
                digit_height = int(44 * 1.5)  # Same height as 7-segment digits
                warning_rect = (oil_rect[0] + 80, oil_rect[1] + 40, 25, digit_height)
                pygame.draw.rect(dsi_surface, RED, warning_rect, 0)
        
        # Pressure unit label (left side)
        pressure_text = font_medium.render(pressure_unit, True, text_color)
        dsi_surface.blit(pressure_text, (oil_rect[0] + 15, oil_rect[1] + 35))
        
        # Oil pressure digits (right side) - 7-segment display with leading zero dimming
        digit_size = int(35 * 1.25)  # 44 (25% larger)
        digit_spacing = int(40 * 1.5)  # 60 (50% more spacing)
        start_x = oil_rect[0] + gauge_width - 3 * digit_spacing - 15
        start_y = oil_rect[1] + 40
        
        draw_dsi_multi_digit_display(dsi_surface, display_pressure, 3, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3)
        
        # "OIL PRESS" label and oil symbol (bottom)
        oil_label = font_small.render("OIL PRESS", True, text_color)
        oil_label_rect = oil_label.get_rect()
        dsi_surface.blit(oil_label, (oil_rect[0] + (gauge_width - oil_label_rect.width) // 2, oil_rect[1] + gauge_height - 35))
        
        # Oil symbol from PNG
        if oil_symbol:
            symbol_x = oil_rect[0] + (gauge_width - oil_label_rect.width) // 2 - 45  # Moved further left
            symbol_y = oil_rect[1] + gauge_height - 55  # Moved up
            # Scale the symbol to appropriate size (about 40x40 pixels - 2x larger)
            scaled_symbol = pygame.transform.scale(oil_symbol, (40, 40))
            dsi_surface.blit(scaled_symbol, (symbol_x, symbol_y))
        else:
            # Fallback: Simple oil can symbol (rectangle with spout)
            oil_can_x = oil_rect[0] + (gauge_width - oil_label_rect.width) // 2 - 25
            oil_can_y = oil_rect[1] + gauge_height - 30
            pygame.draw.rect(dsi_surface, text_color, (oil_can_x, oil_can_y, 12, 16), 2)
            pygame.draw.rect(dsi_surface, text_color, (oil_can_x + 12, oil_can_y + 2, 6, 4), 2)
    
    elif switch_oil_temp:
        # Show Oil Temperature Gauge
        if serial_connected:
            oil_temp = current_oil_temp  # Use real Arduino data
        elif not was_ever_connected:
            oil_temp = 115 + math.sin(time_ms * 0.0002) * 135  # Demo: -20 to +250°F (only if never connected)
        else:
            oil_temp = current_oil_temp  # Use last known value when disconnected
        
        # Convert temperature for metric display and warning logic
        oil_temp_celsius = fahrenheit_to_celsius(oil_temp)
        

        
        # Determine display temperature and unit
        if switch_metric:
            display_oil_temp = oil_temp_celsius
            temp_unit = "°C"
        else:
            display_oil_temp = oil_temp
            temp_unit = "°F"
        
        # Warning light for high oil temperature (between digits and °F/°C)
        if switch_metric:
            warning_light_active = oil_temp_celsius > fahrenheit_to_celsius(250)  # Convert 250°F threshold to °C
        else:
            warning_light_active = oil_temp > 250
        if warning_light_active:
            # Blinking red rectangular warning light - same height as digits
            # Stay on most of the time, off briefly
            blink_time = pygame.time.get_ticks() // 200  # Faster cycle (200ms)
            if blink_time % 5 != 0:  # Show light 4 out of 5 cycles (80% on, 20% off)
                digit_height = int(44 * 1.5)  # Same height as 7-segment digits
                warning_rect = (oil_rect[0] + gauge_width - 80, oil_rect[1] + 40, 25, digit_height)
                pygame.draw.rect(dsi_surface, RED, warning_rect, 0)
        
        # Oil temperature digits (left side) - handle "LO" temperature or normal display
        if display_oil_temp <= -999:  # Special "LO" temperature value from Arduino
            # Display "LO" like original C4 cluster
            lo_font = pygame.font.SysFont('Arial', 48, bold=True)
            lo_text = lo_font.render("LO", True, digit_color)
            lo_rect = lo_text.get_rect()
            dsi_surface.blit(lo_text, (oil_rect[0] + 30, oil_rect[1] + 35))
        else:
            # Normal temperature display - 7-segment display with negative sign support and leading zero dimming
            temp_value = int(display_oil_temp)
            is_negative = temp_value < 0
            abs_temp = abs(temp_value)
            
            digit_size = int(35 * 1.25)  # 44 (25% larger)
            digit_spacing = int(40 * 1.5)  # 60 (50% more spacing)
            # Adjust start position to make room for negative sign
            base_start_x = oil_rect[0] + 15
            start_x = base_start_x + (25 if is_negative else 0)  # Move digits right if negative
            start_y = oil_rect[1] + 40
            
            # Draw negative sign if temperature is negative
            if is_negative:
                minus_font = pygame.font.SysFont('Arial', 32, bold=True)  # Larger font for longer minus
                minus_text = minus_font.render("−", True, digit_color)  # Using proper minus symbol (longer)
                dsi_surface.blit(minus_text, (base_start_x + 5, start_y + 12))  # Positioned before digits
            
            draw_dsi_multi_digit_display(dsi_surface, abs_temp, 3, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3)
        
        # Temperature unit symbol (right side)
        temp_symbol = font_medium.render(temp_unit, True, text_color)
        temp_symbol_rect = temp_symbol.get_rect()
        dsi_surface.blit(temp_symbol, (oil_rect[0] + gauge_width - temp_symbol_rect.width - 15, oil_rect[1] + 35))
        
        # "OIL TEMP" label and symbols (bottom) - moved right to avoid symbol overlap
        oil_temp_label = font_small.render("OIL TEMP", True, text_color)
        oil_temp_label_rect = oil_temp_label.get_rect()
        dsi_surface.blit(oil_temp_label, (oil_rect[0] + (gauge_width - oil_temp_label_rect.width) // 2 + 30, oil_rect[1] + gauge_height - 35))
        
        # Oil symbol and coolant temp symbol from PNG (side by side)
        if oil_symbol and coolant_temp_symbol:
            # Oil symbol (left)
            oil_symbol_x = oil_rect[0] + (gauge_width - oil_temp_label_rect.width) // 2 - 65  # Further left for two symbols
            oil_symbol_y = oil_rect[1] + gauge_height - 55  # Moved up
            scaled_oil_symbol = pygame.transform.scale(oil_symbol, (40, 40))
            dsi_surface.blit(scaled_oil_symbol, (oil_symbol_x, oil_symbol_y))
            
            # Coolant temp symbol (right of oil symbol)
            temp_symbol_x = oil_symbol_x + 45  # 45 pixels to the right
            temp_symbol_y = oil_symbol_y
            scaled_temp_symbol = pygame.transform.scale(coolant_temp_symbol, (40, 40))
            dsi_surface.blit(scaled_temp_symbol, (temp_symbol_x, temp_symbol_y))
    
    # If no switches active, just show empty gauge border
    
    # === 2. GAUGE 2 (Top Right) - Coolant Temperature or Volts ===
    coolant_rect = (DSI_SCREEN_WIDTH - gauge_width - margin, top_margin, gauge_width, gauge_height)
    draw_rounded_rect_border(dsi_surface, border_color, coolant_rect, corner_radius, 3)
    
    if switch_coolant_temp:
        # Show Coolant Temperature Gauge
        if serial_connected:
            coolant_temp = current_coolant_temp  # Use real Arduino data
        elif not was_ever_connected:
            coolant_temp = 115 + math.sin(time_ms * 0.0002) * 135  # Demo: -20 to +250°F (only if never connected)
        else:
            coolant_temp = current_coolant_temp  # Use last known value when disconnected
        
        # Convert temperature for metric display and warning logic
        coolant_temp_celsius = fahrenheit_to_celsius(coolant_temp)
        

        # Determine display temperature and unit
        if switch_metric:
            display_coolant_temp = coolant_temp_celsius
            temp_unit = "°C"
        else:
            display_coolant_temp = coolant_temp
            temp_unit = "°F"
        
        # Warning light for high coolant temperature (between digits and °F/°C)
        if switch_metric:
            warning_light_active = coolant_temp_celsius > fahrenheit_to_celsius(230)  # Convert 230°F threshold to °C
        else:
            warning_light_active = coolant_temp > 230
        if warning_light_active:
            # Blinking red rectangular warning light - same height as digits
            # Stay on most of the time, off briefly
            blink_time = pygame.time.get_ticks() // 200  # Faster cycle (200ms)
            if blink_time % 5 != 0:  # Show light 4 out of 5 cycles (80% on, 20% off)
                digit_height = int(44 * 1.5)  # Same height as 7-segment digits
                warning_rect = (coolant_rect[0] + gauge_width - 80, coolant_rect[1] + 40, 25, digit_height)
                pygame.draw.rect(dsi_surface, RED, warning_rect, 0)
        
        # Temperature digits (left side) - handle "LO" temperature or normal display
        if display_coolant_temp <= -999:  # Special "LO" temperature value from Arduino
            # Display "LO" like original C4 cluster
            lo_font = pygame.font.SysFont('Arial', 48, bold=True)
            lo_text = lo_font.render("LO", True, digit_color)
            lo_rect = lo_text.get_rect()
            dsi_surface.blit(lo_text, (coolant_rect[0] + 30, coolant_rect[1] + 35))
        else:
            # Normal temperature display - 7-segment display with negative sign support and leading zero dimming
            temp_value = int(display_coolant_temp)
            is_negative = temp_value < 0
            abs_temp = abs(temp_value)
            
            digit_size = int(35 * 1.25)  # 44 (25% larger)
            digit_spacing = int(40 * 1.5)  # 60 (50% more spacing)
            # Adjust start position to make room for negative sign
            base_start_x = coolant_rect[0] + 15
            start_x = base_start_x + (25 if is_negative else 0)  # Move digits right if negative
            start_y = coolant_rect[1] + 40
            
            # Draw negative sign if temperature is negative
            if is_negative:
                minus_font = pygame.font.SysFont('Arial', 32, bold=True)  # Larger font for longer minus
                minus_text = minus_font.render("−", True, digit_color)  # Using proper minus symbol (longer)
                dsi_surface.blit(minus_text, (base_start_x + 5, start_y + 12))  # Positioned before digits
            
            draw_dsi_multi_digit_display(dsi_surface, abs_temp, 3, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3)
        
        # Temperature unit symbol (right side)
        temp_symbol = font_medium.render(temp_unit, True, text_color)
        temp_symbol_rect = temp_symbol.get_rect()
        dsi_surface.blit(temp_symbol, (coolant_rect[0] + gauge_width - temp_symbol_rect.width - 15, coolant_rect[1] + 35))
        
        # "COOLANT TEMP" label and thermometer symbol (bottom)
        coolant_label = font_small.render("COOLANT TEMP", True, text_color)
        coolant_label_rect = coolant_label.get_rect()
        dsi_surface.blit(coolant_label, (coolant_rect[0] + (gauge_width - coolant_label_rect.width) // 2, coolant_rect[1] + gauge_height - 35))
        
        # Coolant temperature symbol from PNG
        if coolant_temp_symbol:
            symbol_x = coolant_rect[0] + (gauge_width - coolant_label_rect.width) // 2 - 45  # Moved further left
            symbol_y = coolant_rect[1] + gauge_height - 55  # Moved up
            # Scale the symbol to appropriate size (about 40x40 pixels - 2x larger)
            scaled_symbol = pygame.transform.scale(coolant_temp_symbol, (40, 40))
            dsi_surface.blit(scaled_symbol, (symbol_x, symbol_y))
        else:
            # Fallback: Simple thermometer symbol
            therm_x = coolant_rect[0] + (gauge_width - coolant_label_rect.width) // 2 - 25
            therm_y = coolant_rect[1] + gauge_height - 30
            pygame.draw.circle(dsi_surface, text_color, (therm_x + 3, therm_y + 12), 4, 2)
            pygame.draw.rect(dsi_surface, text_color, (therm_x, therm_y, 6, 12), 2)
    
    elif switch_volts:
        # Show Volts Gauge
        # Use real battery voltage from Arduino
        if serial_connected:
            volts_value = current_battery_voltage
        else:
            volts_value = 12.3  # Demo value (format 00.0)
        
        # Warning light for low voltage (between digits and V)
        warning_light_active = volts_value < 11.0
        if warning_light_active:
            # Blinking red rectangular warning light - same height as digits
            # Stay on most of the time, off briefly
            blink_time = pygame.time.get_ticks() // 200  # Faster cycle (200ms)
            if blink_time % 5 != 0:  # Show light 4 out of 5 cycles (80% on, 20% off)
                digit_height = int(44 * 1.5)  # Same height as 7-segment digits
                # Position between last digit and V symbol - moved right to avoid decimal point overlap
                warning_rect = (coolant_rect[0] + gauge_width - 60, coolant_rect[1] + 40, 25, digit_height)
                pygame.draw.rect(dsi_surface, RED, warning_rect, 0)
        
        # Voltage digits (left side) - 7-segment display (format: 00.0) with leading zero dimming
        digit_size = int(35 * 1.25)  # 44 (25% larger)
        digit_spacing = int(40 * 1.5)  # 60 (50% more spacing)
        start_x = coolant_rect[0] + 15
        start_y = coolant_rect[1] + 40
        
        draw_dsi_multi_digit_display(dsi_surface, volts_value, 3, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3, decimal_pos=2)
        
        # V symbol (right side)
        volts_symbol = font_medium.render("V", True, text_color)
        volts_symbol_rect = volts_symbol.get_rect()
        dsi_surface.blit(volts_symbol, (coolant_rect[0] + gauge_width - volts_symbol_rect.width - 15, coolant_rect[1] + 35))
        
        # "VOLTS" label and battery symbol (bottom)
        volts_label = font_small.render("VOLTS", True, text_color)
        volts_label_rect = volts_label.get_rect()
        dsi_surface.blit(volts_label, (coolant_rect[0] + (gauge_width - volts_label_rect.width) // 2, coolant_rect[1] + gauge_height - 35))
        
        # Battery symbol from PNG
        if battery_symbol:
            symbol_x = coolant_rect[0] + (gauge_width - volts_label_rect.width) // 2 - 45  # Moved further left
            symbol_y = coolant_rect[1] + gauge_height - 55  # Moved up
            # Scale the symbol to appropriate size (about 40x40 pixels - 2x larger)
            scaled_symbol = pygame.transform.scale(battery_symbol, (40, 40))
            dsi_surface.blit(scaled_symbol, (symbol_x, symbol_y))
        else:
            # Fallback: Simple battery symbol (rectangle)
            battery_x = coolant_rect[0] + (gauge_width - volts_label_rect.width) // 2 - 25
            battery_y = coolant_rect[1] + gauge_height - 30
            pygame.draw.rect(dsi_surface, text_color, (battery_x, battery_y, 16, 10), 2)
            pygame.draw.rect(dsi_surface, text_color, (battery_x + 16, battery_y + 3, 3, 4), 2)
    
    # If no switches active, just show empty gauge border
    
    # === 3. GAUGE 3 (Bottom Left) - Range or Trip Odometer ===
    range_rect = (margin, DSI_SCREEN_HEIGHT - gauge_height - bottom_margin, gauge_width, gauge_height)
    # No border for gauge 3
    
    if switch_fuel_range:
        # Show Range Gauge (remove "TRIP" from "RANGE TRIP")
        if serial_connected:
            range_miles = current_fuel_range  # Use real Arduino data
        elif not was_ever_connected:
            range_miles = 275 + math.sin(time_ms * 0.0002) * 275  # Demo: 0-550 miles (only if never connected)
        else:
            range_miles = current_fuel_range  # Use last known value when disconnected
        
        # "RANGE" title (top) - removed "TRIP"
        range_title = font_small.render("RANGE", True, text_color)
        range_title_rect = range_title.get_rect()
        dsi_surface.blit(range_title, (range_rect[0] + (gauge_width - range_title_rect.width) // 2, range_rect[1] + 35))
        
        # Distance unit label (bottom)
        if switch_metric:
            range_km = miles_to_km(range_miles)
            distance_text = font_medium.render("KM", True, text_color)
            display_range = range_km
        else:
            distance_text = font_medium.render("MILES", True, text_color)
            display_range = range_miles
        distance_text_rect = distance_text.get_rect()
        dsi_surface.blit(distance_text, (range_rect[0] + (gauge_width - distance_text_rect.width) // 2, range_rect[1] + gauge_height - 35))
        
        # Range digits (right side) - format 000.0 - 7-segment display with leading zero dimming
        digit_size = int(28 * 1.25)  # 35 (25% larger)
        digit_spacing = int(32 * 1.5)  # 48 (50% more spacing)
        total_width = 4 * digit_spacing + 35  # 4 digits plus decimal point space
        start_x = range_rect[0] + gauge_width - total_width - 10
        start_y = range_rect[1] + 75
        
        draw_dsi_multi_digit_display(dsi_surface, display_range, 4, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3, decimal_pos=3)
    
    elif switch_trip_odo:
        # Show Trip Odometer Gauge
        if serial_connected:
            trip_miles = persistent_data.data["trip_odometer"]  # Use Pi's trip data directly
        elif not was_ever_connected:
            trip_miles = 123.4 + math.sin(time_ms * 0.0003) * 50  # Demo: 73-173 miles (only if never connected)
        else:
            trip_miles = persistent_data.data["trip_odometer"]  # Use Pi's trip data when disconnected
        
        # "TRIP ODO" title (top)
        trip_title = font_small.render("TRIP ODO", True, text_color)
        trip_title_rect = trip_title.get_rect()
        dsi_surface.blit(trip_title, (range_rect[0] + (gauge_width - trip_title_rect.width) // 2, range_rect[1] + 35))
        
        # Distance unit label (bottom)
        if switch_metric:
            trip_km = miles_to_km(trip_miles)
            distance_text = font_medium.render("KM", True, text_color)
            display_trip = trip_km
        else:
            distance_text = font_medium.render("MILES", True, text_color)
            display_trip = trip_miles
        distance_text_rect = distance_text.get_rect()
        dsi_surface.blit(distance_text, (range_rect[0] + (gauge_width - distance_text_rect.width) // 2, range_rect[1] + gauge_height - 35))
        
        # Trip digits (right side) - format 000.0 - 7-segment display with leading zero dimming
        digit_size = int(28 * 1.25)  # 35 (25% larger)
        digit_spacing = int(32 * 1.5)  # 48 (50% more spacing)
        total_width = 4 * digit_spacing + 35  # 4 digits plus decimal point space
        start_x = range_rect[0] + gauge_width - total_width - 10
        start_y = range_rect[1] + 75
        
        draw_dsi_multi_digit_display(dsi_surface, display_trip, 4, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3, decimal_pos=3)
    
    # If no switches active, just show empty gauge area
    
    # === 4. GAUGE 4 (Bottom Right) - Instant MPG or Average MPG ===
    mpg_rect = (DSI_SCREEN_WIDTH - gauge_width - margin, DSI_SCREEN_HEIGHT - gauge_height - bottom_margin, gauge_width, gauge_height)
    # No border for gauge 4
    
    if switch_inst_mpg:
        # Show Instant MPG Gauge
        if serial_connected:
            instant_mpg = current_inst_mpg  # Use real Arduino data
        elif not was_ever_connected:
            instant_mpg = 25 + math.sin(time_ms * 0.0004) * 25  # Demo: 0-50 MPG (only if never connected)
        else:
            instant_mpg = current_inst_mpg  # Use last known value when disconnected
        
        # "INSTANT" title (top)
        instant_title = font_small.render("INSTANT", True, text_color)
        instant_title_rect = instant_title.get_rect()
        dsi_surface.blit(instant_title, (mpg_rect[0] + (gauge_width - instant_title_rect.width) // 2, mpg_rect[1] + 35))
        
        # Handle special instant MPG values from Arduino
        digit_size = int(28 * 1.25)  # 35 (25% larger)
        digit_spacing = int(32 * 1.5)  # 48 (50% more spacing)
        start_x = mpg_rect[0] + 15
        start_y = mpg_rect[1] + 75
        
        if instant_mpg == 0.0:
            # Engine idling - show GPH using real fuel flow data
            if current_fuel_flow_gph > 0.01:  # Use real data if available
                gph_value = current_fuel_flow_gph
            else:
                gph_value = 0.8  # Fallback estimate for idling
            
            # Display GPH value using DSEG format (same as other DSI gauges)
            draw_dsi_multi_digit_display(dsi_surface, gph_value, 3, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3, decimal_pos=2)
        elif instant_mpg == -1.0:
            # Engine off - show "OFF"
            off_font = pygame.font.SysFont('Arial', 32, bold=True)
            off_text = off_font.render("OFF", True, (128, 128, 128))  # Gray color for OFF
            off_rect = off_text.get_rect()
            dsi_surface.blit(off_text, (start_x + 25, start_y + 10))
        else:
            # Normal MPG display (positive values only)
            if instant_mpg > 0:  # Only display positive MPG values
                if switch_metric:
                    instant_lp100km = mpg_to_lp100km(instant_mpg)
                    display_instant = instant_lp100km
                else:
                    display_instant = instant_mpg
                
                draw_dsi_multi_digit_display(dsi_surface, display_instant, 3, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3, decimal_pos=2)
            else:
                # Handle unexpected negative values - show "---"
                dash_font = pygame.font.SysFont('Arial', 32, bold=True)
                dash_text = dash_font.render("---", True, (128, 128, 128))
                dsi_surface.blit(dash_text, (start_x + 25, start_y + 10))
        
        # Fuel economy unit label (under the digits)
        if instant_mpg == 0.0:
            # Show "GPH" when idling
            fuel_econ_text = font_medium.render("GPH", True, text_color)
        elif switch_metric:
            fuel_econ_text = font_medium.render("L/100km", True, text_color)
        else:
            fuel_econ_text = font_medium.render("MPG", True, text_color)
        fuel_econ_text_rect = fuel_econ_text.get_rect()
        dsi_surface.blit(fuel_econ_text, (mpg_rect[0] + (gauge_width - fuel_econ_text_rect.width) // 2, mpg_rect[1] + gauge_height - 35))
    
    elif switch_avg_mpg:
        # Show Average MPG Gauge
        if serial_connected:
            avg_mpg = current_avg_mpg  # Use real Arduino data
        elif not was_ever_connected:
            avg_mpg = 22.3 + math.sin(time_ms * 0.0003) * 8  # Demo: 14-30 MPG (only if never connected)
        else:
            avg_mpg = current_avg_mpg  # Use last known value when disconnected
        
        # "AVERAGE" title (top)
        avg_title = font_small.render("AVERAGE", True, text_color)
        avg_title_rect = avg_title.get_rect()
        dsi_surface.blit(avg_title, (mpg_rect[0] + (gauge_width - avg_title_rect.width) // 2, mpg_rect[1] + 35))
        
        # Fuel economy digits (left side) - format 00.0 - 7-segment display with leading zero dimming
        if switch_metric:
            avg_lp100km = mpg_to_lp100km(avg_mpg)
            display_avg = avg_lp100km
        else:
            display_avg = avg_mpg
        digit_size = int(28 * 1.25)  # 35 (25% larger)
        digit_spacing = int(32 * 1.5)  # 48 (50% more spacing)
        start_x = mpg_rect[0] + 15
        start_y = mpg_rect[1] + 75
        
        draw_dsi_multi_digit_display(dsi_surface, display_avg, 3, start_x, start_y, digit_spacing, digit_color, digit_size, 0.3, decimal_pos=2)
        
        # Fuel economy unit label (under the digits)
        if switch_metric:
            fuel_econ_text = font_medium.render("L/100km", True, text_color)
        else:
            fuel_econ_text = font_medium.render("MPG", True, text_color)
        fuel_econ_text_rect = fuel_econ_text.get_rect()
        dsi_surface.blit(fuel_econ_text, (mpg_rect[0] + (gauge_width - fuel_econ_text_rect.width) // 2, mpg_rect[1] + gauge_height - 35))
    else:
        # If no switches active, just show empty gauge area
        pass
    
    # === 5. FUEL LEVEL GAUGE (Center, vertical bar of ticks) ===
    fuel_center_x = DSI_SCREEN_WIDTH // 2
    fuel_y_start = top_margin + 20  # Use adjusted top margin
    fuel_y_end = DSI_SCREEN_HEIGHT - bottom_margin - 80  # Use adjusted bottom margin
    fuel_height = fuel_y_end - fuel_y_start
    
    # Fuel level (real Arduino data or demo - 0.0 to 1.0)
    if serial_connected:
        fuel_level = current_fuel_level / 100.0  # Convert percentage to 0.0-1.0 range
    elif not was_ever_connected:
        fuel_level = 0.5 + math.sin(time_ms * 0.0001) * 0.5  # Demo: 0-100% full (only if never connected)
    else:
        fuel_level = current_fuel_level / 100.0  # Use last known value when disconnected
    
    # Draw fuel level ticks as horizontal bars (like speedometer) - higher resolution
    tick_count = 17  # More ticks for better resolution (every 1/16th)
    # Define which ticks get labels (every 4th tick: 0, 4, 8, 12, 16 = E, 1/4, 1/2, 3/4, F)
    tick_labels = ["E", "", "", "", "1/4", "", "", "", "1/2", "", "", "", "3/4", "", "", "", "F"]
    
    for i in range(tick_count):
        # Calculate position from bottom to top (E at bottom, F at top)
        tick_y = fuel_y_end - (i / (tick_count - 1)) * fuel_height
        fuel_ratio = i / (tick_count - 1)  # 0.0 to 1.0
        
        # Determine tick properties based on fuel level
        # Add small tolerance for floating-point precision (fixes 100% display issue)
        if fuel_ratio <= (fuel_level + 0.001):
            # Active ticks (fuel present)
            if fuel_ratio < 0.1:  # Very low fuel - red
                tick_color = RED
            elif fuel_ratio < 0.25:  # Low fuel - orange
                tick_color = ORANGE
            else:  # Normal fuel - green
                tick_color = BRIGHT_GREEN
        else:
            # Inactive ticks (no fuel)
            if fuel_ratio < 0.1:
                tick_color = (100, 0, 0)  # Dim red
            elif fuel_ratio < 0.25:
                tick_color = (100, 50, 0)  # Dim orange
            else:
                tick_color = DULL_GREEN  # Dim green
        
        # All ticks same length and 25% longer
        tick_width = int(80 * 1.25)  # 100px (25% longer)
        tick_thickness = 12  # Reduced thickness for better fit in window (was 16)
        
        # Calculate tick position (centered)
        tick_start_x = fuel_center_x - tick_width // 2
        tick_end_x = fuel_center_x + tick_width // 2
        
        # Draw thick horizontal tick (like speedometer)
        pygame.draw.line(dsi_surface, tick_color, 
                        (tick_start_x, tick_y), 
                        (tick_end_x, tick_y), 
                        tick_thickness)
        
        # Draw label if exists (to the left of the tick with dash)
        if tick_labels[i]:
            label_color = YELLOW if fuel_ratio <= fuel_level else (80, 80, 0)
            label_text = font_small.render(tick_labels[i], True, label_color)
            label_rect = label_text.get_rect()
            
            # Position label to the left of tick
            label_x = tick_start_x - label_rect.width - 20  # More space for dash
            label_y = tick_y - label_rect.height // 2
            dsi_surface.blit(label_text, (label_x, label_y))
            
            # Draw small yellow dash between label and tick
            dash_x = tick_start_x - 12  # Position dash between label and tick
            dash_y = tick_y
            pygame.draw.line(dsi_surface, YELLOW, (dash_x - 6, dash_y), (dash_x, dash_y), 3)
    
    # "RESERVE" warning (only if fuel is very low)
    if fuel_level < 0.1:
        reserve_text = font_medium.render("RESERVE", True, RED)
        reserve_rect = reserve_text.get_rect()
        dsi_surface.blit(reserve_text, (fuel_center_x - reserve_rect.width // 2, fuel_y_end + 20))
    
    # "UNLEADED FUEL ONLY" text and fuel pump symbol (bottom) - hide when RESERVE warning is showing
    if fuel_level >= 0.1:  # Only show when NOT in reserve (same condition as reserve warning but inverted)
        fuel_text1 = font_small.render("UNLEADED", True, text_color)
        fuel_text2 = font_small.render("FUEL ONLY", True, text_color)
        
        fuel_text1_rect = fuel_text1.get_rect()
        fuel_text2_rect = fuel_text2.get_rect()
        
        text_y = DSI_SCREEN_HEIGHT - bottom_margin - 50  # Moved up 15px more (was -35, now -50)
        # Center the text under the fuel gauge
        dsi_surface.blit(fuel_text1, (fuel_center_x - fuel_text1_rect.width // 2, text_y))
        dsi_surface.blit(fuel_text2, (fuel_center_x - fuel_text2_rect.width // 2, text_y + 20))
        
        # Gas pump symbol from PNG (to the left of the text)
        if gas_pump_symbol:
            symbol_x = fuel_center_x - 100  # Moved further left
            symbol_y = text_y - 15  # Moved up
            # Scale the symbol to appropriate size (about 50x50 pixels - 2x larger)
            scaled_symbol = pygame.transform.scale(gas_pump_symbol, (50, 50))
            dsi_surface.blit(scaled_symbol, (symbol_x, symbol_y))
        else:
            # Fallback: More realistic gas pipe symbol
            pipe_x = fuel_center_x - 80
            pipe_y = text_y + 8
            # Main vertical pipe
            pygame.draw.rect(dsi_surface, text_color, (pipe_x, pipe_y - 5, 4, 15), 0)
            # Horizontal connector
            pygame.draw.rect(dsi_surface, text_color, (pipe_x + 4, pipe_y + 2, 12, 4), 0)
            # Nozzle tip
            pygame.draw.rect(dsi_surface, text_color, (pipe_x + 16, pipe_y + 1, 8, 6), 0)
            # Handle
            pygame.draw.rect(dsi_surface, text_color, (pipe_x - 2, pipe_y - 8, 8, 3), 0)
    
    # DSI content is now drawn directly on the passed surface
    # No need to blit since we're using the surface parameter directly

print("C4 Corvette Dashboard - Triple Display System")
print(f"Arduino: {SERIAL_PORT} @ {SERIAL_BAUD} baud - {'Connected' if serial_connected else 'Demo Mode'}")
print("Press ESC to exit | F11 for fullscreen")

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    """Handle SIGTERM and SIGINT for graceful shutdown"""
    global running
    running = False

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# ===== CITROËN BX STYLE FUNCTIONS =====

def draw_bx_road_speedometer(surface, speed, rect):
    """Draw Citroën BX style road speedometer - two vertical lines going into distance"""
    # Road dimensions
    road_bottom_width = 120
    road_top_width = 40
    road_height = 200
    
    # Calculate road lines (perspective effect)
    center_x = rect[0] + rect[2] // 2
    bottom_y = rect[1] + rect[3] - 20
    top_y = bottom_y - road_height
    
    # Left road line
    left_bottom = center_x - road_bottom_width // 2
    left_top = center_x - road_top_width // 2
    
    # Right road line  
    right_bottom = center_x + road_bottom_width // 2
    right_top = center_x + road_top_width // 2
    
    # Draw road lines
    pygame.draw.line(surface, BX_GREEN, (left_bottom, bottom_y), (left_top, top_y), 3)
    pygame.draw.line(surface, BX_GREEN, (right_bottom, bottom_y), (right_top, top_y), 3)
    
    # Draw speed ticks along the road (0-120 MPH)
    max_speed = 120
    num_ticks = 12  # Every 10 MPH
    
    for i in range(num_ticks + 1):
        tick_speed = i * 10
        tick_progress = i / num_ticks
        
        # Calculate tick position (bottom to top)
        tick_y = bottom_y - (tick_progress * road_height)
        tick_left_x = left_bottom - (tick_progress * (road_bottom_width - road_top_width) // 2)
        tick_right_x = right_bottom + (tick_progress * (road_bottom_width - road_top_width) // 2)
        
        # Highlight ticks based on current speed
        if tick_speed <= speed:
            color = BX_GREEN
            thickness = 3
        else:
            color = BX_DIM_GREEN
            thickness = 1
            
        # Draw tick across the road
        pygame.draw.line(surface, color, (tick_left_x, tick_y), (tick_right_x, tick_y), thickness)
    
    # Draw digital speed in the center
    font = pygame.font.SysFont('Arial', 48, bold=True)
    speed_text = font.render(f"{int(speed)}", True, BX_GREEN)
    speed_rect = speed_text.get_rect(center=(center_x, bottom_y - road_height // 2))
    surface.blit(speed_text, speed_rect)

def draw_bx_arch_tachometer(surface, rpm, rect):
    """Draw Citroën BX style arch tachometer above the speedometer"""
    # Arch dimensions
    center_x = rect[0] + rect[2] // 2
    center_y = rect[1] + 60
    radius = 100
    
    # RPM range (0-6000)
    max_rpm = 6000
    start_angle = math.pi  # 180 degrees (left)
    end_angle = 0  # 0 degrees (right)
    total_angle = start_angle - end_angle
    
    # Draw arch background
    pygame.draw.arc(surface, BX_DIM_GREEN, 
                   (center_x - radius, center_y - radius, radius * 2, radius * 2),
                   end_angle, start_angle, 3)
    
    # Draw RPM ticks
    num_ticks = 12  # Every 500 RPM
    for i in range(num_ticks + 1):
        tick_rpm = i * 500
        tick_progress = i / num_ticks
        
        # Calculate tick angle (left to right)
        tick_angle = start_angle - (tick_progress * total_angle)
        
        # Highlight ticks based on current RPM
        if tick_rpm <= rpm:
            color = BX_GREEN
            thickness = 4
        else:
            color = BX_DIM_GREEN
            thickness = 2
            
        # Calculate tick position
        inner_radius = radius - 15
        outer_radius = radius + 5
        
        inner_x = center_x + inner_radius * math.cos(tick_angle)
        inner_y = center_y - inner_radius * math.sin(tick_angle)
        outer_x = center_x + outer_radius * math.cos(tick_angle)
        outer_y = center_y - outer_radius * math.sin(tick_angle)
        
        pygame.draw.line(surface, color, (inner_x, inner_y), (outer_x, outer_y), thickness)
    
    # Draw digital RPM below arch
    font = pygame.font.SysFont('Arial', 24, bold=True)
    rpm_text = font.render(f"{int(rpm)}", True, BX_GREEN)
    rpm_rect = rpm_text.get_rect(center=(center_x, center_y + 40))
    surface.blit(rpm_text, rpm_rect)

def draw_bx_horizontal_bar(surface, value, max_value, rect, label):
    """Draw horizontal bar gauge for fuel level"""
    bar_width = rect[2] - 40
    bar_height = 20
    bar_x = rect[0] + 20
    bar_y = rect[1] + 30
    
    # Draw background bar
    pygame.draw.rect(surface, BX_DIM_GREEN, (bar_x, bar_y, bar_width, bar_height), 2)
    
    # Draw filled portion
    fill_width = int((value / max_value) * bar_width)
    if fill_width > 0:
        pygame.draw.rect(surface, BX_GREEN, (bar_x + 2, bar_y + 2, fill_width - 4, bar_height - 4))
    
    # Draw label and value
    font = pygame.font.SysFont('Arial', 16, bold=True)
    label_text = font.render(label, True, BX_GREEN)
    surface.blit(label_text, (bar_x, bar_y - 25))
    
    value_text = font.render(f"{value:.1f}", True, BX_GREEN)
    surface.blit(value_text, (bar_x + bar_width - 50, bar_y - 25))

def draw_bx_vertical_bar(surface, value, max_value, rect, label):
    """Draw vertical bar gauge for oil pressure, temperature, etc."""
    bar_width = 20
    bar_height = rect[3] - 80
    bar_x = rect[0] + rect[2] // 2 - bar_width // 2
    bar_y = rect[1] + 50
    
    # Draw background bar
    pygame.draw.rect(surface, BX_DIM_GREEN, (bar_x, bar_y, bar_width, bar_height), 2)
    
    # Draw filled portion (bottom to top)
    fill_height = int((value / max_value) * bar_height)
    if fill_height > 0:
        pygame.draw.rect(surface, BX_GREEN, 
                        (bar_x + 2, bar_y + bar_height - fill_height - 2, bar_width - 4, fill_height))
    
    # Draw label and value
    font = pygame.font.SysFont('Arial', 14, bold=True)
    label_text = font.render(label, True, BX_GREEN)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + 20))
    surface.blit(label_text, label_rect)
    
    value_text = font.render(f"{value:.1f}", True, BX_GREEN)
    value_rect = value_text.get_rect(center=(rect[0] + rect[2] // 2, bar_y + bar_height + 20))
    surface.blit(value_text, value_rect)

def draw_bx_digital_display(surface, value, label, rect):
    """Draw digital display for trip, range, MPG values"""
    font_label = pygame.font.SysFont('Arial', 14, bold=True)
    font_value = pygame.font.SysFont('Arial', 20, bold=True)
    
    # Draw label
    label_text = font_label.render(label, True, BX_DIM_GREEN)
    surface.blit(label_text, (rect[0], rect[1]))
    
    # Draw value
    if isinstance(value, float):
        value_str = f"{value:.1f}"
    else:
        value_str = str(value)
    
    value_text = font_value.render(value_str, True, BX_GREEN)
    surface.blit(value_text, (rect[0], rect[1] + 20))

def draw_bx_horizontal_bar_thick(surface, value, max_value, rect, label):
    """Draw horizontal bar gauge - THICK VERSION with large fonts and DSEG numbers"""
    bar_width = rect[2] - 40
    bar_height = rect[3] - 60  # Use full rect height minus margins (THICK!)
    bar_x = rect[0] + 20
    bar_y = rect[1] + 50  # More space for larger label above
    
    # Draw background bar with thicker border
    pygame.draw.rect(surface, BX_DIM_GREEN, (bar_x, bar_y, bar_width, bar_height), 4)
    
    # Draw filled portion
    fill_width = int((value / max_value) * bar_width)
    if fill_width > 0:
        pygame.draw.rect(surface, BX_GREEN, (bar_x + 4, bar_y + 4, fill_width - 8, bar_height - 8))
    
    # Draw label with medium font (72pt → 36pt)
    font_medium = pygame.font.SysFont('Arial', 36, bold=True)
    label_text = font_medium.render(label, True, BX_GREEN)
    surface.blit(label_text, (bar_x, bar_y - 50))  # Adjusted space for smaller text
    
    # Draw value using DSEG 7-segment display (smaller size)
    # Calculate DSEG size to match 36pt font height (~30px)
    dseg_size = 30  # Size for 7-segment digits (reduced from 60px)
    
    # Format value based on type and range - match Synthwave formatting
    try:
        # Handle special "LO" temperature readings
        if value <= -999:  # Special "LO" temperature value from Arduino
            # Display "LO" like original C4 cluster
            lo_font = pygame.font.SysFont('Arial', dseg_size, bold=True)
            lo_text = lo_font.render("LO", True, BX_GREEN)
            lo_x = bar_x + bar_width - 80
            lo_y = bar_y - 70
            surface.blit(lo_text, (lo_x, lo_y))
            return
        
        # Determine format based on label type (match Synthwave style)
        if "VOLT" in label.upper():
            # Voltage: 00.0 format (3 digits with decimal)
            num_digits = 3
            digit_width = dseg_size + 20
            display_value = max(0, min(99.9, value))  # Keep raw voltage value for DSI function
            decimal_pos = 2  # Decimal after 2nd digit
            has_decimal = True
        elif "TEMP" in label.upper() or "°F" in label or "°C" in label:
            # Temperature: 000 format (3 digits, integer)
            num_digits = 3
            digit_width = dseg_size + 20
            display_value = max(0, min(999, int(round(value))))
            has_decimal = False
        elif "PRESSURE" in label.upper() or "PSI" in label.upper():
            # Pressure: 000 format (3 digits, integer)
            num_digits = 3
            digit_width = dseg_size + 20
            display_value = max(0, min(999, int(round(value))))
            has_decimal = False
        elif "FUEL" in label.upper() or "%" in label:
            # Fuel: 000 format (3 digits, integer percentage)
            num_digits = 3
            digit_width = dseg_size + 20
            display_value = max(0, min(999, int(round(value))))
            has_decimal = False
        else:
            # Default: 000 format (3 digits, integer)
            num_digits = 3
            digit_width = dseg_size + 20
            display_value = max(0, min(999, int(round(value))))
            has_decimal = False
        
        # Position DSEG numbers on the right side, moved up from the bar
        dseg_start_x = bar_x + bar_width - (num_digits * digit_width) - 20
        dseg_start_y = bar_y - 70  # Moved up from bar
        
        # Draw DSEG numbers with appropriate formatting
        if has_decimal and "VOLT" in label.upper():
            # Use DSI multi-digit display for voltage with decimal point
            draw_dsi_multi_digit_display(surface, display_value, num_digits, dseg_start_x, dseg_start_y, 
                                       digit_width, BX_GREEN, dseg_size, leading_zero_dim=0.5, decimal_pos=decimal_pos)
        else:
            # Use regular multi-digit display for other values
            draw_multi_digit_display(surface, display_value, num_digits, dseg_start_x, dseg_start_y, 
                                   digit_width, BX_GREEN, dseg_size, leading_zero_dim=0.5)
    except (ValueError, TypeError):
        # Fallback: draw "---" if value conversion fails
        font_fallback = pygame.font.SysFont('Arial', dseg_size, bold=True)
        fallback_text = font_fallback.render("---", True, BX_GREEN)
        fallback_x = bar_x + bar_width - 100
        fallback_y = bar_y - 70  # Match DSEG position
        surface.blit(fallback_text, (fallback_x, fallback_y))
    
    # Add min/max static values outside the bar with larger font
    min_max_font = pygame.font.SysFont('Arial', 24, bold=True)  # Increased from 18 to 24
    
    # Determine min/max values based on gauge type
    if "VOLT" in label.upper():
        min_val, max_val = "8.0", "16.0"
    elif "FUEL" in label.upper() or "%" in label:
        min_val, max_val = "0", "100"
    elif "PRESSURE" in label.upper() or "PSI" in label.upper():
        min_val, max_val = "0", "80"
    elif "TEMP" in label.upper() and ("°F" in label or "TEMPERATURE" in label.upper()):
        min_val, max_val = "100", "260"
    else:
        # Default range
        min_val, max_val = "0", str(int(max_value))
    
    # Draw min value (outside bottom left of bar) - brighter color
    min_text = min_max_font.render(min_val, True, BX_GREEN)
    min_x = bar_x - 10  # Moved outside bar (was bar_x + 5)
    min_y = bar_y + bar_height + 10  # Below the bar (was bar_y + bar_height - 25)
    surface.blit(min_text, (min_x, min_y))
    
    # Draw max value (outside bottom right of bar) - brighter color
    max_text = min_max_font.render(max_val, True, BX_GREEN)
    max_text_rect = max_text.get_rect()
    max_x = bar_x + bar_width - max_text_rect.width + 10  # Moved outside bar (was - 5)
    max_y = bar_y + bar_height + 10  # Below the bar (was bar_y + bar_height - 25)
    surface.blit(max_text, (max_x, max_y))

def draw_bx_single_dseg_bordered(surface, value, label, rect):
    """Draw single DSEG-style display with rectangular border (switchable like Synthwave)"""
    # Draw border
    pygame.draw.rect(surface, BX_GREEN, rect, 4)
    
    # Calculate inner area
    border_margin = 15
    inner_rect = (rect[0] + border_margin, rect[1] + border_margin, 
                  rect[2] - (border_margin * 2), rect[3] - (border_margin * 2))
    
    # Draw the single display
    draw_bx_single_dseg_display(surface, value, label, inner_rect)

def draw_bx_thick_road_speedometer(surface, speed, rect):
    """Draw Citroën BX style road speedometer - THICK TAPERED BARS that fill based on speed"""
    # Road dimensions - much wider gap for triple digit DSEG numbers
    road_bottom_width = 507  # 30% wider again (390 * 1.3 = 507)
    road_top_width = 152     # 30% wider top (117 * 1.3 = 152)
    road_height = 180
    bar_thickness_bottom = 75  # Keep same thickness
    bar_thickness_top = 24     # Keep same thickness
    
    # Calculate road center and positions - moved much higher on screen
    center_x = rect[0] + rect[2] // 2
    top_y = rect[1] - 50   # Moved up 10 pixels more to prevent bottom cutoff
    bottom_y = top_y + road_height  # Calculate bottom from top
    
    # Speed range for filling (0-120 MPH)
    max_speed = 120
    speed_progress = min(speed / max_speed, 1.0)  # 0.0 to 1.0
    
    # Calculate fill height based on speed
    fill_height = int(speed_progress * road_height)
    fill_top_y = bottom_y - fill_height
    
    # Left road bar coordinates
    left_bottom_outer = center_x - road_bottom_width // 2
    left_bottom_inner = left_bottom_outer + bar_thickness_bottom
    left_top_outer = center_x - road_top_width // 2
    left_top_inner = left_top_outer + bar_thickness_top
    
    # Right road bar coordinates
    right_bottom_outer = center_x + road_bottom_width // 2
    right_bottom_inner = right_bottom_outer - bar_thickness_bottom
    right_top_outer = center_x + road_top_width // 2
    right_top_inner = right_top_outer - bar_thickness_top
    
    # Draw complete left road bar outline (dim green background)
    left_complete_points = [
        (left_bottom_outer, bottom_y),
        (left_top_outer, top_y),
        (left_top_inner, top_y),
        (left_bottom_inner, bottom_y)
    ]
    pygame.draw.polygon(surface, BX_DIM_GREEN, left_complete_points)
    
    # Draw complete right road bar outline (dim green background)
    right_complete_points = [
        (right_bottom_outer, bottom_y),
        (right_top_outer, top_y),
        (right_top_inner, top_y),
        (right_bottom_inner, bottom_y)
    ]
    pygame.draw.polygon(surface, BX_DIM_GREEN, right_complete_points)
    
    # Draw filled portion on top (bright green) - same shape but clipped to fill height
    if fill_height > 0:
        filled_top_y = max(fill_top_y, top_y)
        
        # Calculate proportional coordinates at fill level
        fill_progress = (bottom_y - filled_top_y) / road_height
        left_fill_outer = left_bottom_outer + (fill_progress * (left_top_outer - left_bottom_outer))
        left_fill_inner = left_bottom_inner + (fill_progress * (left_top_inner - left_bottom_inner))
        right_fill_outer = right_bottom_outer + (fill_progress * (right_top_outer - right_bottom_outer))
        right_fill_inner = right_bottom_inner + (fill_progress * (right_top_inner - right_bottom_inner))
        
        # Draw left filled portion (maintains exact same taper)
        left_filled_points = [
            (left_bottom_outer, bottom_y),
            (left_fill_outer, filled_top_y),
            (left_fill_inner, filled_top_y),
            (left_bottom_inner, bottom_y)
        ]
        pygame.draw.polygon(surface, BX_GREEN, left_filled_points)
        
        # Draw right filled portion (maintains exact same taper)
        right_filled_points = [
            (right_bottom_outer, bottom_y),
            (right_fill_outer, filled_top_y),
            (right_fill_inner, filled_top_y),
            (right_bottom_inner, bottom_y)
        ]
        pygame.draw.polygon(surface, BX_GREEN, right_filled_points)
    
    # Draw speed markers every 20 MPH (including 0 MPH)
    for marker_speed in [0, 20, 40, 60, 80, 100, 120]:
        marker_progress = marker_speed / max_speed
        marker_y = bottom_y - (marker_progress * road_height)
        
        # Calculate road edge positions at this height (for outside markers)
        road_left_edge = center_x - (road_bottom_width // 2) + (marker_progress * (road_bottom_width - road_top_width) // 2)
        road_right_edge = center_x + (road_bottom_width // 2) - (marker_progress * (road_bottom_width - road_top_width) // 2)
        
        # Marker color based on speed
        marker_color = BX_GREEN if marker_speed <= speed else BX_DIM_GREEN
        marker_thickness = 3 if marker_speed <= speed else 1
        
        # Draw shorter marker lines OUTSIDE the road (not across it)
        marker_length = 30  # Short markers instead of full width
        
        # Left side marker (outside left road edge)
        left_marker_start = road_left_edge - marker_length - 10
        left_marker_end = road_left_edge - 10
        pygame.draw.line(surface, marker_color, (left_marker_start, marker_y), (left_marker_end, marker_y), marker_thickness)
        
        # Right side marker (outside right road edge)
        right_marker_start = road_right_edge + 10
        right_marker_end = road_right_edge + marker_length + 10
        pygame.draw.line(surface, marker_color, (right_marker_start, marker_y), (right_marker_end, marker_y), marker_thickness)
        
        # Draw speed numbers outside the road (30% larger font)
        if marker_speed == 0 or marker_speed % 40 == 0:  # Show numbers at 0, 40, 80, 120
            milestone_font_size = int(16 * 1.3)  # 30% larger (16 * 1.3 = 21)
            font = pygame.font.SysFont('Arial', milestone_font_size, bold=True)
            speed_num_text = font.render(str(marker_speed), True, marker_color)
            
            # Left side number (outside left marker)
            left_num_rect = speed_num_text.get_rect(center=(left_marker_start - 20, marker_y))
            surface.blit(speed_num_text, left_num_rect)
            
            # Right side number (outside right marker)
            right_num_rect = speed_num_text.get_rect(center=(right_marker_end + 20, marker_y))
            surface.blit(speed_num_text, right_num_rect)
    
    # Draw central speed in DSEG style (main speed display)
    dseg_size = 45  # Large DSEG for main speed display
    digit_width = dseg_size + 15  # Increased spacing between digits (was +10, now +15)
    
    # Format speed (2 or 3 digits)
    speed_value = int(speed)
    if speed_value >= 100:
        num_digits = 3
    elif speed_value >= 10:
        num_digits = 2
    else:
        num_digits = 1
    
    # Center the DSEG display
    total_width = num_digits * digit_width
    dseg_x = center_x - (total_width // 2)
    dseg_y = bottom_y - road_height // 2 - 20  # MOVED MUCH LOWER - positioned lower in the road gap
    
    # Draw DSEG speed display
    draw_multi_digit_display(surface, speed_value, num_digits, dseg_x, dseg_y, 
                           digit_width, BX_GREEN, dseg_size, leading_zero_dim=0.5)
    
    # Add MPH/KPH label under DSEG speed (same font as milestone numbers)
    milestone_font_size = int(16 * 1.3)  # Same as milestone font (21pt)
    unit_font = pygame.font.SysFont('Arial', milestone_font_size, bold=True)
    
    # Check metric switch for unit display
    unit_text = "KPH" if switch_metric else "MPH"
    unit_label = unit_font.render(unit_text, True, BX_GREEN)
    unit_rect = unit_label.get_rect(center=(center_x, dseg_y + dseg_size + 50))  # Reduced spacing to prevent bottom cutoff
    surface.blit(unit_label, unit_rect)

def draw_bx_gph_display(surface, gph_value, label, rect):
    """Draw GPH display using Synthwave method (no multiplication)"""
    # Label font and positioning
    label_font = pygame.font.SysFont('Arial', 24, bold=True)
    label_text = label_font.render(label, True, BX_GREEN)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + 20))
    surface.blit(label_text, label_rect)
    
    # DSEG display area
    dseg_area_height = rect[3] - 50
    dseg_y = rect[1] + 40
    
    # Use Synthwave's exact method - draw_dsi_multi_digit_display with decimal_pos=2
    digit_size = 35
    digit_spacing = digit_size + 20
    start_x = rect[0] + (rect[2] - (3 * digit_spacing)) // 2  # Center 3 digits
    start_y = dseg_y + dseg_area_height // 2 - digit_size // 2
    
    # Use the exact same function as Synthwave
    draw_dsi_multi_digit_display(surface, gph_value, 3, start_x, start_y, digit_spacing, BX_GREEN, digit_size, 0.3, decimal_pos=2)

def draw_bx_single_dseg_display(surface, value, label, rect):
    """Draw single DSEG value with label (larger size for single display)"""
    # Label font and positioning (larger for single display)
    label_font = pygame.font.SysFont('Arial', 24, bold=True)
    label_text = label_font.render(label, True, BX_GREEN)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + 20))
    surface.blit(label_text, label_rect)
    
    # DSEG display area (larger for single display)
    dseg_area_height = rect[3] - 50  # Leave space for label
    dseg_y = rect[1] + 40
    
    # Handle special values
    if value == -1.0:  # IDLE
        # Show "IDLE" text
        idle_font = pygame.font.SysFont('Arial', 32, bold=True)
        idle_text = idle_font.render("IDLE", True, BX_GREEN)
        idle_rect = idle_text.get_rect(center=(rect[0] + rect[2]//2, dseg_y + dseg_area_height//2))
        surface.blit(idle_text, idle_rect)
    elif value == -2.0:  # OFF
        # Show "OFF" text
        off_font = pygame.font.SysFont('Arial', 32, bold=True)
        off_text = off_font.render("OFF", True, BX_GREEN)
        off_rect = off_text.get_rect(center=(rect[0] + rect[2]//2, dseg_y + dseg_area_height//2))
        surface.blit(off_text, off_rect)
    else:
        # DSEG numbers (larger for single display)
        dseg_size = 35  # Increased from 25
        digit_width = dseg_size + 20  # Increased spacing
        
        # Format value based on type
        if "MPG" in label.upper():
            # MPG: 00.0 format with decimal
            if value > 0:
                display_value = max(0, min(999, int(round(value * 10))))
                num_digits = 3
                has_decimal = True
                decimal_pos = 2
            else:
                display_value = 0
                num_digits = 3
                has_decimal = False
                decimal_pos = None
        elif "GPH" in label.upper() or "FUEL GPH" in label.upper():
            # GPH: 0.0 format with decimal (same as MPG but separate for clarity)
            if value > 0:
                display_value = max(0, min(999, int(round(value * 10))))
                num_digits = 3
                has_decimal = True
                decimal_pos = 2
            else:
                display_value = 0
                num_digits = 3
                has_decimal = False
                decimal_pos = None
        else:
            # Trip/Range: 000.0 format with decimal for better precision
            display_value = max(0, min(9999, int(round(value * 10))))
            num_digits = 4
            has_decimal = True
            decimal_pos = 3
        
        # Center DSEG display
        total_width = num_digits * digit_width
        dseg_x = rect[0] + (rect[2] - total_width) // 2
        
        # Draw DSEG numbers
        if has_decimal:
            draw_dsi_multi_digit_display(surface, display_value, num_digits, dseg_x, dseg_y, 
                                       digit_width, BX_GREEN, dseg_size, leading_zero_dim=0.5, decimal_pos=decimal_pos)
        else:
            draw_multi_digit_display(surface, display_value, num_digits, dseg_x, dseg_y, 
                                   digit_width, BX_GREEN, dseg_size, leading_zero_dim=0.5)

def draw_bx_horizontal_arch_tachometer(surface, rpm, rect):
    """Draw Citroën BX style horizontal arch tachometer with milestone markers (no DSEG)"""
    # Arch dimensions - positioned much lower and made thicker
    center_x = rect[0] + rect[2] // 2
    center_y = rect[1] + 150  # Moved much lower - well into visible area
    arch_width = 600  # Wide horizontal arch
    arch_height = 100  # Height for good proportions
    
    # RPM range (0-6000)
    max_rpm = 6000
    rpm_progress = min(rpm / max_rpm, 1.0)  # 0.0 to 1.0
    
    # Arch coordinates (horizontal ellipse)
    arch_rect = (center_x - arch_width // 2, center_y - arch_height // 2, arch_width, arch_height)
    
    # Draw arch using vertical lines with variable heights
    # Taller at sides (low/high RPM), shorter in middle (mid RPM)
    
    num_lines = 200  # More lines for no gaps between ticks
    arch_start_x = center_x - arch_width // 2 + 20
    arch_end_x = center_x + arch_width // 2 - 20
    
    for i in range(num_lines):
        # Calculate X position for this line (LEFT TO RIGHT)
        line_x = arch_start_x + (i / (num_lines - 1)) * (arch_end_x - arch_start_x)
        
        # Calculate RPM progress for this X position (LEFT = 0 RPM, RIGHT = 6000 RPM)
        line_rpm_progress = i / (num_lines - 1)  # 0.0 to 1.0 (LEFT TO RIGHT)
        line_actual_rpm = line_rpm_progress * 6000  # Convert to actual RPM
        
        # Uniform tick height across the whole arch
        line_height = 30  # Fixed height for all ticks
        
        # Calculate Y position on the arch curve
        # Use ellipse equation for smooth arch shape
        x_offset = line_x - center_x
        a = arch_width // 2  # Semi-major axis
        b = arch_height // 2  # Semi-minor axis
        
        # Calculate Y position on ellipse
        x_ratio = x_offset / a
        if abs(x_ratio) <= 1.0:
            y_offset = math.sqrt(max(0, 1 - x_ratio * x_ratio)) * b
            line_top_y = center_y - y_offset
        else:
            line_top_y = center_y
        
        # Determine line color based on RPM and redline
        if line_actual_rpm >= 4500:  # Redline range (same as synthwave)
            bg_color = (150, 50, 50)  # Dim red for redline background
            fill_color = (255, 100, 100)  # Bright red for redline fill
        else:
            bg_color = BX_DIM_GREEN  # Normal dim green
            fill_color = BX_GREEN    # Normal bright green
        
        # Draw background line (thicker for no gaps)
        line_bottom_y = line_top_y + line_height
        pygame.draw.line(surface, bg_color, (line_x, line_top_y), (line_x, line_bottom_y), 4)
        
        # Draw filled portion - LEFT TO RIGHT fill
        if line_rpm_progress <= rpm_progress:  # Only fill lines up to current RPM
            pygame.draw.line(surface, fill_color, (line_x, line_top_y), (line_x, line_bottom_y), 4)
    
    # Draw RPM milestone markers with EQUAL SPACING (linear, not trigonometric)
    for i, marker_rpm in enumerate([0, 1000, 2000, 3000, 4000, 5000, 6000]):
        # Calculate EQUAL horizontal spacing across the arch width
        marker_progress = i / 6.0  # 0.0, 0.167, 0.333, 0.5, 0.667, 0.833, 1.0
        
        # Linear positioning for equal spacing
        marker_x = (center_x - arch_width // 2 + 20) + marker_progress * (arch_width - 40)
        
        # Calculate Y position on the arch curve for this X position
        # Use ellipse equation: y = center_y - sqrt((1 - ((x-center_x)/a)^2) * b^2)
        x_offset = marker_x - center_x
        a = arch_width // 2  # Semi-major axis
        b = arch_height // 2  # Semi-minor axis
        
        # Ensure we don't go outside the ellipse bounds
        x_ratio = x_offset / a
        if abs(x_ratio) <= 1.0:
            y_offset = math.sqrt(max(0, 1 - x_ratio * x_ratio)) * b
            marker_y = center_y - y_offset
        else:
            marker_y = center_y  # Fallback to center if calculation fails
        
        # Marker color based on current RPM (same thickness for all)
        if marker_rpm <= rpm:
            marker_color = BX_GREEN
        else:
            marker_color = BX_DIM_GREEN
        
        marker_thickness = 2  # Same thickness for both highlighted and non-highlighted
        
        # Draw vertical marker lines extending below the arch (moved slightly up)
        marker_length = 15  # Shorter milestone lines
        marker_start_y = marker_y + 40  # Moved slightly up from +50 to +40
        marker_end_y = marker_start_y + marker_length
        pygame.draw.line(surface, marker_color, (marker_x, marker_start_y), (marker_x, marker_end_y), marker_thickness)
        
        # Draw RPM numbers below markers (show at 0, 2000, 4000, 6000)
        if marker_rpm % 2000 == 0:  # Show numbers at 0, 2000, 4000, 6000
            milestone_font_size = int(16 * 1.3)  # Same as speedometer (21pt)
            font = pygame.font.SysFont('Arial', milestone_font_size, bold=True)
            
            # Format RPM number (show as thousands: 0, 2, 4, 6)
            rpm_display = marker_rpm // 1000
            rpm_num_text = font.render(str(rpm_display), True, marker_color)
            rpm_num_rect = rpm_num_text.get_rect(center=(marker_x, marker_end_y + 12))  # Moved slightly up from +15 to +12
            surface.blit(rpm_num_text, rpm_num_rect)
    
    # Draw REDLINE warning text when RPM >= 4500 (between speedometer and tachometer area)
    if rpm >= 4500:
        # Pulsing effect for redline warning
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 0.5 + 0.5
        warning_font = pygame.font.SysFont('Arial', 32, bold=True)
        
        if rpm >= 5000:  # Critical redline - red pulsing
            warning_color = (int(255 * pulse), 0, 0)
        else:  # Warning zone - yellow
            warning_color = (255, 255, 0)
        
        warning_text = warning_font.render("REDLINE", True, warning_color)
        # Position between speedometer (bottom) and tachometer (top) - center of DSI screen
        warning_rect = warning_text.get_rect(center=(center_x, center_y + 20))
        surface.blit(warning_text, warning_rect)

def draw_xt_3d_vertical_bar(surface, value, max_value, rect, label, color_scheme='amber'):
    """Draw Subaru XT style 3D vertical bar with proper depth order and real values"""
    # Enhanced 3D effect parameters
    bar_width = rect[2] - 40
    bar_height = rect[3] - 120  # More space for labels and DSEG numbers
    bar_x = rect[0] + 20
    bar_y = rect[1] + 80  # More space at top for multi-line labels
    
    # Much deeper 3D effect
    depth = 20  # Deep 3D appearance
    
    # Color scheme with enhanced 3D shading
    bright_color = XT_AMBER
    dim_color = XT_DIM_AMBER
    darker_color = (100, 60, 0)  # Even darker for deep shadows
    bg_color = XT_BLACK
    
    # Check for "LO" condition (for temperature sensors)
    show_lo = False
    if "TEMP" in label.upper() and value < 100:  # Temperature showing LO
        show_lo = True
    
    # STEP 1: Draw vertex lines FIRST (background layer - will be hidden by faces)
    vertex_color = (max(0, XT_AMBER[0] - 50), max(0, XT_AMBER[1] - 30), max(0, XT_AMBER[2] - 10))  # Slightly darker than bright amber, ensure valid range
    
    # Only draw vertex lines that should be visible (not hidden behind faces)
    # Back edges (always visible)
    pygame.draw.line(surface, vertex_color, (bar_x + depth, bar_y - depth), (bar_x + depth, bar_y + bar_height - depth), 2)  # Left back edge
    pygame.draw.line(surface, vertex_color, (bar_x + bar_width + depth, bar_y - depth), (bar_x + bar_width + depth, bar_y + bar_height - depth), 2)  # Right back edge
    pygame.draw.line(surface, vertex_color, (bar_x + depth, bar_y - depth), (bar_x + bar_width + depth, bar_y - depth), 2)  # Top back edge
    pygame.draw.line(surface, vertex_color, (bar_x + depth, bar_y + bar_height - depth), (bar_x + bar_width + depth, bar_y + bar_height - depth), 2)  # Bottom back edge
    
    # Depth connecting edges (always visible)
    pygame.draw.line(surface, vertex_color, (bar_x, bar_y), (bar_x + depth, bar_y - depth), 2)  # Top-left connection
    pygame.draw.line(surface, vertex_color, (bar_x + bar_width, bar_y), (bar_x + bar_width + depth, bar_y - depth), 2)  # Top-right connection
    pygame.draw.line(surface, vertex_color, (bar_x, bar_y + bar_height), (bar_x + depth, bar_y + bar_height - depth), 2)  # Bottom-left connection
    pygame.draw.line(surface, vertex_color, (bar_x + bar_width, bar_y + bar_height), (bar_x + bar_width + depth, bar_y + bar_height - depth), 2)  # Bottom-right connection
    
    # STEP 2: Draw filled portion (middle layer)
    if not show_lo:
        fill_height = int((value / max_value) * bar_height)
        if fill_height > 0:
            fill_y = bar_y + bar_height - fill_height
            
            # Main filled face (back layer)
            pygame.draw.rect(surface, bright_color, (bar_x + 6, fill_y + 2, bar_width - 12, fill_height - 6))
            
            # Top face of filled portion (3D effect)
            if fill_height < bar_height - 6:
                fill_top_points = [(bar_x + 6, fill_y + 2), (bar_x + depth - 4, fill_y - depth + 4),
                                  (bar_x + bar_width + depth - 10, fill_y - depth + 4), (bar_x + bar_width - 6, fill_y + 2)]
                pygame.draw.polygon(surface, bright_color, fill_top_points)
            
            # Right face of filled portion (3D effect)
            if bar_width > 12:
                fill_right_points = [(bar_x + bar_width - 6, fill_y + 2), (bar_x + bar_width + depth - 10, fill_y - depth + 4),
                                   (bar_x + bar_width + depth - 10, bar_y + bar_height - depth + 2), (bar_x + bar_width - 6, bar_y + bar_height - 2)]
                pygame.draw.polygon(surface, dim_color, fill_right_points)
            
            # Add ONLY top vertex lines to the filled portion (other edges hidden by container)
            fill_vertex_color = (max(0, bright_color[0] - 40), max(0, bright_color[1] - 25), max(0, bright_color[2] - 15))  # Darker than fill color
            
            # Only draw the top edges of filled portion (visible edges only)
            if fill_height < bar_height - 6:  # Only if there's a visible top face
                # Top front edge of fill
                pygame.draw.line(surface, fill_vertex_color, (bar_x + 6, fill_y + 2), (bar_x + bar_width - 6, fill_y + 2), 2)
                # Top back edge of fill  
                pygame.draw.line(surface, fill_vertex_color, (bar_x + depth - 4, fill_y - depth + 4), (bar_x + bar_width + depth - 10, fill_y - depth + 4), 2)
                # Top-left connection of fill
                pygame.draw.line(surface, fill_vertex_color, (bar_x + 6, fill_y + 2), (bar_x + depth - 4, fill_y - depth + 4), 2)
                # Top-right connection of fill
                pygame.draw.line(surface, fill_vertex_color, (bar_x + bar_width - 6, fill_y + 2), (bar_x + bar_width + depth - 10, fill_y - depth + 4), 2)
    
    # STEP 3: Draw frame faces ON TOP (front layer) - will hide vertex lines behind them
    # Main frame (ONLY border, no fill to keep it transparent)
    pygame.draw.rect(surface, dim_color, (bar_x, bar_y, bar_width, bar_height), 4)
    
    # Top face frame (3D effect) - brighter (will hide top vertex lines)
    top_points = [(bar_x, bar_y), (bar_x + depth, bar_y - depth), 
                  (bar_x + bar_width + depth, bar_y - depth), (bar_x + bar_width, bar_y)]
    pygame.draw.polygon(surface, bright_color, top_points)
    pygame.draw.polygon(surface, dim_color, top_points, 2)  # Outline
    
    # Right face frame (3D effect) - darker for depth (will hide right vertex lines)
    right_points = [(bar_x + bar_width, bar_y), (bar_x + bar_width + depth, bar_y - depth),
                    (bar_x + bar_width + depth, bar_y + bar_height - depth), (bar_x + bar_width, bar_y + bar_height)]
    pygame.draw.polygon(surface, darker_color, right_points)
    pygame.draw.polygon(surface, dim_color, right_points, 2)  # Outline
    
    # Add horizontal grid lines to container bar for reference
    grid_color = (max(0, dim_color[0] + 20), max(0, dim_color[1] + 15), max(0, dim_color[2] + 10))  # Slightly brighter than dim color
    num_grid_lines = 8  # Number of horizontal reference lines
    
    for i in range(1, num_grid_lines):  # Skip first and last (they're the borders)
        grid_y = bar_y + (i * bar_height // num_grid_lines)
        # Main horizontal grid line (front face)
        pygame.draw.line(surface, grid_color, (bar_x + 4, grid_y), (bar_x + bar_width - 4, grid_y), 1)
        # 3D effect grid line on right face - FIXED to match vertex line angles exactly
        grid_right_start_y = grid_y - depth  # Match the exact angle of vertex lines
        pygame.draw.line(surface, grid_color, (bar_x + bar_width, grid_y), (bar_x + bar_width + depth, grid_right_start_y), 1)
    
    # Add min/max labels at the beginning and end of the bar (like Citroën style) - MUCH LARGER SIZE
    minmax_font = pygame.font.SysFont('Arial', 24, bold=True)  # Increased from 20 to 24 for better readability
    
    # Determine min/max labels based on gauge type
    if "FUEL" in label.upper():
        min_label = "E"
        max_label = "F"
    elif "TEMP" in label.upper():
        min_label = "LO"
        max_label = "HI"
    elif "VOLTS" in label.upper():
        min_label = "8"
        max_label = "16"
    elif "PRESS" in label.upper():
        min_label = "0"
        max_label = "80"
    else:
        min_label = "0"
        max_label = str(int(max_value))
    
    # Draw min label (bottom of bar) - LARGER
    min_text = minmax_font.render(min_label, True, bright_color)
    min_rect = min_text.get_rect(center=(bar_x - 30, bar_y + bar_height - 15))
    surface.blit(min_text, min_rect)
    
    # Draw max label (top of bar) - LARGER
    max_text = minmax_font.render(max_label, True, bright_color)
    max_rect = max_text.get_rect(center=(bar_x - 30, bar_y + 15))
    surface.blit(max_text, max_rect)
    
    # STEP 4: Draw front vertex lines ON TOP (only the ones that should be visible in front)
    # Front edges (visible on top of everything)
    pygame.draw.line(surface, vertex_color, (bar_x, bar_y), (bar_x, bar_y + bar_height), 2)  # Left front edge
    pygame.draw.line(surface, vertex_color, (bar_x + bar_width, bar_y), (bar_x + bar_width, bar_y + bar_height), 2)  # Right front edge
    pygame.draw.line(surface, vertex_color, (bar_x, bar_y), (bar_x + bar_width, bar_y), 2)  # Top front edge
    pygame.draw.line(surface, vertex_color, (bar_x, bar_y + bar_height), (bar_x + bar_width, bar_y + bar_height), 2)  # Bottom front edge
    
    # Draw multi-line label with better formatting
    font_label = pygame.font.SysFont('Arial', 16, bold=True)
    
    # Handle multi-line labels
    if "BATTERY" in label.upper():
        lines = ["BATTERY", "VOLTS"]
    elif "COOLANT" in label.upper():
        lines = ["COOLANT", "TEMP °F"]
    elif "OIL TEMP" in label.upper():
        lines = ["OIL", "TEMP °F"]
    elif "OIL PRESS" in label.upper():
        lines = ["OIL", "PRESS PSI"]
    elif "FUEL" in label.upper():
        lines = ["FUEL", "%"]
    else:
        lines = [label]
    
    # Draw each line of the label
    for i, line in enumerate(lines):
        line_text = font_label.render(line, True, bright_color)
        line_rect = line_text.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + 20 + i * 20))
        surface.blit(line_text, line_rect)
    
    # Draw value in DSEG style with REAL VALUES from Arduino
    dseg_size = 30  # Larger DSEG digits
    digit_width = dseg_size + 8
    
    if show_lo:
        # Show "LO" text for low temperature readings
        lo_font = pygame.font.SysFont('Arial', 32, bold=True)
        lo_text = lo_font.render("LO", True, bright_color)
        lo_rect = lo_text.get_rect(center=(rect[0] + rect[2] // 2, bar_y + bar_height + 40))
        surface.blit(lo_text, lo_rect)
    else:
        # Draw value in DSEG format
        dseg_size = 32  # Large DSEG digits for bar values
        digit_width = dseg_size + 15  # Increased gap between digits
        
        # Format value for DSEG display with real Arduino values
        if "VOLTS" in label.upper():
            # Voltage: 00.0 format (e.g., 12.6V displayed as "12.6")
            display_value = value  # Keep as float for proper decimal formatting
            num_digits = 3
            decimal_pos = 2
        elif "TEMP" in label.upper():
            # Temperature: XXX format (e.g., 185)
            display_value = int(round(value))  # 185 for 185°F
            num_digits = 3
            decimal_pos = None
        elif "PRESS" in label.upper():
            # Pressure: 00 format (e.g., 40 PSI displayed as "40")
            display_value = int(round(value))  # 40 for 40 PSI
            num_digits = 2
            decimal_pos = None
        elif "FUEL" in label.upper():
            # Check for RESERVE warning (low fuel)
            if value < 10:  # Less than 10% fuel
                # Show RESERVE warning instead of DSEG digits
                reserve_font = pygame.font.SysFont('Arial', 28, bold=True)
                reserve_text = reserve_font.render("RESERVE", True, XT_DIM_AMBER)  # Same color as unfilled bars
                reserve_rect = reserve_text.get_rect(center=(rect[0] + rect[2] // 2, bar_y + bar_height + 40))
                surface.blit(reserve_text, reserve_rect)
                return  # Skip DSEG display
            else:
                # Fuel: XXX format (e.g., 75 for 75%)
                display_value = int(round(value))  # 75 for 75%
                num_digits = 3
                decimal_pos = None
        else:
            # Default: XX.X format
            display_value = int(round(value * 10))
            num_digits = 3
            decimal_pos = 2
        
        # Center DSEG display
        total_width = num_digits * digit_width
        dseg_x = rect[0] + (rect[2] - total_width) // 2
        dseg_y = bar_y + bar_height + 30
        
        # Check for danger levels and add red warning rectangle
        is_danger = False
        if "OIL" in label.upper() and "TEMP" in label.upper() and value > 280:  # Oil temp > 280°F
            is_danger = True
        elif "OIL" in label.upper() and "PRESS" in label.upper() and value < 5:  # Oil pressure < 5 PSI
            is_danger = True
        elif "COOLANT" in label.upper() and value > 230:  # Coolant temp > 230°F
            is_danger = True
        elif "VOLTS" in label.upper() and (value < 10.5 or value > 15.5):  # Voltage out of range
            is_danger = True
        
        if is_danger:
            # Draw red danger rectangle near the label
            danger_rect = pygame.Rect(rect[0] + rect[2] - 40, rect[1] + 5, 30, 20)
            pygame.draw.rect(surface, (255, 0, 0), danger_rect)  # Red rectangle
            danger_font = pygame.font.SysFont('Arial', 12, bold=True)
            danger_text = danger_font.render("!", True, (255, 255, 255))  # White exclamation
            danger_text_rect = danger_text.get_rect(center=danger_rect.center)
            surface.blit(danger_text, danger_text_rect)
        
        # Draw DSEG numbers
        if decimal_pos:
            draw_dsi_multi_digit_display(surface, display_value, num_digits, dseg_x, dseg_y,
                                       digit_width, bright_color, dseg_size, leading_zero_dim=0.5, decimal_pos=decimal_pos)
        else:
            draw_multi_digit_display(surface, display_value, num_digits, dseg_x, dseg_y,
                                   digit_width, bright_color, dseg_size, leading_zero_dim=0.5)

def draw_xt_road_bars(surface, speed, rpm, rect):
    """Draw Subaru XT style road bars - left for tachometer, right for speedometer (top to bottom fill)"""
    # Road dimensions - INCREASED GAP BETWEEN BARS
    road_bottom_width = 580  # Increased from 507 to create bigger gap
    road_top_width = 180     # Increased from 152 to maintain proportions
    road_height = 180
    bar_thickness_bottom = 75
    bar_thickness_top = 24
    
    # Calculate road center and positions
    center_x = rect[0] + rect[2] // 2
    top_y = rect[1] + 215  # Adjusted to balance top and bottom margins
    bottom_y = top_y + road_height
    
    # Left road bar (TACHOMETER) - coordinates
    left_bottom_outer = center_x - road_bottom_width // 2
    left_bottom_inner = left_bottom_outer + bar_thickness_bottom
    left_top_outer = center_x - road_top_width // 2
    left_top_inner = left_top_outer + bar_thickness_top
    
    # Right road bar (SPEEDOMETER) - coordinates  
    right_bottom_outer = center_x + road_bottom_width // 2
    right_bottom_inner = right_bottom_outer - bar_thickness_bottom
    right_top_outer = center_x + road_top_width // 2
    right_top_inner = right_top_outer - bar_thickness_top
    
    # Draw left RPM bar with redline section (5000-6000 RPM = top 1/6 of bar)
    redline_start_progress = 5000 / 6000  # 5/6 of the way up
    redline_start_y = top_y + (redline_start_progress * road_height)
    
    # Calculate redline section coordinates
    redline_outer_x = left_top_outer + (left_bottom_outer - left_top_outer) * redline_start_progress
    redline_inner_x = left_top_inner + (left_bottom_inner - left_top_inner) * redline_start_progress
    
    # Draw normal section (bottom 5/6 - darker orange)
    normal_points = [(left_bottom_outer, bottom_y), (redline_outer_x, redline_start_y),
                    (redline_inner_x, redline_start_y), (left_bottom_inner, bottom_y)]
    pygame.draw.polygon(surface, (180, 100, 0), normal_points)  # Darker orange for normal unfilled
    
    # Draw redline section (top 1/6 - dim amber)
    redline_dim_color = XT_DIM_AMBER  # Standard dim amber for redline unfilled
    redline_points = [(redline_outer_x, redline_start_y), (left_top_outer, top_y),
                     (left_top_inner, top_y), (redline_inner_x, redline_start_y)]
    pygame.draw.polygon(surface, redline_dim_color, redline_points)
    
    right_complete_points = [(right_bottom_outer, bottom_y), (right_top_outer, top_y),
                            (right_top_inner, top_y), (right_bottom_inner, bottom_y)]
    pygame.draw.polygon(surface, XT_DIM_AMBER, right_complete_points)
    
    # Fill left bar based on RPM (TOP TO BOTTOM - with separate normal and redline sections)
    max_rpm = 6000
    rpm_progress = min(rpm / max_rpm, 1.0)
    redline_start_progress = 5000 / 6000  # 5/6 of the way up
    
    # 3D offset for left bar (up and left for levitation effect) - REDUCED OFFSET
    offset_x = -12  # Reduced left offset
    offset_y = -8   # Reduced up offset
    
    if rpm_progress > 0:
        fill_height = int(rpm_progress * road_height)
        fill_bottom_y = top_y + fill_height
        
        # Calculate horizontal coordinates at fill level
        fill_progress = fill_height / road_height
        fill_outer_x = left_top_outer + (left_bottom_outer - left_top_outer) * fill_progress
        fill_inner_x = left_top_inner + (left_bottom_inner - left_top_inner) * fill_progress
        
        if rpm <= 5000:
            # Normal RPM range - fill with normal amber
            left_fill_points = [(fill_outer_x + offset_x, fill_bottom_y + offset_y), 
                               (left_top_outer + offset_x, top_y + offset_y),
                               (left_top_inner + offset_x, top_y + offset_y), 
                               (fill_inner_x + offset_x, fill_bottom_y + offset_y)]
            pygame.draw.polygon(surface, XT_AMBER, left_fill_points)
        else:
            # RPM > 5000 - fill normal section + redline section
            redline_start_y = top_y + (redline_start_progress * road_height)
            redline_outer_x = left_top_outer + (left_bottom_outer - left_top_outer) * redline_start_progress
            redline_inner_x = left_top_inner + (left_bottom_inner - left_top_inner) * redline_start_progress
            
            # Fill normal section (0-5000 RPM) with normal amber
            normal_fill_points = [(redline_outer_x + offset_x, redline_start_y + offset_y), 
                                 (left_top_outer + offset_x, top_y + offset_y),
                                 (left_top_inner + offset_x, top_y + offset_y), 
                                 (redline_inner_x + offset_x, redline_start_y + offset_y)]
            pygame.draw.polygon(surface, XT_AMBER, normal_fill_points)
            
            # Fill redline section (5000+ RPM) with bright orange
            redline_fill_points = [(fill_outer_x + offset_x, fill_bottom_y + offset_y), 
                                  (redline_outer_x + offset_x, redline_start_y + offset_y),
                                  (redline_inner_x + offset_x, redline_start_y + offset_y), 
                                  (fill_inner_x + offset_x, fill_bottom_y + offset_y)]
            pygame.draw.polygon(surface, (255, 140, 0), redline_fill_points)  # Bright orange for filled redline
    
    # Fill right bar based on SPEED (TOP TO BOTTOM - with proper tapered shape and 3D offset)
    max_speed = 120
    speed_progress = min(speed / max_speed, 1.0)
    if speed_progress > 0:
        fill_height = int(speed_progress * road_height)
        fill_bottom_y = top_y + fill_height
        
        # 3D offset for right bar (up and right for levitation effect) - REDUCED OFFSET
        offset_x = 12   # Reduced right offset
        offset_y = -8   # Reduced up offset
        
        # Calculate horizontal coordinates at fill level (linear interpolation)
        fill_progress = fill_height / road_height
        fill_outer_x = right_top_outer + (right_bottom_outer - right_top_outer) * fill_progress
        fill_inner_x = right_top_inner + (right_bottom_inner - right_top_inner) * fill_progress
        
        # Apply 3D offset to all coordinates
        right_fill_points = [(fill_outer_x + offset_x, fill_bottom_y + offset_y), 
                            (right_top_outer + offset_x, top_y + offset_y),
                            (right_top_inner + offset_x, top_y + offset_y), 
                            (fill_inner_x + offset_x, fill_bottom_y + offset_y)]
        pygame.draw.polygon(surface, XT_AMBER, right_fill_points)
    
    # Draw milestone markers (CORRECT ORDER - top to bottom) - FOLLOWING BAR SHAPE
    # Left side (RPM): 0, 1, 2, 3, 4, 5, 6 (top to bottom - smaller to bigger)
    for i, marker_rpm in enumerate([0, 1000, 2000, 3000, 4000, 5000, 6000]):
        marker_progress = i / 6.0  # 0.0 to 1.0 (top to bottom)
        marker_y = top_y + (marker_progress * road_height)
        
        # Calculate marker position following the bar shape (linear interpolation)
        marker_outer_x = left_top_outer + (left_bottom_outer - left_top_outer) * marker_progress
        marker_inner_x = left_top_inner + (left_bottom_inner - left_top_inner) * marker_progress
        
        # Left marker (RPM) - ON THE RIGHT SIDE (inner side toward center)
        left_marker_start = marker_inner_x + 10
        left_marker_end = marker_inner_x + 30
        # Fixed filling direction: filled when current fill level is ABOVE this marker
        current_fill_progress = min(rpm / 6000.0, 1.0)
        marker_color = XT_AMBER if current_fill_progress >= marker_progress else XT_DIM_AMBER
        pygame.draw.line(surface, marker_color, (left_marker_start, marker_y), (left_marker_end, marker_y), 2)
        
        # RPM numbers (show at 0, 2000, 4000, 6000) - variable font size - SCALED UP
        if marker_rpm % 2000 == 0:
            # Font size varies from small at top (16) to large at bottom (28) - BIGGER
            font_size = int(16 + (marker_progress * 12))  # 16 to 28
            font = pygame.font.SysFont('Arial', font_size, bold=True)
            rpm_display = marker_rpm // 1000
            rpm_text = font.render(str(rpm_display), True, marker_color)
            rpm_rect = rpm_text.get_rect(center=(left_marker_end + 15, marker_y))
            surface.blit(rpm_text, rpm_rect)
    
    # Right side (SPEED): 0, 20, 40, 60, 80, 100, 120 (top to bottom - smaller to bigger) - FOLLOWING BAR SHAPE
    for i, marker_speed in enumerate([0, 20, 40, 60, 80, 100, 120]):
        marker_progress = i / 6.0  # 0.0 to 1.0 (top to bottom)
        marker_y = top_y + (marker_progress * road_height)
        
        # Calculate marker position following the bar shape (linear interpolation)
        marker_outer_x = right_top_outer + (right_bottom_outer - right_top_outer) * marker_progress
        marker_inner_x = right_top_inner + (right_bottom_inner - right_top_inner) * marker_progress
        
        # Right marker (SPEED) - ON THE LEFT SIDE (inner side toward center)
        right_marker_start = marker_inner_x - 30
        right_marker_end = marker_inner_x - 10
        # Fixed filling direction: filled when current fill level is ABOVE this marker
        current_fill_progress = min(speed / 120.0, 1.0)
        marker_color = XT_AMBER if current_fill_progress >= marker_progress else XT_DIM_AMBER
        pygame.draw.line(surface, marker_color, (right_marker_start, marker_y), (right_marker_end, marker_y), 2)
        
        # Speed numbers (show at 0, 40, 80, 120) - variable font size - SCALED UP
        if marker_speed % 40 == 0:
            # Font size varies from small at top (16) to large at bottom (28) - BIGGER
            font_size = int(16 + (marker_progress * 12))  # 16 to 28
            font = pygame.font.SysFont('Arial', font_size, bold=True)
            speed_text = font.render(str(marker_speed), True, marker_color)
            # Special positioning for 120 to avoid overlap with milestone line
            if marker_speed == 120:
                speed_rect = speed_text.get_rect(center=(right_marker_start - 25, marker_y))
            else:
                speed_rect = speed_text.get_rect(center=(right_marker_start - 15, marker_y))
            surface.blit(speed_text, speed_rect)
    
    # Draw DSEG displays at top of screen
    dseg_size = 40
    digit_width = dseg_size + 18  # Further increased gap between digits
    
    # Left DSEG (RPM) - 00 format with proper dimming like Synthwave
    rpm_display_value = int(rpm // 100)  # Convert to hundreds (0-60 range)
    rpm_x = center_x - 150
    rpm_y = top_y - 130  # Moved up to create proper gap from road bars
    draw_multi_digit_display(surface, rpm_display_value, 2, rpm_x, rpm_y, 
                           digit_width, XT_AMBER, dseg_size, leading_zero_dim=0.3)
    
    # RPM label - MOVED EVEN MORE TO THE RIGHT
    font = pygame.font.SysFont('Arial', 18, bold=True)
    rpm_label = font.render("RPM x100", True, XT_AMBER)
    rpm_label_rect = rpm_label.get_rect(center=(rpm_x + 50, rpm_y + dseg_size + 50))
    surface.blit(rpm_label, rpm_label_rect)
    
    # Right DSEG (SPEED) - 000 format with proper dimming like Synthwave
    speed_display_value = int(speed)  # Keep as is (0-120 range)
    speed_x = center_x + 50
    speed_y = top_y - 130  # Moved up to create proper gap from road bars
    draw_multi_digit_display(surface, speed_display_value, 3, speed_x, speed_y,
                           digit_width, XT_AMBER, dseg_size, leading_zero_dim=0.3)
    
    # Speed label - MOVED EVEN MORE TO THE RIGHT
    speed_label = font.render("MPH", True, XT_AMBER)
    speed_label_rect = speed_label.get_rect(center=(speed_x + 75, speed_y + dseg_size + 50))
    surface.blit(speed_label, speed_label_rect)
    
    # REDLINE warning text in center gap when RPM > 5000
    if rpm > 5000:
        redline_font = pygame.font.SysFont('Arial', 24, bold=True)
        redline_text = redline_font.render("REDLINE", True, (255, 140, 0))  # Same bright orange as redline fill
        redline_rect = redline_text.get_rect(center=(center_x, top_y + road_height // 2))
        surface.blit(redline_text, redline_rect)

def draw_zx_vertical_tick_bar(surface, value, max_value, rect, label):
    """Draw Nissan 300ZX style vertical bar with dimmed ticks and single bright tick at value level"""
    
    # Bar dimensions - MUCH WIDER (4x wider)
    bar_width = 160  # Increased from 40 to 160 (4x wider)
    bar_height = rect[3] - 80  # Leave space for label
    bar_x = rect[0] + (rect[2] - bar_width) // 2
    bar_y = rect[1] + 60  # Space for label at top
    
    # Draw left and right border lines
    pygame.draw.line(surface, ZX_TURQUOISE, (bar_x, bar_y), (bar_x, bar_y + bar_height), 2)
    pygame.draw.line(surface, ZX_TURQUOISE, (bar_x + bar_width, bar_y), (bar_x + bar_width, bar_y + bar_height), 2)
    
    # Draw ticks - EVEN THICKER WITH SMALLER GAPS
    num_ticks = 20  # Number of tick marks
    tick_height = 15  # Much thicker ticks (increased from 8 to 15)
    tick_gap = 1     # Smaller gap between ticks (reduced from 2 to 1)
    tick_spacing = (bar_height - (num_ticks - 1) * tick_gap) / num_ticks
    
    # Calculate which tick should be bright (based on value)
    value_progress = min(value / max_value, 1.0)
    active_tick = int(value_progress * (num_ticks - 1))
    
    for i in range(num_ticks):
        # Calculate tick position with gaps
        tick_y = bar_y + bar_height - (i * (tick_spacing + tick_gap)) - tick_height
        tick_start_x = bar_x + 5
        tick_end_x = bar_x + bar_width - 5
        
        # Use bright color for the active tick, dim for others
        if i == active_tick:
            tick_color = ZX_BRIGHT_TURQUOISE
        else:
            tick_color = ZX_DIM_TURQUOISE
        
        # Draw thick tick as filled rectangle
        tick_rect = pygame.Rect(tick_start_x, tick_y, tick_end_x - tick_start_x, tick_height)
        pygame.draw.rect(surface, tick_color, tick_rect)
    
    # Check for danger levels and add red warning rectangle
    is_danger = False
    if "OIL" in label.upper() and "TEMP" in label.upper() and value > 280:  # Oil temp > 280°F
        is_danger = True
    elif "OIL" in label.upper() and "PRESS" in label.upper() and value < 5:  # Oil pressure < 5 PSI
        is_danger = True
    elif "COOLANT" in label.upper() and value > 230:  # Coolant temp > 230°F
        is_danger = True
    elif "VOLT" in label.upper() and (value < 10.5 or value > 15.5):  # Voltage out of range
        is_danger = True
    elif "FUEL" in label.upper() and value < 10:  # Fuel < 10%
        is_danger = True
    
    # Draw label at top - LARGER FONT
    label_font = pygame.font.SysFont('Arial', 20, bold=True)  # Increased from 16 to 20
    label_text = label_font.render(label, True, ZX_TURQUOISE)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + 30))
    surface.blit(label_text, label_rect)
    
    # Draw red danger rectangle near the label if dangerous level detected
    if is_danger:
        danger_rect = pygame.Rect(rect[0] + rect[2] - 40, rect[1] + 10, 30, 20)
        pygame.draw.rect(surface, (255, 0, 0), danger_rect)  # Red rectangle
        danger_font = pygame.font.SysFont('Arial', 14, bold=True)
        danger_text = danger_font.render("!", True, (255, 255, 255))  # White exclamation
        danger_text_rect = danger_text.get_rect(center=danger_rect.center)
        surface.blit(danger_text, danger_text_rect)
    
    # Add min/max labels with milestone lines (like previous styles) - LARGER FONT
    minmax_font = pygame.font.SysFont('Arial', 22, bold=True)  # Increased from 18 to 22
    
    # Determine min/max labels based on gauge type
    if "FUEL" in label.upper():
        min_label = "E"
        max_label = "F"
    elif "TEMP" in label.upper():
        min_label = "LO"
        max_label = "HI"
    elif "VOLT" in label.upper():
        min_label = "8"
        max_label = "16"
    elif "PRESS" in label.upper():
        min_label = "0"
        max_label = "80"
    else:
        min_label = "0"
        max_label = str(int(max_value))
    
    # Right border line x position
    right_border_x = bar_x + bar_width
    
    # Draw max label (top of bar) with milestone line
    max_text = minmax_font.render(max_label, True, ZX_TURQUOISE)
    max_label_x = right_border_x + 30  # 30px to the right of bar
    max_label_y = bar_y
    max_rect = max_text.get_rect(center=(max_label_x, max_label_y))
    surface.blit(max_text, max_rect)
    
    # Milestone line from right border to max label
    pygame.draw.line(surface, ZX_TURQUOISE, (right_border_x, bar_y), (max_label_x - 15, max_label_y), 2)
    
    # Draw min label (bottom of bar) with milestone line
    min_text = minmax_font.render(min_label, True, ZX_TURQUOISE)
    min_label_x = right_border_x + 30  # 30px to the right of bar
    min_label_y = bar_y + bar_height
    min_rect = min_text.get_rect(center=(min_label_x, min_label_y))
    surface.blit(min_text, min_rect)
    
    # Milestone line from right border to min label
    pygame.draw.line(surface, ZX_TURQUOISE, (right_border_x, bar_y + bar_height), (min_label_x - 15, min_label_y), 2)
    
    # Draw value below bar using DSEG digits - BIGGER SIZE
    dseg_size = 40  # Large DSEG digits
    digit_width = dseg_size + 12
    
    if "TEMP" in label.upper() and value < 100:
        # Show "LO" text for low temperature readings
        lo_font = pygame.font.SysFont('Arial', dseg_size, bold=True)
        lo_text = lo_font.render("LO", True, ZX_TURQUOISE)
        lo_rect = lo_text.get_rect(center=(rect[0] + rect[2] // 2, bar_y + bar_height + 40))
        surface.blit(lo_text, lo_rect)
    elif "FUEL" in label.upper() and value < 10:
        # Show "RESERVE" text for low fuel (red color)
        reserve_font = pygame.font.SysFont('Arial', 28, bold=True)
        reserve_text = reserve_font.render("RESERVE", True, (255, 0, 0))  # Red color for warning
        reserve_rect = reserve_text.get_rect(center=(rect[0] + rect[2] // 2, bar_y + bar_height + 40))
        surface.blit(reserve_text, reserve_rect)
    else:
        # Format value for DSEG display
        if "TEMP" in label.upper():
            # Temperature: XXX format (e.g., 185)
            display_value = int(round(value))
            num_digits = 3
            decimal_pos = None
        elif "PRESS" in label.upper():
            # Pressure: 00 format (e.g., 40) - using same format as voltage for consistency
            display_value = int(round(value))
            num_digits = 2
            decimal_pos = None
        elif "VOLT" in label.upper():
            # Voltage: 00.0 format (e.g., 12.6)
            display_value = value
            num_digits = 3
            decimal_pos = 2
        elif "FUEL" in label.upper():
            # Fuel: XXX format (e.g., 75)
            display_value = int(round(value))
            num_digits = 3
            decimal_pos = None
        else:
            # Default: XX.X format
            display_value = value
            num_digits = 3
            decimal_pos = 2
        
        # Center DSEG display
        total_width = num_digits * digit_width
        dseg_x = rect[0] + (rect[2] - total_width) // 2
        dseg_y = bar_y + bar_height + 30
        
        # Draw DSEG numbers - USE SAME FUNCTION FOR ALL TO ENSURE CONSISTENT THICKNESS
        draw_dsi_multi_digit_display(surface, display_value, num_digits, dseg_x, dseg_y,
                                   digit_width, ZX_TURQUOISE, dseg_size, leading_zero_dim=0.3, decimal_pos=decimal_pos)

def draw_zx_gph_display(surface, gph_value, label, rect):
    """Draw GPH display using Synthwave method (no multiplication)"""
    # Label at top
    label_font = pygame.font.SysFont('Arial', 22, bold=True)
    label_text = label_font.render(label, True, ZX_TURQUOISE)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + 20))
    surface.blit(label_text, label_rect)
    
    # Use Synthwave's exact method - draw_dsi_multi_digit_display with decimal_pos=2
    digit_size = 45
    digit_spacing = digit_size + 15
    start_x = rect[0] + (rect[2] - (3 * digit_spacing)) // 2  # Center 3 digits
    start_y = rect[1] + 60
    
    # Use the exact same function as Synthwave
    draw_dsi_multi_digit_display(surface, gph_value, 3, start_x, start_y, digit_spacing, ZX_TURQUOISE, digit_size, 0.3, decimal_pos=2)

def draw_zx_dseg_display_large(surface, value, label, rect):
    """Draw Nissan 300ZX style DSEG display for MPG/Range/Trip - LARGER SIZE"""
    
    # Label at top - LARGER FONT
    label_font = pygame.font.SysFont('Arial', 22, bold=True)  # Increased from 18
    label_text = label_font.render(label, True, ZX_TURQUOISE)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + 20))
    surface.blit(label_text, label_rect)
    
    # DSEG display area - LARGER SIZE
    dseg_size = 45  # Increased from 32 to 45
    digit_width = dseg_size + 15  # Increased spacing
    
    # Handle special values
    if value == -1.0:  # IDLE
        idle_font = pygame.font.SysFont('Arial', 32, bold=True)  # Larger idle text
        idle_text = idle_font.render("IDLE", True, ZX_TURQUOISE)
        idle_rect = idle_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + rect[3]//2))
        surface.blit(idle_text, idle_rect)
    elif value == -2.0:  # OFF
        off_font = pygame.font.SysFont('Arial', 32, bold=True)  # Larger off text
        off_text = off_font.render("OFF", True, ZX_TURQUOISE)
        off_rect = off_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + rect[3]//2))
        surface.blit(off_text, off_rect)
    else:
        # Format value based on type
        if "MPG" in label.upper():
            display_value = max(0, min(999, int(round(value * 10))))
            num_digits = 3
            decimal_pos = 2
        elif "GPH" in label.upper():
            # GPH: Use smaller format for better display
            display_value = max(0, min(99, int(round(value * 10))))
            num_digits = 2
            decimal_pos = 1
        else:  # Trip/Range
            display_value = max(0, min(9999, int(round(value * 10))))
            num_digits = 4
            decimal_pos = 3
        
        # Center DSEG display
        total_width = num_digits * digit_width
        dseg_x = rect[0] + (rect[2] - total_width) // 2
        dseg_y = rect[1] + 60  # Adjusted for larger size
        
        # Draw DSEG numbers
        draw_dsi_multi_digit_display(surface, display_value, num_digits, dseg_x, dseg_y,
                                   digit_width, ZX_TURQUOISE, dseg_size, leading_zero_dim=0.3, decimal_pos=decimal_pos)

def draw_zx_dseg_display(surface, value, label, rect):
    """Draw Nissan 300ZX style DSEG display for MPG/Range/Trip"""
    
    # Label at top
    label_font = pygame.font.SysFont('Arial', 18, bold=True)
    label_text = label_font.render(label, True, ZX_TURQUOISE)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + 20))
    surface.blit(label_text, label_rect)
    
    # DSEG display area
    dseg_size = 32
    digit_width = dseg_size + 12
    
    # Handle special values
    if value == -1.0:  # IDLE
        idle_font = pygame.font.SysFont('Arial', 24, bold=True)
        idle_text = idle_font.render("IDLE", True, ZX_TURQUOISE)
        idle_rect = idle_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + rect[3]//2))
        surface.blit(idle_text, idle_rect)
    elif value == -2.0:  # OFF
        off_font = pygame.font.SysFont('Arial', 24, bold=True)
        off_text = off_font.render("OFF", True, ZX_TURQUOISE)
        off_rect = off_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + rect[3]//2))
        surface.blit(off_text, off_rect)
    else:
        # Format value based on type
        if "MPG" in label.upper() or "GPH" in label.upper():
            display_value = max(0, min(999, int(round(value * 10))))
            num_digits = 3
            decimal_pos = 2
        else:  # Trip/Range
            display_value = max(0, min(9999, int(round(value * 10))))
            num_digits = 4
            decimal_pos = 3
        
        # Center DSEG display
        total_width = num_digits * digit_width
        dseg_x = rect[0] + (rect[2] - total_width) // 2
        dseg_y = rect[1] + 50
        
        # Draw DSEG numbers
        draw_dsi_multi_digit_display(surface, display_value, num_digits, dseg_x, dseg_y,
                                   digit_width, ZX_TURQUOISE, dseg_size, leading_zero_dim=0.3, decimal_pos=decimal_pos)

def draw_zx_horizontal_tachometer(surface, rpm, rect):
    """Draw Nissan 300ZX style horizontal tachometer line with curved top edge and variable height ticks"""
    import math
    
    # Define max_rpm first
    max_rpm = 6000
    
    # Tachometer line dimensions - SIGNIFICANTLY WIDER - MOVED DOWN
    line_width = rect[2] - 40  # Reduced margin from 100 to 40 (60px wider)
    line_height = 60
    line_x = rect[0] + 20  # Reduced margin from 50 to 20 (30px wider on each side)
    line_y = rect[1] + rect[3] - 120  # Moved down (was -150, now -120, +30px down)
    
    # Create curved top edge using tanh-like function
    curve_points = []
    num_curve_points = 100  # Number of points to define the curve
    
    for i in range(num_curve_points + 1):
        x_progress = i / num_curve_points  # 0 to 1
        x_pos = line_x + (x_progress * line_width)
        
        # Tanh-like curve: y = tanh(4 * (x - 0.5)) scaled and shifted
        # This creates a smooth S-curve that rises from left to right
        curve_input = 4 * (x_progress - 0.5)  # Range from -2 to 2
        tanh_value = math.tanh(curve_input)  # Range from -1 to 1
        
        # Scale and position the curve - LIFT LEFT SIDE
        curve_height = (tanh_value + 1.4) * 1.2 * line_height  # Added 0.4 offset to lift left side
        y_pos = line_y + line_height - curve_height
        
        curve_points.append((int(x_pos), int(y_pos)))
    
    # Add bottom corners to complete the shape
    bottom_left = (line_x, line_y + line_height)
    bottom_right = (line_x + line_width, line_y + line_height)
    
    # Create complete polygon for the tachometer shape
    tach_shape = [bottom_left] + curve_points + [bottom_right]
    
    # Draw border of the curved tachometer with redline section
    gray_color = (128, 128, 128)  # Gray for border and milestone lines
    red_color = (255, 0, 0)       # Red for redline section
    
    # Calculate redline start position (5000 RPM = 83.3% of 6000 RPM)
    redline_start_progress = 5000 / max_rpm  # 0.833
    redline_start_x = line_x + (redline_start_progress * line_width)
    
    # Draw gray border for normal range (0-5000 RPM)
    normal_curve_points = []
    redline_curve_points = []
    
    for i in range(num_curve_points + 1):
        x_progress = i / num_curve_points
        x_pos = line_x + (x_progress * line_width)
        
        curve_input = 4 * (x_progress - 0.5)
        tanh_value = math.tanh(curve_input)
        curve_height = (tanh_value + 1.4) * 1.2 * line_height
        y_pos = line_y + line_height - curve_height
        
        if x_progress <= redline_start_progress:
            normal_curve_points.append((int(x_pos), int(y_pos)))
        else:
            redline_curve_points.append((int(x_pos), int(y_pos)))
    
    # Draw normal range border (gray)
    if len(normal_curve_points) > 1:
        pygame.draw.lines(surface, gray_color, False, normal_curve_points, 2)
    
    # Draw redline range border (red)  
    if len(redline_curve_points) > 1:
        pygame.draw.lines(surface, red_color, False, redline_curve_points, 2)
    
    # Draw bottom and side borders
    pygame.draw.line(surface, gray_color, (line_x, line_y + line_height), (redline_start_x, line_y + line_height), 2)  # Bottom normal
    pygame.draw.line(surface, red_color, (redline_start_x, line_y + line_height), (line_x + line_width, line_y + line_height), 2)  # Bottom redline
    pygame.draw.line(surface, gray_color, (line_x, line_y + line_height), normal_curve_points[0], 2)  # Left side
    pygame.draw.line(surface, red_color, (line_x + line_width, line_y + line_height), redline_curve_points[-1], 2)  # Right side
    
    # Calculate fill progress
    rpm_progress = min(rpm / max_rpm, 1.0)
    fill_width = int(rpm_progress * line_width)
    
    # Draw vertical ticks as fill instead of solid area (left to right based on RPM)
    num_fill_ticks = 30  # Reduced further for thicker ticks with gaps
    tick_width = 12  # Much thicker ticks
    tick_gap = 3    # Small gap between ticks
    # Calculate spacing to fill entire width
    available_width = line_width
    total_gap_space = (num_fill_ticks - 1) * tick_gap
    remaining_width = available_width - total_gap_space
    actual_tick_width = remaining_width / num_fill_ticks
    tick_start_x = line_x  # Start from beginning, not centered
    
    for i in range(num_fill_ticks):
        tick_x = tick_start_x + i * (actual_tick_width + tick_gap)
        
        # Calculate curve height at this x position
        x_progress = (tick_x - line_x) / line_width
        curve_input = 4 * (x_progress - 0.5)
        tanh_value = math.tanh(curve_input)
        curve_height = (tanh_value + 1.4) * 1.2 * line_height
        curve_y = line_y + line_height - curve_height
        
        # Draw thick vertical tick with variable height based on RPM
        tick_start_y = line_y + line_height
        full_tick_height = tick_start_y - curve_y  # Full height to curve
        
        # Variable tick height based on RPM (0-100% of full height)
        rpm_progress = min(rpm / max_rpm, 1.0)
        actual_tick_height = full_tick_height * rpm_progress
        tick_end_y = tick_start_y - actual_tick_height
        
        if actual_tick_height > 0:
            # Determine if this tick is in redline zone (5000+ RPM)
            tick_rpm = (tick_x - line_x) / line_width * max_rpm
            is_redline = tick_rpm >= 5000
            
            # Color logic: redline ticks are red, normal ticks are turquoise
            if tick_x <= line_x + fill_width:
                # Filled area
                if is_redline:
                    tick_color = (255, 100, 100)  # Bright red for filled redline ticks
                else:
                    tick_color = ZX_BRIGHT_TURQUOISE  # Bright turquoise for filled normal ticks
            else:
                # Unfilled area
                if is_redline:
                    tick_color = (150, 50, 50)    # Dim red for unfilled redline ticks
                else:
                    tick_color = ZX_DIM_TURQUOISE  # Dim turquoise for unfilled normal ticks
            
            tick_rect = pygame.Rect(int(tick_x), int(tick_end_y), int(actual_tick_width), int(actual_tick_height))
            pygame.draw.rect(surface, tick_color, tick_rect)
    
    # Draw milestone markers OUTSIDE the bar - GRAY COLOR
    milestone_rpms = [0, 1000, 2000, 3000, 4000, 5000, 6000]
    
    for milestone_rpm in milestone_rpms:
        # Calculate position along tachometer width
        rpm_progress = milestone_rpm / max_rpm
        milestone_x = line_x + (rpm_progress * line_width)
        
        # Calculate curve height at this position
        x_progress = rpm_progress
        curve_input = 4 * (x_progress - 0.5)
        tanh_value = math.tanh(curve_input)
        curve_height = (tanh_value + 1.4) * 1.2 * line_height
        curve_y = line_y + line_height - curve_height
        
        # Draw milestone line OUTSIDE (below) the bar
        milestone_start_y = line_y + line_height + 5  # Start below bar
        milestone_end_y = milestone_start_y + 15      # 15px long line
        
        # Use red color for redline markers (5000+ RPM), gray for others
        if milestone_rpm >= 5000:  # Redline starts at 5000 RPM
            line_color = (255, 0, 0)  # Red for redline
        else:
            line_color = gray_color   # Gray for normal range
            
        pygame.draw.line(surface, line_color, (milestone_x, milestone_start_y), (milestone_x, milestone_end_y), 2)
        
        # Draw RPM numbers below milestone lines (show ALL numbers) - LARGER FONT
        milestone_font = pygame.font.SysFont('Arial', 22, bold=True)  # Increased from 16 to 22
        rpm_display = milestone_rpm // 1000  # Show as 0, 1, 2, 3, 4, 5, 6
        
        # Use red color for redline (5000+ RPM), gray for others
        if milestone_rpm >= 5000:  # Redline starts at 5000 RPM
            number_color = (255, 0, 0)  # Red for redline
        else:
            number_color = gray_color    # Gray for normal range
            
        rpm_text = milestone_font.render(str(rpm_display), True, number_color)
        rpm_rect = rpm_text.get_rect(center=(milestone_x, milestone_end_y + 15))
        surface.blit(rpm_text, rpm_rect)
    
    # RPM label - MOVED EVEN HIGHER
    rpm_font = pygame.font.SysFont('Arial', 18, bold=True)
    rpm_text = rpm_font.render("RPM x1000", True, ZX_TURQUOISE)
    rpm_rect = rpm_text.get_rect(topright=(rect[0] + rect[2] - 20, rect[1] - 60))  # Moved even higher (was -30, now -60)
    surface.blit(rpm_text, rpm_rect)

def draw_xt_dseg_display(surface, value, label, rect):
    """Draw Subaru XT style DSEG display for MPG/Range/Trip"""
    # DSEG display
    dseg_size = 35
    digit_width = dseg_size + 18  # Increased gap between digits
    
    # Handle special values
    if value == -1.0:  # IDLE
        idle_font = pygame.font.SysFont('Arial', 28, bold=True)
        idle_text = idle_font.render("IDLE", True, XT_AMBER)
        idle_rect = idle_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + rect[3]//2))
        surface.blit(idle_text, idle_rect)
    elif value == -2.0:  # OFF
        off_font = pygame.font.SysFont('Arial', 28, bold=True)
        off_text = off_font.render("OFF", True, XT_AMBER)
        off_rect = off_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + rect[3]//2))
        surface.blit(off_text, off_rect)
    else:
        # Format value based on type
        if "MPG" in label.upper():
            display_value = max(0, min(999, int(round(value * 10))))
            num_digits = 3
            decimal_pos = 2
        elif "GPH" in label.upper():
            # GPH: Use smaller format for better display
            display_value = max(0, min(99, int(round(value * 10))))
            num_digits = 2
            decimal_pos = 1
        else:  # Trip/Range
            display_value = max(0, min(9999, int(round(value * 10))))
            num_digits = 4
            decimal_pos = 3
        
        # Center DSEG display
        total_width = num_digits * digit_width
        dseg_x = rect[0] + (rect[2] - total_width) // 2
        dseg_y = rect[1] + rect[3] // 2 - dseg_size // 2
        
        # Draw DSEG numbers
        draw_dsi_multi_digit_display(surface, display_value, num_digits, dseg_x, dseg_y,
                                   digit_width, XT_AMBER, dseg_size, leading_zero_dim=0.5, decimal_pos=decimal_pos)
    
    # Draw label
    font = pygame.font.SysFont('Arial', 18, bold=True)
    label_text = font.render(label, True, XT_AMBER)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + 20))
    surface.blit(label_text, label_rect)

def draw_xt_gph_display(surface, gph_value, label, rect):
    """Draw GPH display using Synthwave method (no multiplication)"""
    # Label
    font = pygame.font.SysFont('Arial', 18, bold=True)
    label_text = font.render(label, True, XT_AMBER)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2]//2, rect[1] + 20))
    surface.blit(label_text, label_rect)
    
    # Use Synthwave's exact method - draw_dsi_multi_digit_display with decimal_pos=2
    digit_size = 35
    digit_spacing = digit_size + 18
    start_x = rect[0] + (rect[2] - (3 * digit_spacing)) // 2  # Center 3 digits
    start_y = rect[1] + rect[3] // 2 - digit_size // 2
    
    # Use the exact same function as Synthwave
    draw_dsi_multi_digit_display(surface, gph_value, 3, start_x, start_y, digit_spacing, XT_AMBER, digit_size, 0.5, decimal_pos=2)

# Main loop
running = True
loop_counter = 0

while running:
    loop_counter += 1
    
    # Read data from Arduino
    speed, rpm = read_arduino_data()
    
    # Update screen brightness based on dimmer input (only when changed)
    if serial_connected:
        brightness_to_use = current_brightness
    else:
        # Demo mode - use default brightness
        brightness_to_use = 90.0
    
    # Only update brightness if it changed significantly (more than 2%)
    if abs(brightness_to_use - last_brightness_value) > 2.0:
        set_screen_brightness(brightness_to_use)
        last_brightness_value = brightness_to_use
    
    # Always update software brightness (fast operation)
    if serial_connected:
        software_brightness = 0.2 + ((max(current_brightness, 20.0) - 20.0) / 80.0) * 0.8
    else:
        software_brightness = 0.75
    
    # Clear main screen
    screen.fill(BLACK)
    
    # Show simple disconnection message if needed
    if not serial_connected and was_ever_connected:
        # Arduino was connected before but now disconnected - show simple message
        disconnect_font = pygame.font.SysFont('Arial', 56, bold=True)
        disconnect_text = disconnect_font.render("ARDUINO DISCONNECTED", True, RED)
        disconnect_rect = disconnect_text.get_rect(center=(TOTAL_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(disconnect_text, disconnect_rect)
    
    # === LEFT SIDE - SPEEDOMETER ===
    if current_style_index == STYLE_SYNTHWAVE:
        # Original Synthwave style
        speedometer_surface.fill(BLACK)
        draw_diagonal_speedometer(speedometer_surface, display_speed)
        draw_speed_display(speedometer_surface, display_speed)
        draw_synthwave_grid(speedometer_surface, display_speed, True, SPEEDO_GRID_X, SPEEDO_GRID_Y)
        draw_connection_status(speedometer_surface, 10)
    elif current_style_index == STYLE_CITROEN_BX:
        # Citroën BX style - horizontal fuel bar and digital displays
        speedometer_surface.fill(BX_BLACK)
        
        # Top: Horizontal fuel bar (moved down for better Citroën BX layout)
        fuel_rect = (212, 200, 600, 170)  # Moved down (150 → 200, +50px down)
        fuel_level = current_fuel_level if 'current_fuel_level' in globals() else 50.0
        draw_bx_horizontal_bar_thick(speedometer_surface, fuel_level, 100, fuel_rect, "FUEL %")
        
        # Bottom: DSEG-style displays (moved down for better Citroën BX layout)
        # Left side: TRIP or RANGE (switchable), Right side: AVG MPG or INST MPG (switchable)
        left_display_rect = (187, 430, 300, 170)   # Moved down (380 → 430, +50px down)
        right_display_rect = (537, 430, 300, 170)  # Moved down (380 → 430, +50px down)
        
        # Get current values with safe defaults
        trip_value = persistent_data.data.get("trip_odometer", 0.0)
        range_value = current_fuel_range if 'current_fuel_range' in globals() else 0.0
        avg_mpg = current_avg_mpg if 'current_avg_mpg' in globals() else 0.0
        inst_mpg = current_inst_mpg if 'current_inst_mpg' in globals() else 0.0
        
        # Left display: TRIP or RANGE (based on switch state) - no border
        if switch_fuel_range:
            draw_bx_single_dseg_display(speedometer_surface, range_value, "RANGE", left_display_rect)
        elif switch_trip_odo:
            draw_bx_single_dseg_display(speedometer_surface, trip_value, "TRIP", left_display_rect)
        else:
            # Default to TRIP if no switch active
            draw_bx_single_dseg_display(speedometer_surface, trip_value, "TRIP", left_display_rect)
        
        # Right display: AVG MPG or INST MPG (based on switch state) - no border
        if switch_avg_mpg:
            draw_bx_single_dseg_display(speedometer_surface, avg_mpg, "AVG MPG", right_display_rect)
        elif switch_inst_mpg:
            # Handle instant MPG with GPH support (using Synthwave method)
            if inst_mpg == 0.0:  # Idling
                gph_value = current_fuel_flow_gph if current_fuel_flow_gph > 0.01 else 0.8
                # Use the same method as Synthwave - create a simple display
                draw_bx_gph_display(speedometer_surface, gph_value, "FUEL GPH", right_display_rect)
            elif inst_mpg == -1.0:  # Engine off
                draw_bx_single_dseg_display(speedometer_surface, 0, "OFF", right_display_rect)
            else:  # Normal MPG
                draw_bx_single_dseg_display(speedometer_surface, inst_mpg, "INST MPG", right_display_rect)
        else:
            # Default to AVG MPG if no switch active
            draw_bx_single_dseg_display(speedometer_surface, avg_mpg, "AVG MPG", right_display_rect)
    
    elif current_style_index == STYLE_SUBARU_XT:
        # Subaru XT style - 3D vertical bars for coolant/volts and oil temp/pressure
        speedometer_surface.fill(XT_BLACK)
        
        # Get current values with safe defaults
        coolant_temp = current_coolant_temp if 'current_coolant_temp' in globals() else 185.0
        volts = current_battery_voltage if 'current_battery_voltage' in globals() else 12.0
        oil_temp = current_oil_temp if 'current_oil_temp' in globals() else 180.0
        oil_pressure = current_oil_pressure if 'current_oil_pressure' in globals() else 40.0
        
        # Bars positioned closer together with smaller gap
        # Left bar: Coolant Temp OR Volts (switchable) - SAME SIZE AS FUEL BAR
        left_bar_rect = (250, 100, 200, 500)  # Same size as fuel bar (200x500)
        if switch_coolant_temp:
            draw_xt_3d_vertical_bar(speedometer_surface, coolant_temp, 250, left_bar_rect, "COOLANT TEMP")
        elif switch_volts:
            draw_xt_3d_vertical_bar(speedometer_surface, volts, 16, left_bar_rect, "BATTERY VOLTS")
        else:
            # Default to coolant temp
            draw_xt_3d_vertical_bar(speedometer_surface, coolant_temp, 250, left_bar_rect, "COOLANT TEMP")
        
        # Right bar: Oil Temperature OR Oil Pressure (switchable) - SAME SIZE AS FUEL BAR
        right_bar_rect = (550, 100, 200, 500)  # Same size as fuel bar (200x500)
        if switch_oil_temp:
            draw_xt_3d_vertical_bar(speedometer_surface, oil_temp, 300, right_bar_rect, "OIL TEMP")
        elif switch_oil_pressure:
            draw_xt_3d_vertical_bar(speedometer_surface, oil_pressure, 80, right_bar_rect, "OIL PRESS")
        else:
            # Default to oil pressure
            draw_xt_3d_vertical_bar(speedometer_surface, oil_pressure, 80, right_bar_rect, "OIL PRESS")
    
    elif current_style_index == STYLE_CORVETTE_C4:
        # Corvette C4 style - same as Synthwave but with smoother rendering
        speedometer_surface.fill(BLACK)
        
        # Use the original diagonal speedometer but with smoother ticks
        draw_diagonal_speedometer_smooth(speedometer_surface, display_speed)
        
        # Draw digital speed display (same as original)
        draw_speed_display(speedometer_surface, display_speed)
        
        # Draw synthwave grid (same as original)
        draw_synthwave_grid(speedometer_surface, display_speed, True, SPEEDO_GRID_X, SPEEDO_GRID_Y)
        
        # Draw connection status
        draw_connection_status(speedometer_surface, 10)
    
    elif current_style_index == STYLE_NISSAN_300ZX:
        # Nissan 300ZX style - fuel bar on right, DSEG displays on left
        speedometer_surface.fill(ZX_BLACK)
        
        # Get current values
        fuel_level = current_fuel_level if 'current_fuel_level' in globals() else 50.0
        inst_mpg = current_inst_mpg if 'current_inst_mpg' in globals() else 25.0
        avg_mpg = current_avg_mpg if 'current_avg_mpg' in globals() else 22.0
        trip_value = persistent_data.data.get("trip_odometer", 0.0)
        range_value = current_fuel_range if 'current_fuel_range' in globals() else 0.0
        
        # Right: Fuel bar (vertical tick bar) - SAME AS RIGHT SCREEN BARS
        fuel_bar_rect = (500, 100, 300, 500)  # Same dimensions as right screen bars
        draw_zx_vertical_tick_bar(speedometer_surface, fuel_level, 100, fuel_bar_rect, "FUEL")
        
        # MPG display (Instant OR Average - switchable) - MOVED FURTHER RIGHT AND DOWN
        mpg_rect = (200, 200, 300, 150)  # Moved further right (150 -> 200) and down (100 -> 200)
        if switch_inst_mpg:
            # Show GPH when idling, MPG when driving (using Synthwave method)
            if inst_mpg == 0.0:  # Idling
                gph_value = current_fuel_flow_gph if current_fuel_flow_gph > 0.01 else 0.8
                draw_zx_gph_display(speedometer_surface, gph_value, "GPH", mpg_rect)
            else:
                draw_zx_dseg_display_large(speedometer_surface, inst_mpg, "INST MPG", mpg_rect)
        elif switch_avg_mpg:
            draw_zx_dseg_display_large(speedometer_surface, avg_mpg, "AVG MPG", mpg_rect)
        else:
            # Default to average MPG
            draw_zx_dseg_display_large(speedometer_surface, avg_mpg, "AVG MPG", mpg_rect)
        
        # Range/Trip display (Range OR Trip - switchable) - MOVED FURTHER RIGHT
        range_rect = (200, 400, 300, 150)  # Moved further right (150 -> 200)
        if switch_fuel_range:
            draw_zx_dseg_display_large(speedometer_surface, range_value, "RANGE", range_rect)
        elif switch_trip_odo:
            draw_zx_dseg_display_large(speedometer_surface, trip_value, "TRIP", range_rect)
        else:
            # Default to range
            draw_zx_dseg_display_large(speedometer_surface, range_value, "RANGE", range_rect)
    
    # Apply software brightness to speedometer
    apply_software_brightness(speedometer_surface, software_brightness)
    
    # Rotate speedometer surface 270 degrees (90° + 180° to fix upside-down display)
    rotated_speedo = pygame.transform.rotate(speedometer_surface, 270)
    speedo_rect = rotated_speedo.get_rect()
    # Move speedometer a bit more UP on left screen
    speedo_center_x = 2100  # Move a bit more UP to top of left screen
    speedo_center_y = (SCREEN_HEIGHT - speedo_rect.height) // 2 + 30
    screen.blit(rotated_speedo, (speedo_center_x, speedo_center_y))
    
    # === RIGHT SIDE - TACHOMETER ===
    if current_style_index == STYLE_SYNTHWAVE:
        # Original Synthwave style
        tachometer_surface.fill(BLACK)
        # Use smoothed RPM for visual display, but actual RPM for warnings
        # Ensure visual_rpm is never None
        if display_rpm is not None and display_rpm > 0:
            visual_rpm = display_rpm
        elif rpm is not None:
            visual_rpm = rpm
        else:
            visual_rpm = 0
        draw_modified_tachometer(tachometer_surface, visual_rpm)
        draw_rpm_display(tachometer_surface, visual_rpm)
        draw_synthwave_mountains(tachometer_surface, visual_rpm)
        draw_connection_status(tachometer_surface, 10)
        draw_odometer_display(tachometer_surface, persistent_data.data["total_odometer"])
        draw_redline_warning(tachometer_surface, rpm)
    elif current_style_index == STYLE_CITROEN_BX:
        # Citroën BX style - switchable horizontal bars
        tachometer_surface.fill(BX_BLACK)
        
        # Get current values with safe defaults
        oil_pressure = current_oil_pressure if 'current_oil_pressure' in globals() else 40.0
        oil_temp = current_oil_temp if 'current_oil_temp' in globals() else 180.0
        volts = current_battery_voltage if 'current_battery_voltage' in globals() else 12.0
        coolant_temp = current_coolant_temp if 'current_coolant_temp' in globals() else 185.0
        
        # Top horizontal bar: Oil Pressure OR Oil Temperature (moved much further down for better Citroën BX layout)
        top_bar_rect = (200, 250, 600, 170)  # Moved much further down (200 → 250, +50px more down)
        if switch_oil_pressure:
            draw_bx_horizontal_bar_thick(tachometer_surface, oil_pressure, 80, top_bar_rect, "OIL PRESSURE PSI")
        elif switch_oil_temp:
            draw_bx_horizontal_bar_thick(tachometer_surface, oil_temp, 300, top_bar_rect, "OIL TEMPERATURE °F")
        else:
            # Default to oil pressure if no switch active
            draw_bx_horizontal_bar_thick(tachometer_surface, oil_pressure, 80, top_bar_rect, "OIL PRESSURE PSI")
        
        # Bottom horizontal bar: Battery Volts OR Coolant Temperature (moved much further down for better Citroën BX layout)
        bottom_bar_rect = (200, 480, 600, 170)  # Moved much further down (430 → 480, +50px more down)
        if switch_volts:
            draw_bx_horizontal_bar_thick(tachometer_surface, volts, 16, bottom_bar_rect, "BATTERY VOLTS")
        elif switch_coolant_temp:
            draw_bx_horizontal_bar_thick(tachometer_surface, coolant_temp, 250, bottom_bar_rect, "COOLANT TEMP °F")
        else:
            # Default to volts if no switch active
            draw_bx_horizontal_bar_thick(tachometer_surface, volts, 16, bottom_bar_rect, "BATTERY VOLTS")
        
        # Add odometer in top right corner
        draw_odometer_display(tachometer_surface, persistent_data.data["total_odometer"])
    
    elif current_style_index == STYLE_SUBARU_XT:
        # Subaru XT style - fuel bar on left, DSEG displays on right
        tachometer_surface.fill(XT_BLACK)
        
        # Get current values with safe defaults
        fuel_level = current_fuel_level if 'current_fuel_level' in globals() else 50.0
        avg_mpg = current_avg_mpg if 'current_avg_mpg' in globals() else 0.0
        inst_mpg = current_inst_mpg if 'current_inst_mpg' in globals() else 0.0
        trip_value = persistent_data.data.get("trip_odometer", 0.0)
        range_value = current_fuel_range if 'current_fuel_range' in globals() else 0.0
        
        # Left: Fuel bar (3D vertical bar) - MOVED DOWN FOR ODOMETER SPACE
        fuel_bar_rect = (250, 200, 200, 500)  # Moved down (100 -> 200) but kept original height (500)
        draw_xt_3d_vertical_bar(tachometer_surface, fuel_level, 100, fuel_bar_rect, "FUEL %")
        
        # Top Right: MPG display (Instant OR Average - switchable) - MOVED DOWN FOR ODOMETER SPACE
        mpg_rect = (500, 250, 300, 150)  # Moved down (150 -> 250) for odometer space
        if switch_inst_mpg:
            # Show GPH when idling, MPG when driving (using Synthwave method)
            if inst_mpg == 0.0:  # Idling
                gph_value = current_fuel_flow_gph if current_fuel_flow_gph > 0.01 else 0.8
                draw_xt_gph_display(tachometer_surface, gph_value, "GPH", mpg_rect)
            else:
                draw_xt_dseg_display(tachometer_surface, inst_mpg, "INST MPG", mpg_rect)
        elif switch_avg_mpg:
            draw_xt_dseg_display(tachometer_surface, avg_mpg, "AVG MPG", mpg_rect)
        else:
            # Default to average MPG
            draw_xt_dseg_display(tachometer_surface, avg_mpg, "AVG MPG", mpg_rect)
        
        # Bottom Right: Range/Trip display (Range OR Trip - switchable) - MOVED DOWN FOR ODOMETER SPACE
        range_rect = (500, 500, 300, 150)  # Moved down (400 -> 500) for better spacing
        if switch_fuel_range:
            draw_xt_dseg_display(tachometer_surface, range_value, "RANGE", range_rect)
        elif switch_trip_odo:
            draw_xt_dseg_display(tachometer_surface, trip_value, "TRIP", range_rect)
        else:
            # Default to range
            draw_xt_dseg_display(tachometer_surface, range_value, "RANGE", range_rect)
        
        # Add odometer in top right corner (same as other styles)
        draw_odometer_display(tachometer_surface, persistent_data.data["total_odometer"])
    
    elif current_style_index == STYLE_CORVETTE_C4:
        # Corvette C4 style - same as Synthwave but with smoother rendering
        tachometer_surface.fill(BLACK)
        
        # Use smoothed RPM for visual display, but actual RPM for warnings
        # Ensure visual_rpm is never None
        if display_rpm is not None and display_rpm > 0:
            visual_rpm = display_rpm
        elif rpm is not None:
            visual_rpm = rpm
        else:
            visual_rpm = 0
        
        # Use the original modified tachometer but with smoother ticks
        draw_modified_tachometer_smooth(tachometer_surface, visual_rpm)
        
        # Draw digital RPM display (same as original)
        draw_rpm_display(tachometer_surface, visual_rpm)
        
        # Draw synthwave mountains (same as original)
        draw_synthwave_mountains(tachometer_surface, visual_rpm)
        
        # Draw connection status
        draw_connection_status(tachometer_surface, 10)
        
        # Draw odometer
        draw_odometer_display(tachometer_surface, persistent_data.data["total_odometer"])
        
        # Draw redline warning
        draw_redline_warning(tachometer_surface, rpm)
    
    elif current_style_index == STYLE_NISSAN_300ZX:
        # Nissan 300ZX style - 2 switchable vertical tick bars
        tachometer_surface.fill(ZX_BLACK)
        
        # Get current values with safe defaults
        oil_temp = current_oil_temp if 'current_oil_temp' in globals() else 180.0
        oil_pressure = current_oil_pressure if 'current_oil_pressure' in globals() else 40.0
        volts = current_battery_voltage if 'current_battery_voltage' in globals() else 12.0
        coolant_temp = current_coolant_temp if 'current_coolant_temp' in globals() else 185.0
        
        # Left bar: Oil Temp OR Oil Pressure (switchable) - MOVED DOWN FOR ODOMETER SPACE
        left_bar_rect = (200, 200, 300, 500)  # Moved down (100 -> 200) to create space for odometer
        if switch_oil_temp:
            draw_zx_vertical_tick_bar(tachometer_surface, oil_temp, 300, left_bar_rect, "OIL TEMP")
        elif switch_oil_pressure:
            draw_zx_vertical_tick_bar(tachometer_surface, oil_pressure, 80, left_bar_rect, "OIL PRESS")
        else:
            # Default to oil temp
            draw_zx_vertical_tick_bar(tachometer_surface, oil_temp, 300, left_bar_rect, "OIL TEMP")
        
        # Right bar: Volts OR Coolant Temp (switchable) - MOVED DOWN FOR ODOMETER SPACE
        right_bar_rect = (500, 200, 300, 500)  # Moved down (100 -> 200) to create space for odometer
        if switch_volts:
            draw_zx_vertical_tick_bar(tachometer_surface, volts, 16, right_bar_rect, "VOLTS")
        elif switch_coolant_temp:
            draw_zx_vertical_tick_bar(tachometer_surface, coolant_temp, 250, right_bar_rect, "COOLANT")
        else:
            # Default to volts
            draw_zx_vertical_tick_bar(tachometer_surface, volts, 16, right_bar_rect, "VOLTS")
        
        # Add odometer above volts bar (same surface as oil/volts bars)
        draw_odometer_display(tachometer_surface, persistent_data.data["total_odometer"])
    
    # Apply software brightness to tachometer
    apply_software_brightness(tachometer_surface, software_brightness)
    
    # Rotate tachometer surface 270 degrees (90° + 180° to fix upside-down display)
    rotated_tacho = pygame.transform.rotate(tachometer_surface, 270)
    tacho_rect = rotated_tacho.get_rect()
    # Move tachometer more LEFT on right screen
    tacho_center_x = 3000  # Keep X position
    tacho_center_y = -100  # Move more LEFT on right screen
    screen.blit(rotated_tacho, (tacho_center_x, tacho_center_y))
    
    # === BOTTOM - DSI SCREEN ===
    # Create temporary surface for DSI content to apply brightness
    dsi_temp_surface = pygame.Surface((DSI_SCREEN_WIDTH, DSI_SCREEN_HEIGHT))
    dsi_temp_surface.fill(BLACK)
    
    # Draw DSI content on temporary surface
    if current_style_index == STYLE_SYNTHWAVE:
        # Original DSI screen with multiple gauges
        draw_dsi_screen_content(dsi_temp_surface, speed, rpm)
    elif current_style_index == STYLE_CITROEN_BX:
        # Citroën BX style DSI - road speedometer and arch tachometer
        dsi_temp_surface.fill(BX_BLACK)
        
        # Road speedometer (bottom half)
        speed_rect = (0, 240, 800, 240)
        draw_bx_thick_road_speedometer(dsi_temp_surface, speed, speed_rect)
        
        # Arch tachometer (top half)
        rpm_rect = (0, 0, 800, 240)
        safe_rpm = rpm if rpm is not None else 0
        draw_bx_horizontal_arch_tachometer(dsi_temp_surface, safe_rpm, rpm_rect)
    
    elif current_style_index == STYLE_SUBARU_XT:
        # Subaru XT style DSI - road bars with top-to-bottom fill and DSEG displays at top
        dsi_temp_surface.fill(XT_BLACK)
        
        # Road bars (full screen)
        road_rect = (0, 0, 800, 480)
        safe_rpm = rpm if rpm is not None else 0
        draw_xt_road_bars(dsi_temp_surface, speed, safe_rpm, road_rect)
    
    elif current_style_index == STYLE_NISSAN_300ZX:
        # Nissan 300ZX style DSI - horizontal tachometer line and speedometer DSEG
        dsi_temp_surface.fill(ZX_BLACK)
        
        # Speedometer DSEG digits (top center)
        speed_dseg_size = 60
        speed_digit_width = speed_dseg_size + 20
        speed_display_value = int(speed)
        speed_num_digits = 3
        
        # Position speedometer DSEG - MOVED FURTHER LEFT AND WAY DOWN
        speed_total_width = speed_num_digits * speed_digit_width
        speed_dseg_x = 70   # Moved further left (was 100, now 70, -30px more left)
        speed_dseg_y = 140  # Moved way down (was 80, now 140, +60px more down)
        
        draw_multi_digit_display(dsi_temp_surface, speed_display_value, speed_num_digits, 
                               speed_dseg_x, speed_dseg_y, speed_digit_width, ZX_TURQUOISE, 
                               speed_dseg_size, leading_zero_dim=0.3)
        
        # Speed label - POSITIONED TO THE RIGHT OF DSEG DIGITS (MOVED SLIGHTLY MORE RIGHT)
        speed_font = pygame.font.SysFont('Arial', 24, bold=True)
        speed_label = speed_font.render("MPH", True, ZX_TURQUOISE)
        speed_label_x = speed_dseg_x + speed_total_width + 30  # Moved slightly more right (was +20, now +30)
        speed_label_y = speed_dseg_y + (speed_dseg_size // 2)  # Vertically center with digits
        speed_label_rect = speed_label.get_rect(center=(speed_label_x, speed_label_y))
        dsi_temp_surface.blit(speed_label, speed_label_rect)
        
        # Horizontal tachometer line (lower portion)
        tacho_rect = (0, 200, DSI_SCREEN_WIDTH, 200)
        safe_rpm = rpm if rpm is not None else 0
        draw_zx_horizontal_tachometer(dsi_temp_surface, safe_rpm, tacho_rect)
        
        # REDLINE warning - aligned with MPH level but slightly higher
        if safe_rpm >= 5000:
            redline_font = pygame.font.SysFont('Arial', 28, bold=True)
            redline_text = redline_font.render("REDLINE", True, (255, 0, 0))  # Red color
            redline_y = speed_dseg_y - 20  # Align with MPH level but 20px higher
            redline_rect = redline_text.get_rect(center=(DSI_SCREEN_WIDTH // 2, redline_y))
            dsi_temp_surface.blit(redline_text, redline_rect)
    
    elif current_style_index == STYLE_CORVETTE_C4:
        # Corvette C4 style DSI - same as Synthwave (original DSI screen)
        draw_dsi_screen_content(dsi_temp_surface, speed, rpm)
    
    # Apply software brightness to DSI surface
    apply_software_brightness(dsi_temp_surface, software_brightness)
    
    # Rotate DSI surface 180 degrees to fix upside-down display
    rotated_dsi = pygame.transform.rotate(dsi_temp_surface, 180)
    # Find middle ground for DSI position (between 4000 and 4100)
    dsi_x = 4050  # Middle ground between previous positions
    dsi_y = 0     # Keep Y at 0
    screen.blit(rotated_dsi, (dsi_x, dsi_y))
    
    # Clean dashboard - all debugging elements removed

    
    pygame.display.flip()
    clock.tick(60)  # 60 FPS for more responsive display
    
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_F11:
                # Toggle fullscreen
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    screen = pygame.display.set_mode((TOTAL_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
                    print("Combined dashboard: Switched to BORDERLESS FULLSCREEN")
                else:
                    screen = pygame.display.set_mode((TOTAL_WIDTH, SCREEN_HEIGHT))
                    print("Combined dashboard: Switched to WINDOWED")

# Cleanup
if serial_connected:
    ser.close()
    print("Serial connection closed")

pygame.quit()
print("Combined dashboard closed")

# ===== CITROËN BX STYLE FUNCTIONS =====

def draw_bx_road_speedometer(surface, speed, rect):
    """Draw Citroën BX style road speedometer - two vertical lines going into distance"""
    # Road dimensions
    road_bottom_width = 120
    road_top_width = 40
    road_height = 200
    
    # Calculate road lines (perspective effect)
    center_x = rect[0] + rect[2] // 2
    bottom_y = rect[1] + rect[3] - 20
    top_y = bottom_y - road_height
    
    # Left road line
    left_bottom = center_x - road_bottom_width // 2
    left_top = center_x - road_top_width // 2
    
    # Right road line  
    right_bottom = center_x + road_bottom_width // 2
    right_top = center_x + road_top_width // 2
    
    # Draw road lines
    pygame.draw.line(surface, BX_GREEN, (left_bottom, bottom_y), (left_top, top_y), 3)
    pygame.draw.line(surface, BX_GREEN, (right_bottom, bottom_y), (right_top, top_y), 3)
    
    # Draw speed ticks along the road (0-120 MPH)
    max_speed = 120
    num_ticks = 12  # Every 10 MPH
    
    for i in range(num_ticks + 1):
        tick_speed = i * 10
        tick_progress = i / num_ticks
        
        # Calculate tick position (bottom to top)
        tick_y = bottom_y - (tick_progress * road_height)
        tick_left_x = left_bottom - (tick_progress * (road_bottom_width - road_top_width) // 2)
        tick_right_x = right_bottom + (tick_progress * (road_bottom_width - road_top_width) // 2)
        
        # Highlight ticks based on current speed
        if tick_speed <= speed:
            color = BX_GREEN
            thickness = 3
        else:
            color = BX_DIM_GREEN
            thickness = 1
            
        # Draw tick across the road
        pygame.draw.line(surface, color, (tick_left_x, tick_y), (tick_right_x, tick_y), thickness)
    
    # Draw digital speed in the center
    font = pygame.font.SysFont('Arial', 48, bold=True)
    speed_text = font.render(f"{int(speed)}", True, BX_GREEN)
    speed_rect = speed_text.get_rect(center=(center_x, bottom_y - road_height // 2))
    surface.blit(speed_text, speed_rect)

def draw_bx_arch_tachometer(surface, rpm, rect):
    """Draw Citroën BX style arch tachometer above the speedometer"""
    # Arch dimensions
    center_x = rect[0] + rect[2] // 2
    center_y = rect[1] + 60
    radius = 100
    
    # RPM range (0-6000)
    max_rpm = 6000
    start_angle = math.pi  # 180 degrees (left)
    end_angle = 0  # 0 degrees (right)
    total_angle = start_angle - end_angle
    
    # Draw arch background
    pygame.draw.arc(surface, BX_DIM_GREEN, 
                   (center_x - radius, center_y - radius, radius * 2, radius * 2),
                   end_angle, start_angle, 3)
    
    # Draw RPM ticks
    num_ticks = 12  # Every 500 RPM
    for i in range(num_ticks + 1):
        tick_rpm = i * 500
        tick_progress = i / num_ticks
        
        # Calculate tick angle (left to right)
        tick_angle = start_angle - (tick_progress * total_angle)
        
        # Highlight ticks based on current RPM
        if tick_rpm <= rpm:
            color = BX_GREEN
            thickness = 4
        else:
            color = BX_DIM_GREEN
            thickness = 2
            
        # Calculate tick position
        inner_radius = radius - 15
        outer_radius = radius + 5
        
        inner_x = center_x + inner_radius * math.cos(tick_angle)
        inner_y = center_y - inner_radius * math.sin(tick_angle)
        outer_x = center_x + outer_radius * math.cos(tick_angle)
        outer_y = center_y - outer_radius * math.sin(tick_angle)
        
        pygame.draw.line(surface, color, (inner_x, inner_y), (outer_x, outer_y), thickness)
    
    # Draw digital RPM below arch
    font = pygame.font.SysFont('Arial', 24, bold=True)
    rpm_text = font.render(f"{int(rpm)}", True, BX_GREEN)
    rpm_rect = rpm_text.get_rect(center=(center_x, center_y + 40))
    surface.blit(rpm_text, rpm_rect)

def draw_bx_horizontal_bar(surface, value, max_value, rect, label):
    """Draw horizontal bar gauge for fuel level"""
    bar_width = rect[2] - 40
    bar_height = 20
    bar_x = rect[0] + 20
    bar_y = rect[1] + 30
    
    # Draw background bar
    pygame.draw.rect(surface, BX_DIM_GREEN, (bar_x, bar_y, bar_width, bar_height), 2)
    
    # Draw filled portion
    fill_width = int((value / max_value) * bar_width)
    if fill_width > 0:
        pygame.draw.rect(surface, BX_GREEN, (bar_x + 2, bar_y + 2, fill_width - 4, bar_height - 4))
    
    # Draw label and value
    font = pygame.font.SysFont('Arial', 16, bold=True)
    label_text = font.render(label, True, BX_GREEN)
    surface.blit(label_text, (bar_x, bar_y - 25))
    
    value_text = font.render(f"{value:.1f}", True, BX_GREEN)
    surface.blit(value_text, (bar_x + bar_width - 50, bar_y - 25))

def draw_bx_vertical_bar(surface, value, max_value, rect, label):
    """Draw vertical bar gauge for oil pressure, temperature, etc."""
    bar_width = 20
    bar_height = rect[3] - 80
    bar_x = rect[0] + rect[2] // 2 - bar_width // 2
    bar_y = rect[1] + 50
    
    # Draw background bar
    pygame.draw.rect(surface, BX_DIM_GREEN, (bar_x, bar_y, bar_width, bar_height), 2)
    
    # Draw filled portion (bottom to top)
    fill_height = int((value / max_value) * bar_height)
    if fill_height > 0:
        pygame.draw.rect(surface, BX_GREEN, 
                        (bar_x + 2, bar_y + bar_height - fill_height - 2, bar_width - 4, fill_height))
    
    # Draw label and value
    font = pygame.font.SysFont('Arial', 14, bold=True)
    label_text = font.render(label, True, BX_GREEN)
    label_rect = label_text.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + 20))
    surface.blit(label_text, label_rect)
    
    value_text = font.render(f"{value:.1f}", True, BX_GREEN)
    value_rect = value_text.get_rect(center=(rect[0] + rect[2] // 2, bar_y + bar_height + 20))
    surface.blit(value_text, value_rect)

def draw_bx_digital_display(surface, value, label, rect):
    """Draw digital display for trip, range, MPG values"""
    font_label = pygame.font.SysFont('Arial', 14, bold=True)
    font_value = pygame.font.SysFont('Arial', 20, bold=True)
    
    # Draw label
    label_text = font_label.render(label, True, BX_DIM_GREEN)
    surface.blit(label_text, (rect[0], rect[1]))
    
    # Draw value
    if isinstance(value, float):
        value_str = f"{value:.1f}"
    else:
        value_str = str(value)
    
    value_text = font_value.render(value_str, True, BX_GREEN)
    surface.blit(value_text, (rect[0], rect[1] + 20))
# Duplicate function removed - moved to proper location before main loop