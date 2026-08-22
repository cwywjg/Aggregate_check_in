<template>
	<view class="page">
		<view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
			<view class="nav-content">
				<text class="nav-title">设置</text>
			</view>
		</view>

		<scroll-view scroll-y class="content" :style="{ paddingTop: (statusBarHeight + 88) + 'px' }">
			<!-- 服务器信息 -->
			<view class="section">
				<text class="section-title">服务器</text>
				<view class="glass-card">
					<view class="setting-row" @tap="goLogin">
						<text class="setting-label">服务器地址</text>
						<text class="setting-value">{{ serverUrl || '未配置' }}</text>
						<text class="arrow">›</text>
					</view>
					<view class="divider"></view>
					<view class="setting-row">
						<text class="setting-label">连接状态</text>
						<view class="status-dot" :class="serverOnline ? 'online' : 'offline'"></view>
						<text class="setting-value" :class="serverOnline ? 'text-success' : 'text-danger'">
							{{ serverOnline ? '已连接' : '未连接' }}
						</text>
					</view>
					<view class="divider"></view>
					<view class="setting-row" @tap="testConnection">
						<text class="setting-label text-brand">测试连接</text>
					</view>
				</view>
			</view>


			<!-- 关于 -->
			<view class="section">
				<text class="section-title">关于</text>
				<view class="glass-card">
					<view class="setting-row">
						<text class="setting-label">版本</text>
						<text class="setting-value">1.0.0</text>
					</view>
					<view class="divider"></view>
					<view class="setting-row">
						<text class="setting-label">项目</text>
						<text class="setting-value">天商便捷助手</text>
					</view>
				</view>
			</view>

			<!-- 危险操作 -->
			<view class="section">
				<view class="glass-card">
					<view class="setting-row" @tap="clearData">
						<text class="setting-label text-danger">清除本地数据</text>
					</view>
				</view>
			</view>
		</scroll-view>
	</view>
</template>

<script>
import { checkServer } from '../../api/request'

export default {
	data() {
		return {
			statusBarHeight: 0
		}
	},
	computed: {
		serverUrl() { return this.$store.state.serverUrl },
		serverOnline() { return this.$store.state.serverOnline }
	},
	onLoad() {
		const sysInfo = uni.getSystemInfoSync()
		this.statusBarHeight = sysInfo.statusBarHeight || 20
	},
	onShow() {
		this.$store.dispatch('checkServerHealth')
	},
	methods: {
		goLogin() {
			uni.navigateTo({ url: '/pages/login/index' })
		},

		async testConnection() {
			uni.showLoading({ title: '测试中...' })
			const ok = await this.$store.dispatch('checkServerHealth')
			uni.hideLoading()
			uni.showToast({
				title: ok ? '连接正常' : '连接失败',
				icon: ok ? 'success' : 'none'
			})
		},
		clearData() {
			uni.showModal({
				title: '警告',
				content: '确定清除所有本地数据？（不影响服务端数据）',
				success: (res) => {
					if (res.confirm) {
						uni.clearStorageSync()
						this.$store.commit('SET_ACCOUNTS', [])
						this.$store.commit('SET_SERVER', { url: '', apiKey: '' })
						uni.showToast({ title: '已清除', icon: 'success' })
						setTimeout(() => {
							uni.reLaunch({ url: '/pages/login/index' })
						}, 1000)
					}
				}
			})
		}
	}
}
</script>

<style lang="scss" scoped>
.page {
	min-height: 100vh;
	background: #F2F2F7;
}

.nav-bar {
	position: fixed; top: 0; left: 0; right: 0; z-index: 100;
	background: rgba(255, 255, 255, 0.98);
	border-bottom: 0.5px solid rgba(0, 0, 0, 0.08);
}

.nav-content {
	height: 88rpx;
	display: flex; align-items: center; justify-content: center;
}

.nav-title { font-size: 34rpx; font-weight: 700; color: #1C1C1E; }

.content { padding: 24rpx 30rpx; }

.section { margin-bottom: 36rpx; }

.section-title {
	font-size: 26rpx;
	font-weight: 600;
	color: #8E8E93;
	margin-bottom: 16rpx;
	margin-left: 8rpx;
	display: block;
}

.setting-row {
	display: flex;
	align-items: center;
	padding: 28rpx 0;
}

.setting-label {
	flex: 1;
	font-size: 28rpx;
	color: #1C1C1E;
}

.setting-value {
	font-size: 26rpx;
	color: #8E8E93;
	margin-right: 12rpx;
}

.arrow { font-size: 32rpx; color: #C7C7CC; }

.divider {
	height: 1px;
	background: rgba(0, 0, 0, 0.04);
}

.status-dot {
	width: 14rpx;
	height: 14rpx;
	border-radius: 50%;
	margin-right: 12rpx;
}

.online { background: #34C759; box-shadow: 0 0 6rpx rgba(52,199,89,0.4); }
.offline { background: #FF3B30; }

.text-brand { color: #0A84FF; font-weight: 600; }
</style>
