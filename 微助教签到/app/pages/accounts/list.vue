<template>
	<view class="page">
		<view class="content">
			<!-- 账号列表 -->
			<view class="section-title">
				<text>已登录账号</text>
				<text class="count-badge">{{ accounts.length }}</text>
			</view>

			<view v-if="accounts.length === 0" class="empty-state glass-card">
				<text class="empty-text">暂无账号</text>
				<text class="empty-hint">点击下方按钮扫码添加</text>
			</view>

			<view v-for="acc in accounts" :key="acc.ref" class="account-card glass-card"
				@longpress="showActions(acc)">
				<view class="account-left">
					<view class="avatar-wrap">
						<image class="avatar" :src="getAvatarUrl(acc)" mode="aspectFill"></image>
						<view class="status-dot" :class="getStatusClass(acc)"></view>
					</view>
					<view class="account-info">
						<view class="name-row">
							<text class="nickname">{{ acc.nickname || '未命名' }}</text>
							<view v-if="acc.is_master" class="master-badge">
								<text class="master-text">👑 主</text>
							</view>
						</view>
						<view class="status-row">
							<text class="status-label" :class="getStatusTextClass(acc)">{{ getStatusText(acc) }}</text>
							<text v-if="acc.last_keepalive_at" class="keepalive-time">
								{{ formatKeepaliveTime(acc.last_keepalive_at) }}
							</text>
						</view>
					</view>
				</view>

				<!-- 需要重扫的账号显示重扫按钮 -->
				<view v-if="acc.needs_rescan" class="rescan-btn" @tap.stop="goRescan(acc)">
					<text class="rescan-text">重新扫码</text>
				</view>
			</view>

			<!-- 失效账号警告 -->
			<view v-if="expiredAccounts.length > 0" class="warning-card">
				<text class="warning-icon">⚠️</text>
				<text class="warning-text">{{ expiredAccounts.length }} 个账号凭证已失效，请点击"重新扫码"恢复</text>
			</view>

			<!-- 操作提示 -->
			<view class="hint" v-if="accounts.length > 0">
				<text class="hint-text">长按账号可设为主账号或删除</text>
			</view>
		</view>

		<!-- 底部添加按钮 -->
		<view class="bottom-bar">
			<view class="btn-primary add-btn" @tap="goAdd">
				<text>+ 扫码添加账号</text>
			</view>
			<view class="sync-btn" @tap="syncAll">
				<text class="sync-text">{{ syncing ? '同步中...' : '从服务器同步' }}</text>
			</view>
		</view>
	</view>
</template>

<script>
import { del, put } from '../../api/request'

export default {
	data() {
		return {
			syncing: false
		}
	},
	computed: {
		accounts() { return this.$store.state.accounts },
		expiredAccounts() { return this.$store.getters.expiredAccounts }
	},
	onShow() {
		this.syncAll()
	},
	methods: {
		getAvatarUrl(acc) {
			if (!acc.avatar_url) return '/static/avatar_default.png'
			if (acc.avatar_url.startsWith('http')) return acc.avatar_url
			return this.$store.state.serverUrl + acc.avatar_url
		},

		getStatusClass(acc) {
			if (acc.needs_rescan) return 'dot-expired'
			if (acc.is_alive) return 'dot-alive'
			if (acc.keepalive_status === 'degraded') return 'dot-degraded'
			return 'dot-unknown'
		},

		getStatusText(acc) {
			if (acc.needs_rescan) return '已失效'
			if (acc.is_alive) return '在线'
			if (acc.keepalive_status === 'degraded') return '不稳定'
			return '未知'
		},

		getStatusTextClass(acc) {
			if (acc.needs_rescan) return 'text-danger'
			if (acc.is_alive) return 'text-success'
			if (acc.keepalive_status === 'degraded') return 'text-warning'
			return 'text-secondary'
		},

		formatKeepaliveTime(timeStr) {
			if (!timeStr) return ''
			try {
				const isoStr = timeStr.includes('T') ? timeStr : timeStr.replace(' ', 'T')
				const t = new Date(isoStr.endsWith('Z') ? isoStr : isoStr + 'Z')
				const now = new Date()
				const diffMs = now.getTime() - t.getTime()
				if (isNaN(diffMs)) return ''
				const diffMin = Math.floor(diffMs / 60000)
				if (diffMin < 1) return '刚刚保活'
				if (diffMin < 60) return `${diffMin}分钟前保活`
				const diffH = Math.floor(diffMin / 60)
				if (diffH < 24) return `${diffH}小时前保活`
				return `${Math.floor(diffH / 24)}天前保活`
			} catch {
				return ''
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

		async syncAll() {
			if (this.syncing) return
			this.syncing = true
			try {
				await this.$store.dispatch('syncAccounts')
				uni.showToast({ title: '同步成功', icon: 'success' })
			} catch (e) {
				uni.showToast({ title: '同步失败', icon: 'none' })
			} finally {
				this.syncing = false
			}
		},

		showActions(acc) {
			const items = acc.is_master
				? ['删除账号']
				: ['设为主账号', '删除账号']

			uni.showActionSheet({
				itemList: items,
				success: async (res) => {
					const action = items[res.tapIndex]
					if (action === '设为主账号') {
						await this.setMaster(acc)
					} else if (action === '删除账号') {
						this.confirmDelete(acc)
					}
				}
			})
		},

		async setMaster(acc) {
			try {
				await put(`/api/accounts/${acc.ref}/master`)
				await this.$store.dispatch('syncAccounts')
				uni.showToast({ title: '已设为主账号', icon: 'success' })
			} catch (e) {
				uni.showToast({ title: '操作失败', icon: 'none' })
			}
		},

		confirmDelete(acc) {
			uni.showModal({
				title: '确认删除',
				content: `确定删除账号 ${acc.nickname || acc.ref}？`,
				success: async (res) => {
					if (res.confirm) {
						try {
							await del(`/api/accounts/${acc.ref}`)
							this.$store.commit('REMOVE_ACCOUNT', acc.ref)
							uni.showToast({ title: '已删除', icon: 'success' })
						} catch (e) {
							uni.showToast({ title: '删除失败', icon: 'none' })
						}
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
	padding-bottom: 240rpx;
}

.content {
	padding: 20rpx 30rpx;
}

.section-title {
	display: flex;
	align-items: center;
	gap: 14rpx;
	margin-bottom: 24rpx;
	font-size: 32rpx;
	font-weight: 600;
	color: #1C1C1E;
}

.count-badge {
	background: rgba(10, 132, 255, 0.1);
	color: #0A84FF;
	padding: 2rpx 16rpx;
	border-radius: 20rpx;
	font-size: 24rpx;
	font-weight: 600;
}

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 80rpx 0;
	gap: 12rpx;
}

.empty-text { font-size: 32rpx; color: #8E8E93; }
.empty-hint { font-size: 24rpx; color: #C7C7CC; }

.account-card {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 20rpx;
	padding: 30rpx;
}

.account-left {
	display: flex;
	align-items: center;
	gap: 24rpx;
	flex: 1;
	min-width: 0;
}

.avatar-wrap {
	position: relative;
	flex-shrink: 0;
}

.avatar {
	width: 88rpx;
	height: 88rpx;
	border-radius: 50%;
	border: 3rpx solid rgba(0,0,0,0.03);
}

.status-dot {
	position: absolute;
	right: 0;
	bottom: 0;
	width: 20rpx;
	height: 20rpx;
	border-radius: 50%;
	border: 3rpx solid #fff;
}

.dot-alive { background: #34C759; box-shadow: 0 0 8rpx rgba(52,199,89,0.5); }
.dot-degraded { background: #FF9500; box-shadow: 0 0 8rpx rgba(255,149,0,0.5); animation: pulse 2s infinite; }
.dot-expired { background: #FF3B30; box-shadow: 0 0 8rpx rgba(255,59,48,0.5); animation: pulse 1.5s infinite; }
.dot-unknown { background: #AEAEB2; }

@keyframes pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.4; }
}

.account-info {
	flex: 1;
	min-width: 0;
}

.name-row {
	display: flex;
	align-items: center;
	gap: 12rpx;
}

.nickname {
	font-size: 30rpx;
	font-weight: 600;
	color: #1C1C1E;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.master-badge {
	background: #FFF5E6;
	border: 1px solid rgba(255, 149, 0, 0.2);
	padding: 2rpx 12rpx;
	border-radius: 8rpx;
	flex-shrink: 0;
}

.master-text {
	font-size: 20rpx;
	color: #FF9500;
	font-weight: bold;
}

.status-row {
	display: flex;
	align-items: center;
	gap: 12rpx;
	margin-top: 6rpx;
}

.status-label {
	font-size: 22rpx;
	font-weight: 600;
}

.keepalive-time {
	font-size: 20rpx;
	color: #AEAEB2;
}

.rescan-btn {
	background: linear-gradient(135deg, #FF3B30 0%, #FF6B6B 100%);
	padding: 12rpx 24rpx;
	border-radius: 24rpx;
	flex-shrink: 0;
}

.rescan-text {
	font-size: 22rpx;
	color: #fff;
	font-weight: 600;
}

.warning-card {
	display: flex;
	align-items: center;
	gap: 16rpx;
	background: #FFF5F5;
	border: 1px solid rgba(255, 59, 48, 0.15);
	border-radius: 16rpx;
	padding: 24rpx 28rpx;
	margin-top: 12rpx;
	margin-bottom: 20rpx;
}

.warning-icon { font-size: 32rpx; }
.warning-text { font-size: 24rpx; color: #FF3B30; font-weight: 500; flex: 1; }

.hint {
	text-align: center;
	margin-top: 20rpx;
}

.hint-text {
	font-size: 22rpx;
	color: #AEAEB2;
}

.bottom-bar {
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	padding: 20rpx 30rpx;
	padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
	background: rgba(255, 255, 255, 0.98);
	border-top: 0.5px solid rgba(0, 0, 0, 0.08);
	display: flex;
	flex-direction: column;
	gap: 16rpx;
}

.add-btn {
	width: 100%;
	height: 88rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 30rpx;
}

.sync-btn {
	text-align: center;
	padding: 10rpx;
}

.sync-text {
	font-size: 26rpx;
	color: #0A84FF;
	font-weight: 600;
}
</style>
