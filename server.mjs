import { createServer } from 'node:http';
import { createReadStream, statSync } from 'node:fs';
import { timingSafeEqual } from 'node:crypto';
import { resolve } from 'node:path';

const root = resolve(process.env.STATIC_ROOT || '/app/public');
const port = Number(process.env.PORT || 8080);
const authDisabled = process.env.DISABLE_AUTH === 'true';
const authUser = process.env.BASIC_AUTH_USER || '';
const authPass = process.env.BASIC_AUTH_PASS || '';

if (!authDisabled && (!authUser || !authPass)) {
  throw new Error('BASIC_AUTH_USER / BASIC_AUTH_PASS が未設定です');
}

const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/narration-bookends.wav', ['narration-bookends.wav', 'audio/wav']],
  ['/robots.txt', ['robots.txt', 'text/plain; charset=utf-8']],
  ['/deck/p01.png', ['deck/p01.png', 'image/png']],
  ['/deck/p06.png', ['deck/p06.png', 'image/png']],
  ['/deck/p13.png', ['deck/p13.png', 'image/png']],
]);

function equal(a, b) {
  const aa = Buffer.from(a), bb = Buffer.from(b);
  return aa.length === bb.length && timingSafeEqual(aa, bb);
}

function authorized(req) {
  if (authDisabled) return true;
  const value = req.headers.authorization || '';
  if (!value.startsWith('Basic ')) return false;
  try {
    const decoded = Buffer.from(value.slice(6), 'base64').toString('utf8');
    const split = decoded.indexOf(':');
    return split >= 0 && equal(decoded.slice(0, split), authUser) && equal(decoded.slice(split + 1), authPass);
  } catch {
    return false;
  }
}

function securityHeaders(res) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");
}

function text(res, status, body) {
  const data = Buffer.from(body);
  res.writeHead(status, {'Content-Type': 'text/plain; charset=utf-8', 'Content-Length': data.length, 'Cache-Control': 'no-store'});
  res.end(data);
}

const server = createServer((req, res) => {
  securityHeaders(res);
  if (req.url === '/healthz') return text(res, 200, 'ok\n');
  if (!authorized(req)) {
    res.setHeader('WWW-Authenticate', 'Basic realm="ASUMO Video", charset="UTF-8"');
    return text(res, 401, '認証が必要です\n');
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') return text(res, 405, 'Method Not Allowed\n');
  let pathname;
  try { pathname = new URL(req.url, 'http://localhost').pathname; }
  catch { return text(res, 400, 'Bad Request\n'); }
  const entry = files.get(pathname);
  if (!entry) return text(res, 404, 'Not Found\n');
  const [relative, contentType] = entry;
  const file = resolve(root, relative);
  const size = statSync(file).size;
  let start = 0, end = size - 1, status = 200;
  const range = req.headers.range;
  if (range) {
    const match = /^bytes=(\d*)-(\d*)$/.exec(range);
    if (!match) {
      res.setHeader('Content-Range', `bytes */${size}`);
      return text(res, 416, 'Range Not Satisfiable\n');
    }
    if (match[1] === '') {
      const suffix = Number(match[2]);
      if (!Number.isInteger(suffix) || suffix <= 0) return text(res, 416, 'Range Not Satisfiable\n');
      start = Math.max(0, size - suffix);
    } else {
      start = Number(match[1]);
      end = match[2] === '' ? size - 1 : Math.min(Number(match[2]), size - 1);
    }
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || start >= size || end < start) {
      res.setHeader('Content-Range', `bytes */${size}`);
      return text(res, 416, 'Range Not Satisfiable\n');
    }
    status = 206;
    res.setHeader('Content-Range', `bytes ${start}-${end}/${size}`);
  }
  res.writeHead(status, {
    'Content-Type': contentType,
    'Content-Length': end - start + 1,
    'Accept-Ranges': 'bytes',
    'Cache-Control': pathname === '/' || pathname === '/index.html' ? 'no-cache' : 'public, max-age=86400',
  });
  if (req.method === 'HEAD') return res.end();
  createReadStream(file, {start, end}).pipe(res);
});

server.listen(port, '0.0.0.0', () => console.log(`ASUMO video server listening on ${port}`));
