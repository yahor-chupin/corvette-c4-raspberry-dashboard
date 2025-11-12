#!/usr/bin/env python3
"""
Timing Analysis Script for Dashboard Performance Issues
This will help identify where the blocking operations are occurring
"""

import time
import serial
import threading
from collections import defaultdict, deque

# Configuration
SERIAL_PORT = '/dev/ttyACM0'
SERIAL_BAUD = 115200
ANALYSIS_DURATION = 60  # Run for 60 seconds

class TimingAnalyzer:
    def __init__(self):
        self.message_counts = defaultdict(int)
        self.message_times = defaultdict(list)
        self.last_message_time = defaultdict(float)
        self.processing_times = deque(maxlen=1000)
        self.start_time = time.time()
        self.total_messages = 0
        
    def log_message(self, message_type, processing_time):
        current_time = time.time()
        
        # Count messages
        self.message_counts[message_type] += 1
        self.total_messages += 1
        
        # Track timing
        if self.last_message_time[message_type] > 0:
            interval = current_time - self.last_message_time[message_type]
            self.message_times[message_type].append(interval)
        
        self.last_message_time[message_type] = current_time
        self.processing_times.append(processing_time)
        
    def print_analysis(self):
        elapsed = time.time() - self.start_time
        print(f"\n🔍 TIMING ANALYSIS RESULTS ({elapsed:.1f}s)")
        print("=" * 60)
        
        print(f"📊 TOTAL MESSAGES: {self.total_messages}")
        print(f"📈 MESSAGE RATE: {self.total_messages/elapsed:.1f} msg/sec")
        
        print(f"\n📋 MESSAGE BREAKDOWN:")
        for msg_type, count in sorted(self.message_counts.items()):
            rate = count / elapsed
            if self.message_times[msg_type]:
                avg_interval = sum(self.message_times[msg_type]) / len(self.message_times[msg_type])
                print(f"  {msg_type:15}: {count:4d} msgs ({rate:5.1f}/sec, avg interval: {avg_interval*1000:6.1f}ms)")
            else:
                print(f"  {msg_type:15}: {count:4d} msgs ({rate:5.1f}/sec)")
        
        if self.processing_times:
            avg_processing = sum(self.processing_times) / len(self.processing_times)
            max_processing = max(self.processing_times)
            print(f"\n⏱️  PROCESSING TIMES:")
            print(f"  Average: {avg_processing*1000:.2f}ms")
            print(f"  Maximum: {max_processing*1000:.2f}ms")
            
            # Find slow processing instances
            slow_count = sum(1 for t in self.processing_times if t > 0.1)  # > 100ms
            if slow_count > 0:
                print(f"  🚨 SLOW PROCESSING: {slow_count} instances > 100ms")

def analyze_serial_performance():
    """Analyze serial message processing performance"""
    analyzer = TimingAnalyzer()
    
    try:
        # Connect to Arduino
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.1)
        print(f"🔌 Connected to Arduino on {SERIAL_PORT}")
        print(f"⏰ Running analysis for {ANALYSIS_DURATION} seconds...")
        print("📡 Monitoring message processing...")
        
        start_time = time.time()
        
        while time.time() - start_time < ANALYSIS_DURATION:
            try:
                # Time the serial read operation
                read_start = time.time()
                
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                else:
                    line = ""
                
                read_time = time.time() - read_start
                
                if line:
                    # Time the message processing
                    process_start = time.time()
                    
                    # Determine message type
                    if "SPEED:" in line:
                        msg_type = "HIGH_FREQ"
                    elif "FUEL_RANGE:" in line:
                        msg_type = "LOW_FREQ"
                    elif "INIT_REQUEST:" in line:
                        msg_type = "INIT_REQ"
                    elif "RESET_TRIP:" in line:
                        msg_type = "RESET"
                    elif "SAVE_DATA:" in line:
                        msg_type = "SAVE_DATA"
                    else:
                        msg_type = "OTHER"
                    
                    # Simulate basic parsing (like the dashboard does)
                    if ":" in line:
                        pairs = line.split(",")
                        data = {}
                        for pair in pairs:
                            if ":" in pair:
                                try:
                                    key, value = pair.split(":", 1)
                                    data[key.strip()] = float(value.strip())
                                except ValueError:
                                    pass
                    
                    process_time = time.time() - process_start
                    total_time = read_time + process_time
                    
                    analyzer.log_message(msg_type, total_time)
                    
                    # Print real-time info for critical messages
                    if msg_type == "LOW_FREQ" and total_time > 0.05:  # > 50ms
                        print(f"🐌 SLOW LOW_FREQ processing: {total_time*1000:.1f}ms")
                
                # Small delay to prevent CPU overload
                time.sleep(0.001)
                
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                continue
        
        # Print final analysis
        analyzer.print_analysis()
        
        # Check for specific issues
        print(f"\n🔍 ISSUE ANALYSIS:")
        
        low_freq_count = analyzer.message_counts.get("LOW_FREQ", 0)
        high_freq_count = analyzer.message_counts.get("HIGH_FREQ", 0)
        
        if low_freq_count == 0:
            print("🚨 CRITICAL: No LOW_FREQ messages received!")
        elif low_freq_count < 10:
            print(f"⚠️  WARNING: Very few LOW_FREQ messages ({low_freq_count})")
        else:
            print(f"✅ LOW_FREQ messages: {low_freq_count} (normal)")
        
        if high_freq_count > low_freq_count * 10:
            print(f"⚠️  WARNING: HIGH_FREQ overwhelming LOW_FREQ ({high_freq_count}:{low_freq_count})")
        
        ser.close()
        
    except Exception as e:
        print(f"❌ Failed to connect to Arduino: {e}")
        print("💡 Make sure Arduino is connected and dashboard is stopped")

if __name__ == "__main__":
    print("🔧 DASHBOARD TIMING ANALYSIS")
    print("=" * 40)
    print("This script will analyze message processing performance")
    print("to identify blocking operations or bottlenecks.")
    print()
    
    # Stop dashboard service first
    import subprocess
    try:
        subprocess.run(['sudo', 'systemctl', 'stop', 'dashboard'], check=True)
        print("🛑 Dashboard service stopped")
    except:
        print("⚠️  Could not stop dashboard service (may not be running)")
    
    analyze_serial_performance()
    
    print(f"\n💡 RECOMMENDATIONS:")
    print("1. If LOW_FREQ messages are missing: Check Arduino timing")
    print("2. If processing times > 50ms: Check for blocking operations")
    print("3. If HIGH_FREQ >> LOW_FREQ: Reduce high frequency message rate")
    print("4. If max processing > 1000ms: There's a serious blocking issue")