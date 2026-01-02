# UI Configuration Support

This document explains the new UI-based configuration feature added to the Neviweb130 integration.

## Overview

The Neviweb130 integration now supports configuration through the Home Assistant UI, in addition to the existing YAML configuration method. This makes it easier to set up and manage your Neviweb devices without manually editing configuration files.

## Features

- **User-friendly setup**: Configure the integration directly from the Home Assistant UI
- **Network discovery**: Automatically discovers available networks (locations) from your Neviweb account
- **Options flow**: Update configuration options after initial setup
- **Backward compatible**: Existing YAML configurations continue to work without changes

## How to Use

### Initial Setup via UI

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "Neviweb130" or "Sinope"
4. Follow the setup wizard:
   - **Step 1**: Enter your Neviweb username (email) and password
   - **Step 2**: Select the networks (locations) you want to control (optional)
   - **Step 3**: Configure optional settings (scan interval, homekit mode, etc.)
5. Click **Submit** to complete the setup

### Configuration Options

#### Required Settings
- **Username**: Your Neviweb email address
- **Password**: Your Neviweb password

#### Optional Settings (Step 2)
- **Network 1**: Primary location/network name from Neviweb
- **Network 2**: Secondary location/network name (if you have multiple)
- **Network 3**: Third location/network name (if you have multiple)

Leave these empty to automatically use the first available networks.

#### Optional Settings (Step 3)
- **Scan Interval** (default: 540 seconds): How often to poll Neviweb for device updates (300-600 seconds recommended)
- **HomeKit Mode** (default: False): Enable HomeKit-specific values if you use HomeKit
- **Ignore Mi-Wi devices** (default: False): Ignore Mi-Wi protocol devices if present in the same location
- **Statistics Interval** (default: 1800 seconds): How often to update energy statistics (300-1800 seconds)
- **Notify** (default: "both"): How to send error notifications
  - "nothing": No notifications
  - "logging": Log only
  - "notification": Home Assistant notifications only
  - "both": Both logging and notifications

### Updating Configuration

After initial setup, you can update optional settings:

1. Go to **Settings** → **Devices & Services**
2. Find the Neviweb130 integration
3. Click **CONFIGURE**
4. Update the desired settings
5. Click **Submit**

Note: Username, password, and network selections cannot be changed after initial setup. To change these, you must remove and re-add the integration.

## Migration from YAML

If you currently use YAML configuration:

1. Your existing YAML configuration will continue to work
2. To migrate to UI configuration:
   - Remove the `neviweb130:` section from your `configuration.yaml`
   - Restart Home Assistant
   - Add the integration through the UI (as described above)
   - Your devices will be re-discovered automatically

**Important**: Do not use both YAML and UI configuration simultaneously for the same account.

## Backward Compatibility

- Existing YAML configurations continue to work unchanged
- You can keep using YAML configuration if you prefer
- The integration supports both configuration methods

## Troubleshooting

### "Cannot connect" error
- Check your internet connection
- Verify that neviweb.com is accessible
- Ensure your firewall allows connections to neviweb.com

### "Invalid auth" error
- Verify your username (email) and password are correct
- Try logging into https://neviweb.com directly to confirm credentials

### "Already configured" error
- This account is already configured
- Remove the existing configuration first if you want to reconfigure

### Devices not appearing
- Check that the selected networks contain your devices
- Verify devices are properly set up in the Neviweb portal
- Check the Home Assistant logs for more details

## Technical Details

### Files Added/Modified

- **config_flow.py**: New file implementing the UI configuration flow
- **strings.json**: UI text strings for the configuration wizard
- **translations/en.json**: English translations for the UI
- **manifest.json**: Updated to indicate config_flow support
- **__init__.py**: Updated to support both YAML and config entry setup

### Data Storage

- Config entries are stored in `.storage/core.config_entries`
- Each entry is identified by a unique ID based on the username
- Multiple accounts can be configured through the UI

### API Interaction

The config flow validates credentials by:
1. Authenticating with the Neviweb API
2. Retrieving available networks/locations
3. Storing validated credentials securely in the config entry
