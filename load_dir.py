import os
import re
import redis

r = redis.StrictRedis()

def load_dir(path):
    files = os.listdir(path)

    for f in files:
        print(f)
        match = re.match(r'^book(\d+).html$', f)
        if match is not None:
            with open(path + f) as file:
                html = file.read()
                print(html)
                book_id = match.group(1)
                r.set(f"{book_id}", html)
                print(f"{file} loaded into Redis")

load_dir('./html/books/')