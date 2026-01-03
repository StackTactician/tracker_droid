# PC Tracker

## What this is

This project is a **learning and research prototype** written in Python.  
It shows how a Windows system can record user activity and communicate with a remote controller using a Telegram bot.

It is intended for **educational and security research purposes only**, not for real-world deployment.

---

## Why it exists

This project helps demonstrate:

- How user activity can be recorded on a system
- How running applications and windows can be tracked
- How basic system and device information can be collected
- How data can be sent remotely using a messaging platform

It is useful for students learning cybersecurity, malware analysis, or system monitoring from a defensive perspective.

---

## What it does (plain terms)

- Records keyboard input and application usage
- Tracks the active program and window title
- Collects basic system and device information
- Estimates location using the device’s public IP
- Stores activity logs locally and compresses them
- Allows status checks and log retrieval through Telegram commands

---

## How it is used

This project is designed to be **compiled into an executable** before use.

Typical workflow:
1. Write and review the Python source
2. Compile it into a Windows executable using PyInstaller
3. Run only in a controlled test environment

This mirrors how many long-running Windows programs are packaged and distributed.

---

## Environment

- Windows
- Python 3.x
- Virtual machine or test system strongly recommended

Do not run this on personal, shared, or production machines.

---

## Telegram interface

A Telegram bot is used as a simple remote interface.  
Commands allow checking status, retrieving logs, and viewing basic device information.

This is included to demonstrate how remote control channels work, not as a production feature.

---

## Important warning

This software **must not be used on systems without clear permission**.

Monitoring activity on a computer without consent is illegal in many regions. This project exists to help people understand how such tools work so they can be detected, analyzed, or defended against.

---

## Disclaimer

This is a proof of concept.  
It is not secure, audited, or suitable for real-world use.

Use it only for learning, testing, and research in environments where you have full authorization.
