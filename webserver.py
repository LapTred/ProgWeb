from functools import cached_property
import re
import redis
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import random
from bs4 import BeautifulSoup
import json

mappings = [
    (r"^/book/(?P<book_id>\d+)$", "get_book"),
    (r"^/books/(?P<book_id>\d+)$", "get_book"),
    (r"^/$", "index"),
    (r"^/search", "search"),
]

r = redis.StrictRedis(host="localhost", port=6379, db=0)

class WebRequestHandler(BaseHTTPRequestHandler):
    
    def search(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        
        query = self.query_data.get('q', '')
        index_page = f"<h>q: {query.split()}</h1>".encode("utf-8")
        self.wfile.write(index_page)
    
        with open('html/index.html') as f:
            html_content = f.read()
    
        soup = BeautifulSoup(html_content, 'html.parser')
        h2_elements = soup.find_all('h2')
    
        matching_books = []
        for h2_element in h2_elements:
            a_element = h2_element.find('a')
            if a_element:
                title = a_element.text.lower()
                link = a_element['href']
                if query.lower() in title:
                    matching_books.append(f"<a href='{link}'>{title}</a>")
    
        if matching_books:
            response_content = "<h1>Libros encontrados:</h1>"
            response_content += "<ul>"
            response_content += "".join([f"<li>{book}</li>" for book in matching_books])
            response_content += "</ul>"
        else:
            response_content = "<p>No se encontraron libros que coincidan con la búsqueda.</p>"
    
        self.wfile.write(response_content.encode('utf-8'))
        
    def get_session(self):
        cookies = self.cookies
        session_id = None
        if 'session_id' not in cookies:
            session_id = str(uuid.uuid4())
        else:
            session_id = cookies['session_id'].value
        return session_id

    def write_session_cookie(self, session_id):
        cookies = SimpleCookie()
        cookies['session_id'] = str(session_id)
        cookies['session_id']['max-age'] = 1000
        self.send_header('Set-Cookie', cookies.output(header=''))

    @property
    def cookies(self):
        return SimpleCookie(self.headers.get('Cookie', ''))
        
    @property
    def query_data(self):
        return dict(parse_qsl(self.url.query))
        
    @property
    def url(self):
        return urlparse(self.path)

    def do_GET(self):
        self.url_mapping_response()

    def get_params(self, pattern, path):
        match = re.match(pattern, path)
        if match:
            return match.groupdict()

    def url_mapping_response(self):
        for (pattern, method) in mappings:
            match = self.get_params(pattern, self.path)
            if match is not None:
                md = getattr(self, method)
                md(**match)
                return

        self.send_response(404)
        self.end_headers()
        self.wfile.write('Not Found'.encode('utf-8'))

    def index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        
        index_page = """
        <CENTER><h1>¡Bienvenidos a los libros!</h1>
            <form action="/search" method="GET">
                <label for="q">Search</label>
                <input type ="text" name="q"/>
                <input type ="submit" value="Buscar libros">
            </form>
        </CENTER>
        """.encode("utf-8")
        self.wfile.write(index_page)
        self.wfile.write(self.show_all_books().encode("utf-8"))

    def get_book(self, book_id):
        session_id = self.get_session()
        book_recommend = self.recommend_book(session_id, book_id)
        r.lpush(f'session:{session_id}', f'book:{book_id}')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.write_session_cookie(session_id)
        self.end_headers()
        book_info = r.get(f'book:{book_id}')
        self.wfile.write(f'Book ID: {book_id}\n'.encode('utf-8'))
        
        if book_info is not None:
            self.wfile.write(f'Book Info: {book_info.decode("utf-8")}\n'.encode('utf-8'))
        else:
            self.wfile.write(f"""<h1>No existe libro</h1>
             <p>  Recomendacion: Libro {book_recommend}</p>\n""".encode('utf-8'))
            
        book_list = r.lrange(f'session:{session_id}', 0, -1)
        for book in book_list:
            self.wfile.write(f'Book: {book.decode("utf-8")}\n'.encode('utf-8'))
    
    def show_all_books(self):
        self.end_headers()
        with open('html/index.html') as f:
            response = f.read()
        self.wfile.write(response.encode("utf-8"))
    
    def recommend_book(self, session_id, book_id):
        r.rpush(session_id, book_id)
        books = r.lrange(session_id, 0, 7)
        all_books = set(str(i+1) for i in range(6))
        new = [b for b in all_books if b not in [vb.decode() for vb in books]]
        if new:
            return self.get_book_link(new[0])
        else:
            return self.get_book_link(random.choice([vb.decode() for vb in books]))

    def get_book_link(self, book_id):
        return f"<a href='/book/{book_id}'>Libro {book_id}</a>"
        
if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()
