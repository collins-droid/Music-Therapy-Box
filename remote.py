#!/usr/bin/env python3
"""
Pi IP Address Getter - For Remote Access
Gets both local and public IP addresses for SSH connection
"""

import socket
import subprocess
import requests
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

def get_public_ip():
    """Get the Pi's public IP address"""
    try:
        # Try multiple services in case one is down
        services = [
            "https://api.ipify.org",
            "https://ipinfo.io/ip",
            "https://icanhazip.com",
            "https://checkip.amazonaws.com"
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    return response.text.strip()
            except:
                continue
        
        return "Unknown (no internet connection?)"
    except:
        return "Unknown"

def check_ssh():
    """Check if SSH is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'ssh'], 
                              capture_output=True, text=True)
        return result.stdout.strip() == 'active'
    except:
        return False

def get_router_info():
    """Get router/gateway information"""
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            parts = lines[0].split()
            if len(parts) >= 3:
                return parts[2]  # Gateway IP
        return "Unknown"
    except:
        return "Unknown"

def main():
    """Main function"""
    print("=" * 60)
    print("RASPBERRY PI NETWORK INFORMATION")
    print("=" * 60)
    
    local_ip = get_local_ip()
    public_ip = get_public_ip()
    ssh_status = check_ssh()
    hostname = socket.gethostname()
    router_ip = get_router_info()
    
    print(f"Hostname: {hostname}")
    print(f"Local IP: {local_ip}")
    print(f"Public IP: {public_ip}")
    print(f"Router/Gateway: {router_ip}")
    print(f"SSH Status: {'Running' if ssh_status else 'Not Running'}")
    print("=" * 60)
    
    if ssh_status:
        print("✓ SSH is running!")
        print(f"Local SSH: ssh pi@{local_ip}")
        print(f"Public SSH: ssh pi@{public_ip}")
    else:
        print("✗ SSH is not running")
        print("Enable SSH: sudo systemctl enable ssh")
        print("Start SSH: sudo systemctl start ssh")
    
    print("=" * 60)
    print("REMOTE ACCESS SETUP:")
    print("=" * 60)
    print("To access this Pi from outside your network:")
    print("")
    print("1. PORT FORWARDING (Router Setup):")
    print(f"   - Login to your router (usually http://{router_ip})")
    print("   - Go to Port Forwarding/Virtual Server")
    print("   - Forward external port 22 to internal port 22")
    print(f"   - Internal IP: {local_ip}")
    print("   - Protocol: TCP")
    print("")
    print("2. SSH CONNECTION:")
    print(f"   ssh pi@{public_ip}")
    print("")
    print("3. ALTERNATIVE METHODS:")
    print("   - Use a VPN (WireGuard, OpenVPN)")
    print("   - Use SSH tunneling service (ngrok, etc.)")
    print("   - Use dynamic DNS service")
    print("=" * 60)
    
    # Save to file
    try:
        with open('pi_network_info.txt', 'w') as f:
            f.write(f"Pi Network Information\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Hostname: {hostname}\n")
            f.write(f"Local IP: {local_ip}\n")
            f.write(f"Public IP: {public_ip}\n")
            f.write(f"Router: {router_ip}\n")
            f.write(f"SSH Status: {'Running' if ssh_status else 'Not Running'}\n")
            f.write(f"Local SSH: ssh pi@{local_ip}\n")
            f.write(f"Public SSH: ssh pi@{public_ip}\n")
            f.write(f"\nRouter Setup:\n")
            f.write(f"- Login: http://{router_ip}\n")
            f.write(f"- Forward port 22 to {local_ip}:22\n")
        print("✓ Network info saved to pi_network_info.txt")
    except:
        print("✗ Failed to save network info")

if __name__ == "__main__":
    main()
