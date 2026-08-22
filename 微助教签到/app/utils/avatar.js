/**
 * 账号头像本地持久化缓存工具
 * 逻辑：仅从网络/后端拉取一次头像，成功后自动固化到手机本地持久存储中，
 * 之后所有展示直接使用本地文件/缓存，秒级呈现且不消耗网络请求。
 */

const avatarMemoryMap = {}
const downloadingRefs = new Set()

export function getCachedAvatar(ref, serverUrl, fallbackAvatarUrl) {
	if (!ref) return '/static/avatar_default.png'

	// 1. 内存运行时缓存
	if (avatarMemoryMap[ref]) {
		return avatarMemoryMap[ref]
	}

	// 2. 本地 LocalStorage 持久缓存
	try {
		const localSavedPath = uni.getStorageSync('avatar_cache_' + ref)
		if (localSavedPath) {
			avatarMemoryMap[ref] = localSavedPath
			return localSavedPath
		}
	} catch (e) {
		console.warn('[AvatarCache] read storage failed:', e)
	}

	// 3. 构建远端 URL
	let remoteUrl = fallbackAvatarUrl
	if (!remoteUrl || !remoteUrl.startsWith('http')) {
		const base = (serverUrl || '').replace(/\/+$/, '')
		const path = (fallbackAvatarUrl || `/api/accounts/${encodeURIComponent(ref)}/avatar`).replace(/^\/+/, '')
		remoteUrl = base ? `${base}/${path}` : `/${path}`
	}

	// 4. 触发异步下载并固化到本地（防重复并发下载）
	if (!downloadingRefs.has(ref) && remoteUrl.startsWith('http')) {
		downloadingRefs.add(ref)
		downloadAndSaveAvatar(ref, remoteUrl)
	}

	return remoteUrl
}

function downloadAndSaveAvatar(ref, url) {
	uni.downloadFile({
		url: url,
		timeout: 10000,
		success: (res) => {
			if (res.statusCode === 200 && res.tempFilePath) {
				// #ifdef APP-PLUS
				uni.saveFile({
					tempFilePath: res.tempFilePath,
					success: (saveRes) => {
						const permanentPath = saveRes.savedFilePath
						avatarMemoryMap[ref] = permanentPath
						uni.setStorageSync('avatar_cache_' + ref, permanentPath)
						downloadingRefs.delete(ref)
					},
					fail: () => {
						avatarMemoryMap[ref] = res.tempFilePath
						uni.setStorageSync('avatar_cache_' + ref, res.tempFilePath)
						downloadingRefs.delete(ref)
					}
				})
				// #endif

				// #ifndef APP-PLUS
				avatarMemoryMap[ref] = res.tempFilePath
				uni.setStorageSync('avatar_cache_' + ref, res.tempFilePath)
				downloadingRefs.delete(ref)
				// #endif
			} else {
				downloadingRefs.delete(ref)
			}
		},
		fail: () => {
			downloadingRefs.delete(ref)
		}
	})
}

export function clearAvatarCache(ref) {
	if (ref) {
		delete avatarMemoryMap[ref]
		uni.removeStorageSync('avatar_cache_' + ref)
	}
}
