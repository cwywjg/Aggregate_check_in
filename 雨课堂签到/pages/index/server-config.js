/**
 * 远程服务器配置中心 (GitCode 分发)
 * 允许在不重新打包 App 的情况下随时通过 GitCode 变更服务器 IP / 域名
 */

const DEFAULT_SERVER_URL = 'http://43.133.67.180:5000';
const STORAGE_KEY_SERVER_URL = 'cached_server_config_url';
const STORAGE_KEY_SERVER_META = 'cached_server_config_meta';

// GitCode 多节点远程源（多重兜底防单点故障）
const REMOTE_CONFIG_ENDPOINTS = [
	'https://raw.gitcode.com/2501_94257442/yuketang/raw/main/server_config.json',
	'https://raw.gitcode.com/2501_94257442/yuketang/raw/master/server_config.json',
	'https://api.gitcode.com/api/v5/repos/2501_94257442/yuketang/contents/server_config.json'
];

let runtimeServerUrl = '';

export function getSyncServerUrl() {
	if (runtimeServerUrl) return runtimeServerUrl;
	try {
		const cached = (typeof uni !== 'undefined' && typeof uni.getStorageSync === 'function')
			? uni.getStorageSync(STORAGE_KEY_SERVER_URL)
			: '';
		if (cached && typeof cached === 'string') {
			runtimeServerUrl = cached.trim().replace(/\/+$/, '');
			return runtimeServerUrl;
		}
	} catch (_) {}
	return DEFAULT_SERVER_URL;
}

export function setSyncServerUrl(url) {
	if (!url || typeof url !== 'string') return;
	const cleanUrl = url.trim().replace(/\/+$/, '');
	runtimeServerUrl = cleanUrl;
	try {
		if (typeof uni !== 'undefined' && typeof uni.setStorageSync === 'function') {
			uni.setStorageSync(STORAGE_KEY_SERVER_URL, cleanUrl);
		}
	} catch (e) {
		console.warn('Failed to cache server url', e);
	}
}

export function getServerConfigMeta() {
	try {
		if (typeof uni !== 'undefined' && typeof uni.getStorageSync === 'function') {
			const metaStr = uni.getStorageSync(STORAGE_KEY_SERVER_META);
			if (metaStr) return JSON.parse(metaStr);
		}
	} catch (_) {}
	return null;
}

function decodeBase64Utf8(base64Str) {
	try {
		const clean = String(base64Str || '').replace(/\s+/g, '');
		if (typeof Buffer !== 'undefined') {
			return Buffer.from(clean, 'base64').toString('utf8');
		}
		if (typeof atob === 'function') {
			const binary = atob(clean);
			const bytes = new Uint8Array(binary.length);
			for (let i = 0; i < binary.length; i++) {
				bytes[i] = binary.charCodeAt(i);
			}
			if (typeof TextDecoder !== 'undefined') {
				return new TextDecoder('utf-8').decode(bytes);
			}
			return decodeURIComponent(escape(binary));
		}
	} catch (e) {
		console.warn('Base64 decode failed', e);
	}
	return '';
}

function parseConfigPayload(data) {
	if (!data) return null;
	let obj = data;
	if (typeof obj === 'string') {
		try {
			obj = JSON.parse(obj);
		} catch (_) {}
	}
	if (obj && typeof obj === 'object') {
		if (obj.encoding === 'base64' && typeof obj.content === 'string') {
			const decoded = decodeBase64Utf8(obj.content);
			if (decoded) {
				try {
					return JSON.parse(decoded);
				} catch (_) {}
			}
		}
		if (obj.server_url || obj.serverUrl || obj.url || obj.api_url) {
			return obj;
		}
	}
	return null;
}

/**
 * 每次 App 打开时默认从 GitCode 拉取一次最新服务器配置
 * 若请求超时或失败，则自动降级使用本地缓存配置
 */
export async function refreshServerConfigFromRemote() {
	for (const endpoint of REMOTE_CONFIG_ENDPOINTS) {
		try {
			const rawData = await new Promise((resolve, reject) => {
				if (typeof uni !== 'undefined' && typeof uni.request === 'function') {
					uni.request({
						url: `${endpoint}?_t=${Date.now()}`,
						method: 'GET',
						timeout: 6000,
						dataType: 'json',
						success: (resp) => {
							if (resp.statusCode >= 200 && resp.statusCode < 300 && resp.data) {
								resolve(resp.data);
							} else {
								reject(new Error(`HTTP ${resp.statusCode}`));
							}
						},
						fail: (err) => reject(err)
					});
				} else {
					reject(new Error('uni.request not available'));
				}
			});

			const config = parseConfigPayload(rawData);
			if (config && typeof config === 'object') {
				const remoteUrl = config.server_url || config.serverUrl || config.url || config.api_url;
				if (remoteUrl && typeof remoteUrl === 'string' && (remoteUrl.startsWith('http://') || remoteUrl.startsWith('https://'))) {
					setSyncServerUrl(remoteUrl);
					try {
						if (typeof uni !== 'undefined' && typeof uni.setStorageSync === 'function') {
							uni.setStorageSync(STORAGE_KEY_SERVER_META, JSON.stringify(config));
						}
					} catch (_) {}
					console.log(`[动态配置] 已成功从 GitCode 拉取最新服务器地址: ${getSyncServerUrl()}`);
					return getSyncServerUrl();
				}
			}
		} catch (err) {
			console.warn(`[动态配置] 从 ${endpoint} 拉取配置失败: ${err?.message || err}`);
		}
	}
	console.log(`[动态配置] 远程请求未就绪或离线，继续使用本地缓存地址: ${getSyncServerUrl()}`);
	return getSyncServerUrl();
}
