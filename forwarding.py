#!/usr/bin/env python3
"""
Port Forwarding Setup Helper
Helps configure router for SSH access to Pi
"""

import socket
import subprocess
import webbrowser
from datetime import datetime

def get_local_ip():
    """Get the Pi's local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"

def get_router_ip():
    """Get router IP address"""
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            parts = lines[0].split()
            if len(parts) >= 3:
                return parts[2]
        return "Unknown"
    except:
        return "Unknown"

def main():
    """Main function"""
    print("=" * 60)
    print("PORT FORWARDING SETUP FOR SSH ACCESS")
    print("=" * 60)
    
    local_ip = get_local_ip()
    router_ip = get_router_ip()
    
    print(f"Pi Local IP: {local_ip}")
    print(f"Router IP: {router_ip}")
    print("=" * 60)
    
    print("STEP-BY-STEP ROUTER SETUP:")
    print("=" * 60)
    print("1. Open your router's web interface:")
    print(f"   http://{router_ip}")
    print("   (Common default passwords: admin/admin, admin/password)")
    print("")
    print("2. Look for these sections (varies by router):")
    print("   - Port Forwarding")
    print("   - Virtual Server")
    print("   - NAT Forwarding")
    print("   - Advanced > Port Forwarding")
    print("")
    print("3. Add a new port forwarding rule:")
    print(f"   Service Name: SSH-Pi")
    print(f"   External Port: 22")
    print(f"   Internal IP: {local_ip}")
    print(f"   Internal Port: 22")
    print("   Protocol: TCP")
    print("   Status: Enabled")
    print("")
    print("4. Save and apply the settings")
    print("")
    print("5. Test the connection:")
    print("   - Get your public IP: curl ifconfig.me")
    print("   - From outside: ssh pi@<public_ip>")
    print("=" * 60)
    
    # Try to open router interface
    try:
        response = input(f"\nOpen router interface (http://{router_ip})? (y/n): ")
        if response.lower() in ['y', 'yes']:
            webbrowser.open(f"http://{router_ip}")
            print("✓ Router interface opened in browser")
    except:
        pass
    
    print("\nCOMMON ROUTER BRANDS:")
    print("- Netgear: Advanced > Port Forwarding")
    print("- Linksys: Smart Wi-Fi Tools > Port Forwarding")
    print("- TP-Link: Advanced > NAT Forwarding")
    print("- ASUS: Advanced Settings > Port Forwarding")
    print("- D-Link: Advanced > Port Forwarding")
    print("=" * 60)
    
    # Save instructions
    try:
        with open('port_forwarding_instructions.txt', 'w') as f:
            f.write(f"Port Forwarding Instructions\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Pi Local IP: {local_ip}\n")
            f.write(f"Router IP: {router_ip}\n")
            f.write(f"\nRouter Setup:\n")
            f.write(f"1. Go to: http://{router_ip}\n")
            f.write(f"2. Find Port Forwarding section\n")
            f.write(f"3. Add rule:\n")
            f.write(f"   - External Port: 22\n")
            f.write(f"   - Internal IP: {local_ip}\n")
            f.write(f"   - Internal Port: 22\n")
            f.write(f"   - Protocol: TCP\n")
            f.write(f"4. Save and test\n")
        print("✓ Instructions saved to port_forwarding_instructions.txt")
    except:
        print("✗ Failed to save instructions")

if __name__ == "__main__":
    main()
