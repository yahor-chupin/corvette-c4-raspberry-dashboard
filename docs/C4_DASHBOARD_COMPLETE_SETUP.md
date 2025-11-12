# C4 Corvette Dashboard - Complete Setup Guide

## Overview
This guide provides complete setup instructions for the C4 Corvette dashboard on Raspberry Pi OS Lite with triple display configuration.

## Hardware Requirements
- **Raspberry Pi 4** (recommended)
- **3 Displays**:
  - Left: HDMI-1 (1024x768)
  - Center: DSI-1 (800x480) - Official Pi touchscreen
  - Right: HDMI-2 (1024x768)
- **Arduino** connected via USB for sensor data

## Software Requirements
- **Raspberry Pi OS Lite** (for performance)
- **Python 3** with pygame, serial, math libraries
- **X11 server** (minimal installation)
- **Arduino IDE** (for sensor programming)
- **ALDL Integration** (real-time fuel consumption monitoring)

## Installation Steps

### 1. Install Required Packages
```bash
sudo apt update
sudo apt install python3-pygame python3-serial python3-pip
sudo apt install xserver-xorg-core xinit x11-xserver-utils xrandr
```

### 2. GPU Configuration
Edit `/boot/firmware/config.txt`:
```bash
sudo nano /boot/firmware/config.txt
```

Add these lines:
```
gpu_mem=128
dtoverlay=vc4-kms-v3d
hdmi_force_hotplug=1
hdmi_drive=2
disable_overscan=1
```

### 3. Display Configuration
The dashboard requires specific display positioning:
```bash
DISPLAY=:0 xrandr --output HDMI-1 --mode 1024x768 --pos 0x0 --rotate normal
DISPLAY=:0 xrandr --output HDMI-2 --mode 1024x768 --pos 1024x0 --rotate normal  
DISPLAY=:0 xrandr --output DSI-1 --mode 800x480 --pos 2048x0 --rotate normal
```

### 4. Dashboard Files
Required files in `/home/pi/`:
- `arduino_combined_dashboard.py` - Main dashboard application with ALDL integration
- `arduino_code.cpp` - Arduino code with real-time fuel consumption monitoring
- `coolant_temp_symbol.png` - Coolant temperature icon
- `oil_symbol.png` - Oil pressure icon  
- `gas_pump_symbol.png` - Fuel level icon
- `battery_symbol.png` - Battery voltage icon

## Key Configuration Details

### Display Layout
- **Physical Layout**: Left HDMI → Center DSI → Right HDMI
- **Logical Layout**: HDMI-1(0,0) → HDMI-2(1024,0) → DSI-1(2048,0)
- **Total Resolution**: 2848x768 extended desktop

### Coordinate System Discovery
The dashboard uses a **vertical stacking coordinate system**:
- **Higher X coordinates** = Move UP/LEFT in the stack
- **Lower X coordinates** = Move DOWN/RIGHT in the stack
- **Y coordinates** = Move LEFT/RIGHT within same screen

### Final Positioning
- **Speedometer**: X=2100, Y=30 → Left physical screen
- **DSI Gauges**: X=3000, Y=0 → Center physical screen
- **Tachometer**: X=3800, Y=-100 → Right physical screen
- **Pygame Surface**: 5000x768 pixels (prevents clipping)

### Critical Settings
- **No window positioning**: `SDL_VIDEO_WINDOW_POS` removed
- **Audio disabled**: `pygame.mixer.quit()` prevents ALSA errors
- **Fullscreen mode**: Borderless window spanning all displays

## Performance Improvements - OPTIMIZED ⚡
- **Boot time**: ~8-9 seconds (vs 37 seconds with desktop) - **77% improvement!**
- **System boot**: 6.014s (2.028s kernel + 3.985s userspace)
- **Dashboard startup**: ~2-3 seconds
- **RAM usage**: ~100MB (vs 500MB+ with desktop)
- **Hardware acceleration**: Enabled with kmsdrm driver
- **SSH workflow**: Preserved for development

### Boot Optimization Applied
**Phase 1**: Sleep reduction (28s → 15s)
**Phase 2**: Service optimization (15s → 8-9s)
**Services disabled**: NetworkManager-wait-online, bluetooth, wifi-powersave, triggerhappy
**Total improvement**: 19-20 seconds faster boot time

## Troubleshooting

### Display Issues
If displays show identical content (mirrored):
```bash
# Check configuration
DISPLAY=:0 xrandr

# Should show: current 2848 x 768 (extended)
# If not, reconfigure displays with xrandr commands above
```

### X11 Crashes
```bash
sudo pkill X
sudo rm -f /tmp/.X0-lock
sudo X :0 vt7 &
# Wait 3 seconds, then reconfigure displays
```

### Performance Issues
- Ensure GPU memory is set to 128MB in config.txt
- Verify hardware acceleration: `python3 -c "import pygame; pygame.init(); print(pygame.display.get_driver())"`
- Should show 'x11' driver

## File Locations
- **Dashboard**: `/home/pi/arduino_combined_dashboard.py`
- **Icons**: `/home/pi/*.png`
- **Config**: `/boot/firmware/config.txt`
- **Startup**: `/etc/systemd/system/dashboard.service`
- **Display setup**: `/usr/local/bin/setup-displays.sh`

## Success Criteria
✅ Dashboard boots in <15 seconds  
✅ Speedometer on left screen (rotated 270°)  
✅ DSI gauges on center screen (rotated 180°)  
✅ Tachometer on right screen (rotated 270°)  
✅ SSH workflow preserved  
✅ Configuration survives reboots  
✅ Arduino data integration working  
✅ **ALDL fuel consumption monitoring active**  
✅ **Real-time GAL/HR display when idling**  
✅ **Instant switch response (< 1 second)**

## Support
For issues, check:
1. Display configuration with `DISPLAY=:0 xrandr`
2. X11 server status with `ps aux | grep X`
3. Dashboard logs in terminal output
4. Arduino connection with `ls /dev/ttyACM*`