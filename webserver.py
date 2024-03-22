from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import re
from http.cookies import SimpleCookie
import uuid
import redis
import os
import random
r = redis.StrictRedis(host='localhost', port=6379, db=0)

# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html
mappings ={
        (r"^/books/(?P<book_id>\d+)$", "get_book"),
        (r"^/$", "index"),
        }


class WebRequestHandler(BaseHTTPRequestHandler):
    
    @cached_property
    def cookies(self):
        return SimpleCookie(self.headers.get("Cookie"))
    
    def get_session(self):
        cookies = self.cookies
        session_id = None
        if not cookies:
            session_id = uuid.uuid4()
        else:
            session_id = cookies["session_id"].value
        return session_id
    
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie()
        cookies["session_id"] = session_id
        cookies["session_id"]["max-age"] = 1000
        self.send_header("Set-Cookie", cookies.output(header=""))
    
    @cached_property
    def url(self):
        return urlparse(self.path)

    @cached_property
    def query_data(self):
        return dict(parse_qsl(self.url.query))

    @cached_property
    def post_data(self):
        content_length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_length)

    @cached_property
    def form_data(self):
        return dict(parse_qsl(self.post_data.decode("utf-8")))

    def get_params(self, pattern, path):
        match=re.match(pattern, path)
        if match:
          return match.groupdict()
        

    def url_mapping_response(self):
        for pattern, method in mappings:
            match = self.get_params(pattern, self.path)
            print(match)
            if match is not None:
                md = getattr(self, method)
                md(**match)
                return
        
        self.send_response(404)
        self.end_headers()
        self.wfile.write("Not Found".encode("utf-8"))
        
    def index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        with open('html/index.html') as f:
            response = f.read()
        self.wfile.write(response.encode("utf-8"))
        
    def get_book(self,book_id):
        bookKey = f"{book_id}"
        session_id =self.get_session()
        book_recomendation = self.get_book_recomendation(session_id, book_id)
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        self.end_headers()
        
        book_info = r.get(bookKey) or "<h1> No existe el libro </h1>".encode("utf-8")
        book_info_with_recommendation = book_info + f"<p>Recomendación: {book_recomendation}</p>".encode("utf-8")
    
        self.wfile.write(book_info_with_recommendation)
        #self.wfile.write(book_info)
        book_list = r.lrange(f"session: {session_id}", 0, -1)
       
        if bookKey.encode('utf-8') not in book_list:
            r.lpush(f"session: {session_id}", bookKey)
    
    def get_book_recomendation(self, session_id, book_id):
        session_id_str = str(session_id)  # Convertir UUID a cadena
        r.rpush(f"session: {session_id_str}", book_id)  # cadena convertida
        books = r.lrange(f"session: {session_id_str}", 0, 5)  # cadena convertida
        while True:
            random_number = random.randint(1, 4)
            if random_number != int(book_id):
                return random_number

    
    def do_GET(self):
       self.url_mapping_response()
    
             
    def get_response(self):
        return f"""
    <h1> Hola Web </h1>
    <p>  {self.path}         </p>
    <p>  {self.headers}      </p>
    <p>  {self.cookies}      </p>
    <p>  {self.query_data}   </p>

"""
if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()
