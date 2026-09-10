"""ローカル確認専用。音声シーク用の HTTP Range 対応。"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import mimetypes, re, sys
ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def end_headers(self):
        self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store');super().end_headers()
    def send_head(self):
        self.remaining=None
        path=Path(self.translate_path(self.path))
        try:path.resolve().relative_to(ROOT)
        except ValueError:self.send_error(403);return None
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',self.headers.get('Range',''))
        if not match or not path.is_file():return super().send_head()
        size=path.stat().st_size;a,b=match.groups()
        start=int(a) if a else max(0,size-int(b or 0))
        end=min(int(b) if a and b else size-1,size-1)
        if start>end:
            self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return None
        self.remaining=end-start+1
        self.send_response(206);self.send_header('Content-Type',mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.send_header('Content-Length',str(self.remaining));self.end_headers()
        f=path.open('rb');f.seek(start);return f
    def copyfile(self,source,output):
        if self.remaining is None:return super().copyfile(source,output)
        while self.remaining:
            buf=source.read(min(65536,self.remaining))
            if not buf:break
            output.write(buf);self.remaining-=len(buf)
    def log_message(self,*args):pass
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',int(sys.argv[1]) if len(sys.argv)>1 else 4322),Handler).serve_forever()
