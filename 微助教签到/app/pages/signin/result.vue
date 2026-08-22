<template>
	<view class="page">
		<view class="result-header glass-card">
			<text class="result-title">签到完成</text>
			<view class="result-summary">
				<text class="summary-text">
					成功 <text class="text-success">{{ successCount }}</text> / 共 {{ results.length }} 人
				</text>
			</view>
		</view>

		<view v-for="(r, i) in results" :key="i" class="result-item glass-card">
			<view class="result-left">
				<view class="result-icon" :class="r.success ? 'icon-success' : 'icon-fail'">
					<text>{{ r.success ? '✓' : '✗' }}</text>
				</view>
				<view class="result-info">
					<text class="result-name">{{ r.nickname || r.ref }}</text>
					<text class="result-msg" :class="r.success ? 'text-success' : 'text-danger'">
						{{ r.message }}
					</text>
				</view>
			</view>
		</view>

		<view class="btn-primary back-btn" @tap="goBack">
			<text>返回</text>
		</view>
	</view>
</template>

<script>
export default {
	data() {
		return {
			results: [],
			successCount: 0
		}
	},
	onLoad(options) {
		if (options.data) {
			try {
				const data = JSON.parse(decodeURIComponent(options.data))
				this.results = data.results || []
				this.successCount = data.success_count || 0
			} catch (e) {
				console.error('Parse result failed:', e)
			}
		}
	},
	methods: {
		goBack() {
			uni.navigateBack()
		}
	}
}
</script>

<style lang="scss" scoped>
.page {
	min-height: 100vh;
	background: #F2F2F7;
	padding: 30rpx;
}

.result-header {
	text-align: center;
	margin-bottom: 30rpx;
	padding: 40rpx;
}

.result-title {
	font-size: 36rpx;
	font-weight: 700;
	color: #1C1C1E;
	display: block;
	margin-bottom: 16rpx;
}

.summary-text {
	font-size: 28rpx;
	color: #8E8E93;
}

.result-item {
	display: flex;
	align-items: center;
	margin-bottom: 16rpx;
	padding: 28rpx;
}

.result-left {
	display: flex;
	align-items: center;
	gap: 20rpx;
}

.result-icon {
	width: 56rpx;
	height: 56rpx;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 28rpx;
	color: #fff;
	flex-shrink: 0;
}

.icon-success { background: #E5F9ED; color: #34C759; font-weight: bold; }
.icon-fail { background: #FFEBEB; color: #FF3B30; font-weight: bold; }

.result-name {
	font-size: 28rpx;
	font-weight: 600;
	color: #1C1C1E;
	display: block;
}

.result-msg {
	font-size: 24rpx;
	margin-top: 4rpx;
	display: block;
}

.back-btn {
	margin-top: 40rpx;
	width: 100%;
	height: 88rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 30rpx;
}
</style>
