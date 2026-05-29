#!/usr/bin/env bash
set -e

echo "Setting up ADB..."

# Check if adb exists
if command -v adb &> /dev/null; then
    echo "ADB already installed: $(adb version)"
else
    echo "Please install Android SDK Platform Tools manually"
    echo "https://developer.android.com/studio/releases/platform-tools"
    exit 1
fi

# Connect to local emulator (adjust port as needed)
echo "Connecting to emulator at 127.0.0.1:5555..."
adb connect 127.0.0.1:5555 || true

adb devices

echo "ADB setup complete"
