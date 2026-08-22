import { createStore } from 'vuex'
import { get, checkServer, fetchRemoteConfig } from '../api/request'

function safeGetStorageJSON(key, defaultVal) {
	try {
		const val = uni.getStorageSync(key)
		if (!val) return defaultVal
		if (typeof val === 'object') return val
		return JSON.parse(val)
	} catch (e) {
		return defaultVal
	}
}

const store = createStore({
	state() {
		return {
			// 服务器连接
			serverUrl: uni.getStorageSync('serverUrl') || 'http://127.0.0.1:17521',
			apiKey: uni.getStorageSync('apiKey') || 'your-secure-api-key-here',
			serverOnline: false,

			// 账号
			accounts: safeGetStorageJSON('accounts', []),
			masterRef: uni.getStorageSync('masterRef') || '',

			// 本地选中的 ref (openid) 列表
			selectedRefs: (() => {
				const saved = safeGetStorageJSON('selected_refs', null)
				if (Array.isArray(saved)) return saved
				const oldAccs = safeGetStorageJSON('accounts', [])
				if (Array.isArray(oldAccs) && oldAccs.length > 0) {
					return oldAccs.map(a => a && a.ref).filter(Boolean)
				}
				return []
			})(),
			allServerAccounts: [],

			// 答题状态
			quizAccountRef: safeGetStorageJSON('quiz_account_ref', '') || uni.getStorageSync('quiz_account_ref') || '',
			currentCourse: null,
			questionsList: [],
			questionsTotal: 0,
		}
	},

	getters: {
		masterAccount(state) {
			return state.accounts.find(a => a.is_alive && !a.needs_rescan) || state.accounts[0] || null
		},
		quizAccount(state, getters) {
			if (state.quizAccountRef) {
				const found = state.accounts.find(a => a.ref === state.quizAccountRef || a.openid === state.quizAccountRef)
				if (found) return found
			}
			return getters.masterAccount
		},
		subAccounts(state, getters) {
			const master = getters.masterAccount
			if (!master) return state.accounts
			return state.accounts.filter(a => a.ref !== master.ref)
		},
		accountCount(state) {
			return state.accounts.length
		},
		expiredAccounts(state) {
			return state.accounts.filter(a => a.needs_rescan || a.keepalive_status === 'expired')
		},
		hasExpiredAccounts(state, getters) {
			return getters.expiredAccounts.length > 0
		}
	},

	mutations: {
		SET_SERVER(state, { url, apiKey }) {
			state.serverUrl = url
			state.apiKey = apiKey || state.apiKey
			uni.setStorageSync('serverUrl', url)
			if (apiKey) uni.setStorageSync('apiKey', apiKey)
		},

		SET_SERVER_STATUS(state, online) {
			state.serverOnline = online
		},

		SET_ALL_SERVER_ACCOUNTS(state, list) {
			state.allServerAccounts = list
		},

		SET_SELECTED_REFS(state, refs) {
			state.selectedRefs = refs
			uni.setStorageSync('selected_refs', JSON.stringify(refs))
		},

		ADD_SELECTED_REF(state, ref) {
			if (!state.selectedRefs.includes(ref)) {
				state.selectedRefs.push(ref)
				uni.setStorageSync('selected_refs', JSON.stringify(state.selectedRefs))
			}
		},

		REMOVE_SELECTED_REF(state, ref) {
			state.selectedRefs = state.selectedRefs.filter(r => r !== ref)
			uni.setStorageSync('selected_refs', JSON.stringify(state.selectedRefs))
		},

		SET_QUIZ_ACCOUNT_REF(state, ref) {
			state.quizAccountRef = ref
			uni.setStorageSync('quiz_account_ref', ref)
		},

		SET_ACCOUNTS(state, accounts) {
			state.accounts = accounts
			uni.setStorageSync('accounts', JSON.stringify(accounts))
			// 更新 masterRef
			const master = accounts.find(a => a.is_master)
			if (master) {
				state.masterRef = master.ref
				uni.setStorageSync('masterRef', master.ref)
			}
		},

		ADD_ACCOUNT(state, account) {
			const idx = state.accounts.findIndex(a => a.ref === account.ref)
			if (idx >= 0) {
				state.accounts.splice(idx, 1, account)
			} else {
				state.accounts.push(account)
			}
			uni.setStorageSync('accounts', JSON.stringify(state.accounts))
			
			// 新增账号自动放入选中列表
			if (!state.selectedRefs.includes(account.ref)) {
				state.selectedRefs.push(account.ref)
				uni.setStorageSync('selected_refs', JSON.stringify(state.selectedRefs))
			}
		},

		REMOVE_ACCOUNT(state, ref) {
			state.accounts = state.accounts.filter(a => a.ref !== ref)
			uni.setStorageSync('accounts', JSON.stringify(state.accounts))
			state.selectedRefs = state.selectedRefs.filter(r => r !== ref)
			uni.setStorageSync('selected_refs', JSON.stringify(state.selectedRefs))
		},

		UPDATE_ACCOUNT_HEALTH(state, healthList) {
			// 用 health 数据更新现有账号的保活状态
			const healthMap = {}
			for (const h of healthList) {
				healthMap[h.ref] = h
			}
			for (const acc of state.accounts) {
				const h = healthMap[acc.ref]
				if (h) {
					acc.is_alive = h.is_alive
					acc.keepalive_status = h.keepalive_status
					acc.last_keepalive_at = h.last_keepalive_at
					acc.keepalive_fail_count = h.keepalive_fail_count
					acc.needs_rescan = h.needs_rescan
				}
			}
			uni.setStorageSync('accounts', JSON.stringify(state.accounts))
		},

		SET_CURRENT_COURSE(state, course) {
			state.currentCourse = course
		},

		SET_QUESTIONS(state, { questions, total }) {
			state.questionsList = questions
			state.questionsTotal = total
		},

		APPEND_QUESTIONS(state, questions) {
			state.questionsList = [...state.questionsList, ...questions]
		}
	},

	actions: {
		async syncAccounts({ commit, state }) {
			try {
				const data = await get('/api/accounts/sync')
				const serverList = data.accounts || []
				
				commit('SET_ALL_SERVER_ACCOUNTS', serverList)

				let currentSelected = state.selectedRefs || []
				const savedStorage = safeGetStorageJSON('selected_refs', null)
				if (Array.isArray(savedStorage) && savedStorage.length > 0) {
					currentSelected = savedStorage
				} else if (serverList.length > 0) {
					currentSelected = serverList.map(a => a && a.ref).filter(Boolean)
					commit('SET_SELECTED_REFS', currentSelected)
				}

				const cleanSelected = currentSelected.map(r => String(r).trim()).filter(Boolean)
				let localList = serverList.filter(a => a && a.ref && cleanSelected.includes(String(a.ref).trim()))
				if (localList.length === 0 && serverList.length > 0) {
					localList = serverList
				}
				commit('SET_ACCOUNTS', localList)
				return localList
			} catch (e) {
				console.error('Sync accounts failed:', e)
				throw e
			}
		},

		async checkAccountHealth({ commit, state }) {
			try {
				const data = await get('/api/accounts/health')
				const healthList = data.accounts || []
				commit('UPDATE_ACCOUNT_HEALTH', healthList)

				// 仅检查本地已选中且失效的账号
				const expired = state.accounts.filter(a => a.needs_rescan)
				if (expired.length > 0) {
					const names = expired.map(e => e.ref.substring(0, 8) + '...').join(', ')
					return { hasExpired: true, expiredNames: names }
				}
				return { hasExpired: false }
			} catch (e) {
				console.error('Check account health failed:', e)
				return { hasExpired: false }
			}
		},

		async checkServerHealth({ commit, state }) {
			try {
				const ok = await checkServer(state.serverUrl)
				commit('SET_SERVER_STATUS', ok)
				return ok
			} catch {
				commit('SET_SERVER_STATUS', false)
				return false
			}
		},

		async loadRemoteConfig({ commit, state }) {
			try {
				const config = await fetchRemoteConfig()
				if (config && config.serverUrl) {
					commit('SET_SERVER', { url: config.serverUrl, apiKey: config.apiKey })
					const ok = await checkServer(config.serverUrl)
					commit('SET_SERVER_STATUS', ok)
					return config
				}
			} catch (e) {
				console.warn('[Store] loadRemoteConfig error:', e)
			}
			return null
		}
	}
})

export default store

