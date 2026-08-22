<template>
	<view class="container">
		<!-- Hero Section -->
		<view class="hero">
			<view class="hero-bg-decoration"></view>
			<view class="hero-content">
				<view class="hero-title-wrap">
					<text class="hero-title">微助教多协议签到</text>
					<view class="hero-badge">AI 守护</view>
				</view>
				<view class="title-underline"></view>
				<view class="subtitle-wrapper">
					<text class="hero-subtitle">普通 · GPS 定位 · WSS 动态扫码 · 全自动并发引擎</text>
				</view>
			</view>
		</view>

		<view class="content-wrapper">
			<!-- 1. 全自动签到守护总开关卡片 -->
			<view class="daemon-card" :class="{ 'daemon-active': autoDaemonEnabled }">
				<view class="daemon-header">
					<view class="daemon-title-row">
						<view class="daemon-dot" :class="{ 'dot-pulsing': autoDaemonEnabled }"></view>
						<text class="daemon-title">全自动签到守护引擎</text>
					</view>
					<switch :checked="autoDaemonEnabled" @change="toggleAutoDaemon" color="#34C759" style="transform: scale(0.85);" />
				</view>
				<text class="daemon-desc">
					{{ autoDaemonEnabled 
						? '🟢 守护中：后台每 5 秒探测一次，检测到签到自动执行对应模式打卡；打卡完成后将直接停止探测。' 
						: '⚪ 未开启：打开后将自动探测签到事件并自动判型打卡（普通/GPS/二维码）。' }}
				</text>
				<view class="daemon-actions" v-if="!autoDaemonEnabled">
					<view class="daemon-btn" @click="runSingleDetect(false)">
						<text class="daemon-btn-text">🔍 立即探测一次活跃签到</text>
					</view>
				</view>
			</view>

			<!-- 2. 核心状态与选定终端看板 -->
			<view class="dashboard">
				<view class="dash-item dark-bg">
					<text class="dash-val">{{ selectedRefs.length }} / {{ accounts.length }}</text>
					<text class="dash-lbl">选定签到终端数</text>
				</view>
				<view class="dash-item accent-bg" :class="{ 'dash-disabled': signinState === 'submitting' }" @click="startBatchScan">
					<view class="scan-title">{{ signinState === 'submitting' ? '正在执行…' : '📷 立即扫码签到' }}</view>
					<text class="dash-lbl">{{ prepareLabel }}</text>
				</view>
			</view>

			<!-- 3. 快捷签到模式操作面板 -->
			<view class="card">
				<view class="card-header">
					<view class="card-title-box">
						<text class="card-title">独立模式快速触发</text>
						<text class="card-subtitle">若不需要全自动守护，可在此针对单模式手动批量执行</text>
					</view>
				</view>

				<view class="mode-grid">
					<!-- 普通一键签到 -->
					<view class="mode-btn normal-btn" @click="startNormalSignin">
						<text class="mode-icon">📝</text>
						<view class="mode-texts">
							<text class="mode-main">普通一键签到</text>
							<text class="mode-sub">无定位与二维码活动</text>
						</view>
					</view>

					<!-- WSS 动态码实时监听 -->
					<view class="mode-btn wss-btn" @click="startWssQrSignin">
						<text class="mode-icon">⚡</text>
						<view class="mode-texts">
							<text class="mode-main">WSS 动态监听</text>
							<text class="mode-sub">长连接秒级截获打卡</text>
						</view>
					</view>
				</view>
			</view>

			<!-- 4. GPS 定位签到配置卡片 -->
			<view class="card">
				<view class="card-header">
					<view class="card-title-box">
						<text class="card-title">📍 GPS 定位签到配置</text>
						<text class="card-subtitle">内置高精度防风控物理微扰动 (±5~10m)</text>
					</view>
					<view class="card-actions">
						<view class="pill-btn primary" @click="fetchCurrentLocation">
							<text>📍 一键获取当前定位</text>
						</view>
					</view>
				</view>

				<view class="gps-config-box">
					<view class="gps-input-row">
						<view class="gps-field">
							<text class="gps-label">纬度 (Latitude)</text>
							<input class="gps-input" type="digit" v-model="baseLat" placeholder="如 39.18252" @blur="saveGpsCoords" />
						</view>
						<view class="gps-field">
							<text class="gps-label">经度 (Longitude)</text>
							<input class="gps-input" type="digit" v-model="baseLon" placeholder="如 117.11943" @blur="saveGpsCoords" />
						</view>
					</view>

					<view class="gps-submit-btn" @click="startGpsSignin">
						<text class="gps-submit-text">🚀 立即执行 GPS 批量签到</text>
					</view>
				</view>
			</view>

			<!-- 5. 账号选择列表 -->
			<view class="card">
				<view class="card-header">
					<view class="card-title-box">
						<text class="card-title">选择参与签到账号</text>
						<text class="card-subtitle">支持高并发多账号独立互斥打卡</text>
					</view>
					<view class="card-actions">
						<view class="pill-btn primary" @click="toggleAll">
							<text>{{ allSelected ? '取消全选' : '全选' }}</text>
						</view>
					</view>
				</view>

				<view class="accounts-list">
					<view v-for="acc in accounts" :key="acc.ref"
						class="account-row" @tap="toggleAccount(acc.ref)">
						<view class="check-box" :class="{ checked: selectedRefs.includes(acc.ref) }">
							<text v-if="selectedRefs.includes(acc.ref)" class="check-icon">✓</text>
						</view>
						<image class="row-avatar" :src="getAvatarUrl(acc)" mode="aspectFill"></image>
						<view class="row-info">
							<text class="row-name">{{ acc.nickname || '未命名' }}</text>
							<text class="row-status" :class="acc.is_alive ? 'text-success' : 'text-danger'">
								{{ acc.is_alive ? '在线' : '离线' }}
							</text>
						</view>
						<view v-if="acc.is_master" class="master-tag">
							<text class="master-tag-text">主</text>
						</view>
					</view>
					
					<view v-if="accounts.length === 0" class="empty-zone">
						<text class="empty-emoji">👥</text>
						<text class="empty-hint">暂无账号，请先在首页添加</text>
					</view>
				</view>
			</view>
		</view>

		<!-- Shell Terminal Log Dialog -->
		<view class="blur-mask" :class="{ 'mask-active': showProgressDialog }">
			<view class="shell-modal" v-if="showProgressDialog">
				<view class="shell-header">
					<view class="mac-dots">
						<view class="dot red" @click="closeProgressDialog"></view>
						<view class="dot yellow"></view>
						<view class="dot green"></view>
					</view>
					<text class="shell-title">微助教高并发签到控制台</text>
				</view>
				<view class="shell-body">
					<view class="shell-status-row">
						<view v-if="!isProgressFinished" class="terminal-spinner"></view>
						<text class="shell-status">> Status: {{ progressMsg }}</text>
					</view>
					<scroll-view scroll-y class="shell-logs" :scroll-top="scrollTop">
						<view class="log-line" v-for="(log, idx) in runLogs" :key="idx">
							<text class="log-time">[{{ log.time }}]</text>
							<text class="log-text" :class="log.success ? 'log-good' : 'log-bad'">{{ log.text }}</text>
						</view>
					</scroll-view>
				</view>
				<view class="shell-footer" v-if="isProgressFinished">
					<button class="shell-btn" @click="closeProgressDialog">关闭控制台</button>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { post, get } from '../../api/request'

export default {
	data() {
		return {
			selectedRefs: [],
			showProgressDialog: false,
			isProgressFinished: false,
			progressMsg: '',
			runLogs: [],
			scrollTop: 0,
			signinState: 'idle',
			prepareState: 'idle',
			prepareTimer: null,

			// 全自动签到守护状态
			autoDaemonEnabled: false,
			daemonTimer: null,
			isDetecting: false,

			// GPS 坐标配置（默认天津商业大学）
			baseLat: '39.18252',
			baseLon: '117.11943'
		}
	},
	computed: {
		accounts() { return this.$store.state.accounts || [] },
		allSelected() {
			return this.accounts.length > 0 && this.selectedRefs.length === this.accounts.length
		},
		prepareLabel() {
			if (this.prepareState === 'preparing') return '正在预热微信凭证…'
			if (this.prepareState === 'ready') return '微信凭证已就绪 (0.2s秒签)'
			if (this.prepareState === 'error') return '签到时现场建立连接'
			return '点击进行相机/相册扫码'
		}
	},
	onLoad() {
		this.baseLat = uni.getStorageSync('signin_lat') || '39.18252'
		this.baseLon = uni.getStorageSync('signin_lon') || '117.11943'
		this.selectedRefs = this.accounts.map(a => a.ref)
	},
	onShow() {
		this.signinState = 'idle'
		this.$store.dispatch('syncAccounts').then(() => {
			if (this.selectedRefs.length === 0 || this.selectedRefs.length < this.accounts.length) {
				this.selectedRefs = this.accounts.map(a => a.ref)
			}
			this.prepareSelectedAccounts()
		}).catch(() => {})
	},
	onHide() {
		if (this.prepareTimer) clearTimeout(this.prepareTimer)
		this.stopDaemonLoop()
		uni.hideLoading()
	},
	onUnload() {
		if (this.prepareTimer) clearTimeout(this.prepareTimer)
		this.stopDaemonLoop()
		uni.hideLoading()
	},
	methods: {
		closeProgressDialog() {
			this.showProgressDialog = false
			this.signinState = 'idle'
		},
		saveGpsCoords() {
			if (this.baseLat) uni.setStorageSync('signin_lat', this.baseLat)
			if (this.baseLon) uni.setStorageSync('signin_lon', this.baseLon)
		},
		// 📍 一键获取当前定位
		fetchCurrentLocation() {
			uni.showLoading({ title: '正在获取定位...' })
			uni.getLocation({
				type: 'gcj02',
				geocode: true,
				success: (res) => {
					uni.hideLoading()
					this.baseLat = Number(res.latitude).toFixed(5)
					this.baseLon = Number(res.longitude).toFixed(5)
					this.saveGpsCoords()
					uni.showToast({ title: '已获取当前真实坐标', icon: 'success' })
				},
				fail: (err) => {
					uni.hideLoading()
					console.warn('Get location error:', err)
					uni.showModal({
						title: '定位获取提示',
						content: '未能自动获取到 GPS 坐标，请确认已开启手机定位权限，或手动输入经纬度。',
						showCancel: false
					})
				}
			})
		},

		// 🟢 全自动签到守护总开关
		toggleAutoDaemon(e) {
			const enabled = e.detail ? e.detail.value : !this.autoDaemonEnabled
			this.autoDaemonEnabled = enabled
			if (enabled) {
				if (this.selectedRefs.length === 0) {
					uni.showToast({ title: '请至少勾选一个签到终端', icon: 'none' })
					this.autoDaemonEnabled = false
					return
				}
				uni.showToast({ title: '全自动守护已开启', icon: 'success' })
				this.startDaemonLoop()
			} else {
				this.stopDaemonLoop()
				uni.showToast({ title: '全自动守护已关闭', icon: 'none' })
			}
		},
		startDaemonLoop() {
			this.stopDaemonLoop()
			this.runSingleDetect(true)
			this.daemonTimer = setInterval(() => {
				if (!this.autoDaemonEnabled) return
				this.runSingleDetect(true)
			}, 5000)
		},
		stopDaemonLoop() {
			if (this.daemonTimer) {
				clearInterval(this.daemonTimer)
				this.daemonTimer = null
			}
		},

		// 🔍 活跃签到探测与执行
		async runSingleDetect(fromDaemon = false) {
			if (this.isDetecting) return
			this.isDetecting = true
			try {
				if (!fromDaemon) {
					uni.showLoading({ title: '正在探测活跃签到...' })
				}
				const res = await post('/api/signin/auto-detect-and-sign', {
					lat: this.baseLat,
					lon: this.baseLon,
					account_refs: [...this.selectedRefs]
				}, { timeout: 35000 })

				if (!fromDaemon) {
					uni.hideLoading()
				}

				if (res.has_active) {
					if (res.executed) {
						this.stopDaemonLoop()
						this.autoDaemonEnabled = false
						this.openProgress(`自动打卡: ${res.course_name || '微助教'}`)
						this.renderExecutionResults(res)
						uni.showToast({ title: '签到完成，守护已自动关闭', icon: 'success' })
					} else {
						this.openProgress(`发现活动: ${res.course_name || ''}`)
						this.addLog(`[提示] ${res.message}`, false)
						this.isProgressFinished = true
						this.progressMsg = res.message || '请手动处理'
					}
				} else {
					if (!fromDaemon) {
						uni.showToast({ title: '当前无正在进行的签到', icon: 'none' })
					}
				}
			} catch (e) {
				if (!fromDaemon) {
					uni.hideLoading()
					uni.showToast({ title: '探测失败: ' + e.message, icon: 'none' })
				}
				console.warn('Detect error:', e)
			} finally {
				this.isDetecting = false
			}
		},

		// 📝 普通一键签到
		async startNormalSignin() {
			if (this.selectedRefs.length === 0) {
				uni.showToast({ title: '请至少勾选一个账号', icon: 'none' })
				return
			}
			this.signinState = 'submitting'
			uni.showLoading({ title: '查询活跃签到...' })
			try {
				const activeRes = await get('/api/signin/active')
				uni.hideLoading()
				if (!activeRes.has_active || !activeRes.latest) {
					uni.showToast({ title: '当前未发现活跃签到', icon: 'none' })
					this.signinState = 'idle'
					return
				}
				const item = activeRes.latest
				this.openProgress(`普通签到: ${item.name || ''}`)
				this.progressMsg = `正在提交 ${this.selectedRefs.length} 个终端普通签到...`

				const res = await post('/api/signin/normal', {
					course_id: item.courseId,
					sign_id: item.signId,
					account_refs: [...this.selectedRefs]
				}, { timeout: 35000 })
				this.renderExecutionResults(res)
			} catch (e) {
				uni.hideLoading()
				this.openProgress('普通签到异常')
				this.addLog(`[异常] > ${e.message}`, false)
				this.isProgressFinished = true
				this.progressMsg = '请求异常: ' + e.message
				uni.showToast({ title: '签到失败: ' + e.message, icon: 'none' })
			} finally {
				this.signinState = 'idle'
			}
		},

		// 📍 GPS 定位签到
		async startGpsSignin() {
			if (this.selectedRefs.length === 0) {
				uni.showToast({ title: '请至少勾选一个账号', icon: 'none' })
				return
			}
			this.signinState = 'submitting'
			uni.showLoading({ title: '查询活跃签到...' })
			try {
				const activeRes = await get('/api/signin/active')
				uni.hideLoading()
				if (!activeRes.has_active || !activeRes.latest) {
					uni.showToast({ title: '当前未发现活跃签到', icon: 'none' })
					this.signinState = 'idle'
					return
				}
				const item = activeRes.latest
				this.openProgress(`GPS签到: ${item.name || ''}`)
				this.progressMsg = `正在提交 ${this.selectedRefs.length} 个终端 GPS 签到...`

				const res = await post('/api/signin/gps', {
					course_id: item.courseId,
					sign_id: item.signId,
					lat: this.baseLat,
					lon: this.baseLon,
					account_refs: [...this.selectedRefs]
				}, { timeout: 35000 })
				this.renderExecutionResults(res)
			} catch (e) {
				uni.hideLoading()
				this.openProgress('GPS 签到异常')
				this.addLog(`[异常] > ${e.message}`, false)
				this.isProgressFinished = true
				this.progressMsg = '请求异常: ' + e.message
				uni.showToast({ title: 'GPS签到失败: ' + e.message, icon: 'none' })
			} finally {
				this.signinState = 'idle'
			}
		},

		// ⚡ WSS 动态码实时监听签到
		async startWssQrSignin() {
			if (this.selectedRefs.length === 0) {
				uni.showToast({ title: '请至少勾选一个账号', icon: 'none' })
				return
			}
			this.signinState = 'submitting'
			uni.showLoading({ title: '查询活跃签到...' })
			try {
				const activeRes = await get('/api/signin/active')
				uni.hideLoading()
				if (!activeRes.has_active || !activeRes.latest) {
					uni.showToast({ title: '当前未发现活跃签到', icon: 'none' })
					this.signinState = 'idle'
					return
				}
				const item = activeRes.latest
				this.openProgress(`WSS 动态监听: ${item.name || ''}`)
				this.progressMsg = `已连接 Faye WSS，等待教师端投影仪切码广播...`
				this.addLog(`[WSS] 订阅频道: /attendance/${item.courseId}/${item.signId}/qr`, true)

				const res = await post('/api/signin/auto-qr', {
					course_id: item.courseId,
					sign_id: item.signId,
					timeout_sec: 35,
					account_refs: [...this.selectedRefs]
				}, { timeout: 40000 })

				if (res.success && res.results) {
					this.renderExecutionResults(res)
				} else {
					this.addLog(`[WSS结果] ${res.message || '未捕获到新码'}`, false)
					this.isProgressFinished = true
					this.progressMsg = '监听结束，建议使用手动扫码保底'
				}
			} catch (e) {
				uni.hideLoading()
				this.addLog(`[异常] > ${e.message}`, false)
				this.isProgressFinished = true
				this.progressMsg = 'WSS 异常: ' + e.message
				uni.showToast({ title: 'WSS 异常: ' + e.message, icon: 'none' })
			} finally {
				this.signinState = 'idle'
			}
		},

		// 渲染统一日志与结果
		renderExecutionResults(response) {
			for (const result of response.results || []) {
				const name = result.nickname || result.ref?.substring(0, 10) || '未知账号'
				if (result.success) {
					this.addLog(`[成功] > ${name} | ${result.message || '签到成功'}`, true)
				} else {
					this.addLog(`[失败] > ${name} | ${result.message || '签到未完成'}`, false)
				}
			}
			this.progressMsg = `批量执行完成: 成功 ${response.success_count || 0} / 共 ${response.total || this.selectedRefs.length} 人`
			this.addLog('======= 批量云端任务处理完毕 =======', true)
			this.isProgressFinished = true
			this.signinState = 'idle'
		},

		// 微信 Code 预热
		async prepareSelectedAccounts() {
			if (this.selectedRefs.length === 0) {
				this.prepareState = 'idle'
				return
			}
			if (this.signinState === 'submitting') return
			this.prepareState = 'preparing'
			try {
				const result = await post('/api/signin/prepare', { account_refs: [...this.selectedRefs] }, { timeout: 20000 })
				this.prepareState = (result.failed || 0) > 0 ? 'error' : 'ready'
			} catch (e) {
				this.prepareState = 'error'
				console.warn('Code prefetch notice:', e)
			}
		},
		schedulePrepare() {
			if (this.prepareTimer) clearTimeout(this.prepareTimer)
			this.prepareTimer = setTimeout(() => this.prepareSelectedAccounts(), 180)
		},
		getAvatarUrl(acc) {
			if (!acc.avatar_url) return '/static/avatar_default.png'
			if (acc.avatar_url.startsWith('http')) return acc.avatar_url
			return this.$store.state.serverUrl + acc.avatar_url
		},
		toggleAccount(ref) {
			const idx = this.selectedRefs.indexOf(ref)
			if (idx >= 0) {
				this.selectedRefs.splice(idx, 1)
			} else {
				this.selectedRefs.push(ref)
			}
			this.schedulePrepare()
		},
		toggleAll() {
			if (this.allSelected) {
				this.selectedRefs = []
			} else {
				this.selectedRefs = this.accounts.map(a => a.ref)
			}
			this.schedulePrepare()
		},
		getLogTime() {
			const now = new Date()
			return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
		},
		addLog(text, success) {
			this.runLogs.push({ time: this.getLogTime(), text, success })
			this.scrollTop = this.runLogs.length * 60
		},
		// 手动相机/相册扫码
		startBatchScan() {
			if (this.selectedRefs.length === 0) {
				uni.showToast({ title: '请至少勾选一个账号', icon: 'none' })
				return
			}
			this.signinState = 'scanning'
			uni.scanCode({
				scanType: ['qrCode'],
				success: (res) => {
					this.handleScanResult(res.result)
				},
				fail: () => {
					this.signinState = 'idle'
					uni.showToast({ title: '扫码取消', icon: 'none' })
				}
			})
		},
		handleScanResult(qrUrl) {
			const match = qrUrl.match(/([a-f0-9]{32,})/i)
			let extra = match ? match[1] : ''

			if (!extra) {
				uni.showModal({
					title: '二维码解析提示',
					content: '未能自动提取到 32 位 extra 参数，是否以原链接发送至服务器测试？',
					success: (res) => {
						if (res.confirm) {
							const forceExtra = qrUrl.trim()
							this.openProgress(forceExtra)
							this.executeBatchScanTasks(forceExtra)
						} else {
							this.signinState = 'idle'
						}
					}
				})
				return
			}

			this.openProgress(extra)
			this.executeBatchScanTasks(extra)
		},
		openProgress(extra) {
			this.signinState = 'submitting'
			this.showProgressDialog = true
			this.isProgressFinished = false
			this.progressMsg = '载入签到终端队列...'
			this.runLogs = []
			this.addLog(`[引擎] 成功解析到任务: ${extra.substring(0, 16)}...`, true)
		},
		async executeBatchScanTasks(extra) {
			this.progressMsg = `并发引擎启动，正在同步提交 ${this.selectedRefs.length} 个终端...`
			const refs = [...this.selectedRefs]
			for (const ref of refs) {
				const acc = this.accounts.find(a => a.ref === ref)
				this.addLog(`[队列] ${(acc && acc.nickname) || ref.substring(0, 10)} 已就绪`, true)
			}
			try {
				const response = await post('/api/signin', {
					extra,
					account_refs: refs
				}, { timeout: 35000 })
				this.renderExecutionResults(response)
			} catch (e) {
				this.progressMsg = '签到请求结束，网络返回异常'
				this.addLog(`[异常] > ${e.message}`, false)
				this.isProgressFinished = true
			} finally {
				this.signinState = 'idle'
			}
		}
	}
}
</script>

<style lang="scss" scoped>
/* ================== Apple UI / 现代化卡片设计 ================== */
.container { padding: 0; min-height: 100vh; box-sizing: border-box; background-color: #F2F2F7; }
.hero { position: relative; padding: 60px 24px 24px 24px; background: #FFFFFF; box-shadow: 0 16px 40px rgba(44, 62, 80, 0.04); overflow: hidden; margin-bottom: 16px; }
.hero-bg-decoration { position: absolute; top: -40px; right: -20px; width: 180px; height: 180px; background: rgba(10, 132, 255, 0.05); border-radius: 50%; z-index: 1; }
.hero-content { position: relative; z-index: 2; }
.hero-title-wrap { display: flex; align-items: center; gap: 12px; }
.hero-title { font-size: 30px; font-weight: 800; letter-spacing: -0.5px; color: #1C1C1E; }
.hero-badge { background: linear-gradient(135deg, #0A84FF 0%, #005BB5 100%); color: #FFFFFF; font-size: 13px; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-style: italic; box-shadow: 0 6px 12px rgba(10, 132, 255, 0.25); }
.title-underline { width: 44px; height: 5px; background: linear-gradient(90deg, #0A84FF 0%, #30B0C7 100%); border-radius: 3px; margin-top: 12px; margin-bottom: 12px; }
.subtitle-wrapper { display: flex; justify-content: space-between; align-items: center; }
.hero-subtitle { font-size: 13px; color: #8E8E93; font-weight: 500; letter-spacing: 1px; }
.content-wrapper { padding: 0 16px 30px 16px; }

/* 全自动签到守护卡片 */
.daemon-card { background: #FFFFFF; border-radius: 20px; padding: 18px 20px; margin-bottom: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.04); border: 2px solid transparent; transition: all 0.3s ease; }
.daemon-card.daemon-active { border-color: #34C759; background: #F8FFF9; box-shadow: 0 8px 24px rgba(52, 199, 89, 0.15); }
.daemon-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.daemon-title-row { display: flex; align-items: center; gap: 8px; }
.daemon-dot { width: 10px; height: 10px; border-radius: 5px; background: #C7C7CC; }
.daemon-dot.dot-pulsing { background: #34C759; box-shadow: 0 0 10px #34C759; animation: daemon-pulse 1.5s infinite; }
@keyframes daemon-pulse { 0% { opacity: 0.6; transform: scale(0.9); } 50% { opacity: 1; transform: scale(1.2); } 100% { opacity: 0.6; transform: scale(0.9); } }
.daemon-title { font-size: 17px; font-weight: 700; color: #1C1C1E; }
.daemon-desc { font-size: 13px; color: #636366; line-height: 1.5; display: block; margin-bottom: 10px; }
.daemon-actions { display: flex; justify-content: flex-end; }
.daemon-btn { background: #F2F2F7; padding: 6px 14px; border-radius: 20px; }
.daemon-btn:active { background: #E5E5EA; }
.daemon-btn-text { font-size: 13px; font-weight: 600; color: #0A84FF; }

/* Dashboard 看板 */
.dashboard { display: flex; gap: 12px; margin-bottom: 16px; }
.dash-item { flex: 1; border-radius: 16px; padding: 16px 18px; display: flex; flex-direction: column; justify-content: center; }
.accent-bg { background-color: #0A84FF; box-shadow: 0 8px 16px rgba(10, 132, 255, 0.2); }
.dark-bg { background-color: #1C1C1E; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15); }
.dash-val { font-size: 26px; font-weight: 700; color: #FFFFFF; }
.dash-lbl { font-size: 12px; font-weight: 500; color: rgba(255,255,255,0.75); margin-top: 4px; }
.scan-title { font-size: 18px; font-weight: bold; color: #FFF; margin-bottom: 2px; }
.dash-disabled { opacity: .72; pointer-events: none; }

/* 通用卡片 */
.card { background: #FFFFFF; border-radius: 20px; padding: 18px 20px; margin-bottom: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-title-box { display: flex; flex-direction: column; }
.card-title { font-size: 17px; font-weight: 700; color: #1C1C1E; }
.card-subtitle { font-size: 12px; color: #8E8E93; margin-top: 2px; }
.card-actions { display: flex; align-items: center; gap: 8px; }
.pill-btn { padding: 6px 14px; border-radius: 30px; background-color: #F2F2F7; }
.pill-btn text { font-size: 12px; font-weight: 600; color: #0A84FF; }
.pill-btn:active { background-color: #E5E5EA; }

/* 模式网格 */
.mode-grid { display: flex; gap: 12px; }
.mode-btn { flex: 1; border-radius: 14px; padding: 14px 16px; display: flex; align-items: center; gap: 10px; }
.normal-btn { background: #F2F8FF; border: 1px solid #D6E8FF; }
.normal-btn:active { background: #E1EFFF; }
.wss-btn { background: #FFF9E6; border: 1px solid #FFE9A6; }
.wss-btn:active { background: #FFF2CC; }
.mode-icon { font-size: 24px; }
.mode-texts { display: flex; flex-direction: column; }
.mode-main { font-size: 15px; font-weight: 700; color: #1C1C1E; }
.mode-sub { font-size: 11px; color: #8E8E93; margin-top: 2px; }

/* GPS 配置区 */
.gps-config-box { display: flex; flex-direction: column; gap: 12px; }
.gps-input-row { display: flex; gap: 12px; }
.gps-field { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.gps-label { font-size: 12px; font-weight: 600; color: #636366; }
.gps-input { background: #F2F2F7; border-radius: 10px; height: 38px; line-height: 38px; padding: 0 12px; font-size: 14px; font-weight: 600; color: #1C1C1E; }
.gps-submit-btn { background: linear-gradient(135deg, #34C759 0%, #28A745 100%); border-radius: 12px; padding: 12px 0; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 12px rgba(52, 199, 89, 0.25); }
.gps-submit-btn:active { opacity: 0.85; }
.gps-submit-text { color: #FFFFFF; font-size: 15px; font-weight: 700; }

/* 账号列表 */
.accounts-list { display: flex; flex-direction: column; }
.account-row { display: flex; align-items: center; gap: 20rpx; padding: 22rpx 0; border-bottom: 1px solid rgba(0, 0, 0, 0.04); }
.account-row:last-child { border-bottom: none; }
.check-box { width: 44rpx; height: 44rpx; border-radius: 22rpx; border: 2rpx solid #C7C7CC; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 0.2s; }
.check-box.checked { background: #0A84FF; border-color: #0A84FF; }
.check-icon { font-size: 24rpx; color: #fff; }
.row-avatar { width: 68rpx; height: 68rpx; border-radius: 50%; }
.row-info { display: flex; flex-direction: column; flex: 1; }
.row-name { font-size: 28rpx; color: #1C1C1E; font-weight: 600; }
.row-status { font-size: 20rpx; margin-top: 4rpx; }
.master-tag { background: #FFF5E6; padding: 2rpx 12rpx; border-radius: 6rpx; }
.master-tag-text { font-size: 20rpx; color: #FF9500; font-weight: bold; }
.empty-zone { display: flex; flex-direction: column; align-items: center; padding: 40rpx 0; gap: 10rpx; }
.empty-emoji { font-size: 60rpx; }
.empty-hint { font-size: 24rpx; color: #8E8E93; }

/* 控制台 Shell 弹窗 */
.blur-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 999; display: flex; flex-direction: column; justify-content: flex-end; opacity: 0; pointer-events: none; transition: opacity 0.3s; }
.blur-mask.mask-active { opacity: 1; pointer-events: auto; }
.shell-modal { margin: auto; background: #1C1C1E; width: 94%; border-radius: 16px; padding: 16px 14px; box-shadow: 0 20px 48px rgba(0,0,0,0.6); box-sizing: border-box; }
.shell-header { display: flex; align-items: center; margin-bottom: 12px; }
.mac-dots { display: flex; gap: 6px; margin-right: 12px;}
.dot { width: 12px; height: 12px; border-radius: 6px; }
.dot.red { background: #FF5F56; } .dot.yellow { background: #FFBD2E; } .dot.green { background: #27C93F; }
.shell-title { font-size: 13px; color: #8E8E93; font-weight: 600; font-family: monospace; }
.shell-body { background: #000; border-radius: 10px; padding: 12px 14px; box-sizing: border-box; }
.shell-status-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; }
.shell-status { color: #0A84FF; font-family: monospace; font-size: 12px; font-weight: bold; word-break: break-all; }
.terminal-spinner { width: 12px; height: 12px; border: 2px solid rgba(10,132,255,.3); border-top-color: #0A84FF; border-radius: 50%; animation: terminal-spin .75s linear infinite; flex-shrink: 0; }
@keyframes terminal-spin { to { transform: rotate(360deg); } }
.shell-logs { height: 280px; box-sizing: border-box; }
.log-line { margin-bottom: 8px; font-family: monospace, Consolas, Courier, sans-serif; font-size: 12px; line-height: 1.5; word-break: break-all; word-wrap: break-word; }
.log-time { color: #8E8E93; margin-right: 6px; }
.log-text { word-break: break-all; }
.log-good { color: #34C759; }
.log-bad { color: #FF3B30; }
.shell-footer { display: flex; justify-content: center; margin-top: 14px; }
.shell-btn { height: 72rpx; line-height: 72rpx; background: rgba(255,255,255,0.12); color: #FFF; font-size: 24rpx; border-radius: 36rpx; font-family: monospace; font-weight: bold; padding: 0 40rpx; text-align: center; border: none;}
.shell-btn:active { background: rgba(255,255,255,0.2); }
.shell-btn::after { border: none; }
</style>
