<template>
	<view class="page">
		<view class="header">
			<image class="logo" src="/static/logo.png" mode="aspectFit"></image>
			<text class="title">天商便捷助手</text>
			<text class="subtitle">连接你的后端服务器</text>
		</view>

		<view class="form-area">
			<view class="glass-card">
				<view class="field">
					<text class="label">服务器地址</text>
					<input class="input" v-model="serverUrl" placeholder="http://192.168.1.100:5000"
						placeholder-class="placeholder"></input>
				</view>
				<view class="field">
					<text class="label">API Key</text>
					<input class="input" v-model="apiKey" placeholder="tjcu-helper-2026"
						placeholder-class="placeholder" :password="!showKey"></input>
					<text class="toggle-key" @tap="showKey = !showKey">{{ showKey ? '隐藏' : '显示' }}</text>
				</view>
			</view>

			<view class="btn-primary connect-btn" :class="{ 'btn-loading': connecting }" @tap="connect">
				<text v-if="!connecting">连接服务器</text>
				<text v-else>连接中...</text>
			</view>

			<view class="status-area" v-if="statusMsg">
				<text :class="statusOk ? 'text-success' : 'text-danger'">{{ statusMsg }}</text>
			</view>
		</view>
	</view>
</template>

<script>
import { checkServer } from '../../api/request'

export default {
	data() {
		return {
			serverUrl: 'http://127.0.0.1:17521',
			apiKey: 'your-secure-api-key-here',
			showKey: false,
			connecting: false,
			statusMsg: '',
			statusOk: false
		}
	},
	onLoad() {
		this.serverUrl = uni.getStorageSync('serverUrl') || 'http://127.0.0.1:17521'
		this.apiKey = uni.getStorageSync('apiKey') || 'your-secure-api-key-here'
	},
	methods: {
		async connect() {
			if (this.connecting) return
			let url = this.serverUrl.trim()
			if (!url) {
				uni.showToast({ title: '请输入服务器地址', icon: 'none' })
				return
			}
			// 去掉末尾斜杠
			url = url.replace(/\/+$/, '')
			this.serverUrl = url

			this.connecting = true
			this.statusMsg = ''

			try {
				const ok = await checkServer(url)
				if (ok) {
					this.$store.commit('SET_SERVER', { url, apiKey: this.apiKey })
					this.statusMsg = '连接成功!'
					this.statusOk = true
					// 同步账号
					try {
						await this.$store.dispatch('syncAccounts')
					} catch (e) {
						console.log('首次同步跳过:', e)
					}
					setTimeout(() => {
						uni.switchTab({ url: '/pages/index/index' })
					}, 800)
				} else {
					this.statusMsg = '连接失败，请检查地址'
					this.statusOk = false
				}
			} catch (e) {
				this.statusMsg = '连接失败: ' + e.message
				this.statusOk = false
			} finally {
				this.connecting = false
			}
		}
	}
}
</script>

<style lang="scss" scoped>
.page {
	min-height: 100vh;
	background: #F8F9FA;
	padding: 60rpx 40rpx;
	box-sizing: border-box;
}

.header {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding-top: 100rpx;
	margin-bottom: 60rpx;
}

.logo {
	width: 130rpx;
	height: 130rpx;
	margin-bottom: 24rpx;
}

.title {
	font-size: 44rpx;
	font-weight: 700;
	color: #0058BC;
	margin-bottom: 10rpx;
}

.subtitle {
	font-size: 26rpx;
	color: #717786;
}

.form-area {
	margin-top: 20rpx;
}

.glass-card {
	background: #FFFFFF;
	border-radius: 20rpx;
	padding: 30rpx;
	border: 1px solid #E1E3E4;
	box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.04);
}

.field {
	margin-bottom: 30rpx;
	position: relative;
}

.field:last-child {
	margin-bottom: 0;
}

.label {
	display: block;
	font-size: 24rpx;
	color: #414755;
	margin-bottom: 10rpx;
	font-weight: 600;
}

.input {
	width: 100%;
	height: 84rpx;
	background: #F3F4F5;
	border-radius: 12rpx;
	padding: 0 24rpx;
	color: #191C1D;
	font-size: 26rpx;
	box-sizing: border-box;
}

.placeholder {
	color: #C1C6D7;
}

.toggle-key {
	position: absolute;
	right: 24rpx;
	top: 54rpx;
	color: #0058BC;
	font-size: 24rpx;
	font-weight: 600;
}

.connect-btn {
	margin-top: 40rpx;
	width: 100%;
	height: 90rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 30rpx;
	font-weight: 700;
	border-radius: 14rpx;
	background: #0058BC;
	color: #FFFFFF;
	box-shadow: 0 4rpx 12rpx rgba(0, 88, 188, 0.25);
}

.btn-loading {
	opacity: 0.7;
}

.status-area {
	text-align: center;
	margin-top: 30rpx;
	font-size: 26rpx;
}
.text-success { color: #006E28; }
.text-danger { color: #BA1A1A; }
</style>

