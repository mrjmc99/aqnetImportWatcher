# AQNet DICOM Import Watcher

This Python script monitors a directory containing DICOM (`.dcm`) files for a hung or stuck file and takes action by moving the stuck file to an archive folder. In addition, it checks the status of a specified Windows service (AQNetDICOMImport), and sends notification emails (with memes!) to inform the team about the status of DICOM processing.

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Script](#running-the-script)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)

---

## Features

1. **Directory Monitoring**  
   - Looks for the oldest subfolder (ignoring `_invalidFiles`) in `AQNetImport`.  
   - Checks if there is a `.dcm` file that’s older than 30 seconds, assuming it might be stuck.

2. **Service Check**  
   - Verifies whether the `AQNetDICOMImport` service (or another specified service) is running.

3. **Stuck File Handling**  
   - Moves the stuck `.dcm` file to the `AQNetImport_old` folder if it’s not being processed.

4. **Notifications**  
   - Sends an email notification if the service is not running.  
   - Sends a “success” notification if a stuck file was moved.

5. **Meme Generation**  
   - Dynamically generates memes (via [Pillow](https://pillow.readthedocs.io/en/stable/)) to embed in the HTML email.

---

## How It Works

1. The script reads environment variables from a `.env` file.
2. It checks the specified `ROOT_FOLDER` for subfolders inside `AQNetImport`.  
   - Ignores `_invalidFiles`.  
   - Finds the oldest subfolder by creation time.
3. It looks for the oldest `.dcm` file in that subfolder.
4. Pauses for 30 seconds to confirm if the file is stuck (i.e., not being processed).
5. If the file still exists, checks the Windows service (specified by `SERVICE_NAME`):
   - If the service is **not running**, an email (with a meme) is sent out indicating the issue and no further action is taken.
   - If the service **is running**, the script moves the file to `AQNetImport_old` and sends a “success” email (with a meme) indicating that the stuck file was moved.

---

## Requirements

- **Python 3.8+** (earlier versions might work, but 3.8+ is recommended)
- **pip** (Python package manager)
- **Virtual environment** (optional but recommended)
- **Installed Python packages**:
  - [python-dotenv](https://pypi.org/project/python-dotenv/)  
  - [psutil](https://pypi.org/project/psutil/)  
  - [Pillow](https://pypi.org/project/Pillow/)
- **Windows** (for service checks). The script can run on other operating systems, but the service check feature uses Windows-specific `psutil.win_service_get`.

---

## Installation

1. **Clone or Download** this repository onto the machine that needs to monitor the AQNet DICOM files.
2. **Create a Virtual Environment** (optional but recommended):

   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # On Windows
   ```
3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```
   
   Or manually install each package:
   ```bash
   pip install python-dotenv psutil Pillow
   ```

4. **Place Memes** in the `memes/` folder (or whichever path you’ve configured).

---

## Configuration

1. **`.env` File**  
   Create or edit a `.env` file in the same folder as the script. An example structure is shown below:

   ```ini
   # watcher.env

   #######################
   # AQNET Variables
   #######################
   # Path to the AQNetCache root (no quotes, and do not prefix with r" ")
   ROOT_FOLDER=E:\AQNetCache

   # Windows service name to check
   SERVICE_NAME=AQNetDICOMImport

   #######################
   # SMTP Configuration
   #######################
   SMTP_SERVER=mail.example.com
   SMTP_PORT=25
   SMTP_USERNAME=""
   SMTP_PASSWORD=None
   SMTP_FROM_DOMAIN="example.com"
   SMTP_RECIPIENTS="user1@example.com,user2@example.com"

   #######################
   # Meme Configuration
   #######################
   SUCCESSFUL_RESTART_MEME=No_Need_To_Thank_Me.jpg
   UNSUCCESSFUL_RESTART_MEME=Boromir.jpg
   ```

   - **ROOT_FOLDER**: Points to your AQNetCache directory.  
   - **SERVICE_NAME**: Name of the Windows service to check (e.g., `AQNetDICOMImport`).  
   - **SMTP_* Variables**: Email server settings, username, password, etc.  
   - **SUCCESSFUL_RESTART_MEME / UNSUCCESSFUL_RESTART_MEME**: The filenames (within the `memes/` directory) to use for your “success” or “failure” emails.

2. **Memes Folder**  
   - By default, the script looks in a folder named `memes` (alongside the script) for the images specified by `SUCCESSFUL_RESTART_MEME` and `UNSUCCESSFUL_RESTART_MEME`.

3. **Adjust Logging**  
   - The script uses the built-in Python `logging` library. By default, it logs to the console with level `INFO`. You can change the logging level and format if needed.

---

## Running the Script

1. **Activate Your Virtual Environment** (if used):

   ```bash
   .\.venv\Scripts\activate
   ```
2. **Run** the script:

   ```bash
   python watcher.py
   ```

3. **Scheduled Task** (Optional)  
   - To run this periodically (e.g., every 5 minutes), use **Windows Task Scheduler**.  
   - You can also create a loop in the script or wrap it in a `while True:` with a `time.sleep(...)` interval.

---

## Logging

- The script uses Python’s `logging` module. By default, you’ll see `INFO`, `WARNING`, and `ERROR` messages in your console.
- Example log lines:

  ```
  2025-01-23 10:00:00,123 - INFO - Oldest .dcm file found: E:\AQNetCache\AQNetImport\12345\myfile.dcm
  2025-01-23 10:00:30,456 - WARNING - The file still exists after 30 seconds...
  ...
  ```

You can easily redirect these logs to a file by modifying the `logging.basicConfig(...)` call in the script.

---

## Troubleshooting

1. **Service Not Found**  
   - If `psutil` can’t find the service, make sure you’re running on Windows and the `SERVICE_NAME` is correct.

2. **Environment Variables**  
   - If `ROOT_FOLDER` is coming back as `None`, verify your `.env` file syntax.  
   - Make sure there are no quotes or raw-string prefixes.  
   - Example: `ROOT_FOLDER=E:\AQNetCache` (no quotes, no `r" "`).

3. **Email Not Sending**  
   - Check that `SMTP_SERVER`, `SMTP_PORT`, and credentials are correct.  
   - Test sending mail via Telnet or another mail client to confirm your mail server config.

4. **Meme Generation Issues**  
   - Ensure the meme filenames in the `.env` match actual image files in the `memes/` directory.  
   - [Pillow (PIL)](https://pillow.readthedocs.io/en/stable/) must be installed.

5. **File Paths / Permissions**  
   - If you see `[WinError 123]`, `[Errno 13] Permission denied`, or `[Errno 2] No such file or directory`, ensure the `ROOT_FOLDER` path is correct and that your user has **read** and **write** permissions.

---



