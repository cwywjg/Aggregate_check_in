<script>
let healthTimer = null

export default {
	async onLaunch() {
		if (this.$store && typeof this.$store.dispatch === 'function') {
			await this.$store.dispatch('loadRemoteConfig').catch(() => {})
			this.$store.dispatch('syncAccounts').catch(() => {})
			this.$store.dispatch('checkServerHealth').catch(() => {})
		}
		this._startHealthPolling()
	},
	onShow() {
		if (this.$store && typeof this.$store.dispatch === 'function') {
			this.$store.dispatch('loadRemoteConfig').catch(() => {})
		}
		this._startHealthPolling()
	},

	onHide() {
		if (healthTimer) {
			clearInterval(healthTimer)
			healthTimer = null
		}
	},
	methods: {
		_startHealthPolling() {
			if (healthTimer) {
				clearInterval(healthTimer)
				healthTimer = null
			}
			// 每 5 分钟在后台静默检查账号健康状态
			healthTimer = setInterval(() => {
				if (this.$store && typeof this.$store.dispatch === 'function') {
					this.$store.dispatch('checkAccountHealth').catch(() => {})
				}
			}, 5 * 60 * 1000)
		}
	}
}
</script>

<style>
/* 全局基础样式 */
page {
	background-color: #F2F2F7;
	color: #1C1C1E;
	font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
}

/* 全局卡片样式 */
.glass-card {
	background: #FFFFFF;
	border: 1px solid rgba(0, 0, 0, 0.04);
	border-radius: 24rpx;
	padding: 30rpx;
	box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.03);
}

.glass-card-hover {
	background: #FAFAFA;
}

/* 品牌渐变背景 */
.brand-gradient {
	background: linear-gradient(135deg, #0A84FF, #30B0C7);
}

/* 文字颜色 */
.text-primary { color: #1C1C1E; }
.text-secondary { color: #8E8E93; }
.text-muted { color: #C7C7CC; }
.text-brand { color: #0A84FF; }
.text-success { color: #34C759; }
.text-danger { color: #FF3B30; }
.text-warning { color: #FF9500; }

/* 全局按钮 */
.btn-primary {
	background: linear-gradient(135deg, #0A84FF 0%, #005BB5 100%);
	color: #fff;
	border: none;
	border-radius: 16rpx;
	padding: 24rpx 48rpx;
	font-size: 30rpx;
	font-weight: 600;
	text-align: center;
	box-shadow: 0 8rpx 24rpx rgba(10, 132, 255, 0.25);
	transition: all 0.2s ease;
}

.btn-primary:active {
	transform: scale(0.97);
	opacity: 0.9;
}

/* 状态标签 */
.badge {
	display: inline-block;
	padding: 4rpx 16rpx;
	border-radius: 20rpx;
	font-size: 22rpx;
	font-weight: 500;
}
.badge-success { background: #E5F9ED; color: #34C759; }
.badge-danger { background: #FFEBEB; color: #FF3B30; }
.badge-warning { background: #FFF5E6; color: #FF9500; }
.badge-info { background: #E6F2FF; color: #0A84FF; }
</style>
