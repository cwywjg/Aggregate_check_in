<template>
	<view class="page-container">
		<!-- Top App Bar -->
		<view class="top-app-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
			<view class="app-bar-inner">
				<text class="app-title">答题助手</text>
				<view class="refresh-pill-btn" @tap="forceRefreshSession">
					<text class="refresh-icon">🔄</text>
					<text class="refresh-text">刷新会话</text>
				</view>
			</view>
		</view>

		<scroll-view scroll-y class="main-content" :style="{ paddingTop: (statusBarHeight + 56) + 'px' }"
			@scrolltolower="loadMore" refresher-enabled @refresherrefresh="onRefresh"
			:refresher-triggered="refreshing">

			<!-- 选定当前答题账号卡片 -->
			<view class="account-selector-bar" @tap="openAccountPicker">
				<view class="acc-selected-left">
					<image class="acc-avatar" :src="getAvatar(currentQuizAccount)" mode="aspectFill"></image>
					<view class="acc-text-info">
						<view class="acc-name-row">
							<text class="acc-label">当前答题账号：</text>
							<text class="acc-name">{{ currentQuizAccount?.nickname || currentQuizAccount?.name || '点击选择答题账号' }}</text>
						</view>
						<text class="acc-hint">获取课程、题目及提交均使用此账号</text>
					</view>
				</view>
				<view class="switch-pill">
					<text class="switch-text">切换 ▾</text>
				</view>
			</view>

			<view v-if="loading && courses.length === 0" class="loading-state">
				<text class="loading-text">正在拉取「{{ currentQuizAccount?.nickname || '当前账号' }}」的课程...</text>
			</view>

			<view v-else-if="accounts.length === 0" class="empty-card">
				<text class="empty-emoji">👥</text>
				<text class="empty-title">暂无关联账号</text>
				<text class="empty-sub">请先在首页添加微助教账号后查看课程</text>
				<view class="action-btn" @tap="goAccounts">
					<text>前往添加账号</text>
				</view>
			</view>

			<view v-else-if="courses.length === 0" class="empty-card">
				<text class="empty-emoji">📚</text>
				<text class="empty-title">「{{ currentQuizAccount?.nickname || '当前账号' }}」暂无课程</text>
				<text class="empty-sub">若已在微信中加入课程，请点击下方重新同步，或切换其他账号答题</text>
				<view class="empty-btns-row">
					<view class="action-btn" @tap="onRefresh">
						<text>🔄 重新同步</text>
					</view>
					<view class="action-btn action-btn-secondary" @tap="openAccountPicker">
						<text>👥 切换答题账号</text>
					</view>
				</view>
			</view>

			<view v-for="course in courses" :key="course.courseId"
				class="course-card"
				@tap="goCourse(course)">
				<view class="course-info">
					<text class="course-name">{{ course.name }}</text>
					<text class="course-teacher"> {{ course.teacherName || '任课教师' }}</text>
				</view>
				<view class="course-arrow">
					<text class="arrow-icon">›</text>
				</view>
			</view>

			<view style="height: 40px;"></view>
		</scroll-view>

		<!-- 账号切换弹窗 -->
		<view v-if="showAccountPicker" class="picker-mask" @tap.self="showAccountPicker = false">
			<view class="picker-content">
				<view class="picker-header">
					<view class="picker-title-box">
						<text class="picker-icon">👥</text>
						<text class="picker-title">选定答题账号</text>
					</view>
					<text class="close-btn" @tap="showAccountPicker = false">✕</text>
				</view>
				<text class="picker-subtitle">选择后，后续所有课程、题目与作答均基于该账号</text>

				<scroll-view scroll-y class="picker-list">
					<view v-for="acc in accounts" :key="acc.ref"
						class="account-picker-item"
						:class="{ active: acc.ref === currentQuizAccount?.ref }"
						@tap="selectQuizAccount(acc)">
						<image class="item-avatar" :src="getAvatar(acc)" mode="aspectFill"></image>
						<view class="item-info">
							<view class="item-name-row">
								<text class="item-name">{{ acc.nickname || acc.name || '未命名账号' }}</text>
								<text v-if="acc.ref === currentQuizAccount?.ref" class="item-badge-active">当前选定</text>
							</view>
							<text class="item-sub">凭证状态: {{ acc.is_alive && !acc.needs_rescan ? '正常有效' : '需检查' }}</text>
						</view>
						<view class="item-check" v-if="acc.ref === currentQuizAccount?.ref">
							<text class="check-icon">✓</text>
						</view>
					</view>
				</scroll-view>
			</view>
		</view>
	</view>
</template>

<script>
import { get, post } from '../../api/request'
import { getCachedAvatar } from '../../utils/avatar'

export default {
	data() {
		return {
			statusBarHeight: 20,
			courses: [],
			loading: false,
			refreshing: false,
			showAccountPicker: false
		}
	},
	computed: {
		accounts() { return this.$store.state.accounts || [] },
		currentQuizAccount() {
			return this.$store.getters.quizAccount
		}
	},
	onLoad() {
		const sysInfo = uni.getSystemInfoSync()
		this.statusBarHeight = sysInfo.statusBarHeight || 20
	},
	async onShow() {
		try {
			await this.$store.dispatch('syncAccounts')
		} catch (e) {}
		this.loadCourses()
	},
	onHide() {
		uni.hideLoading()
	},
	onUnload() {
		uni.hideLoading()
	},
	methods: {
		getAvatar(acc) {
			if (!acc) return '/static/avatar_default.png'
			return getCachedAvatar(acc.ref || acc.openid, this.$store.state.serverUrl, acc.avatar_url)
		},
		openAccountPicker() {
			this.showAccountPicker = true
		},
		selectQuizAccount(acc) {
			this.$store.commit('SET_QUIZ_ACCOUNT_REF', acc.ref)
			this.showAccountPicker = false
			uni.showToast({ title: `已切换至「${acc.nickname || '指定账号'}」`, icon: 'success' })
			this.loadCourses(true)
		},
		async forceRefreshSession() {
			uni.showLoading({ title: '正在重建会话...' })
			try {
				const res = await post('/api/quiz/refresh-session')
				uni.showToast({ title: res.message || '会话已刷新', icon: 'success' })
				await this.loadCourses(true)
			} catch (e) {
				uni.showToast({ title: '刷新失败: ' + (e.message || '超时'), icon: 'none' })
			} finally {
				uni.hideLoading()
			}
		},
		async loadCourses(force = false) {
			const targetRef = this.currentQuizAccount?.ref || this.currentQuizAccount?.openid || ''
			const cacheKey = 'courses_cache_' + (targetRef || 'default')

			if (!force) {
				const cache = uni.getStorageSync(cacheKey)
				if (cache) {
					try { this.courses = JSON.parse(cache) } catch (e) {}
				}
			}
			if (this.courses.length === 0) {
				this.loading = true
			}

			try {
				const url = targetRef ? `/api/quiz/courses?ref=${encodeURIComponent(targetRef)}` : '/api/quiz/courses'
				const data = await get(url)
				const list = data.courses || []
				this.courses = list
				uni.setStorageSync(cacheKey, JSON.stringify(list))
				if (list.length === 0 && data.message) {
					uni.showToast({ title: data.message, icon: 'none' })
				}
			} catch (e) {
				console.warn('Load courses failed:', e)
				if (this.courses.length === 0) {
					uni.showToast({ title: e.message || '加载课程失败', icon: 'none' })
				}
			} finally {
				this.loading = false
			}
		},
		async onRefresh() {
			this.refreshing = true
			await this.loadCourses(true)
			this.refreshing = false
		},
		loadMore() {},
		goCourse(course) {
			this.$store.commit('SET_CURRENT_COURSE', course)
			const targetRef = this.currentQuizAccount?.ref || ''
			uni.navigateTo({
				url: `/pages/quiz/questions?courseId=${course.courseId}&courseName=${encodeURIComponent(course.name)}&ref=${encodeURIComponent(targetRef)}`
			})
		},
		goAccounts() {
			uni.switchTab({ url: '/pages/index/index' })
		}
	}
}
</script>

<style lang="scss" scoped>
.page-container {
	min-height: 100vh;
	background-color: #F8F9FA;
	box-sizing: border-box;
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
.app-title {
	font-size: 20px;
	font-weight: 700;
	color: #0058BC;
	letter-spacing: -0.2px;
}
.refresh-pill-btn {
	background: #D8E2FF;
	padding: 6px 12px;
	border-radius: 20px;
	display: flex;
	align-items: center;
	gap: 4px;
}
.refresh-pill-btn:active {
	opacity: 0.8;
}
.refresh-icon {
	font-size: 12px;
}
.refresh-text {
	font-size: 12px;
	font-weight: 600;
	color: #004493;
}

/* 选定当前答题账号卡片 */
.account-selector-bar {
	background: linear-gradient(135deg, #0A84FF 0%, #0058BC 100%);
	border-radius: 20rpx;
	padding: 24rpx 28rpx;
	margin-bottom: 24rpx;
	display: flex;
	align-items: center;
	justify-content: space-between;
	box-shadow: 0 8rpx 24rpx rgba(10, 132, 255, 0.25);
	transition: all 0.2s ease;
}
.account-selector-bar:active {
	opacity: 0.92;
	transform: scale(0.99);
}

.acc-selected-left {
	display: flex;
	align-items: center;
	gap: 20rpx;
	flex: 1;
	min-width: 0;
}

.acc-avatar {
	width: 76rpx;
	height: 76rpx;
	border-radius: 50%;
	border: 2rpx solid rgba(255, 255, 255, 0.8);
	flex-shrink: 0;
	background: #fff;
}

.acc-text-info {
	display: flex;
	flex-direction: column;
	gap: 4rpx;
	flex: 1;
	min-width: 0;
}

.acc-name-row {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 6rpx;
}

.acc-label {
	font-size: 22rpx;
	color: rgba(255, 255, 255, 0.85);
	font-weight: 500;
}

.acc-name {
	font-size: 28rpx;
	font-weight: 700;
	color: #FFFFFF;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.acc-hint {
	font-size: 20rpx;
	color: rgba(255, 255, 255, 0.75);
}

.switch-pill {
	background: rgba(255, 255, 255, 0.22);
	border: 1px solid rgba(255, 255, 255, 0.4);
	padding: 8rpx 18rpx;
	border-radius: 24rpx;
	flex-shrink: 0;
}

.switch-text {
	font-size: 22rpx;
	color: #FFFFFF;
	font-weight: 600;
}

.empty-btns-row {
	display: flex;
	gap: 12px;
	margin-top: 10px;
	flex-wrap: wrap;
	justify-content: center;
}
.action-btn-secondary {
	background: #006E28 !important;
	box-shadow: 0 2px 8px rgba(0, 110, 40, 0.2) !important;
}

.main-content {
	padding: 16px 20px 40px 20px;
	box-sizing: border-box;
}

.empty-card {
	background: #FFFFFF;
	border-radius: 16px;
	padding: 40px 20px;
	border: 1px solid #E1E3E4;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
	display: flex;
	flex-direction: column;
	align-items: center;
	text-align: center;
	gap: 10px;
	margin-top: 10px;
}
.empty-emoji { font-size: 40px; }
.empty-title { font-size: 16px; font-weight: 700; color: #191C1D; }
.empty-sub { font-size: 13px; color: #717786; line-height: 1.5; }

.action-btn {
	margin-top: 10px;
	padding: 10px 24px;
	background: #0058BC;
	color: #FFFFFF;
	font-size: 14px;
	font-weight: 600;
	border-radius: 10px;
	box-shadow: 0 2px 8px rgba(0, 88, 188, 0.2);
}

.loading-state {
	text-align: center;
	padding: 60px 0;
}
.loading-text {
	font-size: 14px;
	color: #717786;
}

.course-card {
	background: #FFFFFF;
	border-radius: 16px;
	padding: 18px 20px;
	border: 1px solid #E1E3E4;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
	margin-bottom: 14px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	transition: transform 0.15s;
}
.course-card:active {
	transform: scale(0.99);
	background: #F8F9FA;
}

.course-info {
	display: flex;
	flex-direction: column;
	gap: 6px;
	flex: 1;
	min-width: 0;
}
.course-name {
	font-size: 16px;
	font-weight: 700;
	color: #191C1D;
	word-break: break-all;
}
.course-teacher {
	font-size: 13px;
	color: #717786;
}

.course-arrow {
	padding-left: 12px;
}
.arrow-icon {
	font-size: 24px;
	color: #C1C6D7;
	font-weight: 300;
}

/* 账号选择弹窗 */
.picker-mask {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.6);
	backdrop-filter: blur(8px);
	z-index: 9999;
	display: flex;
	align-items: flex-end;
}

.picker-content {
	width: 100%;
	max-height: 75vh;
	background: #FFFFFF;
	border-top-left-radius: 36rpx;
	border-top-right-radius: 36rpx;
	padding: 36rpx 32rpx 48rpx;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	animation: slideUp 0.22s ease-out;
}

@keyframes slideUp {
	from { transform: translateY(100%); }
	to { transform: translateY(0); }
}

.picker-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 8rpx;
}

.picker-title-box {
	display: flex;
	align-items: center;
	gap: 12rpx;
}

.picker-icon { font-size: 36rpx; }
.picker-title { font-size: 32rpx; font-weight: 700; color: #191C1D; }
.close-btn { font-size: 34rpx; color: #8E8E93; padding: 10rpx; }

.picker-subtitle {
	font-size: 24rpx;
	color: #717786;
	margin-bottom: 24rpx;
}

.picker-list {
	max-height: 50vh;
}

.account-picker-item {
	display: flex;
	align-items: center;
	gap: 20rpx;
	padding: 24rpx 20rpx;
	border-radius: 18rpx;
	margin-bottom: 14rpx;
	border: 1px solid rgba(0, 0, 0, 0.06);
	background: #F8F9FA;
	transition: all 0.2s ease;
}

.account-picker-item.active {
	border-color: #0A84FF;
	background: #EBF4FF;
}

.item-avatar {
	width: 72rpx;
	height: 72rpx;
	border-radius: 50%;
	background: #E1E3E4;
	flex-shrink: 0;
}

.item-info {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: 4rpx;
}

.item-name-row {
	display: flex;
	align-items: center;
	gap: 12rpx;
}

.item-name {
	font-size: 28rpx;
	font-weight: 700;
	color: #191C1D;
}

.item-badge-active {
	font-size: 20rpx;
	font-weight: 600;
	color: #0A84FF;
	background: rgba(10, 132, 255, 0.15);
	padding: 2rpx 10rpx;
	border-radius: 6rpx;
}

.item-sub {
	font-size: 22rpx;
	color: #717786;
}

.item-check {
	width: 44rpx;
	height: 44rpx;
	border-radius: 50%;
	background: #0A84FF;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.check-icon {
	color: #FFFFFF;
	font-size: 24rpx;
	font-weight: 700;
}
</style>

