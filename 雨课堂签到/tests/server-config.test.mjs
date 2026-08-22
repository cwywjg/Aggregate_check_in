import assert from 'node:assert/strict';
import { getSyncServerUrl, setSyncServerUrl, refreshServerConfigFromRemote, getServerConfigMeta } from '../pages/index/server-config.js';

const storage = new Map();
globalThis.uni = {
	getStorageSync: (key) => storage.get(key) || '',
	setStorageSync: (key, val) => storage.set(key, val),
	request: ({ url, success, fail }) => {
		if (url.includes('raw.gitcode.com')) {
			success({
				statusCode: 200,
				data: {
					server_url: 'http://123.45.67.89:5000',
					updated_at: '2026-08-21T05:00:00Z',
					version: '1.0.1'
				}
			});
		} else if (url.includes('api.gitcode.com')) {
			success({
				statusCode: 200,
				data: {
					encoding: 'base64',
					content: Buffer.from(JSON.stringify({ server_url: 'http://123.45.67.90:5000', version: '1.0.2' })).toString('base64')
				}
			});
		} else {
			fail(new Error('Network offline'));
		}
	}
};

assert.equal(typeof getSyncServerUrl(), 'string');
setSyncServerUrl('http://192.168.1.100:5000/');
assert.equal(getSyncServerUrl(), 'http://192.168.1.100:5000');

const refreshedUrl = await refreshServerConfigFromRemote();
assert.equal(refreshedUrl, 'http://123.45.67.89:5000');
assert.equal(getSyncServerUrl(), 'http://123.45.67.89:5000');
assert.equal(getServerConfigMeta()?.version, '1.0.1');

globalThis.uni.request = ({ fail }) => fail(new Error('All endpoints timeout'));
const fallbackUrl = await refreshServerConfigFromRemote();
assert.equal(fallbackUrl, 'http://123.45.67.89:5000');

console.log('server-config: all 6 assertions passed');
