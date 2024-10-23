#add path to be the directory for program to look at to delete files



import os
import time
import sys

path = " "
now = time.time()

for f in os.listdir(path):
    if os.stat(f).st_mtime < now - 7 * 86400:
        if os.path.isfile(f):
            os.remove(os.path.join(path,f))

#https://stackoverflow.com/questions/12485666/python-deleting-all-files-in-a-folder-older-than-x-days