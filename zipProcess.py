#leave /var/log path as is
#leave tmp file location as is
#line 27 change dest file path to desired output


import os
import zipfile
import tempfile
import argparse
import configparser
import pathlib
import logging
from datetime import datetime
import sys

config = configparser.ConfigParser()
config.read("log.cfg")



parser = argparse.ArgumentParser(description="Log Rotation System")
parser.add_argument("--threshold_mb", type=float, default=config.getfloat("settings", "threshold_mb", fallback=100), help="Threshold size in MB for logging a warning.")
parser.add_argument("--main_dir", type=str, default=os.path.expanduser(config.get("settings", "main_dir", fallback="~/course_project")), help="Directory where the whole project will be stored.")
parser.add_argument("--log_dir", type=str, default=os.path.expanduser(config.get("settings", "log_dir", fallback="~/course_project/log")), help="Directory where log files are stored.")
parser.add_argument("--zipped_dir", type=str, default=os.path.expanduser(config.get("settings", "zipped_dir", fallback="~/course_project/zipped_logs")), help="Directory where zipped logs will be saved.")
parser.add_argument("--log_file", type=str, default=os.path.expanduser(config.get("settings", "log_file", fallback="~/course_project/log_rotation.log")), help="File to store logs of the script.")
args = parser.parse_args()

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


logging.basicConfig(
    filename=f"{main_dir}/log_rotation.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


now = datetime.now()
date_str = now.strftime("%Y-%m-%d_%H-%M-%S")

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
            logging.info(f"Zipped {log_files_count} files. Largest file: {largest_file.name}, Size: {largest_file_size} bytes, Timestamp: {date_str}")
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

threshold_mb = args.threshold_mb
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

check_log_size(log_dir, threshold_mb)