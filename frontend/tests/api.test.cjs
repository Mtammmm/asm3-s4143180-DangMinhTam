const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function client(fetch) {
  const window = { CSV_INSIGHT_API_URL: 'http://localhost:8080' };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../api.js'), 'utf8'), {
    window, fetch, FormData,
    localStorage: { getItem: () => 'test-token' }, sessionStorage: { getItem: () => null }
  });
  return window;
}

test('S3 uploads send signed POST fields and file without a bearer token or JSON header', async () => {
  const calls = [];
  const app = client(async (url, options) => {
    calls.push({ url, options });
    if (calls.length === 1) return { ok: true, status: 201, json: async () => ({
      dataset: { id: 'one', status: 'uploading' },
      upload: { url: 'https://bucket.example', method: 'POST', fields: { key: 'source.csv', policy: 'signed-policy' } }
    }) };
    return { ok: true, status: 204 };
  });
  await app.DatasetApi.createDataset({ name: 'data.csv', size: 4, file: new Blob(['x\n1\n']) });
  const upload = calls[1].options;
  assert.equal(upload.method, 'POST');
  assert.equal(upload.body.get('key'), 'source.csv');
  assert.equal(upload.body.get('policy'), 'signed-policy');
  assert.equal(await upload.body.get('file').text(), 'x\n1\n');
  assert.equal(upload.headers.Authorization, undefined);
  assert.equal(upload.headers['Content-Type'], undefined);
});

test('local uploads authenticate and return the processed dataset', async () => {
  const calls = [];
  const app = client(async (url, options) => {
    calls.push({ url, options });
    if (calls.length === 1) return { ok: true, status: 201, json: async () => ({
      dataset: { id: 'one', status: 'uploading' },
      upload: { url: 'http://localhost:8080/datasets/one/content', method: 'PUT', authenticated: true }
    }) };
    return { ok: true, status: 200, json: async () => ({ id: 'one', status: 'ready' }) };
  });
  const result = await app.DatasetApi.createDataset({ name: 'data.csv', size: 4, file: new Blob(['x\n1\n']) });
  assert.equal(result.status, 'ready');
  assert.equal(calls[1].options.headers.Authorization, 'Bearer test-token');
  assert.equal(calls[1].options.headers['Content-Type'], 'text/csv');
});

test('password reset sends the recovery code and new password to the API', async () => {
  let sent;
  const app = client(async (url, options) => {
    sent = { url, options };
    return { ok: true, status: 200, json: async () => ({ message: 'Password reset.' }) };
  });
  await app.AuthApi.resetPassword('user@example.com', 'code', 'new-password');
  assert.equal(sent.url, 'http://localhost:8080/auth/reset-password');
  assert.deepEqual(JSON.parse(sent.options.body), { email: 'user@example.com', resetToken: 'code', newPassword: 'new-password' });
});

test('local configuration selects localhost and respects an explicit override', () => {
  const code = fs.readFileSync(path.join(__dirname, '../config.js'), 'utf8');
  const window = { location: { hostname: 'localhost' } };
  vm.runInNewContext(code, { window });
  assert.equal(window.CSV_INSIGHT_API_URL, 'http://localhost:8080');
  window.CSV_INSIGHT_API_URL = 'https://custom.example';
  vm.runInNewContext(code, { window });
  assert.equal(window.CSV_INSIGHT_API_URL, 'https://custom.example');
});
