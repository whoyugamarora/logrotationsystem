import os
import zipfile
import tempfile
import pathlib
from datetime import datetime

now = datetime.now()
date_str = now.strftime("%Y-%m-%d_%H-%M-%S")

with tempfile.NamedTemporaryFile(mode='wb', suffix=".zip", dir='/tmp/', delete=False) as temp_file:
    with zipfile.ZipFile(temp_file.name, 'a') as zipf:
        # Add files to the zip
        for log_name in list(pathlib.Path('/var/log/').glob('*.log')):
            if not os.path.isfile(log_name):
                continue
            file_path = pathlib.Path(log_name)
            if not file_path.exists():
                print(f"warning file path doesn't exist/or readable {log_name}")
            print(log_name)
            zipf.write(log_name, arcname=log_name.name)

    os.rename(temp_file.name, f'{os.path.expanduser("~")}/Desktop/zippedLogs.{date_str}.zip')

    # A.
    # recursive walk all files and folders and zip?
    # what about rec files that are not named .log? Zip ALL files or just .log files?
    # delete - delete ALL .log and other files or just .log?

    # D.
    # is this log under var log or is it under ~/...
    # . if under var log, folder would be zipping itself while running

    # G.
    # which inputs are config? source dir? dest dir? zipping compression?
    # daily run time?
