const https = require('https');

function probe() {
  const options = {
    host: 'api.grok.ai',
    port: 443,
    path: '/v1/chat/completions',
    method: 'OPTIONS',
    servername: 'api.grok.ai',
    ALPNProtocols: ['h2', 'http/1.1'],
    headers: { 'User-Agent': 'probe/1.0' }
  };

  const req = https.request(options, (res) => {
    console.log('statusCode', res.statusCode);
    console.log('alpnProtocol', res.socket.alpnProtocol);
    res.on('data', (d) => process.stdout.write(d));
  });

  req.on('error', (e) => {
    console.error('error', e && e.message ? e.message : e);
  });
  req.end();
}

probe();
