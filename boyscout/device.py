"""Device information utilities"""
import socket
import platform

DEVICE_HOSTNAME = None
DEVICE_INFO_CACHE = None


def get_device_name():
    """Get the device hostname."""
    global DEVICE_HOSTNAME
    if DEVICE_HOSTNAME is None:
        try:
            hostname = socket.gethostname()
            DEVICE_HOSTNAME = hostname.replace('.local', '').replace('.lan', '')
        except Exception:
            DEVICE_HOSTNAME = "Unknown Device"
    return DEVICE_HOSTNAME


def get_device_info():
    """Get formatted device info string."""
    global DEVICE_INFO_CACHE
    if DEVICE_INFO_CACHE is None:
        try:
            hostname = get_device_name()
            release = platform.release()
            try:
                edition = platform.win32_edition() if hasattr(platform, 'win32_edition') else ""
                full_system = f"Windows {release} {edition}".strip()
            except Exception:
                full_system = f"Windows {release}"
            DEVICE_INFO_CACHE = f"{hostname} ({full_system})"
        except Exception:
            DEVICE_INFO_CACHE = "Unknown Device"
    return DEVICE_INFO_CACHE
