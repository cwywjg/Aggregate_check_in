/**
 * 统一 HTTP 请求与远端动态配置拉取模块
 * =============================================================
 * 特性：
 * 1. 自动注入 X-API-Key 鉴权请求头
 * 2. 多源并发并行竞速（Racing Mode）拉取远端配置，0.1s 极速自愈
 * 3. 统一错误处理与文件上传封装
 */

// 远端动态配置备用镜像源列表（支持 GitCode / AtomGit / 自建 Raw 镜像）
export const REMOTE_CONFIG_URLS = [
	'https://raw.gitcode.com/your-org/helper-config/raw/main/config.json',
	'https://raw.atomgit.com/your-org/helper-config/raw/main/config.json'
]

/**
 * 多源并发竞速拉取最新远端服务器配置
 */
export const fetchRemoteConfig = () => {
	return new Promise((resolve) => {
		let isResolved = false
		let pendingCount = REMOTE_CONFIG_URLS.length

		const checkAndResolve = (result, sourceUrl) => {
			if (isResolved) return
			if (result && result.serverUrl) {
				isResolved = true
				uni.setStorageSync('serverUrl', result.serverUrl)
				if (result.apiKey) uni.setStorageSync('apiKey', result.apiKey)
				resolve(result)
			} else {
				pendingCount--
				if (pendingCount <= 0 && !isResolved) {
					isResolved = true
					resolve(null)
				}
			}
		}

		// 全源并发并行竞速，哪个最快返回哪个立即生效（0.1s 极速）
		REMOTE_CONFIG_URLS.forEach((rawUrl) => {
			const fetchUrl = rawUrl + (rawUrl.includes('?') ? '&' : '?') + '_t=' + Date.now()
			uni.request({
				url: fetchUrl,
				method: 'GET',
				timeout: 4000,
				success: (res) => {
					if (res.statusCode === 200 && res.data) {
						let data = res.data
						if (typeof data === 'string') {
							try {
								// 排除 HTML 页面错误返回
								if (data.trim().startsWith('<')) {
									checkAndResolve(null, rawUrl)
									return
								}
								data = JSON.parse(data)
							} catch (e) {
								checkAndResolve(null, rawUrl)
								return
							}
						}
						if (data && typeof data === 'object') {
							const serverUrl = (data.serverUrl || data.server_url || data.api_url || data.host || '').trim().replace(/\/+$/, '')
							const apiKey = data.apiKey || data.api_key || data.key
							if (serverUrl) {
								checkAndResolve({ serverUrl, apiKey, data }, rawUrl)
								return
							}
						}
					}
					checkAndResolve(null, rawUrl)
				},
				fail: () => {
					checkAndResolve(null, rawUrl)
				}
			})
		})

		// 4 秒兜底超时
		setTimeout(() => {
			if (!isResolved) {
				isResolved = true
				resolve(null)
			}
		}, 4000)
	})
}

export const getBaseUrl = () => {
	const url = uni.getStorageSync('serverUrl') || 'http://127.0.0.1:17521'
	return url.trim().replace(/\/+$/, '')
}

export const getApiKey = () => {
	return uni.getStorageSync('apiKey') || 'your-secure-api-key-here'
}

const request = (options) => {
	return new Promise((resolve, reject) => {
		const baseUrl = getBaseUrl()
		if (!baseUrl && !options.skipBaseCheck) {
			reject(new Error('请先配置服务器地址'))
			return
		}

		uni.request({
			url: baseUrl + options.url,
			method: options.method || 'GET',
			data: options.data,
			header: {
				'Content-Type': options.contentType || 'application/json',
				'X-API-Key': getApiKey(),
				...options.header
			},
			timeout: options.timeout || 15000,
			success: (res) => {
				if (res.statusCode >= 200 && res.statusCode < 300) {
					resolve(res.data)
				} else if (res.statusCode === 403) {
					uni.showToast({ title: 'API Key 无效', icon: 'none' })
					reject(new Error('API Key 无效'))
				} else {
					reject(new Error(res.data?.detail || res.data?.message || `请求失败 ${res.statusCode}`))
				}
			},
			fail: (err) => {
				reject(new Error(err.errMsg || '网络连接失败'))
			}
		})
	})
}

// 快捷请求方法
export const get = (url, data, options = {}) => request({ url, method: 'GET', data, ...options })
export const post = (url, data, options = {}) => request({ url, method: 'POST', data, ...options })
export const put = (url, data, options = {}) => request({ url, method: 'PUT', data, ...options })
export const del = (url, data, options = {}) => request({ url, method: 'DELETE', data, ...options })

// 文件上传封装
export const uploadFile = (url, filePath, name = 'file', formData = {}) => {
	return new Promise((resolve, reject) => {
		const baseUrl = getBaseUrl()
		uni.uploadFile({
			url: baseUrl + url,
			filePath,
			name,
			formData,
			header: { 'X-API-Key': getApiKey() },
			success: (res) => {
				if (res.statusCode === 200) {
					resolve(JSON.parse(res.data))
				} else {
					reject(new Error(`上传失败 ${res.statusCode}`))
				}
			},
			fail: (err) => reject(new Error(err.errMsg || '上传失败'))
		})
	})
}

// 服务器健康连通性检查
export const checkServer = async (url) => {
	return new Promise((resolve) => {
		uni.request({
			url: url + '/health',
			method: 'GET',
			timeout: 5000,
			success: (res) => resolve(res.statusCode === 200 && res.data?.ok === true),
			fail: () => resolve(false)
		})
	})
}

export default request
