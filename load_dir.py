import os
import re
import redis
from bs4 import BeautifulSoup

r = redis.StrictRedis(host="localhost", port=6379, db=0)

def load_dir(path):
    files = os.listdir(path)
    print(files)
    for f in files:
        match = re.match(r"^book(\d+).html$", f)
        if match is not None:
            with open(path + f) as file:
                html = file.read()
                book_id = match.group(1)
                r.set(f"book:{book_id}" , html)
                print(f"{file} loaded into Redis")

            
def create_index(book_id, html):
    soup = BeautifulSoup(html,'html.parser')
    ts = soup.get_text().split()
    for t in ts:
        r.sadd(t,book_id)

load_dir("html/books/")