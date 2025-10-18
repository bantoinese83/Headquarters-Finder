#!/usr/bin/env python3
"""
Build script for creating Windows executable.
Uses PyInstaller to create a standalone executable.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        print("✓ PyInstaller already installed")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install PyInstaller: {e}")
            return False


def create_spec_file():
    """Create PyInstaller spec file for the executable."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.ini', '.'),
        ('config_sample.ini', '.'),
        ('README.md', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'google.generativeai',
        'pandas',
        'configparser',
        'logging.handlers',
        'difflib',
        're',
        'datetime',
        'argparse',
        'tempfile',
        'pathlib'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HeadquartersFinder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)
'''
    
    with open('HeadquartersFinder.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ PyInstaller spec file created")


def build_executable():
    """Build the Windows executable."""
    print("Building Windows executable...")
    
    try:
        # Clean previous builds
        if os.path.exists('build'):
            shutil.rmtree('build')
        if os.path.exists('dist'):
            shutil.rmtree('dist')
        
        # Build executable
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "HeadquartersFinder.spec"]
        subprocess.check_call(cmd)
        
        print("✓ Executable built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to build executable: {e}")
        return False


def create_distribution_package():
    """Create distribution package with all necessary files."""
    print("Creating distribution package...")
    
    dist_dir = Path("HeadquartersFinder_Distribution")
    
    # Create distribution directory
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    
    # Copy executable
    exe_src = Path("dist/HeadquartersFinder.exe")
    exe_dst = dist_dir / "HeadquartersFinder.exe"
    if exe_src.exists():
        shutil.copy2(exe_src, exe_dst)
        print("✓ Executable copied to distribution")
    else:
        print("✗ Executable not found in dist/ directory")
        return False
    
    # Copy configuration files
    config_files = [
        "config_sample.ini",
        "README.md",
        "requirements.txt"
    ]
    
    for file in config_files:
        if os.path.exists(file):
            shutil.copy2(file, dist_dir / file)
            print(f"✓ {file} copied to distribution")
    
    # Create sample input CSV
    sample_csv = dist_dir / "sample_input.csv"
    sample_data = """Geographic Location,Payee Name of Record,Address1 of Record,Address 2 of Record,City of Record,State of Record,Zip of Record
State of California,GOOGLE INC,,,,,
Cook County Illinois,MICROSOFT CORP,1 MICROSOFT WAY,,REDMOND,WA,98052
State of California,APPLE INC,1 APPLE PARK WAY,,CUPERTINO,CA,95014"""
    
    with open(sample_csv, 'w') as f:
        f.write(sample_data)
    print("✓ Sample input CSV created")
    
    # Create usage instructions
    instructions = dist_dir / "USAGE_INSTRUCTIONS.txt"
    with open(instructions, 'w') as f:
        f.write("""HEADQUARTERS FINDER - USAGE INSTRUCTIONS

1. SETUP:
   - Rename 'config_sample.ini' to 'config.ini'
   - Edit config.ini and set your Gemini API key in the [API] section
   - Place your input CSV file in this directory

2. RUNNING:
   - Double-click HeadquartersFinder.exe
   - Or run from command line: HeadquartersFinder.exe

3. INPUT CSV FORMAT:
   - Must contain a column named "Payee Name of Record"
   - See sample_input.csv for reference

4. OUTPUT:
   - Results will be saved to data/output.csv
   - Logs will be created in logs/ directory

5. COMMAND LINE OPTIONS:
   - HeadquartersFinder.exe --test (test API connection)
   - HeadquartersFinder.exe --validate (validate against gold standard)
   - HeadquartersFinder.exe --help (show help)

6. TROUBLESHOOTING:
   - Check logs/ directory for detailed error messages
   - Ensure your API key is valid
   - Make sure input CSV file exists and is properly formatted

For detailed documentation, see README.md
""")
    print("✓ Usage instructions created")
    
    print(f"✓ Distribution package created: {dist_dir}")
    return True


def main():
    """Main build process."""
    print("=" * 60)
    print("HEADQUARTERS FINDER - WINDOWS EXECUTABLE BUILDER")
    print("=" * 60)
    
    # Check if we're on Windows (PyInstaller works best on target platform)
    if sys.platform != "win32":
        print("WARNING: This script is designed for Windows. Building on other platforms")
        print("may result in compatibility issues.")
        print()
    
    # Install PyInstaller
    if not install_pyinstaller():
        return 1
    
    # Create spec file
    create_spec_file()
    
    # Build executable
    if not build_executable():
        return 1
    
    # Create distribution package
    if not create_distribution_package():
        return 1
    
    print("\n" + "=" * 60)
    print("BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("Distribution package created: HeadquartersFinder_Distribution/")
    print("Contents:")
    print("- HeadquartersFinder.exe (main executable)")
    print("- config_sample.ini (configuration template)")
    print("- sample_input.csv (sample input file)")
    print("- README.md (documentation)")
    print("- USAGE_INSTRUCTIONS.txt (quick start guide)")
    print("\nTo deploy:")
    print("1. Copy the entire HeadquartersFinder_Distribution folder")
    print("2. Rename config_sample.ini to config.ini")
    print("3. Set your API key in config.ini")
    print("4. Add your input CSV file")
    print("5. Run HeadquartersFinder.exe")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
