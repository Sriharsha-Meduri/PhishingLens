const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade'
]);

const normalizeBase = (value = '') => value.replace(/\/$/, '');

export default async function handler(req, res) {
  const base = normalizeBase(process.env.PHISHING_API_BASE_URL || process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://157.245.106.241');
  const pathSegments = req.query.path;
  const targetPath = Array.isArray(pathSegments) ? pathSegments.join('/') : pathSegments || '';
  const query = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
  const targetUrl = `${base}/${targetPath}${query}`;

  const method = req.method || 'GET';
  const headers = Object.fromEntries(
    Object.entries(req.headers)
      .filter(([key]) => key && !HOP_BY_HOP_HEADERS.has(key.toLowerCase()))
      .map(([key, value]) => [key, value])
  );

  let body;
  if (!['GET', 'HEAD'].includes(method)) {
    if (Buffer.isBuffer(req.body) || typeof req.body === 'string') {
      body = req.body;
    } else if (req.body && typeof req.body === 'object') {
      body = JSON.stringify(req.body);
      headers['content-type'] = headers['content-type'] || 'application/json';
    }
  }

  let response;
  try {
    response = await fetch(targetUrl, {
      method,
      headers,
      body
    });
  } catch (error) {
    console.error('Proxy request failed', error);
    res.status(502).json({ message: 'Upstream analysis service unreachable.' });
    return;
  }

  const buffer = Buffer.from(await response.arrayBuffer());
  res.status(response.status);
  response.headers.forEach((value, key) => {
    if (key === 'content-length') return;
    res.setHeader(key, value);
  });
  res.setHeader('content-length', buffer.length);
  res.send(buffer);
}
