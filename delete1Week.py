#add path to be the directory for program to look at to delete files



import os
import time
import logging
import sys

zipped_dir = os.path.expanduser("~/course_project/zipped_logs")
log_dir = os.path.expanduser("~/course_project/log")

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
    filename=f"{log_dir}/log_rotation.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def delete_old_zips():
    try:
        now = time.time()
        deleted_files_count = 0

        for f in os.listdir(zipped_dir):
            file_path = os.path.join(zipped_dir, f)
            if os.path.isfile(file_path) and os.stat(file_path).st_mtime < now - 7 * 86400:
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

#https://stackoverflow.com/questions/12485666/python-deleting-all-files-in-a-folder-older-than-x-days