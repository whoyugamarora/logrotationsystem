#!/bin/python3

import os
import time
import zipfile
import tempfile
import argparse
import configparser
import pathlib
import logging
from datetime import datetime
import sys
import subprocess
import pwd

#This Configparser reads the configuration file and gives the values to the script  
def parse_config():
    config = configparser.ConfigParser()
    config.read("log.cfg")

    #This prints the usage statement when -h or --help is typed
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Log Rotation System",
        epilog='''\
Usage examples:
    python script.py --threshold_mb 50 --main_dir ~/my_project --log_dir ~/my_project/log --zipped_dir ~/my_project/zipped_logs --log_file ~/my_project/log_rotation.log

Expected results:
    - The script will zip log files in the specified log directory if their total size exceeds the threshold.
    - Zipped logs will be stored in the specified zipped directory.
    - Old zipped logs older than a week will be deleted.

Parameters:
    --threshold_mb (float): The size in MB at which a warning is logged.
    --main_dir (str): Directory for the entire project.
    --log_dir (str): Directory for log files.
    --zipped_dir (str): Directory for storing zipped logs.
    --log_file (str): File to log the script's actions.

Configuration file layout (log.cfg):
    [settings]
    threshold_mb = 100.0
    main_dir = ~/course_project
    log_dir = ~/course_project/log
    zipped_dir = ~/course_project/zipped_logs
    log_file = ~/course_project/log_rotation.log

Error messages and exit codes:
    - Error messages are logged for invalid directories or permission issues.
    - The script exits with code 1 for errors, and code 0 for successful execution.
        ''')

    #This argsparser takes the values from command line and puts it in the script
    parser.add_argument("--threshold_mb", type=float, default=config.getfloat("settings", "threshold_mb", fallback=100.0),
                        help="Threshold size in MB for logging a warning.")
    parser.add_argument("--main_dir", type=str,
                        default=os.path.expanduser(config.get("settings", "main_dir", fallback="~/course_project")),
                        help="Directory where the whole project will be stored.")
    parser.add_argument("--log_dir", type=str,
                        default=os.path.expanduser(config.get("settings", "log_dir", fallback="~/course_project/log")),
                        help="Directory where log files are stored.")
    parser.add_argument("--zipped_dir", type=str, default=os.path.expanduser(
        config.get("settings", "zipped_dir", fallback="~/course_project/zipped_logs")),
                        help="Directory where zipped logs will be saved.")
    parser.add_argument("--log_file", type=str, default=os.path.expanduser(
        config.get("settings", "log_file", fallback="~/course_project/log_rotation.log")),
                        help="File to store logs of the script.")
    parser.add_argument("--delegate", type=str, help="Transfer script ownership to another user")
    args = parser.parse_args()
    return args

def transfer_ownership(args):
    try:
        pwd.getpwnam(args.delegate)
    except KeyError:
      sys.stderr.write(f"Error, user {args.delegate} does not exist")
      sys.exit(1)
     
    try:
        # swap ownership of the logrotate service file
        subprocess.run(["sudo", "chown", f"{args.delegate}:{args.delegate}", "/etc/systemd/system/log_rotation.service"], check=True)
        print(f"Ownership transferred to {args.delegate}")

        # service file updated to run under new user
        with open("/etc/systemd/system/log_rotation.service", "r") as file:
            lines = file.readlines()
        with open("/etc/systemd/system/log_rotation.service", "w") as file:
            for line in lines:
                if line.startswith("User="):
                    file.write(f"User={args.delegate}\n")
                else:
                    file.write(line)

        # Reload the systemd and restart service
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "log_rotation.service"], check=True)
        print(f"Log rotation service restarted under user {args.delegate}")

    except subprocess.CalledProcessError as e:
        print(f"Error during ownership transfer: {e}")
        sys.exit(1)


#This function sets up the directories if not already created
def setup_dir(args):
    if not os.path.isdir(args.main_dir):
        sys.stderr.write(f"Error, {args.main_dir} directory not found")
        sys.exit(1)
    if not os.path.isdir(args.log_dir):
        sys.stderr.write(f"Error, {args.log_dir} directory not found")
        sys.exit(1)
    if not os.path.isdir(args.zipped_dir):
        sys.stderr.write(f"Error, {args.zipped_dir} directory not found")
        sys.exit(1)
    if not isinstance(args.threshold_mb, float):
        sys.stderr.write(f"Error, {args.threshold_mb} is not a valid Threshold size")
        sys.exit(1)

    main_dir = args.main_dir
    log_dir = args.log_dir
    zipped_dir = args.zipped_dir

    try:
        os.makedirs(zipped_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        sys.stderr.write(f"Operating System error creating {zipped_dir} or {log_dir}: {e}")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error during {zipped_dir} or {log_dir} creation: {e}")
        sys.exit(1)

    logging.basicConfig(filename=f"{main_dir}/log_rotation.log", level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")


#This function zips the log files in the folder and renames it to the final location
def zip_up_logs(zipped_dir, log_dir):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    log_files = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', suffix=".zip", dir='/tmp/', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'a') as zipf:
                # Add files to the zip
                log_files = list(pathlib.Path(log_dir).glob('*.log'))

                if log_files:
                    for log_file in log_files:
                        if log_file.is_file():
                            zipf.write(log_file, arcname=log_file.name)
                            print(f"Adding file: {log_file}")
                    print("Zip File Created Successfully")
                else:
                    print("No log files found in the specified directory.")

            final_zip_path = os.path.join(zipped_dir, f'zippedLogs.{date_str}.zip')
            os.rename(temp_file.name, final_zip_path)

            log_files_count = len(log_files)
            largest_file = max(log_files, key=lambda f: f.stat().st_size, default=None)
            if largest_file:
                largest_file_size = largest_file.stat().st_size
                logging.info(
                    f"Zipped {log_files_count} files. Largest file: {largest_file.name}, Size: {largest_file_size} bytes, Timestamp: {date_str}")
            else:
                logging.info("No log files were found to zip.")

    except PermissionError as e:
        logging.error(f"Permission error during zipping files: {e}")
        sys.exit(1)
    except OSError as e:
        logging.error(f"Operating system error during zipping logs: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error during zipping logs: {e}")
        sys.exit(1)

    if log_files:
        for log_file in log_files:
           try:
               os.remove(log_file)
           except OSError as e:
               logging.error(f"Couldn't delete log file {log_file} after zipping {e}")


#This function checks the size of log folder and displays a warning sign if size > threshold
def check_log_size(log_dir, threshold_mb):
    try:
        total_size = 0
        for root, _, files in os.walk(log_dir):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)

        total_size_mb = total_size / (1024 * 1024)

        if total_size_mb >= threshold_mb:
            logging.warning(f"Total log size exceeded {threshold_mb} MB: {total_size_mb} MB")
            print(f"WARNING!Total log size have exceeded Threshold Size of {threshold_mb} MB: {total_size_mb} MB")

    except OSError as e:
        logging.error(f"Operating system error during log size calculation: {e}")
        return 1
    except Exception as e:
        logging.error(f"Error during log size calculation: {e}")
        return 1


#This would zip the old zip files that are more than a week old
def delete_old_zips(zipped_dir):
    try:
        now = time.time()
        now_minus_7 = now - 7 * 86400
        deleted_files_count = 0

        for f in os.listdir(zipped_dir):
            file_path = os.path.join(zipped_dir, f)
            if os.path.isfile(file_path) and os.stat(file_path).st_mtime < now_minus_7 :
                os.remove(file_path)
                deleted_files_count += 1
                logging.info(f"Deleted old zip file: {file_path}")

        logging.info(f"Deleted {deleted_files_count} old zipped files older than one week.")
    except OSError as e:
        logging.error(f"Operating System error during deletion of old zipped files: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error during deletion of old zipped files: {e}")
        sys.exit(1)
    sys.exit(0)

def main():
    args = parse_config()
    if args.delegate:
        transfer_ownership(args)
    setup_dir(args)
    zip_up_logs(args.zipped_dir, args.log_dir)
    check_log_size(args.log_dir, args.threshold_mb)
    delete_old_zips(args.zipped_dir)

if __name__ == "__main__":
    main()