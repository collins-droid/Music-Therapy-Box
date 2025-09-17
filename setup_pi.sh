#!/bin/bash
"""
Setup script for Pi IP reporter
Run this on your Raspberry Pi to set up email reporting
"""

echo "Setting up Pi IP Reporter..."

# Make the pi script executable
chmod +x pi

# Install required packages
echo "Installing required packages..."
sudo apt update
sudo apt install -y python3-pip
pip3 install --user smtplib

# Enable SSH if not already enabled
echo "Checking SSH status..."
if ! systemctl is-active --quiet ssh; then
    echo "Enabling SSH..."
    sudo systemctl enable ssh
    sudo systemctl start ssh
    echo "✓ SSH enabled"
else
    echo "✓ SSH already running"
fi

# Create a simple email setup script
cat > setup_email.sh << 'EOF'
#!/bin/bash
echo "Gmail App Password Setup"
echo "========================"
echo ""
echo "1. Go to your Google Account settings"
echo "2. Enable 2-factor authentication"
echo "3. Generate an App Password for 'Mail'"
echo "4. Run this command with your app password:"
echo ""
echo "export GMAIL_APP_PASSWORD='your_app_password_here'"
echo ""
echo "5. Add this to your ~/.bashrc to make it permanent:"
echo "echo 'export GMAIL_APP_PASSWORD=\"your_app_password_here\"' >> ~/.bashrc"
echo ""
echo "6. Then run: source ~/.bashrc"
echo ""
echo "7. Test by running: python3 pi"
EOF

chmod +x setup_email.sh

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Run: ./setup_email.sh"
echo "2. Set up your Gmail app password"
echo "3. Run: python3 pi"
echo ""
echo "The script will:"
echo "- Get your Pi's IP address"
echo "- Send it to collinsmtonga1390@gmail.com"
echo "- Save it to pi_ip.txt"
