<template>
	<view class="page-container">
		<!-- Top App Bar -->
		<view class="top-app-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
			<view class="app-bar-inner">
				<view class="back-btn" @tap="goBack">
					<text class="back-icon">←</text>
				</view>
				<text class="app-title">添加账号</text>
				<view class="bar-btn-placeholder"></view>
			</view>
		</view>

		<view class="main-content" :style="{ paddingTop: (statusBarHeight + 56) + 'px' }">
			<!-- Notice Box -->
			<view class="notice-card">
				<text class="notice-icon">ℹ️</text>
				<view class="notice-text-wrap">
					<text class="notice-title">{{ targetRef ? '定向重扫说明' : '微信授权登录说明' }}</text>
					<text class="notice-desc">
						{{ targetRef ? `正在为「${targetName}」恢复凭证，请确保使用该微信账号扫码。` : '使用微信扫描下方二维码进行授权，系统将自动关联并建立保活。' }}
					</text>
				</view>
			</view>

			<!-- QR Code Area -->
			<view class="qr-main-card">
				<view class="qr-box" @tap="createQR">
					<view v-if="qrLoading" class="qr-loading-box">
						<view class="qr-card-spinner"></view>
						<text class="qr-loading-text">正在生成登录二维码...</text>
					</view>
					<view v-else-if="!qrImage" class="qr-empty">
						<text class="qr-placeholder-icon">📱</text>
						<text class="qr-placeholder-text">点击生成登录二维码</text>
					</view>
					<image v-else class="qr-image" :src="qrImage" mode="aspectFit"></image>
				</view>
				<text class="qr-status-text" :class="statusClass">{{ statusText }}</text>
				<text class="qr-sub-tip">请使用手机微信“扫一扫”完成登录授权</text>
			</view>

			<!-- Steps Card -->
			<view class="steps-card">
				<text class="steps-title">操作步骤</text>
				<view class="step-row">
					<view class="step-num-badge">1</view>
					<text class="step-text">系统生成微助教专属登录二维码</text>
				</view>
				<view class="step-row">
					<view class="step-num-badge">2</view>
					<text class="step-text">打开微信，使用“扫一扫”功能扫描二维码</text>
				</view>
				<view class="step-row">
					<view class="step-num-badge">3</view>
					<text class="step-text">在手机微信上确认登录授权</text>
				</view>
				<view class="step-row">
					<view class="step-num-badge">4</view>
					<text class="step-text">{{ targetRef ? '系统自动恢复并更新账号凭证' : '系统自动关联并保存微信账号信息' }}</text>
				</view>
			</view>

			<view v-if="status === 'authorized' || status === 'confirmed'" class="save-confirm-btn" @tap="confirmAndSave">
				<text>确认并关联账号</text>
			</view>

			<view style="height: 30px;"></view>
		</view>
	</view>
</template>

<script>
import { post, get } from '../../api/request'

export default {
	data() {
		return {
			statusBarHeight: 20,
			sessionId: '',
			qrImage: '',
			qrLoading: false,
			status: '',
			polling: false,
			pollTimer: null,
			isPollingRequest: false,
			saving: false,
			targetRef: '',
			targetName: ''
		}
	},
	computed: {
		statusText() {
			if (this.qrLoading) return '正在生成二维码...'
			const map = {
				'': '点击上方生成二维码',
				'pending': '等待扫码...',
				'scanned': '已扫码，请在手机微信中确认',
				'authorized': '已授权！正在自动保存...',
				'confirmed': this.targetRef ? '凭证已恢复！' : '账号关联成功！',
				'expired': '二维码已过期，请点击重新生成',
				'cancelled': '已取消登录',
				'mismatch': '⚠️ 微信号不匹配，请使用原账号扫码'
			}
			return map[this.status] || this.status
		},
		statusClass() {
			if (['authorized', 'confirmed'].includes(this.status)) return 'text-success'
			if (['expired', 'cancelled', 'mismatch'].includes(this.status)) return 'text-danger'
			if (this.status === 'scanned') return 'text-warning'
			return 'text-primary'
		}
	},
	onLoad(options) {
		const sys = uni.getSystemInfoSync()
		this.statusBarHeight = sys.statusBarHeight || 20
		if (options.target_ref) {
			this.targetRef = decodeURIComponent(options.target_ref)
			this.targetName = decodeURIComponent(options.target_name || '未知账号')
		}
		this.createQR()
	},
	onShow() {
		if (this.sessionId && ['pending', 'scanned'].includes(this.status) && !this.polling) {
			this.startPolling()
		}
	},
	onHide() {
		this.stopPolling()
		uni.hideLoading()
	},
	onUnload() {
		this.stopPolling()
		uni.hideLoading()
	},
	methods: {
		goBack() {
			this.stopPolling()
			uni.hideLoading()
			uni.navigateBack()
		},
		async createQR() {
			if (this.qrLoading) return
			this.qrLoading = true
			this.stopPolling()
			try {
				const data = await post('/api/accounts/qr', null, { timeout: 10000 })
				if (data && data.session_id) {
					this.sessionId = data.session_id
					this.qrImage = data.image_base64
					this.status = 'pending'
					this.startPolling()
				} else {
					throw new Error('未获取到二维码数据')
				}
			} catch (e) {
				this.status = 'expired'
				uni.showToast({ title: '生成失败: ' + (e.message || '网络超时'), icon: 'none' })
			} finally {
				this.qrLoading = false
				uni.hideLoading()
			}
		},
		startPolling() {
			this.stopPolling()
			this.polling = true
			this._pollStep()
		},
		async _pollStep() {
			if (!this.polling || !this.sessionId || this.isPollingRequest) return
			this.isPollingRequest = true
			try {
				const data = await get(`/api/accounts/qr/${this.sessionId}/poll`, null, { timeout: 12000 })
				if (!this.polling) return
				if (data && data.status) {
					this.status = data.status
					if (data.status === 'authorized') {
						this.stopPolling()
						this.confirmAndSave()
						return
					} else if (['expired', 'cancelled', 'confirmed'].includes(data.status)) {
						this.stopPolling()
						return
					}
				}
			} catch (e) {
				console.warn('Poll notice:', e.message || e)
			} finally {
				this.isPollingRequest = false
				if (this.polling) {
					this.pollTimer = setTimeout(() => {
						this._pollStep()
					}, 1500)
				}
			}
		},
		stopPolling() {
			this.polling = false
			this.isPollingRequest = false
			if (this.pollTimer) {
				clearTimeout(this.pollTimer)
				this.pollTimer = null
			}
		},
		async confirmAndSave() {
			if (this.saving) return
			this.saving = true
			uni.showLoading({ title: this.targetRef ? '恢复凭证中...' : '保存中...' })
			try {
				let url = `/api/accounts/qr/${this.sessionId}/confirm`
				if (this.targetRef) {
					url += `?target_ref=${encodeURIComponent(this.targetRef)}`
				}

				const data = await post(url, null, { timeout: 15000 })
				uni.hideLoading()

				if (data && data.success === false) {
					this.status = 'mismatch'
					this.saving = false
					uni.showModal({
						title: '微信号不匹配',
						content: data.message || '请使用原来的微信号扫码',
						showCancel: false,
					})
					return
				}

				this.status = 'confirmed'
				const nickname = (data && data.nickname) || '账号'
				if (this.targetRef) {
					uni.showToast({ title: `${nickname} 凭证已恢复`, icon: 'success' })
				} else {
					uni.showToast({ title: `${nickname} 添加成功`, icon: 'success' })
				}

				try {
					await this.$store.dispatch('syncAccounts')
				} catch (_) {}

				setTimeout(() => {
					this.saving = false
					uni.navigateBack()
				}, 1500)
			} catch (e) {
				this.saving = false
				uni.hideLoading()
				try {
					await this.$store.dispatch('syncAccounts')
				} catch (_) {}
				uni.showModal({
					title: '提示',
					content: e.message || '操作失败，请返回查看账号状态',
					showCancel: false,
					success: () => uni.navigateBack()
				})
			} finally {
				uni.hideLoading()
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
	padding: 0 16px;
}
.back-btn {
	width: 40px;
	height: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 20px;
}
.back-icon {
	font-size: 24px;
	color: #414755;
	font-weight: bold;
}
.app-title {
	font-size: 18px;
	font-weight: 700;
	color: #0058BC;
}
.bar-btn-placeholder {
	width: 40px;
}

/* Main Content */
.main-content {
	padding: 16px 20px 40px 20px;
	display: flex;
	flex-direction: column;
	gap: 16px;
}

/* Notice Box */
.notice-card {
	background: #FFFFFF;
	border-radius: 16px;
	padding: 16px;
	border: 1px solid #E1E3E4;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
	display: flex;
	align-items: flex-start;
	gap: 12px;
	margin-bottom: 16px;
}
.notice-icon {
	font-size: 20px;
	flex-shrink: 0;
	margin-top: 2px;
}
.notice-text-wrap {
	display: flex;
	flex-direction: column;
	gap: 4px;
}
.notice-title {
	font-size: 15px;
	font-weight: 700;
	color: #191C1D;
}
.notice-desc {
	font-size: 13px;
	color: #414755;
	line-height: 1.5;
}

/* QR Card */
.qr-main-card {
	background: #FFFFFF;
	border-radius: 20px;
	padding: 28px 20px;
	border: 1px solid #E1E3E4;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
	display: flex;
	flex-direction: column;
	align-items: center;
	text-align: center;
	margin-bottom: 16px;
}
.qr-box {
	width: 210px;
	height: 210px;
	background: #F8F9FA;
	border-radius: 16px;
	border: 2px dashed #C1C6D7;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: 16px;
	overflow: hidden;
}
.qr-loading-box {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 12px;
	padding: 20px;
}
.qr-card-spinner {
	width: 36px;
	height: 36px;
	border: 3px solid rgba(0, 88, 188, 0.15);
	border-top-color: #0058BC;
	border-radius: 50%;
	animation: spin 0.8s linear infinite;
}
.qr-loading-text {
	font-size: 13px;
	color: #0058BC;
	font-weight: 600;
}
@keyframes spin {
	to { transform: rotate(360deg); }
}
.qr-empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 8px;
}
.qr-placeholder-icon {
	font-size: 40px;
}
.qr-placeholder-text {
	font-size: 13px;
	color: #0058BC;
	font-weight: 600;
}
.qr-image {
	width: 200px;
	height: 200px;
	border-radius: 12px;
}
.qr-status-text {
	font-size: 16px;
	font-weight: 700;
	margin-bottom: 6px;
}
.text-primary { color: #0058BC; }
.text-success { color: #006E28; }
.text-warning { color: #9E3D00; }
.text-danger { color: #BA1A1A; }
.qr-sub-tip {
	font-size: 13px;
	color: #717786;
}

/* Steps Card */
.steps-card {
	background: #FFFFFF;
	border-radius: 16px;
	padding: 18px;
	border: 1px solid #E1E3E4;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
	margin-bottom: 16px;
}
.steps-title {
	font-size: 15px;
	font-weight: 700;
	color: #191C1D;
	margin-bottom: 14px;
	display: block;
}
.step-row {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-bottom: 12px;
}
.step-row:last-child {
	margin-bottom: 0;
}
.step-num-badge {
	width: 24px;
	height: 24px;
	border-radius: 12px;
	background: #0070EB;
	color: #FFFFFF;
	font-size: 12px;
	font-weight: bold;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}
.step-text {
	font-size: 13px;
	color: #191C1D;
	line-height: 1.4;
}

.save-confirm-btn {
	height: 48px;
	line-height: 48px;
	background: #0058BC;
	color: #FFFFFF;
	font-size: 15px;
	font-weight: 700;
	border-radius: 12px;
	text-align: center;
	box-shadow: 0 4px 12px rgba(0, 88, 188, 0.25);
}
</style>

