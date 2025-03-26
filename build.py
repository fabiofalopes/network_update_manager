#!/usr/bin/env python3
"""
NetworkUpdateManager - Build Script
----------------------------------
Creates a distributable executable using PyInstaller.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build_dirs():
    """Clean up build and dist directories"""
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name} directory...")
            shutil.rmtree(dir_name)
            
    # Also remove PyInstaller spec files
    for spec_file in Path('.').glob('*.spec'):
        print(f"Removing {spec_file}...")
        os.remove(spec_file)

def ensure_dependencies():
    """Ensure all required dependencies are installed"""
    required_packages = [
        'pyinstaller',
        'pillow',
        'pystray',
        'pywin32',
        'apscheduler',
        'pysmb',
        'python-dotenv'
    ]
    
    print("Checking dependencies...")
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is not installed. Installing...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def build_executable():
    """Build the executable with PyInstaller"""
    print("Building executable with PyInstaller...")
    
    # Ensure the icon file exists
    icon_path = Path('network_update_manager/app/icons/updater.ico')
    if not icon_path.exists():
        print("Warning: Icon file not found, using default icon")
        icon_path = None
    
    # Prepare PyInstaller command
    pyinstaller_args = [
        'pyinstaller',
        '--name=siges_updater',
        '--onefile',
        '--windowed',  # No console window
        '--clean',
        '--noconfirm',
    ]
    
    # Add icon if available
    if icon_path:
        pyinstaller_args.append(f'--icon={icon_path}')
    
    # Add hidden imports
    pyinstaller_args.extend([
        '--hidden-import=win32timezone',
        '--hidden-import=PIL._tkinter_finder',
    ])
    
    # Add data files (icons, etc.)
    pyinstaller_args.extend([
        '--add-data=network_update_manager/app/icons;app/icons',
        '--add-data=network_update_manager/.env.example;.',
    ])
    
    # Main script
    pyinstaller_args.append('network_update_manager/run.py')
    
    # Execute PyInstaller
    subprocess.check_call(pyinstaller_args)

def create_inno_setup_script():
    """Create an Inno Setup script for the installer"""
    
    # Get version number (you could extract this from your code)
    version = "1.0.0"
    
    # Create the Inno Setup script
    inno_script = f"""
#define MyAppName "SIGES Updater"
#define MyAppVersion "{version}"
#define MyAppPublisher "Digitalis"
#define MyAppExeName "siges_updater.exe"
#define MyAppIcoName "updater.ico"

[Setup]
AppId={{{{D4BAF4D0-8A2F-4CF8-89DE-0E7A1A89BC56}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=siges_updater_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=network_update_manager\\app\\icons\\{{#MyAppIcoName}}
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "autostart"; Description: "Start automatically when Windows starts"; GroupDescription: "Auto-start options:"; Flags: checkedonce

[Files]
Source: "dist\\{{#MyAppExeName}}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "network_update_manager\\app\\icons\\*"; DestDir: "{{app}}\\app\\icons"; Flags: ignoreversion recursesubdirs
Source: "network_update_manager\\.env.example"; DestDir: "{{app}}"; DestName: ".env"; Flags: onlyifdoesntexist

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{userdesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon
Name: "{{commondesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"

[Registry]
Root: HKCU; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Run"; ValueType: string; ValueName: "NetworkUpdateManager"; ValueData: "{{app}}\\{{#MyAppExeName}}"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
"""

    script_file = Path('inno_setup.iss')
    print(f"Creating Inno Setup script: {script_file}")
    with open(script_file, 'w') as f:
        f.write(inno_script)
        
    return script_file

def create_installer(inno_script):
    """Create installer using Inno Setup"""
    try:
        # Try to find Inno Setup compiler
        iscc_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe"
        ]
        
        iscc_path = None
        for path in iscc_paths:
            if os.path.exists(path):
                iscc_path = path
                break
                
        if not iscc_path:
            print("Inno Setup Compiler (ISCC.exe) not found.")
            print("Please install Inno Setup 6 from https://jrsoftware.org/isdl.php")
            print("You can manually compile the script later by opening inno_setup.iss")
            return False
        
        # Create installer
        print("Creating installer with Inno Setup...")
        subprocess.check_call([iscc_path, str(inno_script)])
        print("Installer created successfully in the 'installer' directory.")
        return True
        
    except Exception as e:
        print(f"Error creating installer: {e}")
        return False

def main():
    """Main build process"""
    print("Starting build process for NetworkUpdateManager...")
    
    # Change to the script's directory
    os.chdir(Path(__file__).parent)
    
    # Clean previous build artifacts
    clean_build_dirs()
    
    # Ensure dependencies are installed
    ensure_dependencies()
    
    # Build the executable
    try:
        build_executable()
        print("Executable built successfully.")
        
        # Create Inno Setup script
        inno_script = create_inno_setup_script()
        
        # Create installer
        if inno_script and os.path.exists('dist/siges_updater.exe'):
            if not os.path.exists('installer'):
                os.makedirs('installer')
                
            create_installer(inno_script)
        else:
            print("Skipping installer creation due to missing executable.")
            
    except Exception as e:
        print(f"Error building executable: {e}")
        return 1
        
    print("Build process completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 