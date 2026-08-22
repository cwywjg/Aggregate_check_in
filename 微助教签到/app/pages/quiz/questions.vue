<template>
	<view class="page-container">
		<!-- 顶部统一固定吸顶头部：包含导航条 + 状态分类筛选按钮 + 汇总条（绝不随页面滚动消失） -->
		<view class="top-fixed-header" :style="{ paddingTop: statusBarHeight + 'px' }">
			<!-- 导航条 -->
			<view class="app-bar-inner">
				<view class="nav-back-btn" @tap="goBack">
					<text class="back-arrow">‹</text>
					<text class="back-text">课程</text>
				</view>
				<view class="title-col">
					<text class="app-title">{{ courseName || '题目列表' }}</text>
					<text class="acc-badge">👤 {{ currentAccount?.nickname || currentAccount?.name || '答题账号' }}</text>
				</view>
				<view class="app-bar-right">
					<view class="refresh-pill-btn" @tap="forceRefresh">
						<text class="refresh-icon">🔄</text>
					</view>
				</view>
			</view>

			<!-- 状态分类筛选栏（吸顶固定，永久可见） -->
			<view class="filter-bar">
				<view v-for="f in filters" :key="f.key"
					class="filter-item" :class="{ active: currentFilter === f.key }"
					@tap="changeFilter(f.key)">
					<text>{{ f.label }}</text>
				</view>
			</view>

			<!-- 数据汇总条 -->
			<view class="summary-bar">
				<text class="summary-text">{{ questions.length > 0 ? `已加载 ${questions.length} / ${totalQuestions} 道题目` : '题目列表' }}</text>
				<text class="summary-sub" v-if="questions.length > 0">下拉或滚动以加载更多</text>
			</view>
		</view>

		<!-- 主体滚动区域（从吸顶头部下方开始无缝滚动） -->
		<view class="main-body" :style="{ paddingTop: headerPaddingTop + 'px' }">
			<scroll-view scroll-y class="content" @scrolltolower="onReachBottomScroll" refresher-enabled @refresherrefresh="onRefreshScroll" :refresher-triggered="refreshing">
				<view class="questions-container">
					<view v-if="loading && questions.length === 0" class="question-skeletons">
						<view v-for="idx in 5" :key="idx" class="question-skeleton glass-card">
							<view class="skeleton-pill"></view>
							<view class="skeleton-text"></view>
							<view class="skeleton-text short"></view>
						</view>
					</view>

					<view v-else-if="loadError && questions.length === 0" class="error-state" @tap="loadQuestions(false)">
						<text class="error-emoji">⚠️</text>
						<text class="error-text">加载失败，点击此处重试</text>
					</view>

					<view v-else-if="questions.length === 0" class="empty-state">
						<text class="empty-emoji">📝</text>
						<text class="empty-text">当前暂无匹配题目</text>
					</view>

					<view v-for="q in questions" :key="q.id"
						class="question-card glass-card" hover-class="glass-card-hover"
						@tap="goDetail(q)">
						<view class="q-header">
							<view class="q-type-badge" :class="'type-' + q.type">
								<text>{{ typeLabel(q.type) }}</text>
							</view>
							<view v-if="q.isOpen === 1" class="badge badge-success">
								<text>开放中</text>
							</view>
							<view v-else class="badge badge-info">
								<text>已关闭</text>
							</view>
							<view v-if="q.isAnswered === 1" class="badge badge-warning">
								<text>已作答</text>
							</view>
						</view>
						<text class="q-title">{{ stripHtml(q.title || q.content || '无标题') }}</text>
						<text class="q-time">{{ q.startTime || '' }}</text>
					</view>

					<!-- 加载更多状态指示 -->
					<view class="loadmore" v-if="loadingMore">
						<text class="loadmore-text">正在加载更多...</text>
					</view>
					<view class="loadmore" v-else-if="!hasMore && questions.length > 0">
						<text class="loadmore-text">已加载全部题目</text>
					</view>
				</view>
			</scroll-view>
		</view>
	</view>
</template>

<script>
import { get } from '../../api/request'

export default {
	data() {
		return {
			statusBarHeight: 20,
			courseId: 0,
			courseName: '',
			accountRef: '',
			questions: [],
			totalQuestions: 0,
			page: 0,
			hasMore: true,
			loading: false,
			loadingMore: false,
			refreshing: false,
			loadError: false,
			currentFilter: 'all',
			filters: [
				{ key: 'all', label: '全部' },
				{ key: 'open', label: '开放中' },
				{ key: 'unanswered', label: '未作答' },
				{ key: 'answered', label: '已作答' }
			]
		}
	},
	computed: {
		currentAccount() {
			if (this.accountRef) {
				const accounts = this.$store.state.accounts || []
				const found = accounts.find(a => a.ref === this.accountRef || a.openid === this.accountRef)
				if (found) return found
			}
			return this.$store.getters.quizAccount
		},
		headerPaddingTop() {
			// statusBarHeight + 52px(导航条) + 44px(分类按钮栏) + 38px(数据汇总栏)
			return (this.statusBarHeight || 20) + 134
		}
	},
	onLoad(options) {
		const sys = uni.getSystemInfoSync()
		this.statusBarHeight = sys.statusBarHeight || 20
		this.courseId = parseInt(options.courseId)
		this.courseName = decodeURIComponent(options.courseName || '')
		this.accountRef = options.ref || this.$store.getters.quizAccount?.ref || ''
		uni.$on('quiz-answer-submitted', this.handleAnswerSubmitted)
		this.loadQuestions()
	},
	onShow() {
		const currentSelectedRef = this.$store.getters.quizAccount?.ref || ''
		if (currentSelectedRef && currentSelectedRef !== this.accountRef) {
			this.accountRef = currentSelectedRef
			this.loadQuestions(false)
		}
	},
	onUnload() {
		uni.$off('quiz-answer-submitted', this.handleAnswerSubmitted)
	},
	methods: {
		goBack() {
			uni.navigateBack({
				fail: () => {
					uni.switchTab({ url: '/pages/quiz/courses' })
				}
			})
		},
		async onRefreshScroll() {
			this.refreshing = true
			await this.loadQuestions(false)
			this.refreshing = false
		},
		onReachBottomScroll() {
			if (this.hasMore && !this.loading && !this.loadingMore) {
				this.page++
				this.loadQuestions(true)
			}
		},
		typeLabel(type) {
			const map = { 0: '单选', 1: '单选', 2: '多选', 3: '判断', 4: '填空', 5: '主观' }
			return map[type] || '未知'
		},
		stripHtml(s) {
			if (!s) return '无标题'
			const text = s.replace(/<[^>]+>/g, '').trim()
			if (!text && s.includes('<img')) {
				return '[图片题]'
			}
			return text.substring(0, 60) || '无标题'
		},

		async forceRefresh() {
			uni.showLoading({ title: '刷新中...' })
			try {
				await this.loadQuestions(false)
				uni.showToast({ title: '已刷新', icon: 'success' })
			} catch (e) {
				uni.showToast({ title: '刷新失败', icon: 'none' })
			} finally {
				uni.hideLoading()
			}
		},

		async loadQuestions(append = false) {
			this.loadError = false
			const cacheKey = 'questions_cache_' + (this.accountRef || 'default') + '_' + this.courseId
			if (!append) {
				this.page = 0
				const cache = this.currentFilter === 'all'
					? uni.getStorageSync(cacheKey)
					: ''
				if (cache) {
					try {
						this.questions = JSON.parse(cache)
					} catch (e) {
						this.questions = []
					}
					this.totalQuestions = this.questions.length
				} else {
					this.loading = true
					this.questions = []
					this.totalQuestions = 0
				}
			} else {
				this.loadingMore = true
			}

			try {
				const params = { courseId: this.courseId, page: this.page }
				if (this.accountRef) params.ref = this.accountRef

				if (this.currentFilter === 'open') params.isOpen = 1
				else if (this.currentFilter === 'unanswered') params.isAnswered = 0
				else if (this.currentFilter === 'answered') params.isAnswered = 1

				const data = await get('/api/quiz/questions', params)
				const list = data.questions || data.data || []

				if (append) {
					const merged = [...this.questions, ...list]
					this.questions = merged.filter((item, index) =>
						merged.findIndex(candidate => candidate.id === item.id) === index
					)
				} else {
					this.questions = list
					if (this.page === 0 && this.currentFilter === 'all') {
						uni.setStorageSync(cacheKey, JSON.stringify(list))
					}
				}

				this.hasMore = this.questions.length < (data.questionNum || 0)
				this.totalQuestions = data.questionNum || this.questions.length
			} catch (e) {
				console.error(e)
				this.loadError = true
			} finally {
				this.loading = false
				this.loadingMore = false
			}
		},

		changeFilter(key) {
			this.currentFilter = key
			this.loadQuestions()
		},

		handleAnswerSubmitted(payload) {
			if (Number(payload?.courseId) !== this.courseId) return
			const question = this.questions.find(item => Number(item.id) === Number(payload.questionId))
			if (question) question.isAnswered = 1
			if (this.currentFilter === 'unanswered' && question) {
				this.questions = this.questions.filter(item => Number(item.id) !== Number(payload.questionId))
			}
			const cacheKey = 'questions_cache_' + (this.accountRef || 'default') + '_' + this.courseId
			if (this.currentFilter === 'all') {
				uni.setStorageSync(cacheKey, JSON.stringify(this.questions))
			}
			setTimeout(() => this.loadQuestions(false), 350)
		},

		goDetail(q) {
			uni.navigateTo({
				url: `/pages/quiz/detail?questionId=${q.id}&courseId=${this.courseId}&ref=${encodeURIComponent(this.accountRef)}`
			})
		}
	}
}
</script>

<style lang="scss" scoped>
.page-container {
	height: 100vh;
	background: #F8F9FA;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

/* 顶部统一固定吸顶头部容器（导航 + 分类筛选 + 汇总条） */
.top-fixed-header {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	background: #FFFFFF;
	z-index: 1000;
	box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
}

.app-bar-inner {
	height: 52px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 28rpx;
	border-bottom: 0.5px solid rgba(0, 0, 0, 0.04);
}

.nav-back-btn {
	display: flex;
	align-items: center;
	gap: 4rpx;
	padding: 12rpx 16rpx 12rpx 0;
}

.back-arrow {
	font-size: 40rpx;
	font-weight: 300;
	color: #0A84FF;
	line-height: 1;
}

.back-text {
	font-size: 28rpx;
	font-weight: 600;
	color: #0A84FF;
}

.title-col {
	display: flex;
	flex-direction: column;
	align-items: center;
	max-width: 420rpx;
}

.app-title {
	font-size: 30rpx;
	font-weight: 700;
	color: #191C1D;
	text-align: center;
	max-width: 400rpx;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.acc-badge {
	font-size: 20rpx;
	color: #0A84FF;
	font-weight: 600;
	margin-top: 2rpx;
}

.app-bar-right {
	min-width: 80rpx;
	display: flex;
	justify-content: flex-end;
}

.refresh-pill-btn {
	width: 60rpx;
	height: 60rpx;
	border-radius: 50%;
	background: #FFFFFF;
	display: flex;
	align-items: center;
	justify-content: center;
	border: 1px solid rgba(0, 0, 0, 0.08);
	box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
}

.refresh-icon {
	font-size: 26rpx;
}

.main-body {
	flex: 1;
	display: flex;
	flex-direction: column;
	width: 100%;
}

.filter-bar {
	display: flex;
	padding: 16rpx 28rpx;
	gap: 16rpx;
	background: #FFFFFF;
	border-bottom: 0.5px solid rgba(0, 0, 0, 0.05);
	flex-shrink: 0;
}

.filter-item {
	padding: 10rpx 26rpx;
	border-radius: 20rpx;
	font-size: 24rpx;
	color: #717786;
	background: #F2F2F7;
	transition: all 0.2s;
	font-weight: 500;
}

.filter-item.active {
	background: linear-gradient(135deg, #0A84FF, #005BB5);
	color: #fff;
	font-weight: 600;
}

.summary-bar {
	padding: 14rpx 28rpx;
	background: #FFFFFF;
	display: flex;
	justify-content: space-between;
	align-items: center;
	border-bottom: 0.5px solid rgba(0,0,0,0.05);
	flex-shrink: 0;
}

.summary-text {
	font-size: 24rpx;
	color: #717786;
	font-weight: 500;
}

.summary-sub {
	font-size: 22rpx;
	color: #AEAEB2;
}

.content {
	flex: 1;
	width: 100%;
	box-sizing: border-box;
}

.questions-container {
	width: 100%;
	max-width: 700rpx;
	margin: 0 auto;
	padding: 24rpx 28rpx 80rpx;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	gap: 20rpx;
}

.glass-card {
	background: #FFFFFF;
	border-radius: 24rpx;
	padding: 28rpx;
	box-sizing: border-box;
	border: 1px solid rgba(0, 0, 0, 0.06);
	box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.03);
}

.glass-card-hover {
	opacity: 0.88;
	transform: scale(0.99);
}

.question-skeleton { padding: 28rpx; overflow: hidden; }
.skeleton-pill, .skeleton-text {
	position: relative;
	overflow: hidden;
	background: #E9E9EE;
}
.skeleton-pill { width: 108rpx; height: 34rpx; border-radius: 10rpx; margin-bottom: 22rpx; }
.skeleton-text { height: 24rpx; border-radius: 12rpx; margin-bottom: 16rpx; }
.skeleton-text.short { width: 65%; margin-bottom: 0; }
.skeleton-pill::after, .skeleton-text::after {
	content: '';
	position: absolute;
	top: 0;
	bottom: 0;
	left: -80%;
	width: 65%;
	background: linear-gradient(90deg, transparent, rgba(255,255,255,.85), transparent);
	animation: question-shimmer 1.35s infinite;
}
@keyframes question-shimmer { to { left: 120%; } }

.error-state, .empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 16rpx;
	background: #FFFFFF;
	border-radius: 24rpx;
	padding: 60rpx 40rpx;
	box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.03);
	margin-top: 40rpx;
}

.error-emoji, .empty-emoji {
	font-size: 56rpx;
}

.empty-text, .error-text { font-size: 28rpx; color: #717786; font-weight: 500; }

.question-card {
	width: 100%;
}

.q-header {
	display: flex;
	align-items: center;
	gap: 12rpx;
	margin-bottom: 16rpx;
	flex-wrap: wrap;
}

.q-type-badge {
	padding: 6rpx 18rpx;
	border-radius: 10rpx;
	font-size: 22rpx;
	font-weight: 600;
}

.badge {
	padding: 6rpx 18rpx;
	border-radius: 10rpx;
	font-size: 22rpx;
	font-weight: 600;
}

.badge-success { background: #E5F9ED; color: #006E28; }
.badge-info { background: #F2F2F7; color: #8E8E93; }
.badge-warning { background: #FFF5DF; color: #9A5B00; }

.type-0, .type-1 { background: #E6F2FF; color: #0A84FF; }
.type-2 { background: rgba(108, 92, 231, 0.12); color: #6c5ce7; }
.type-3 { background: #E5F9ED; color: #006E28; }
.type-4 { background: #FFF5DF; color: #D97706; }
.type-5 { background: #FFEBEB; color: #DC2626; }

.q-title {
	font-size: 28rpx;
	color: #191C1D;
	line-height: 1.55;
	display: block;
	font-weight: 500;
}

.q-time {
	font-size: 22rpx;
	color: #8E8E93;
	margin-top: 14rpx;
	display: block;
}

.loadmore {
	text-align: center;
	padding: 30rpx;
}

.loadmore-text { font-size: 26rpx; color: #0A84FF; }
</style>
