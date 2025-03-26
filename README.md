# NetworkUpdateManager

A system tray application that monitors and manages updates from a network share

NetworkUpdateManager solves this by:

1. Using a dedicated set of credentials to connect to the network share
2. Automatically downloading updates to a local directory
3. Notifying the application when updates are available
4. Running silently in the background with minimal user intervention

## Features

- **Secure Credential Management**: Stores network share credentials securely using encryption tied to the machine
- **Automatic Updates**: Checks for updates on a configurable schedule (daily at specific time or interval-based)
- **Version Tracking**: Monitors version files to determine when updates are needed
- **System Tray Interface**: Simple, unobtrusive interface that runs in the system tray
- **Robust Error Handling**: Automatically retries failed connections and downloads
- **Detailed Logging**: Comprehensive logging for troubleshooting
- **Configuration Wizard**: User-friendly setup interface for initial configuration
- **Windows Integration**: Starts with Windows and runs silently in the background
- **UAC Handling**: Automatically requests elevated privileges when needed

## Installation

### Prerequisites

- Windows 7 or later
- Network share access credentials

### For End Users

1. Download the installer (`siges_updater_setup.exe`)
2. Run the installer with administrative privileges
3. Follow the setup wizard to configure the updater
4. Enter your network share credentials when prompted

### For Developers

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python run.py`
4. To build the executable: `python build.py`

## Configuration

During first run, you'll be prompted to configure:

1. **Network Share Path**: The UNC path to the update share (e.g., `\\server\updates`)
2. **Local Update Path**: Where updates should be stored locally (default: `C:\Users\Public\Digitalis\PRODUCAO`)
3. **Version File Pattern**: Pattern to match version files (e.g., `SIGES *.txt`)
4. **Update Schedule**: Daily check at specified time (e.g., 8:00 AM) or interval-based
5. **Share Credentials**: Username and password for the network share

Advanced configuration options are available in the `.env` file:

```
# Network share configuration
UPDATE_SHARE_PATH=\\server\updates
DOMAIN=ulht

# Local application paths
LOCAL_UPDATE_PATH=C:\Users\Public\Digitalis\PRODUCAO
APP_EXECUTABLE_PATH=C:\Users\Public\Desktop\siges_updater.exe
APP_PRETTY_NAME=SIGES Updater

# Version tracking
VERSION_FILE_PATTERN=SIGES *.txt
CHECK_FREQUENCY=daily  # daily, hourly, or minutes
CHECK_TIME=08:00       # Time to run daily check (24-hour format)
CHECK_INTERVAL=300     # in seconds - used if CHECK_FREQUENCY=minutes

# UI Configuration
TRAY_ICON_PATH=app/icons/updater.ico
```

You can place custom icons in the `app/icons/` directory to customize the application appearance.

## Version Checking

The application checks for version files in the configured directory matching the specified pattern. When a newer version is available on the network share, the application automatically downloads the updates.

## Building from Source

To build the application into a standalone executable and create an installer:

1. Run `python build.py`
2. The executable will be created in the `dist` directory
3. An installer will be created in the `installer` directory (requires Inno Setup)

## Troubleshooting

Common issues and solutions:

1. **Application won't start**: Check the logs in the `logs` directory
2. **Can't connect to share**: Verify credentials and network connectivity
3. **Updates not downloading**: Ensure the configured paths are correct and accessible
4. **Version not detected**: Verify that version files match the configured pattern


