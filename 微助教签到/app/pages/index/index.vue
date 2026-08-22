<template>

	<view class="page-container">

		<!-- Top App Bar -->

		<view class="top-app-bar" :style="{ paddingTop: statusBarHeight + 'px' }">

			<view class="app-bar-inner">

				<view class="bar-btn" @click="showAuthorDialog = true">

					<text class="icon-menu">☰</text>

				</view>

				<text class="app-title">微助教签到助手</text>

				<view class="bar-btn-placeholder"></view>

			</view>

		</view>



		<view class="main-content" :style="{ paddingTop: (statusBarHeight + 56) + 'px' }">

			

			<!-- 1. Top Check-in Action Bar (Button Cards) -->

			<view class="trigger-buttons-row">

				<view class="mode-trigger-btn" @tap="startNormalSignin">

					<text class="mode-btn-title">普通签到</text>

					<text class="mode-btn-sub">一键打卡</text>

				</view>

				<view class="mode-trigger-btn highlight-btn" @tap="startGpsSignin">

					<text class="mode-btn-title">GPS 签到</text>

					<text class="mode-btn-sub">防风控</text>

				</view>

				<view class="mode-trigger-btn" @tap="startBatchScan()">

					<text class="mode-btn-title">扫码签到</text>

					<text class="mode-btn-sub">极速并发</text>

				</view>

			</view>



			<!-- 2. 全自动签到守护引擎卡片 -->

			<view class="daemon-card" :class="{ 'daemon-active': autoDaemonEnabled }">

				<view class="daemon-header">

					<view class="daemon-title-row">

						<view class="pulse-indicator">

							<view class="pulse-ring" v-if="autoDaemonEnabled"></view>

							<view class="pulse-dot" :class="{ 'dot-active': autoDaemonEnabled }"></view>

						</view>

						<text class="daemon-title">全自动签到守护引擎</text>

					</view>

					<switch :checked="autoDaemonEnabled" color="#0058bc" @change="toggleAutoDaemon" />

				</view>

				<view class="daemon-desc-row">

					<view class="desc-dot" :class="{ 'desc-dot-active': autoDaemonEnabled }"></view>

					<text class="daemon-desc">

						{{ autoDaemonEnabled ? '守护中：后台每 5 秒探测一次，检测到签到自动执行对应模式打卡；打卡完成后将直接停止探测。' : '未开启：开启后将全自动在后台监听活跃签到并秒级自动完成打卡。' }}

					</text>

				</view>

			</view>



			<!-- 3. 快捷操作网格（双层高级卡片，配备高端科技扫描图标） -->

			<view class="quick-cards-grid">

				<view class="action-card card-scan" @tap="startBatchScan()">

					<view class="card-badge-row">

						<text class="card-pill primary-pill">极速识别</text>

						<!-- 高端科技扫描取景框微动效图标 -->

						<view class="scanner-glyph">

							<view class="glyph-corner tl"></view>

							<view class="glyph-corner tr"></view>

							<view class="glyph-corner bl"></view>

							<view class="glyph-corner br"></view>

							<view class="glyph-laser"></view>

						</view>

					</view>

					<view class="card-text-group">

						<text class="card-main-title">手动扫码</text>

						<text class="card-sub-title">支持动态码秒级打卡</text>

					</view>

				</view>



				<view class="action-card card-account" @tap="goAdd">

					<view class="card-badge-row">

						<text class="card-pill neutral-pill">微信授权</text>

						<text class="card-plus">+</text>

					</view>

					<view class="card-text-group">

						<text class="card-main-title">添加账号</text>

						<text class="card-sub-title">多终端凭证自动保活</text>

					</view>

				</view>

			</view>



			<!-- 4. GPS 坐标配置卡片（紧凑轻量化胶囊设计） -->

			<view class="gps-compact-card">

				<view class="gps-compact-header">

					<view class="gps-title-wrap">

						<text class="gps-title">GPS 定位坐标</text>

					</view>

					<view class="gps-btn-group">

						<view class="gps-action-btn locate-btn" @tap="fetchCurrentLocation">

							<text class="gps-btn-text">获取定位</text>

						</view>

						<view class="gps-action-btn save-btn" @tap="saveGpsCoords">

							<text class="gps-btn-text save-text">保存</text>

						</view>

					</view>

				</view>

				<view class="gps-compact-body">

					<view class="gps-chip">

						<text class="chip-tag">纬度</text>

						<input type="text" class="chip-input" v-model="baseLat" placeholder="39.18252" @blur="saveGpsCoords" />

					</view>

					<view class="gps-chip">

						<text class="chip-tag">经度</text>

						<input type="text" class="chip-input" v-model="baseLon" placeholder="117.11943" @blur="saveGpsCoords" />

					</view>

				</view>

			</view>



			<!-- 5. 管理账号卡片 -->

			<view class="ethos-card">

				<view class="card-header">

					<text class="card-title">管理账号 ({{ accounts.length }})</text>

					<view class="card-actions-right">

						<view class="cloud-sync-btn" @tap="syncAll">

							<text class="cloud-btn-text">从云端拉取</text>

						</view>

					</view>

				</view>



				<view class="accounts-list">

					<view v-for="acc in accounts" :key="acc.ref" class="account-item">

						<view class="acc-left">

							<view class="avatar-wrap">

								<image class="avatar-img" :src="getAvatarUrl(acc)" mode="aspectFill"></image>

								<view class="status-dot" :class="acc.needs_rescan ? 'dot-dead' : (acc.is_alive ? 'dot-alive' : 'dot-dead')"></view>

							</view>

							<view class="acc-info">

								<view class="name-row">

									<text class="acc-name">{{ acc.nickname || '未命名' }}</text>

								</view>

								<view class="time-meta-row">

									<text class="time-meta-item">🕒 保活: {{ formatRelativeTime(acc.last_keepalive_at) }}</text>

									<text class="time-meta-dot">·</text>

									<text class="time-meta-item">检验: {{ formatRelativeTime(acc.last_probe_at) }}</text>

								</view>

							</view>

						</view>



						<view class="acc-right">

							<!-- Always show vertical capsule stack -->

							<view class="capsule-vertical-stack" @tap.stop>

								<view class="action-capsule-sm rescan-capsule-sm" @tap.stop="handleRescan(acc)">

									<text class="capsule-sm-text rescan-text">重扫</text>

								</view>

								<view class="action-capsule-sm delete-capsule-sm" @tap.stop="handleDelete(acc)">

									<text class="capsule-sm-text delete-text">删除</text>

								</view>

							</view>



			

						</view>

					</view>



					<view v-if="accounts.length === 0" class="empty-state" @tap="goAdd">

						<text class="empty-emoji">👥</text>

						<text class="empty-text">暂无账号，点击添加账号</text>

					</view>

				</view>



				<button class="add-more-btn" @tap="goAdd">

					<text>➕ 添加更多账号</text>

				</button>

			</view>



			<view style="height: 30px;"></view>

		</view>



				<!-- Shell Terminal Log Dialog (Pro Terminal UI) -->
		<view class="blur-mask terminal-mask" :class="{ 'mask-active': showProgressDialog }">
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
						<text class="shell-status">> {{ progressMsg }}</text>
					</view>
					<scroll-view scroll-y class="shell-logs" :scroll-top="scrollTop">
						<view class="log-line" v-for="(log, idx) in runLogs" :key="idx" :class="'level-' + (log.level || 'info').toLowerCase()">
							<text class="log-time">{{ log.time }}</text>
							<text class="log-tag">[{{ log.level || 'INFO' }}]</text>
							<text class="log-text">{{ log.text }}</text>
						</view>
					</scroll-view>
				</view>
				<view class="shell-footer" v-if="isProgressFinished">
					<button v-if="showManualScanBtn" class="shell-btn direct-scan-btn" @click="startBatchScanFromTerminal">
						📷 立即扫码打卡
					</button>
					<button v-if="pendingSalvageRefs.length > 0" class="shell-btn salvage-btn" @click="startSalvageScan">
						📷 重新扫码打捞剩余 ({{ pendingSalvageRefs.length }} 人)
					</button>
					<button class="shell-btn" @click="closeProgressDialog">关闭控制台</button>
				</view>
			</view>
		</view>

<!-- 同步账号多选 Dialog -->

		<view class="blur-mask" :class="{ 'mask-active': showSyncDialog }">

			<view class="sheet-modal" v-if="showSyncDialog">

				<view class="sheet-header">

					<view class="sheet-title-row">

						<text class="sheet-title">从云端拉取托管账号</text>

						<text v-if="allServerAccounts.length > 0" class="sheet-sub-badge">云端 {{ allServerAccounts.length }} 个</text>

					</view>

					<view class="sheet-header-actions">

						<text v-if="allServerAccounts.length > 0" class="sheet-action-link" @tap="toggleSelectAll">

							{{ tempSelectedRefs.length === allServerAccounts.length ? '取消全选' : '全选' }}

						</text>

						<text class="sheet-close" @tap="showSyncDialog = false">关闭</text>

					</view>

				</view>

				

				<scroll-view scroll-y style="height: 500rpx; margin-bottom: 20px;">

					<view v-if="allServerAccounts.length === 0" class="empty-state">

						<text class="empty-emoji">👥</text>

						<text class="empty-text">云端没有托管账号，请先扫码添加</text>

					</view>

					<view class="sync-list" v-else>

						<view v-for="acc in allServerAccounts" :key="acc.ref" class="sync-item" :class="{ 'sync-item-selected': isRefSelected(acc.ref) }" @tap="toggleTempSelect(acc.ref)">

							<view class="sync-item-left">

								<view class="sync-check-wrap">

									<checkbox :checked="isRefSelected(acc.ref)" color="#0058bc" style="pointer-events: none; transform: scale(0.85);"></checkbox>

								</view>

								<image class="sync-avatar" :src="getAvatarUrl(acc)" mode="aspectFill"></image>

								<view class="sync-meta">

									<text class="sync-name">{{ acc.nickname || '未命名' }}</text>

									<text class="sync-desc">保活: {{ formatRelativeTime(acc.last_keepalive_at) }}</text>

								</view>

							</view>

							<view class="sync-item-right">

								<text class="sync-badge" :class="acc.is_alive ? 'alive' : 'dead'">

									{{ acc.is_alive ? '在线' : '离线' }}

								</text>

							</view>

						</view>

					</view>

				</scroll-view>

				

				<view class="confirm-sync-btn" @tap="confirmSyncSelection" v-if="allServerAccounts.length > 0">

					<text>确认同步所选账号 (已选 {{ tempSelectedRefs.length }} / {{ allServerAccounts.length }} 个)</text>

				</view>

			</view>

		</view>



		<!-- Author Dialog -->

		<view class="blur-mask" :class="{ 'mask-active': showAuthorDialog }">

			<view class="sheet-modal" v-if="showAuthorDialog">

				<view class="sheet-header">

					<text class="sheet-title">作者寄语</text>

					<text class="sheet-close" @click="showAuthorDialog = false">关闭</text>

				</view>

				<view class="author-body">

					<view class="paragraph">世间最大的遗憾，往往不是洞悉世事后的那份疏离，而是习惯了规则的缠绕，最终在无形的茧房里安之若素。</view>

					<view class="paragraph">我所做的，只是在这按部就班的轨道旁，为不甘平庸的你递上一把挣脱繁文缛节的钥匙。</view>

					<view class="author-meta">

						<text class="author-name">作者 — 相濡以沫</text>

						<text class="author-contact" @click="copyContact">邮箱: 2768484926@qq.com</text>

					</view>

				</view>

			</view>

		</view>

	</view>

</template>



<script>

import { get, post, del, put } from '../../api/request'

import { getCachedAvatar } from '../../utils/avatar'



export default {

	data() {

		return {

			statusBarHeight: 20,

			showAuthorDialog: false,

			syncing: false,

			showSyncDialog: false,

			tempSelectedRefs: [],



			// 控制台弹窗

			showProgressDialog: false,

			isProgressFinished: false,

			progressMsg: '',

			runLogs: [],

			scrollTop: 0,

			signinState: 'idle',



			// 二维码过期打捞机制状态

			pendingSalvageRefs: [],

			lastSuccessRefs: [],

			expandedRef: '',



			// 全自动签到守护

			autoDaemonEnabled: false,

			daemonTimer: null,
			cdTimer: null,

			isDetecting: false,



			// GPS 坐标配置（默认天津商业大学）

			baseLat: '39.18252',

			baseLon: '117.11943',



			// 本地直连预热 Code 缓存

			cachedPreparedCodes: {},



			// 终端内一键扫码按钮控制

			showManualScanBtn: false

		}

	},

	computed: {

		accounts() { return this.$store.state.accounts || [] },

		masterAccount() { return this.$store.getters.masterAccount },

		allServerAccounts() { return this.$store.state.allServerAccounts || [] }

	},

	onLoad() {

		const sys = uni.getSystemInfoSync()

		this.statusBarHeight = sys.statusBarHeight || 20

		this.baseLat = uni.getStorageSync('signin_lat') || '39.18252'

		this.baseLon = uni.getStorageSync('signin_lon') || '117.11943'

	},

	onShow() {

		this.signinState = 'idle'

		this.$store.dispatch('checkServerHealth').catch(() => {})

		this.$store.dispatch('syncAccounts').catch(() => {})

	},

	onHide() {

		this.stopDaemonLoop()

		uni.hideLoading()

	},

	onUnload() {

		this.stopDaemonLoop()

		uni.hideLoading()

	},

	methods: {

		getAvatarUrl(acc) {

			if (!acc) return '/static/avatar_default.png'

			return getCachedAvatar(acc.ref, this.$store.state.serverUrl, acc.avatar_url)

		},

		formatRelativeTime(timeStr) {

			if (!timeStr) return '未检验'

			try {

				const isoStr = timeStr.includes('T') ? timeStr : timeStr.replace(' ', 'T')

				const t = new Date(isoStr.endsWith('Z') ? isoStr : isoStr + 'Z')

				const now = new Date()

				const diffMs = now.getTime() - t.getTime()

				if (isNaN(diffMs) || diffMs < 0) return '刚刚'

				const diffMin = Math.floor(diffMs / 60000)

				if (diffMin < 1) return '刚刚'

				if (diffMin < 60) return `${diffMin}分钟前`

				const diffH = Math.floor(diffMin / 60)

				if (diffH < 24) return `${diffH}小时前`

				return `${Math.floor(diffH / 24)}天前`

			} catch {

				return '刚刚'

			}

		},

		goAdd() {

			uni.navigateTo({ url: '/pages/accounts/add' })

		},

		goRescan(acc) {

			uni.navigateTo({

				url: `/pages/accounts/add?target_ref=${encodeURIComponent(acc.ref)}&target_name=${encodeURIComponent(acc.nickname || '未知')}`

			})

		},

		saveGpsCoords() {

			if (this.baseLat) uni.setStorageSync('signin_lat', this.baseLat)

			if (this.baseLon) uni.setStorageSync('signin_lon', this.baseLon)

			uni.showToast({ title: '坐标已保存', icon: 'success' })

		},

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

					uni.showToast({ title: '已更新真实定位', icon: 'success' })

				},

				fail: (err) => {

					uni.hideLoading()

					console.warn('Location error:', err)

					uni.showToast({ title: '定位获取失败，请手动输入', icon: 'none' })

				}

			})

		},

		copyContact() {

			uni.setClipboardData({

				data: '2768484926@qq.com',

				success: () => uni.showToast({ title: '作者邮箱已复制', icon: 'none' })

			})

		},



		isPrimaryAccount(acc) {

			if (!acc || !acc.ref) return false

			const primary = this.accounts.find(a => a.is_alive && !a.needs_rescan) || this.accounts[0]

			return primary && primary.ref === acc.ref

		},



		// ── 账号管理操作 ──

		toggleAccountMenu(ref) {

			this.expandedRef = (this.expandedRef === ref) ? '' : ref

		},

		handleRescan(acc) {

			this.expandedRef = ''

			this.goRescan(acc)

		},

		handleDelete(acc) {

			this.expandedRef = ''

			uni.showModal({

				title: '确认删除',

				content: `确定删除账号「${acc.nickname || acc.ref}」吗？`,

				confirmColor: '#BA1A1A',

				success: async (confirmRes) => {

					if (confirmRes.confirm) {

						try {

							await del(`/api/accounts/${encodeURIComponent(acc.ref)}`)

							this.$store.commit('REMOVE_ACCOUNT', acc.ref)

							uni.showToast({ title: '已删除', icon: 'success' })

						} catch (e) {

							uni.showToast({ title: e.message || '删除失败', icon: 'none' })

						}

					}

				}

			})

		},

		showActions(acc) {

			const itemList = ['重新扫码', '删除账号']

			uni.showActionSheet({

				itemList,

				success: async (res) => {

					const action = itemList[res.tapIndex]

					if (action === '重新扫码') {

						this.goRescan(acc)

					} else if (action === '删除账号') {

						this.handleDelete(acc)

					}

				}

			})

		},



		// ── 云端同步弹窗 ──

		async syncAll() {

			if (this.syncing) return

			this.syncing = true

			uni.showLoading({ title: '加载云端数据...' })

			try {

				await this.$store.dispatch('syncAccounts')

				const all = this.$store.state.allServerAccounts || []

				// 默认全选云端所有有效账号

				const allValidRefs = all.map(a => a && a.ref && String(a.ref).trim()).filter(Boolean)

				this.tempSelectedRefs = [...allValidRefs]

				this.showSyncDialog = true

			} catch (e) {

				uni.showToast({ title: '同步失败: ' + (e.message || '超时'), icon: 'none' })

			} finally {

				uni.hideLoading()

				this.syncing = false

			}

		},

		isRefSelected(ref) {

			if (!ref) return false

			const target = String(ref).trim()

			return this.tempSelectedRefs.some(r => String(r).trim() === target)

		},

		toggleTempSelect(ref) {

			if (!ref) return

			const target = String(ref).trim()

			const idx = this.tempSelectedRefs.findIndex(r => String(r).trim() === target)

			if (idx >= 0) {

				this.tempSelectedRefs.splice(idx, 1)

			} else {

				this.tempSelectedRefs.push(target)

			}

			this.tempSelectedRefs = [...this.tempSelectedRefs]

		},

		toggleSelectAll() {

			const all = this.$store.state.allServerAccounts || []

			const allValidRefs = all.map(a => a && a.ref && String(a.ref).trim()).filter(Boolean)

			if (this.tempSelectedRefs.length >= allValidRefs.length && allValidRefs.length > 0) {

				this.tempSelectedRefs = []

			} else {

				this.tempSelectedRefs = [...allValidRefs]

			}

		},

		confirmSyncSelection() {

			const cleanSelected = this.tempSelectedRefs.map(r => String(r).trim()).filter(Boolean)

			this.$store.commit('SET_SELECTED_REFS', cleanSelected)

			const all = this.$store.state.allServerAccounts || []

			const localList = all.filter(a => a && a.ref && cleanSelected.includes(String(a.ref).trim()))

			this.$store.commit('SET_ACCOUNTS', localList)

			this.showSyncDialog = false

			uni.showToast({ title: `已同步 ${localList.length} 个账号`, icon: 'success' })

		},



		// ── 签到执行逻辑 ──
		closeProgressDialog() {
			this.showProgressDialog = false
			this.showManualScanBtn = false
			if (this.cdTimer) {
				clearInterval(this.cdTimer)
				this.cdTimer = null
			}
			this.signinState = 'idle'
		},
		startBatchScanFromTerminal() {
			this.closeProgressDialog()
			this.startBatchScan()
		},
		getLogTime() {
			const now = new Date()
			return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
		},
		addLog(level, text) {
			this.runLogs.push({ time: this.getLogTime(), level: level.toUpperCase(), text })
			this.scrollTop = this.runLogs.length * 60
		},
		openProgress(title) {
			this.signinState = 'submitting'
			this.showProgressDialog = true
			this.isProgressFinished = false
			this.showManualScanBtn = false
			this.progressMsg = title || '载入签到终端队列...'
			if (this.pendingSalvageRefs.length === 0) {
				this.runLogs = []
			}
		},
		renderExecutionResults(response, targetRefs) {
			const failedRefs = []
			for (const result of response.results || []) {
				const ref = result.ref
				const name = result.nickname || ref?.substring(0, 10) || '未知账号'
				if (result.success) {
					if (!this.lastSuccessRefs.includes(ref)) {
						this.lastSuccessRefs.push(ref)
					}
					this.addLog('SUCCESS', `✔ ${name} | ${result.message || '签到成功'}`)
				} else {
					failedRefs.push(ref)
					this.addLog('ERROR', `✖ ${name} | ${result.message || '签到失败'}`)
				}
			}

			const totalTarget = (targetRefs && targetRefs.length) || (response.results && response.results.length) || 0
			this.pendingSalvageRefs = failedRefs
			this.progressMsg = `执行完毕: 成功 ${response.success_count || 0} / 目标 ${totalTarget} 人`

			if (failedRefs.length > 0) {
				this.addLog('WARN', `⚠ 检测到 ${failedRefs.length} 个账号未能打卡，可点击下方【重新扫码打捞】`)
			} else {
				this.addLog('DONE', `🎉 全部账号打卡任务处理完毕 (成功 ${response.success_count || 0} / ${totalTarget} 人)`)
			}

			this.isProgressFinished = true
			this.signinState = 'idle'
		},

		// 普通签到（全并发毫秒级极速提交）
		async startNormalSignin() {
			if (this.accounts.length === 0) {
				uni.showToast({ title: '请先添加或勾选账号', icon: 'none' })
				return
			}
			this.signinState = 'submitting'
			this.pendingSalvageRefs = []
			this.lastSuccessRefs = []
			const targetRefs = this.accounts.map(a => a.ref)
			uni.showLoading({ title: `并发探测 ${targetRefs.length} 个账号活跃签到...` })
			try {
				const activeRes = await get('/api/signin/active', { refs: targetRefs.join(',') })
				uni.hideLoading()
				if (!activeRes.has_active || !activeRes.latest) {
					uni.showToast({ title: '当前未发现活跃签到活动', icon: 'none' })
					this.signinState = 'idle'
					return
				}
				const item = activeRes.latest
				this.openProgress(`普通签到: ${item.name || ''}`)
				this.progressMsg = `正在全并发提交 ${targetRefs.length} 个终端普通签到...`
				this.addLog('EXEC', `⚡ 启动微助教高并发秒签引擎 (毫秒级并发提交)...`)

				const res = await post('/api/signin/normal', {
					course_id: item.courseId,
					sign_id: item.signId,
					account_refs: targetRefs
				}, { timeout: 35000 })
				this.renderExecutionResults(res, targetRefs)
			} catch (e) {
				uni.hideLoading()
				this.openProgress('普通签到异常')
				this.addLog('ERROR', `✖ 异常报错: ${e.message}`)
				this.isProgressFinished = true
				this.progressMsg = '请求异常: ' + e.message
			} finally {
				this.signinState = 'idle'
			}
		},

		// GPS 签到（全并发极速打卡 + 5~10 米物理微扰动）
		async startGpsSignin() {
			if (this.accounts.length === 0) {
				uni.showToast({ title: '请先添加或勾选账号', icon: 'none' })
				return
			}
			this.signinState = 'submitting'
			this.pendingSalvageRefs = []
			this.lastSuccessRefs = []
			const targetRefs = this.accounts.map(a => a.ref)
			uni.showLoading({ title: `并发探测 ${targetRefs.length} 个账号活跃签到...` })
			try {
				const activeRes = await get('/api/signin/active', { refs: targetRefs.join(',') })
				uni.hideLoading()
				if (!activeRes.has_active || !activeRes.latest) {
					uni.showToast({ title: '当前未发现活跃签到活动', icon: 'none' })
					this.signinState = 'idle'
					return
				}
				const item = activeRes.latest
				this.openProgress(`GPS签到: ${item.name || ''}`)
				this.progressMsg = `正在全并发提交 ${targetRefs.length} 个终端 GPS 签到...`
				this.addLog('EXEC', `⚡ 启动 GPS 定位并发引擎 (为每个账号施加 5~10 米物理独立微扰动)...`)

				const res = await post('/api/signin/gps', {
					course_id: item.courseId,
					sign_id: item.signId,
					lat: this.baseLat,
					lon: this.baseLon,
					account_refs: targetRefs
				}, { timeout: 35000 })
				this.renderExecutionResults(res, targetRefs)
			} catch (e) {
				uni.hideLoading()
				this.openProgress('GPS 签到异常')
				this.addLog('ERROR', `✖ 异常报错: ${e.message}`)
				this.isProgressFinished = true
				this.progressMsg = '请求异常: ' + e.message
			} finally {
				this.signinState = 'idle'
			}
		},

		// 客户端本地直接请求微助教打卡（国内网络 20~40ms 极速响应，用于手动扫码秒杀）
		directClientSignin(ref, code, extra, nickname) {
			const signinHost = 'https://www.teachermate.com.cn'
			const url = `${signinHost}/api/v1/wechat/r?isTeacher=0&m=s_qr_sign&extra=${encodeURIComponent(extra)}&code=${encodeURIComponent(code)}&state=`

			return new Promise((resolve) => {
				const startTime = Date.now()
				uni.request({
					url,
					method: 'GET',
					header: {
						'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/122.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.48 NetType/WIFI Language/zh_CN'
					},
					timeout: 8000,
					success: (res) => {
						const costMs = Date.now() - startTime
						let finalLocation = ''
						if (res.header) {
							finalLocation = res.header['location'] || res.header['Location'] || ''
						}
						const responseText = typeof res.data === 'string' ? res.data : JSON.stringify(res.data || '')

						let rank = null
						const rankMatch = (finalLocation + ' ' + responseText).match(/rank[":=]\s*"?(\d+)"?/i) || responseText.match(/第\s*(\d+)\s*名/i)
						if (rankMatch) {
							rank = rankMatch[1]
						}

						const combined = (finalLocation + ' ' + responseText).toLowerCase()
						if (combined.includes('open.weixin.qq.com') || combined.includes('oauth2')) {
							resolve({ ref, nickname, success: false, message: '微信授权失效需重扫', needServerFallback: true })
							return
						}
						if (combined.includes('不在签到范围') || (combined.includes('不在') && combined.includes('范围'))) {
							resolve({ ref, nickname, success: false, message: '不在有效签到地理范围内' })
							return
						}
						if (combined.includes('二维码已过期') || combined.includes('二维码失效') || combined.includes('已失效')) {
							resolve({ ref, nickname, success: false, message: '签到二维码已过期或失效' })
							return
						}
						if (combined.includes('签到已结束') || combined.includes('签到结束')) {
							resolve({ ref, nickname, success: false, message: '签到已结束' })
							return
						}

						const isSuccess = combined.includes('success=1') 
							|| combined.includes('success=true')
							|| combined.includes('signresult')
							|| combined.includes('sign-result')
							|| combined.includes('签到成功')
							|| combined.includes('已签到')
							|| (res.statusCode >= 200 && res.statusCode < 400 && !combined.includes('error'))

						if (isSuccess) {
							const msg = rank ? `直连秒签成功 (第${rank}名, ${costMs}ms)` : `直连签到成功 (${costMs}ms)`
							resolve({ ref, nickname, success: true, message: msg, rank })
						} else {
							resolve({ ref, nickname, success: false, message: '签到未完成' })
						}
					},
					fail: (err) => {
						resolve({ ref, nickname, success: false, message: '本地直连超时: ' + (err.errMsg || ''), needServerFallback: true })
					}
				})
			})
		},

		// ── 两步扫码签到与打捞逻辑 ──
		async startBatchScan(targetRefs = null) {
			const refsToSign = targetRefs || this.accounts.map(a => a.ref)
			if (refsToSign.length === 0) {
				uni.showToast({ title: '没有需要签到的账号', icon: 'none' })
				return
			}

			if (!targetRefs) {
				this.lastSuccessRefs = []
				this.pendingSalvageRefs = []
			}

			// 第一步：严格确保所有账号的 Code 凭证 100% 准备完成并返回本地
			uni.showLoading({ title: `⚡ 正在准备 ${refsToSign.length} 个账号凭证...`, mask: true })
			try {
				const prepRes = await post('/api/signin/prepare', { account_refs: refsToSign, force: true }, { timeout: 15000 })
				uni.hideLoading()
				if (prepRes && prepRes.codes) {
					this.cachedPreparedCodes = prepRes.codes
				}
				if (prepRes && prepRes.ready > 0) {
					uni.showToast({ title: `已就绪 ${prepRes.ready} 人，请扫码`, icon: 'none', duration: 1000 })
				}
			} catch (err) {
				uni.hideLoading()
				console.warn('Pre-warm notice:', err)
			}

			// 第二步：唤起相机扫码，扫码瞬间国内直连 0.05 秒极速打卡
			this.signinState = 'scanning'
			uni.scanCode({
				scanType: ['qrCode'],
				success: (res) => {
					const match = res.result.match(/([a-f0-9]{32,})/i)
					const extra = match ? match[1] : res.result.trim()
					this.openProgress(`扫码签到: ${extra.substring(0, 12)}...`)
					this.executeBatchScan(extra, refsToSign)
				},
				fail: () => {
					this.signinState = 'idle'
					uni.showToast({ title: '扫码已取消', icon: 'none' })
				}
			})
		},

		async executeBatchScan(extra, refsToSign) {
			this.progressMsg = `国内直连并发引擎启动，正在瞬间打卡 ${refsToSign.length} 个终端...`
			const targetAccounts = this.accounts.filter(a => refsToSign.includes(a.ref))

			// 1. 检查是否有本地准备好的微信 Code（国内直连模式）
			const directTasks = []
			const fallbackRefs = []

			for (const acc of targetAccounts) {
				const code = this.cachedPreparedCodes && this.cachedPreparedCodes[acc.ref]
				if (code) {
					this.addLog('AUTH', `🔑 ${acc.nickname || acc.ref.substring(0, 8)} 凭证已就绪，发起秒签...`)
					directTasks.push(this.directClientSignin(acc.ref, code, extra, acc.nickname || '未知'))
				} else {
					fallbackRefs.push(acc.ref)
				}
			}

			let allResults = []

			// 2. 本地全并发直接打卡（零海外延迟）
			if (directTasks.length > 0) {
				const directResults = await Promise.all(directTasks)
				for (const dr of directResults) {
					if (dr.needServerFallback) {
						fallbackRefs.push(dr.ref)
					} else {
					allResults.push(dr)
					}
				}
			}

			// 3. 对未准备好 Code 或本地失效的账号走服务端兜底打卡
			if (fallbackRefs.length > 0) {
				this.addLog('WARN', `⚠ 触发服务端自动打捞 ${fallbackRefs.length} 个账号...`)
				try {
					const response = await post('/api/signin', {
						extra,
						account_refs: fallbackRefs
					}, { timeout: 35000 })
					if (response && response.results) {
						allResults = allResults.concat(response.results)
					}
				} catch (e) {
					this.addLog('ERROR', `✖ 服务端打捞异常: ${e.message}`)
				}
			}

			// 4. 清理已消费的 Code
			this.cachedPreparedCodes = {}

			// 5. 异步同步日志到服务端（不阻塞前端界面）
			post('/api/signin/batch-log', { results: allResults, extra }).catch(() => {})

			// 6. 渲染最终结果
			const successCount = allResults.filter(r => r.success).length
			this.renderExecutionResults({ results: allResults, success_count: successCount, total: allResults.length }, refsToSign)
			this.signinState = 'idle'
		},

		// 重新扫码打捞（仅提交未成功的账号）
		startSalvageScan() {
			if (this.pendingSalvageRefs.length === 0) {
				uni.showToast({ title: '所有账号已成功，无需打捞', icon: 'success' })
				return
			}
			this.addLog('WARN', `⚠ 启动精准打捞：请重新扫描最新二维码`)
			this.startBatchScan(this.pendingSalvageRefs)
		},

		// 全自动守护
		toggleAutoDaemon(e) {
			const enabled = e.detail ? e.detail.value : !this.autoDaemonEnabled
			this.autoDaemonEnabled = enabled
			if (enabled) {
				if (this.accounts.length === 0) {
					uni.showToast({ title: '请先添加或勾选账号', icon: 'none' })
					this.autoDaemonEnabled = false
					return
				}
				uni.showToast({ title: '守护引擎已启动', icon: 'success' })
				this.startDaemonLoop()
			} else {
				this.stopDaemonLoop()
				uni.showToast({ title: '守护引擎已关闭', icon: 'none' })
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
		async runSingleDetect(fromDaemon = false) {
			if (this.isDetecting) return
			this.isDetecting = true
			try {
				const targetRefs = this.accounts.map(a => a.ref)
				// 1. 极速探测是否有活跃签到（0.1s 秒级响应）
				const activeRes = await get('/api/signin/active', { refs: targetRefs.join(',') })

				if (!activeRes.has_active || !activeRes.latest) {
					// 无活跃签到，继续静默守护
					return
				}

				// 2. ⚡ 只要探测到签到，第一时间立即停止守护循环并调起终端控制台！
				this.stopDaemonLoop()
				this.autoDaemonEnabled = false
				try { uni.vibrateLong() } catch (_) {}

				const item = activeRes.latest
				const courseId = item.courseId
				const signId = item.signId
				const isGps = item.isGPS === 1
				const isQr = item.isQR === 1
				const courseName = item.name || '微助教课程签到'

				const typeName = isGps ? 'GPS 定位签到' : (isQr ? '动态二维码签到' : '普通一键签到')
				this.openProgress(`自动打卡: ${courseName}`)
				this.addLog('DISCOVER', `🔍 探测到活跃签到: 《${courseName}》`)
				this.addLog('INFO', `📌 签到模式: ${typeName} (CourseId: ${courseId}, SignId: ${signId})`)

				// 3. 根据签到类型在终端内清晰执行全流程
				if (!isGps && !isQr) {
					// ── A. 普通一键签到 ──
					this.progressMsg = `正在全并发提交 ${targetRefs.length} 个终端普通签到...`
					this.addLog('EXEC', `⚡ 启动微助教高并发秒签引擎 (0.1s 极速直达)...`)

					const res = await post('/api/signin/normal', {
						course_id: courseId,
						sign_id: signId,
						account_refs: targetRefs
					}, { timeout: 35000 })
					this.renderExecutionResults(res, targetRefs)

				} else if (isGps) {
					// ── B. GPS 定位签到 ──
					this.progressMsg = `正在全并发提交 ${targetRefs.length} 个终端 GPS 签到...`
					this.addLog('EXEC', `⚡ 启动 GPS 定位并发引擎 (为每个账号施加 5~10 米独立物理微扰动)...`)

					const res = await post('/api/signin/gps', {
						course_id: courseId,
						sign_id: signId,
						lat: this.baseLat,
						lon: this.baseLon,
						account_refs: targetRefs
					}, { timeout: 35000 })
					this.renderExecutionResults(res, targetRefs)

				} else if (isQr) {
					// ── C. 二维码签到（动态监听 15 秒并实时倒计时，控制台下方常驻扫码按钮） ──
					this.addLog('LISTEN', `📡 正在连接微助教实时频道，监听教师端切码...`)
					this.addLog('INFO', `👉 控制台下方已准备好【📷 立即扫码打卡】，您可随时点击！`)
					
					// 终端底部常驻显示扫码打卡按钮（允许用户随时点击跳过等待）
					this.showManualScanBtn = true

					// 异步在本地预热微信 Code
					post('/api/signin/prepare', { account_refs: targetRefs, force: true }).then((prepRes) => {
						if (prepRes && prepRes.codes) {
							this.cachedPreparedCodes = prepRes.codes
							this.addLog('AUTH', `🔑 账号微信凭证预热完成 (${prepRes.ready || targetRefs.length}/${targetRefs.length} 人)`)
						}
					}).catch(() => {})

					// 启动 15 秒动态倒计时流式感知
					let remainSec = 15
					this.progressMsg = `正在监听动态码广播 (剩余 ${remainSec}s)...`
					if (this.cdTimer) clearInterval(this.cdTimer)
					this.cdTimer = setInterval(() => {
						remainSec -= 1
						if (remainSec > 0) {
							this.progressMsg = `正在监听动态码广播 (剩余 ${remainSec}s)...`
						} else {
							if (this.cdTimer) { clearInterval(this.cdTimer); this.cdTimer = null; }
						}
					}, 1000)

					try {
						const wsRes = await post('/api/signin/auto-qr', {
							course_id: courseId,
							sign_id: signId,
							timeout_sec: 15,
							account_refs: targetRefs
						}, { timeout: 25000 })

						if (this.cdTimer) { clearInterval(this.cdTimer); this.cdTimer = null; }

						if (wsRes.success && wsRes.results) {
							this.addLog('SUCCESS', `⚡ 成功截获动态二维码！全员并发秒签成功！`)
							this.renderExecutionResults(wsRes, targetRefs)
							return
						}
					} catch (wsErr) {
						if (this.cdTimer) { clearInterval(this.cdTimer); this.cdTimer = null; }
						console.warn('WSS listen warning:', wsErr)
					}

					if (this.cdTimer) { clearInterval(this.cdTimer); this.cdTimer = null; }

					// 15 秒超时未在频道捕获到动态码
					this.isProgressFinished = true
					this.showManualScanBtn = true
					this.progressMsg = '15秒未截获动态码，请点击下方按钮扫码'
					this.addLog('WARN', `⚠ 15 秒通道内未收到切码广播 (可能为静态码或首码)`)
					this.addLog('INFO', `👉 请直接点击下方【📷 立即扫码打卡】完成签到！`)
				}

			} catch (e) {
				console.warn('Detect error:', e)
			} finally {
				this.isDetecting = false
			}
		}
	}
}
</script>
<style lang="scss" scoped>

/* ================== Ethos Design Tokens ================== */

.page-container {

	background-color: #F8F9FA;

	min-height: 100vh;

	box-sizing: border-box;

	color: #191C1D;

	font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'PingFang SC', 'Helvetica Neue', sans-serif;

}



/* Top App Bar */

.top-app-bar {

	position: fixed;

	top: 0;

	left: 0;

	right: 0;

	background: #F8F9FA;

	z-index: 50;

	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);

}

.app-bar-inner {

	height: 56px;

	display: flex;

	align-items: center;

	justify-content: space-between;

	padding: 0 20px;

}

.bar-btn {

	width: 40px;

	height: 40px;

	display: flex;

	align-items: center;

	justify-content: center;

	border-radius: 20px;

}

.icon-menu {

	font-size: 22px;

	color: #414755;

}

.app-title {

	font-size: 20px;

	font-weight: 700;

	color: #0058BC;

	letter-spacing: -0.2px;

}

.bar-btn-placeholder {

	width: 40px;

}



/* Main Content */

.main-content {

	padding: 16px 20px 40px 20px;

}



/* 1. 顶部模式按钮行 (Mode Trigger Button Cards) */

.trigger-buttons-row {

	display: grid;

	grid-template-columns: 1fr 1fr 1fr;

	gap: 10px;

	margin-bottom: 14px;

}



.mode-trigger-btn {

	background: #FFFFFF;

	border: 1px solid #E1E3E4;

	border-radius: 14px;

	padding: 10px 4px;

	display: flex;

	flex-direction: column;

	align-items: center;

	justify-content: center;

	gap: 2px;

	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);

	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

}



.mode-trigger-btn:active {

	transform: scale(0.96);

	background: #F0F4F9;

}



.mode-btn-title {

	font-size: 13px;

	font-weight: 700;

	color: #191C1D;

	line-height: 1.2;

}



.mode-btn-sub {

	font-size: 10px;

	font-weight: 600;

	color: #717786;

}



.highlight-btn {

	background: #F0F7FF;

	border-color: #A3C9FE;

}



.highlight-btn .mode-btn-title {

	color: #0058BC;

}



.highlight-btn .mode-btn-sub {

	color: #0058BC;

}



/* 2. 全自动签到守护引擎卡片 */

.daemon-card {

	background: #FFFFFF;

	border-radius: 16px;

	padding: 16px;

	border: 1px solid #E1E3E4;

	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);

	margin-bottom: 14px;

	transition: all 0.3s ease;

}

.daemon-card.daemon-active {

	border-color: #53E16F;

	background: #F4FDF6;

}

.daemon-header {

	display: flex;

	justify-content: space-between;

	align-items: center;

	margin-bottom: 10px;

}

.daemon-title-row {

	display: flex;

	align-items: center;

	gap: 10px;

}

.pulse-indicator {

	position: relative;

	width: 16px;

	height: 16px;

	display: flex;

	align-items: center;

	justify-content: center;

}

.pulse-ring {

	position: absolute;

	width: 16px;

	height: 16px;

	border-radius: 50%;

	background: #53E16F;

	opacity: 0.6;

	animation: pulse-anim 1.5s infinite;

}

.pulse-dot {

	width: 10px;

	height: 10px;

	border-radius: 50%;

	background: #C1C6D7;

}

.pulse-dot.dot-active {

	background: #006E28;

}

@keyframes pulse-anim {

	0% { transform: scale(0.8); opacity: 0.8; }

	100% { transform: scale(1.6); opacity: 0; }

}

.daemon-title {

	font-size: 16px;

	font-weight: 700;

	color: #191C1D;

}

.daemon-desc-row {

	display: flex;

	align-items: flex-start;

	gap: 8px;

}

.desc-dot {

	width: 8px;

	height: 8px;

	border-radius: 4px;

	background: #C1C6D7;

	margin-top: 6px;

	flex-shrink: 0;

}

.desc-dot-active {

	background: #53E16F;

}

.daemon-desc {

	font-size: 13px;

	color: #414755;

	line-height: 1.55;

}



/* 3. 快捷操作网格 (High-end Action Cards) */

.quick-cards-grid {

	display: grid;

	grid-template-columns: 1fr 1fr;

	gap: 12px;

	margin-bottom: 14px;

}



.action-card {

	border-radius: 16px;

	padding: 16px 14px;

	display: flex;

	flex-direction: column;

	justify-content: space-between;

	min-height: 98px;

	box-sizing: border-box;

	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);

}



.action-card:active {

	transform: scale(0.98);

}



.card-scan {

	background: linear-gradient(135deg, #0058BC 0%, #003F8A 100%);

	color: #FFFFFF;

	border: 1px solid rgba(255, 255, 255, 0.12);

}



.card-account {

	background: #FFFFFF;

	border: 1px solid #D8E2FF;

}



.card-badge-row {

	display: flex;

	align-items: center;

	justify-content: space-between;

	margin-bottom: 10px;

}



.card-pill {

	font-size: 11px;

	font-weight: 700;

	padding: 3px 8px;

	border-radius: 6px;

	letter-spacing: 0.5px;

}



.primary-pill {

	background: rgba(255, 255, 255, 0.2);

	color: #FFFFFF;

}



.neutral-pill {

	background: #EEF2F6;

	color: #0058BC;

}



/* 科技感微动效扫描取景器图标 */

.scanner-glyph {

	position: relative;

	width: 22px;

	height: 22px;

	display: flex;

	align-items: center;

	justify-content: center;

}

.glyph-corner {

	position: absolute;

	width: 6px;

	height: 6px;

	border-color: #FFFFFF;

	border-style: solid;

}

.glyph-corner.tl {

	top: 0;

	left: 0;

	border-width: 2px 0 0 2px;

	border-top-left-radius: 3px;

}

.glyph-corner.tr {

	top: 0;

	right: 0;

	border-width: 2px 2px 0 0;

	border-top-right-radius: 3px;

}

.glyph-corner.bl {

	bottom: 0;

	left: 0;

	border-width: 0 0 2px 2px;

	border-bottom-left-radius: 3px;

}

.glyph-corner.br {

	bottom: 0;

	right: 0;

	border-width: 0 2px 2px 0;

	border-bottom-right-radius: 3px;

}

.glyph-laser {

	width: 14px;

	height: 2px;

	background: #53E16F;

	box-shadow: 0 0 6px #53E16F;

	border-radius: 1px;

	animation: laser-scan 1.8s ease-in-out infinite alternate;

}

@keyframes laser-scan {

	0% { transform: translateY(-5px); opacity: 0.6; }

	100% { transform: translateY(5px); opacity: 1; }

}



.card-plus {

	font-size: 16px;

	font-weight: 700;

	color: #0058BC;

}



.card-text-group {

	display: flex;

	flex-direction: column;

	gap: 3px;

}



.card-main-title {

	font-size: 16px;

	font-weight: 700;

	line-height: 1.2;

}



.card-scan .card-main-title {

	color: #FFFFFF;

}



.card-account .card-main-title {

	color: #191C1D;

}



.card-sub-title {

	font-size: 11px;

	line-height: 1.3;

}



.card-scan .card-sub-title {

	color: rgba(255, 255, 255, 0.75);

}



.card-account .card-sub-title {

	color: #717786;

}



/* 4. GPS 坐标配置（紧凑轻量化设计） */

.gps-compact-card {

	background: #FFFFFF;

	border-radius: 16px;

	padding: 14px 16px;

	border: 1px solid #E1E3E4;

	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);

	margin-bottom: 14px;

}



.gps-compact-header {

	display: flex;

	justify-content: space-between;

	align-items: center;

	margin-bottom: 10px;

}



.gps-title {

	font-size: 14px;

	font-weight: 700;

	color: #191C1D;

}



.gps-btn-group {

	display: flex;

	align-items: center;

	gap: 8px;

}



.gps-action-btn {

	padding: 5px 12px;

	border-radius: 8px;

	display: flex;

	align-items: center;

	justify-content: center;

	transition: all 0.15s;

}



.locate-btn {

	background: #EEF2F6;

	border: 1px solid #E1E3E4;

}



.locate-btn:active {

	background: #E1E3E4;

}



.save-btn {

	background: #0058BC;

}



.save-btn:active {

	background: #004493;

}



.gps-btn-text {

	font-size: 12px;

	font-weight: 600;

	color: #414755;

}



.save-text {

	color: #FFFFFF;

}



.gps-compact-body {

	display: grid;

	grid-template-columns: 1fr 1fr;

	gap: 10px;

}



.gps-chip {

	display: flex;

	align-items: center;

	background: #F8F9FA;

	border: 1px solid #E1E3E4;

	border-radius: 10px;

	padding: 0 10px;

	height: 38px;

}



.chip-tag {

	font-size: 12px;

	font-weight: 700;

	color: #717786;

	margin-right: 8px;

	flex-shrink: 0;

}



.chip-input {

	flex: 1;

	font-size: 13px;

	font-weight: 600;

	color: #191C1D;

	height: 100%;

}



/* 5. 通用 Ethos 卡片 */

.ethos-card {

	background: #FFFFFF;

	border-radius: 16px;

	padding: 18px;

	border: 1px solid #E1E3E4;

	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);

	margin-bottom: 16px;

}

.card-header {

	display: flex;

	justify-content: space-between;

	align-items: center;

	margin-bottom: 16px;

}

.card-title {

	font-size: 17px;

	font-weight: 700;

	color: #191C1D;

}

.card-actions-right {

	display: flex;

	align-items: center;

	gap: 8px;

}

.cloud-sync-btn {

	display: inline-flex;

	align-items: center;

	justify-content: center;

	padding: 6px 14px;

	background: #EEF2F6;

	border: 1px solid #D8E2FF;

	border-radius: 20px;

	transition: all 0.2s;

}



.cloud-sync-btn:active {

	background: #D8E2FF;

	transform: scale(0.96);

}



.cloud-btn-text {

	font-size: 12px;

	font-weight: 700;

	color: #0058BC;

	letter-spacing: 0.3px;

}



/* 账号列表 */

.accounts-list {

	display: flex;

	flex-direction: column;

}

.account-item {

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding: 12px 16px; /* increased horizontal padding */

    border: 1px solid #E1E3E4;

    border-radius: 8px;

    margin-bottom: 12px; /* increased gap between items */

    box-sizing: border-box;

}

.acc-left {

	display: flex;

	align-items: center;

	gap: 12px;

	flex: 1;

	min-width: 0;

}

.avatar-wrap {

	position: relative;

	width: 44px;

	height: 44px;

	flex-shrink: 0;

}

.avatar-img {

	width: 44px;

	height: 44px;

	border-radius: 22px;

	background: #E7E8E9;

}

.status-dot {

	position: absolute;

	bottom: 0;

	right: 0;

	width: 12px;

	height: 12px;

	border-radius: 6px;

	border: 2px solid #FFFFFF;

}

.dot-alive { background: #53E16F; }

.dot-dead { background: #BA1A1A; }

.acc-info {

	display: flex;

	flex-direction: column;

	gap: 3px;

	min-width: 0;

}

.name-row {

	display: flex;

	align-items: center;

	gap: 6px;

}

.acc-name {

	font-size: 15px;

	font-weight: 700;

	color: #191C1D;

	white-space: nowrap;

	overflow: hidden;

	text-overflow: ellipsis;

}

.time-meta-row {

	display: flex;

	align-items: center;

	gap: 6px;

}

.time-meta-item {

	font-size: 11px;

	color: #717786;

	font-weight: 500;

}

.time-meta-dot {

	font-size: 10px;

	color: #C1C6D7;

}



/* 账号右侧展开胶囊区域 */

.acc-right {

	display: flex;

	align-items: center;

	gap: 6px;

	flex-shrink: 0;

}



.capsule-vertical-stack {

	display: flex;

	flex-direction: column;

	gap: 4px;

	align-items: flex-end;

	justify-content: center;

	animation: fadeIn 0.15s ease;

}



.action-capsule-sm {

	padding: 2px 10px;

	border-radius: 10px;

	display: flex;

	align-items: center;

	justify-content: center;

	transition: all 0.12s;

	height: 22px;

	box-sizing: border-box;

}



.action-capsule-sm:active {

	transform: scale(0.92);

}



.rescan-capsule-sm {

	background: #E8F0FE;

	border: 1px solid #A3C9FE;

}



.rescan-capsule-sm .capsule-sm-text {

	font-size: 11px;

	font-weight: 700;

	color: #0058BC;

	line-height: 1;

}



.delete-capsule-sm {

	background: #FDE8E8;

	border: 1px solid #F9B4B4;

}



.delete-capsule-sm .capsule-sm-text {

	font-size: 11px;

	font-weight: 700;

	color: #BA1A1A;

	line-height: 1;

}



.acc-menu-trigger-wrap {

	display: flex;

	align-items: center;

	gap: 6px;

}



.more-dot-btn {

	width: 32px;

	height: 32px;

	border-radius: 16px;

	display: flex;

	align-items: center;

	justify-content: center;

	transition: background 0.15s;

}



.more-dot-btn:active {

	background: #EEF2F6;

}



.more-dot-icon {

	font-size: 18px;

	font-weight: 700;

	color: #717786;

	line-height: 1;

}



.rescan-pill {

	background: #FFEBEB;

	padding: 4px 10px;

	border-radius: 12px;

}

.rescan-pill text {

	font-size: 11px;

	font-weight: 600;

	color: #FF3B30;

}

.empty-state {

	padding: 30px 0;

	display: flex;

	flex-direction: column;

	align-items: center;

	gap: 8px;

}

.empty-emoji {

	font-size: 36px;

}

.empty-text {

	font-size: 13px;

	color: #717786;

}

.add-more-btn {

	margin-top: 14px;

	width: 100%;

	height: 44px;

	line-height: 44px;

	background: transparent;

	border: 1px dashed #0058BC;

	color: #0058BC;

	border-radius: 10px;

	font-size: 14px;

	font-weight: 600;

	text-align: center;

}

.add-more-btn:active {

	background: rgba(0, 88, 188, 0.05);

}

.add-more-btn::after {

	border: none;

}



/* 控制台 Shell 弹窗 */

.blur-mask {
	position: fixed;
	top: 0; left: 0; right: 0; bottom: 0;
	background: rgba(0,0,0,0.75);
	backdrop-filter: blur(4px);
	z-index: 999;
	display: flex;
	flex-direction: column;
	justify-content: flex-end;
	opacity: 0;
	pointer-events: none;
	transition: opacity 0.25s ease;
}
.blur-mask.terminal-mask {
	justify-content: center;
	align-items: center;
	padding: 20rpx;
	box-sizing: border-box;
}

.blur-mask.mask-active {

	opacity: 1;

	pointer-events: auto;

}

.shell-modal {
	width: 92vw;
	max-width: 680rpx;
	max-height: 82vh;
	margin: auto;
	background: #0D1117;
	border-radius: 18px;
	overflow: hidden;
	box-shadow: 0 24px 60px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.1);
	display: flex;
	flex-direction: column;
	animation: popIn 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.shell-header {
	background: #161B22;
	padding: 10px 14px;
	display: flex;
	align-items: center;
	position: relative;
	border-bottom: 1px solid rgba(255,255,255,0.06);
}
.mac-dots {
	display: flex;
	gap: 6px;
}
.dot {
	width: 10px;
	height: 10px;
	border-radius: 50%;
}
.dot.red { background: #FF5F56; }
.dot.yellow { background: #FFBD2E; }
.dot.green { background: #27C93F; }
.shell-title {
	position: absolute;
	left: 0; right: 0;
	text-align: center;
	font-size: 12px;
	color: #8B949E;
	font-weight: 600;
	font-family: 'JetBrains Mono', Consolas, monospace;
	letter-spacing: 0.5px;
}
.shell-body {
	background: #0D1117;
	padding: 12px 14px;
	box-sizing: border-box;
}
.shell-status-row {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-bottom: 10px;
	border-bottom: 1px solid rgba(255,255,255,0.06);
	padding-bottom: 8px;
}
.shell-status {
	color: #58A6FF;
	font-family: 'JetBrains Mono', Consolas, monospace;
	font-size: 12px;
	font-weight: 700;
	word-break: break-all;
}
.terminal-spinner {
	width: 12px;
	height: 12px;
	border: 2px solid rgba(88,166,255,.3);
	border-top-color: #58A6FF;
	border-radius: 50%;
	animation: terminal-spin .75s linear infinite;
	flex-shrink: 0;
}
@keyframes terminal-spin { to { transform: rotate(360deg); } }
.shell-logs {
	height: 300px;
	box-sizing: border-box;
}
.log-line {
	margin-bottom: 7px;
	font-family: 'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace;
	font-size: 12px;
	line-height: 1.55;
	word-break: break-all;
	word-wrap: break-word;
	display: flex;
	flex-wrap: wrap;
	align-items: flex-start;
}
.log-time {
	color: #6E7681;
	font-size: 11px;
	margin-right: 6px;
	flex-shrink: 0;
}
.log-tag {
	font-size: 11px;
	font-weight: 700;
	margin-right: 6px;
	flex-shrink: 0;
}
.log-text {
	flex: 1;
	word-break: break-all;
}

/* 极客配色徽标与文案 */
.level-info .log-tag { color: #58A6FF; }
.level-info .log-text { color: #C9D1D9; }

.level-discover .log-tag { color: #79C0FF; }
.level-discover .log-text { color: #E6EDF3; font-weight: 600; }

.level-auth .log-tag { color: #D2A8FF; }
.level-auth .log-text { color: #E6EDF3; }

.level-exec .log-tag { color: #56D4DD; }
.level-exec .log-text { color: #C9D1D9; }

.level-listen .log-tag { color: #FFA657; }
.level-listen .log-text { color: #C9D1D9; }

.level-success .log-tag { color: #7EE787; }
.level-success .log-text { color: #7EE787; font-weight: 600; }

.level-warn .log-tag { color: #E3B341; }
.level-warn .log-text { color: #E3B341; }

.level-error .log-tag { color: #FF7B72; }
.level-error .log-text { color: #FFA198; }

.level-done .log-tag { color: #7EE787; }
.level-done .log-text { color: #7EE787; font-weight: 700; }

.shell-footer {
	display: flex;
	gap: 10px;
	justify-content: center;
	align-items: center;
	padding: 12px 14px 16px;
	background: #161B22;
	border-top: 1px solid rgba(255,255,255,0.06);
}
.shell-btn {
	height: 68rpx;
	line-height: 68rpx;
	background: rgba(255,255,255,0.08);
	color: #C9D1D9;
	font-size: 24rpx;
	border-radius: 34rpx;
	font-family: 'JetBrains Mono', Consolas, monospace;
	font-weight: 600;
	padding: 0 28rpx;
	text-align: center;
	border: 1px solid rgba(255,255,255,0.1);
}
.shell-btn:active {
	background: rgba(255,255,255,0.15);
}
.shell-btn.salvage-btn {
	background: #238636;
	color: #FFFFFF;
	border: 1px solid rgba(255,255,255,0.2);
	box-shadow: 0 2px 8px rgba(35, 134, 54, 0.4);
}
.shell-btn.salvage-btn:active {
	background: #2EA043;
}
.shell-btn.direct-scan-btn {
	background: #1F6FEB;
	color: #FFFFFF;
	border: 1px solid rgba(255,255,255,0.2);
	box-shadow: 0 2px 10px rgba(31, 111, 235, 0.5);
	animation: pulse-blue 1.5s infinite;
}
.shell-btn.direct-scan-btn:active {
	background: #388BFD;
}
@keyframes pulse-blue {
	0% { transform: scale(1); }
	50% { transform: scale(1.03); }
	100% { transform: scale(1); }
}
.shell-btn::after {
	border: none;
}

/* 底部抽屉 Sheet 弹窗 */

.sheet-modal {

	background: #FFFFFF;

	border-radius: 20px 20px 0 0;

	padding: 20px;

	max-height: 80vh;

}

.sheet-header {

	display: flex;

	justify-content: space-between;

	align-items: center;

	margin-bottom: 16px;

}

.sheet-title-row {

	display: flex;

	align-items: center;

	gap: 8px;

}

.sheet-title {

	font-size: 17px;

	font-weight: 700;

	color: #191C1D;

}

.sheet-sub-badge {

	font-size: 11px;

	background: #EEF2F6;

	color: #0058BC;

	padding: 2px 8px;

	border-radius: 10px;

	font-weight: 600;

}

.sheet-header-actions {

	display: flex;

	align-items: center;

	gap: 14px;

}

.sheet-action-link {

	font-size: 13px;

	font-weight: 600;

	color: #0058BC;

	padding: 4px 6px;

}

.sheet-action-link:active {

	opacity: 0.7;

}

.sheet-close {

	font-size: 13px;

	color: #717786;

	padding: 4px 6px;

}

.sheet-close:active {

	opacity: 0.7;

}

.sync-list {

	display: flex;

	flex-direction: column;

	gap: 10px;

}

.sync-item {

	display: flex;

	align-items: center;

	justify-content: space-between;

	padding: 10px 14px;

	background: #F8F9FA;

	border: 1.5px solid transparent;

	border-radius: 14px;

	transition: all 0.2s ease;

}

.sync-item:active {

	transform: scale(0.99);

}

.sync-item-selected {

	background: #F0F7FF;

	border-color: #A3C9FE;

}

.sync-item-left {

	display: flex;

	align-items: center;

	gap: 10px;

	flex: 1;

}

.sync-check-wrap {

	display: flex;

	align-items: center;

	justify-content: center;

}

.sync-avatar {

	width: 38px;

	height: 38px;

	border-radius: 19px;

	background: #E7E8E9;

	flex-shrink: 0;

}

.sync-meta {

	display: flex;

	flex-direction: column;

	gap: 2px;

	min-width: 0;

}

.sync-name {

	font-size: 14px;

	font-weight: 700;

	color: #191C1D;

	white-space: nowrap;

	overflow: hidden;

	text-overflow: ellipsis;

}

.sync-desc {

	font-size: 11px;

	color: #717786;

}

.sync-badge {

	font-size: 11px;

	padding: 3px 8px;

	border-radius: 10px;

	font-weight: 600;

	flex-shrink: 0;

}

.sync-badge.alive {

	background: #E5F9ED;

	color: #006E28;

}

.sync-badge.dead {

	background: #FFEBEB;

	color: #BA1A1A;

}

.confirm-sync-btn {

	width: 100%;

	height: 44px;

	line-height: 44px;

	background: #0058BC;

	color: #FFFFFF;

	font-size: 14px;

	font-weight: 700;

	border-radius: 12px;

	text-align: center;

}

.author-body {

	padding: 10px 0;

}

.paragraph {

	font-size: 14px;

	line-height: 1.6;

	color: #414755;

	margin-bottom: 12px;

}

.author-meta {

	margin-top: 16px;

	display: flex;

	flex-direction: column;

	gap: 4px;

}

.author-name {

	font-size: 14px;

	font-weight: 700;

	color: #0058BC;

}

.author-contact {

	font-size: 12px;

	color: #717786;

}



@keyframes fadeIn {

	from { opacity: 0; transform: scale(0.92); }

	to { opacity: 1; transform: scale(1); }

}

</style>





