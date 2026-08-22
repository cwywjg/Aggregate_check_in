<template>
	<view class="page-container">
		<!-- 自定义顶部导航栏（带返回按钮与当前答题账号展示） -->
		<view class="top-app-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
			<view class="app-bar-inner">
				<view class="nav-back-btn" @tap="goBack">
					<text class="back-arrow">‹</text>
					<text class="back-text">返回</text>
				</view>
				<view class="title-col">
					<text class="app-title">{{ typeLabel(question ? question.type : 1) }}题详情</text>
					<text class="acc-badge">👤 {{ currentAccount?.nickname || currentAccount?.name || '答题账号' }}</text>
				</view>
				<view class="app-bar-right">
					<view class="refresh-pill-btn" @tap="loadDetail(false)">
						<text class="refresh-icon">🔄</text>
					</view>
				</view>
			</view>
		</view>

		<scroll-view scroll-y class="main-content" :style="{ paddingTop: (statusBarHeight + 52) + 'px' }">
			<view class="quiz-container">
				<!-- 首屏骨架 -->
				<view v-if="loading" class="skeleton-wrap">
					<view class="skeleton-card skeleton-shimmer">
						<view class="skeleton-line short"></view>
						<view class="skeleton-line"></view>
						<view class="skeleton-line medium"></view>
					</view>
					<view v-for="idx in 4" :key="idx" class="skeleton-option skeleton-shimmer"></view>
				</view>

				<template v-else-if="question">
					<!-- 当前答题账号提示条 -->
					<view class="account-identity-bar">
						<image class="id-avatar" :src="getAvatar(currentAccount)" mode="aspectFill"></image>
						<text class="id-text">当前查看「{{ currentAccount?.nickname || currentAccount?.name || '选定账号' }}」的作答状态</text>
					</view>

					<view v-if="feedbackMessage" class="feedback-banner" :class="feedbackType">
						<text>{{ feedbackMessage }}</text>
					</view>
					<view v-if="syncState !== 'idle'" class="sync-banner" :class="syncState">
						<view v-if="syncState === 'running'" class="mini-spinner"></view>
						<text>{{ syncMessage }}</text>
					</view>

					<!-- 题目信息卡片 -->
					<view class="q-header glass-card">
						<view class="q-meta">
							<view class="q-type-badge" :class="'type-' + question.type">
								<text>{{ typeLabel(question.type) }}</text>
							</view>
							<view v-if="question.isOpen === 1" class="badge badge-success"><text>开放中</text></view>
							<view v-else class="badge badge-info"><text>已关闭</text></view>
							<view v-if="isAnsweredLocked" class="badge badge-answered"><text>🔒 已作答 (不可修改)</text></view>
							<view v-else class="badge badge-warning"><text>未作答</text></view>
						</view>
						<!-- 题目内容 (HTML) -->
						<rich-text class="q-content" :nodes="formatRichText(question.title || question.content || '')"></rich-text>
					</view>

					<!-- ===== 选择题 (单选/多选/判断) ===== -->
					<view v-if="isChoiceType" class="options-area">
						<view v-for="(opt, idx) in options" :key="idx"
							class="option-card glass-card"
							:class="{
								'option-locked': isAnsweredLocked,
								'option-submitted': isAnsweredLocked && isRankSubmitted(opt.rank) && !isRankCorrect(opt.rank),
								'option-correct': hasCorrectAnswer && isRankCorrect(opt.rank),
								'option-both': isAnsweredLocked && isRankSubmitted(opt.rank) && isRankCorrect(opt.rank),
								'option-wrong': isAnsweredLocked && hasCorrectAnswer && isRankSubmitted(opt.rank) && !isRankCorrect(opt.rank),
								'option-selected': !isAnsweredLocked && isRankSelected(opt.rank),
								'option-disabled': isAnsweredLocked || submitting
							}"
							@tap="!isAnsweredLocked && selectOption(opt)">
							<view class="option-letter"
								:class="{
									'letter-submitted': isAnsweredLocked && isRankSubmitted(opt.rank) && !isRankCorrect(opt.rank),
									'letter-correct': hasCorrectAnswer && isRankCorrect(opt.rank),
									'letter-both': isAnsweredLocked && isRankSubmitted(opt.rank) && isRankCorrect(opt.rank),
									'letter-wrong': isAnsweredLocked && hasCorrectAnswer && isRankSubmitted(opt.rank) && !isRankCorrect(opt.rank),
									'letter-selected': !isAnsweredLocked && isRankSelected(opt.rank)
								}">
								<text>{{ String.fromCharCode(65 + idx) }}</text>
							</view>
							<view class="option-content-box">
								<rich-text class="option-content" :nodes="formatRichText(opt.content || '')"></rich-text>
							</view>
							<view class="option-tag-list">
								<text v-if="hasCorrectAnswer && isRankCorrect(opt.rank)" class="opt-tag tag-correct-badge">正确答案</text>
								<text v-if="isAnsweredLocked && isRankSubmitted(opt.rank)" class="opt-tag tag-submitted-badge">已提交记录</text>
								<text v-else-if="!isAnsweredLocked && isRankSelected(opt.rank)" class="opt-tag tag-my-badge">自选</text>
							</view>
						</view>
					</view>

					<!-- ===== 填空题 ===== -->
					<view v-else-if="question.type === 4" class="fill-container">
						<!-- 已作答：展示每空的作答对比卡片 -->
						<template v-if="isAnsweredLocked">
							<view v-for="(ans, idx) in submittedFillAnswers" :key="idx" class="fill-compare-card glass-card">
								<view class="fill-card-top">
									<view class="fill-index-pill">
										<text class="fill-index-icon">✏️</text>
										<text class="fill-index-label">第 {{ idx + 1 }} 空</text>
									</view>
								</view>

								<view class="fill-sections-wrap">
									<!-- 提交的作答 -->
									<view class="fill-block my-fill-block">
										<view class="block-title-row">
											<text class="block-icon">👤</text>
											<text class="block-label">提交作答</text>
										</view>
										<text class="block-val my-val">{{ formatCleanAnswer(ans) || '(未填写)' }}</text>
									</view>

									<!-- 标准答案 -->
									<view v-if="getBlankCorrectAnswer(idx)" class="fill-block std-fill-block">
										<view class="block-title-row">
											<text class="block-icon">✅</text>
											<text class="block-label">标准答案</text>
										</view>
										<text class="block-val std-val">{{ getBlankCorrectAnswer(idx) }}</text>
									</view>
								</view>
							</view>
						</template>

						<!-- 未作答：交互式填写 -->
						<template v-else>
							<view class="fill-area glass-card">
								<text class="area-label">填写答案</text>
								<view v-for="(ans, idx) in fillAnswers" :key="idx" class="fill-edit-item">
									<text class="fill-edit-label">第 {{ idx + 1 }} 空</text>
									<input class="fill-input" v-model="fillAnswers[idx]"
										placeholder="请输入此空答案" placeholder-class="placeholder"></input>
								</view>
								<view class="add-fill-btn" @tap="addFillSlot">
									<text class="add-fill-text">+ 添加填空项</text>
								</view>
							</view>
						</template>
					</view>

					<!-- ===== 主观题 ===== -->
					<view v-else-if="question.type === 5" class="subjective-area">
						<!-- 已作答：只读展示 -->
						<template v-if="isAnsweredLocked">
							<view class="glass-card text-input-card">
								<text class="area-label">已提交作答内容 (服务器记录)</text>
								<view class="subjective-readonly-box">
									<text class="subjective-readonly-text">{{ submittedSubjectiveText || '无文字作答内容' }}</text>
								</view>
							</view>
							<view v-if="serverFiles.length" class="glass-card upload-section">
								<text class="area-label">已提交附件</text>
								<text class="existing-file-hint">服务器已保存 {{ serverFiles.length }} 个作答附件</text>
							</view>
						</template>

						<!-- 未作答：编辑与上传 -->
						<template v-else>
							<view class="glass-card text-input-card">
								<text class="area-label">文字作答</text>
								<textarea class="text-input" v-model="subjectiveText"
									placeholder="请输入答案内容..."
									placeholder-class="placeholder" :auto-height="true" :maxlength="2000"></textarea>
							</view>

							<!-- 图片上传 -->
							<view class="glass-card upload-section">
								<text class="area-label">图片附件 (最多3张)</text>
								<view class="image-grid">
									<view v-for="(img, idx) in uploadedImages" :key="idx" class="image-item">
										<image :src="img.localPath" mode="aspectFill" class="preview-img"></image>
										<view class="remove-btn" @tap="removeImage(idx)">
											<text class="remove-icon">×</text>
										</view>
									</view>
									<view v-if="uploadedImages.length < 3" class="image-add" @tap="chooseImage">
										<text class="add-icon">+</text>
										<text class="add-hint">添加图片</text>
									</view>
								</view>
							</view>

							<!-- 录音上传 -->
							<view class="glass-card upload-section">
								<text class="area-label">录音附件</text>
								<view v-for="(audio, idx) in uploadedAudios" :key="idx" class="audio-item">
									<text class="audio-name">{{ audio.name }}</text>
									<text class="remove-audio text-danger" @tap="removeAudio(idx)">删除</text>
								</view>
								<view class="action-btn" @tap="chooseAudio">
									<text class="action-text">+ 选择录音文件</text>
								</view>
							</view>
						</template>
					</view>

					<!-- 作答结果与解析卡片 (只展示服务器记录的答案与正确答案对比) -->
					<view class="result-summary-card glass-card" v-if="isAnsweredLocked || hasCorrectAnswer">
						<view class="result-card-header">
							<view class="result-title-group">
								<text class="result-icon">📊</text>
								<text class="result-card-title">作答结果与解析</text>
							</view>
							<view v-if="question.isCorrect === 1" class="judge-badge judge-correct">
								<text>✓ 回答正确</text>
							</view>
							<view v-else-if="question.isCorrect === 0" class="judge-badge judge-wrong">
								<text>✗ 回答错误</text>
							</view>
							<view v-else class="judge-badge judge-submitted">
								<text>已作答记录</text>
							</view>
						</view>

						<!-- 服务器记录的自选答案 -->
						<view class="answer-compare-row" v-if="isAnsweredLocked">
							<text class="compare-label">👤 提交作答：</text>
							<text class="compare-val my-answer-val">{{ myAnswerText }}</text>
						</view>

						<!-- 正确答案 -->
						<view class="answer-compare-row" v-if="hasCorrectAnswer">
							<text class="compare-label">✅ 正确答案：</text>
							<text class="compare-val correct-answer-val">{{ correctAnswerText }}</text>
						</view>

						<!-- 题目解析 -->
						<view class="explain-container" v-if="question.explain">
							<text class="explain-heading">💡 题目解析：</text>
							<rich-text class="explain-body" :nodes="formatRichText(question.explain)"></rich-text>
						</view>
					</view>

					<!-- 操作区域：已作答锁定 / 允许提交（已关闭题目未作答时亦可提交） -->
					<view class="submit-area" v-if="!loading">
						<!-- 1. 已作答锁定卡片（仅提交过的才限制） -->
						<view v-if="isAnsweredLocked" class="lock-status-card">
							<text class="lock-status-icon">🔒</text>
							<view class="lock-status-content">
								<text class="lock-status-title">该题目已完成作答</text>
								<text class="lock-status-desc">答案已固化提交至微助教服务器，系统不支持二次修改</text>
							</view>
						</view>

						<!-- 2. 未作答：均允许提交（支持开放中提交与已关闭补交） -->
						<view v-else class="btn-primary submit-btn" :class="{ 'btn-loading': submitting }" @tap="submitAnswer">
							<view v-if="submitting" class="button-spinner"></view>
							<text>{{ submitting ? '正在提交...' : (question.isOpen === 0 ? '🚀 确认并提交答案 (补交)' : '🚀 确认并提交答案') }}</text>
						</view>
					</view>
				</template>
			</view>
		</scroll-view>
	</view>
</template>

<script>
import { get, post, uploadFile } from '../../api/request'
import { getCachedAvatar } from '../../utils/avatar'

export default {
	data() {
		return {
			statusBarHeight: 20,
			courseId: 0,
			questionId: 0,
			accountRef: '',
			question: null,
			options: [],
			loading: true,
			submitting: false,

			// 未作答时的交互状态
			selectedRanks: [],
			selectedContents: [],
			fillAnswers: [''],
			subjectiveText: '',
			uploadedImages: [],   // [{localPath, fileKey}]
			uploadedAudios: [],   // [{name, fileKey}]
			serverFiles: [],

			// 提交与后台同步状态机
			feedbackMessage: '',
			feedbackType: 'success',
			syncState: 'idle',
			syncMessage: '',
			syncResults: {},
			syncTimer: null,
			loadSequence: 0
		}
	},
	computed: {
		isChoiceType() {
			return this.question && [1, 2, 3].includes(this.question.type)
		},
		isMultiSelect() {
			return this.question && this.question.type === 2
		},
		currentAccount() {
			if (this.accountRef) {
				const accounts = this.$store.state.accounts || []
				const found = accounts.find(a => a.ref === this.accountRef || a.openid === this.accountRef)
				if (found) return found
			}
			return this.$store.getters.quizAccount
		},
		// 已作答严格锁定
		isAnsweredLocked() {
			return Boolean(this.question && Number(this.question.isAnswered) === 1)
		},
		// 服务器记录的选择题答案 rank 列表
		submittedChoiceRanks() {
			if (!this.question || !this.isChoiceType || !this.isAnsweredLocked) return []
			const ans = this.question.serverAnswer || []
			return ans.map(item => {
				const value = item && typeof item === 'object' ? item.rank : item
				return this.normalizeRank(value)
			}).filter(rank => rank !== undefined && rank !== null)
		},
		// 服务器记录的填空题答案
		submittedFillAnswers() {
			if (!this.question || this.question.type !== 4 || !this.isAnsweredLocked) return []
			const ans = this.question.serverAnswer || []
			return ans.map(String)
		},
		// 服务器记录的主观题答案
		submittedSubjectiveText() {
			if (!this.question || this.question.type !== 5 || !this.isAnsweredLocked) return ''
			const ans = this.question.serverAnswer || []
			return ans[0] || ''
		},
		hasCorrectAnswer() {
			if (!this.question) return false
			if (this.isChoiceType) {
				return Array.isArray(this.question.correctAnswerRanks) && this.question.correctAnswerRanks.length > 0
			}
			if (this.question.type === 4) {
				if (Array.isArray(this.question.correctFillAnswers) && this.question.correctFillAnswers.some(ans => ans && !['true', 'false', '1', '0'].includes(String(ans).trim().toLowerCase()))) {
					return true
				}
				const clean = (s) => typeof s === 'string' && s.trim() && !['true', 'false', '1', '0', 'null'].includes(s.trim().toLowerCase())
				return clean(this.question.correctAnswer) || clean(this.question.standardAnswer)
			}
			const clean = (s) => typeof s === 'string' && s.trim() && !['true', 'false', '1', '0', 'null'].includes(s.trim().toLowerCase())
			return clean(this.question.correctAnswer) || clean(this.question.standardAnswer)
		},
		correctAnswerText() {
			if (!this.question) return '暂未公布'
			if (this.isChoiceType && this.hasCorrectAnswer) {
				return this.question.correctAnswerRanks.map(r => {
					const idx = this.options.findIndex(o => this.normalizeRank(o.rank) === r)
					if (idx >= 0) {
						const letter = String.fromCharCode(65 + idx)
						const opt = this.options[idx]
						const text = opt?.content ? opt.content.replace(/<[^>]+>/g, '').trim() : ''
						if (this.question.type === 3 && text && !['a', 'b', '1', '0'].includes(text.toLowerCase())) {
							return `${letter} (${text})`
						}
						return letter
					}
					return r + 1
				}).join(', ')
			}
			if (this.question.type === 4) {
				if (Array.isArray(this.question.correctFillAnswers) && this.question.correctFillAnswers.length > 0) {
					const validFills = this.question.correctFillAnswers.filter(ans => ans && !['true', 'false', '1', '0'].includes(String(ans).trim().toLowerCase()))
					if (validFills.length > 0) {
						return this.question.correctFillAnswers.map((ans, idx) => `空${idx + 1}: ${ans || '未填'}`).join('   |   ')
					}
				}
				const cleanStr = (s) => (typeof s === 'string' && s.trim() && !['true', 'false', '1', '0', 'null'].includes(s.trim().toLowerCase())) ? s.trim() : ''
				if (cleanStr(this.question.correctAnswer)) return cleanStr(this.question.correctAnswer)
				if (cleanStr(this.question.standardAnswer)) return cleanStr(this.question.standardAnswer)
			}
			const cleanStr = (s) => (typeof s === 'string' && s.trim() && !['true', 'false', '1', '0', 'null'].includes(s.trim().toLowerCase())) ? s.trim() : ''
			if (cleanStr(this.question.correctAnswer)) return cleanStr(this.question.correctAnswer)
			if (cleanStr(this.question.standardAnswer)) return cleanStr(this.question.standardAnswer)
			return this.hasCorrectAnswer ? '详见题目解析' : '暂未公布'
		},
		myAnswerText() {
			if (!this.question) return '未作答'
			if (this.isAnsweredLocked) {
				if (this.isChoiceType) {
					const ranks = this.submittedChoiceRanks
					if (!ranks.length) return '已作答'
					return ranks.map(r => {
						const idx = this.options.findIndex(o => this.normalizeRank(o.rank) === r)
						if (idx >= 0) {
							const letter = String.fromCharCode(65 + idx)
							const opt = this.options[idx]
							const text = opt?.content ? opt.content.replace(/<[^>]+>/g, '').trim() : ''
							if (this.question.type === 3 && text && !['a', 'b', '1', '0'].includes(text.toLowerCase())) {
								return `${letter} (${text})`
							}
							return letter
						}
						return r + 1
					}).join(', ')
				}
				if (this.question.type === 4) {
					const fills = this.submittedFillAnswers.filter(a => a && !['true', 'false', '1', '0'].includes(String(a).toLowerCase()))
					return fills.length ? fills.join(' | ') : (this.submittedFillAnswers.length ? this.submittedFillAnswers.join(' | ') : '已作答')
				}
				if (this.question.type === 5) {
					return this.submittedSubjectiveText || (this.serverFiles.length ? `已提交 ${this.serverFiles.length} 个附件` : '已作答')
				}
				return '已作答'
			} else {
				if (this.isChoiceType) {
					if (!this.selectedRanks.length) return '未作答'
					return this.selectedRanks.map(r => {
						const idx = this.options.findIndex(o => this.normalizeRank(o.rank) === r)
						return idx >= 0 ? String.fromCharCode(65 + idx) : (r + 1)
					}).join(', ')
				}
				if (this.question.type === 4) {
					const nonEmpties = this.fillAnswers.filter(Boolean)
					return nonEmpties.length ? nonEmpties.join(' | ') : '未作答'
				}
				if (this.question.type === 5) {
					return this.subjectiveText || '未作答'
				}
				return '未作答'
			}
		}
	},
	onLoad(options) {
		const sys = uni.getSystemInfoSync()
		this.statusBarHeight = sys.statusBarHeight || 20
		this.courseId = Number(options.courseId) || 0
		this.questionId = Number(options.questionId) || 0
		this.accountRef = options.ref || this.$store.getters.quizAccount?.ref || ''
		this.loadDetail()
	},
	onShow() {
		const currentSelectedRef = this.$store.getters.quizAccount?.ref || ''
		if (currentSelectedRef && currentSelectedRef !== this.accountRef) {
			this.accountRef = currentSelectedRef
			this.loadDetail(false)
		}
	},
	onHide() {
		uni.hideLoading()
	},
	onUnload() {
		if (this.syncTimer) clearTimeout(this.syncTimer)
		uni.hideLoading()
	},
	methods: {
		formatCleanAnswer(val) {
			if (val === null || val === undefined || typeof val === 'boolean') return ''
			if (Array.isArray(val)) {
				return val.map(x => this.formatCleanAnswer(x)).filter(Boolean).join(' / ')
			}
			let s = String(val).trim()
			if (!s) return ''
			if ((s.startsWith('[') && s.endsWith(']')) || (s.startsWith('{') && s.endsWith('}'))) {
				try {
					const parsed = JSON.parse(s)
					if (Array.isArray(parsed)) {
						return parsed.map(x => this.formatCleanAnswer(x)).filter(Boolean).join(' / ')
					}
					if (typeof parsed === 'object' && parsed) {
						return this.formatCleanAnswer(parsed.content || parsed.answer || parsed.value || '')
					}
				} catch (e) {
					s = s.replace(/^\s*\[\s*['"]?(.*?)['"]?\s*\]\s*$/, '$1').trim()
				}
			}
			s = s.replace(/^\s*\[\s*['"]?(.*?)['"]?\s*\]\s*$/, '$1').trim()
			s = s.replace(/<[^>]+>/g, '').trim()
			if (['true', 'false', 'null', 'undefined'].includes(s.toLowerCase())) return ''
			return s
		},
		getBlankCorrectAnswer(idx) {
			if (!this.question) return ''
			const fills = this.question.correctFillAnswers || []
			if (fills[idx]) {
				return this.formatCleanAnswer(fills[idx])
			}
			return ''
		},
		getAvatar(acc) {
			if (!acc) return '/static/avatar_default.png'
			return getCachedAvatar(acc.ref || acc.openid, this.$store.state.serverUrl, acc.avatar_url)
		},
		goBack() {
			uni.navigateBack({
				fail: () => {
					uni.redirectTo({
						url: `/pages/quiz/questions?courseId=${this.courseId}&ref=${encodeURIComponent(this.accountRef)}`
					})
				}
			})
		},
		normalizeRank(value) {
			const rank = Number(value)
			return Number.isFinite(rank) ? rank : value
		},
		isRankSelected(rank) {
			return this.selectedRanks.includes(this.normalizeRank(rank))
		},
		isRankSubmitted(rank) {
			return this.submittedChoiceRanks.includes(this.normalizeRank(rank))
		},
		isRankCorrect(rank) {
			if (!this.hasCorrectAnswer) return false
			return this.question.correctAnswerRanks.includes(this.normalizeRank(rank))
		},
		formatRichText(html) {
			if (!html) return ''
			let newHtml = html.replace(/<img[^>]*>/gi, (match) => {
				if (match.indexOf('style=') >= 0) {
					return match.replace(/style=['"][^'"]*['"]/gi, 'style="max-width:100%;height:auto;display:block;"')
				} else {
					return match.replace(/>/g, ' style="max-width:100%;height:auto;display:block;" >')
				}
			})
			return newHtml
		},
		typeLabel(type) {
			const map = { 0: '阅读', 1: '单选', 2: '多选', 3: '判断', 4: '填空', 5: '主观', 6: '排序' }
			return map[type] || '未知'
		},

		async loadDetail(silent = false) {
			const sequence = ++this.loadSequence
			if (!silent) this.loading = true
			try {
				const params = { courseId: this.courseId }
				if (this.accountRef) params.ref = this.accountRef

				const data = await get(`/api/quiz/questions/${this.questionId}`, params)
				if (sequence !== this.loadSequence) return
				if (!data || !data.id) throw new Error(data?.message || '题目数据为空')
				const type = Number(data.type)
				this.question = {
					...data,
					type: Number.isFinite(type) ? type : data.type,
					isOpen: Number(data.isOpen) === 1 ? 1 : 0,
					isAnswered: Number(data.isAnswered) === 1 ? 1 : 0
				}
				this.options = (data.answerContent || []).map(opt => ({
					...opt,
					rank: this.normalizeRank(opt.rank)
				}))
				this.serverFiles = Array.isArray(data.serverFiles) ? data.serverFiles : []
				
				// 仅在未作答时初始化交互表单
				if (!this.isAnsweredLocked) {
					this.selectedRanks = []
					this.selectedContents = []
					this.fillAnswers = Array.from(
						{ length: Math.max(1, Number(data.blankNum) || 1) },
						() => ''
					)
					this.subjectiveText = ''
				}
			} catch (e) {
				if (sequence === this.loadSequence) {
					uni.showToast({ title: e.message || '加载失败', icon: 'none' })
				}
			} finally {
				if (sequence === this.loadSequence) {
					this.loading = false
				}
			}
		},

		// ── 选择题交互 ──
		selectOption(opt) {
			if (this.isAnsweredLocked || this.submitting) return
			const rank = this.normalizeRank(opt.rank)

			if (this.question.type === 1 || this.question.type === 3) {
				// 单选 / 判断
				this.selectedRanks = [rank]
				this.selectedContents = [opt.content || '']
			} else if (this.question.type === 2) {
				// 多选
				const idx = this.selectedRanks.indexOf(rank)
				if (idx > -1) {
					this.selectedRanks.splice(idx, 1)
					this.selectedContents.splice(idx, 1)
				} else {
					const max = Number(this.question.maxChosen) || 0
					if (max > 0 && this.selectedRanks.length >= max) {
						uni.showToast({ title: `最多选择 ${max} 项`, icon: 'none' })
						return
					}
					this.selectedRanks.push(rank)
					this.selectedContents.push(opt.content || '')
				}
			}
		},

		// ── 填空题 ──
		addFillSlot() {
			if (this.isAnsweredLocked) return
			this.fillAnswers.push('')
		},

		// ── 主观题：图片 ──
		async chooseImage() {
			if (this.isAnsweredLocked) return
			try {
				const res = await new Promise((resolve, reject) => {
					uni.chooseImage({
						count: 3 - this.uploadedImages.length,
						sizeType: ['compressed'],
						sourceType: ['album', 'camera'],
						success: resolve,
						fail: reject
					})
				})

				for (const filePath of res.tempFilePaths) {
					uni.showLoading({ title: '上传图片中...' })
					try {
						const uploadRes = await uploadFile(filePath, 'image')
						this.uploadedImages.push({
							localPath: filePath,
							fileKey: uploadRes.fileKey || uploadRes.key || uploadRes.url
						})
					} catch (e) {
						uni.showToast({ title: '图片上传失败: ' + e.message, icon: 'none' })
					} finally {
						uni.hideLoading()
					}
				}
			} catch (err) {
				console.error('Image choose error:', err)
			}
		},

		removeImage(idx) {
			if (this.isAnsweredLocked) return
			this.uploadedImages.splice(idx, 1)
		},

		// ── 主观题：音频 ──
		async chooseAudio() {
			if (this.isAnsweredLocked) return
			try {
				// #ifdef APP-PLUS
				const FilePicker = plus.android.importClass('android.content.Intent')
				const Activity = plus.android.runtimeMainActivity()
				const intent = new FilePicker(FilePicker.ACTION_GET_CONTENT)
				intent.setType('audio/*')
				intent.addCategory(FilePicker.CATEGORY_OPENABLE)

				Activity.startActivityForResult(intent, 1002)
				return
				// #endif

				// #ifdef H5
				const input = document.createElement('input')
				input.type = 'file'
				input.accept = 'audio/*'
				input.onchange = async (e) => {
					const file = e.target.files[0]
					if (!file) return
					uni.showLoading({ title: '上传音频中...' })
					try {
						const uploadRes = await uploadFile(URL.createObjectURL(file), 'audio')
						this.uploadedAudios.push({
							name: file.name,
							fileKey: uploadRes.fileKey || uploadRes.key || uploadRes.url
						})
					} catch (err) {
						uni.showToast({ title: '音频上传失败: ' + err.message, icon: 'none' })
					} finally {
						uni.hideLoading()
					}
				}
				input.click()
				return
				// #endif

				// #ifdef MP-WEIXIN
				if (uni.chooseMessageFile) {
					uni.chooseMessageFile({
						count: 1,
						type: 'file',
						extension: ['mp3', 'wav', 'm4a', 'aac', 'ogg'],
						success: async (res) => {
							const file = res.tempFiles[0]
							uni.showLoading({ title: '上传音频中...' })
							try {
								const uploadRes = await uploadFile(file.path, 'audio')
								this.uploadedAudios.push({
									name: file.name,
									fileKey: uploadRes.fileKey || uploadRes.key || uploadRes.url
								})
							} catch (e) {
								uni.showToast({ title: '音频上传失败: ' + e.message, icon: 'none' })
							} finally {
								uni.hideLoading()
							}
						}
					})
					return
				}
				// #endif

				// #ifndef H5 || MP-WEIXIN
				if (plus && plus.io) {
					plus.io.resolveLocalFileSystemURL('_doc/', (entry) => {
						uni.showLoading({ title: '准备选择音频...' })
						try {
							uni.chooseFile({
								count: 1,
								type: 'all',
								success: async (res) => {
									const file = res.tempFiles[0]
									uni.showLoading({ title: '上传音频中...' })
									try {
										const uploadRes = await uploadFile(file.path, 'audio')
										this.uploadedAudios.push({
											name: file.name,
											fileKey: uploadRes.fileKey || uploadRes.key || uploadRes.url
										})
									} catch (e) {
										uni.showToast({ title: '音频上传失败: ' + e.message, icon: 'none' })
									} finally {
										uni.hideLoading()
									}
								}
							})
						} catch (e) {
							uni.showToast({ title: '音频选择失败', icon: 'none' })
						} finally {
							uni.hideLoading()
						}
					}, () => {}, { filter: 'none' })
					return
				}
				// #endif
				uni.showToast({ title: '当前设备不支持音频选择', icon: 'none' })
			} catch (err) {
				console.error('Audio choose error:', err)
			}
		},

		removeAudio(idx) {
			if (this.isAnsweredLocked) return
			this.uploadedAudios.splice(idx, 1)
		},

		// ── 直接提交本账号答案 ──
		async submitAnswer() {
			if (this.isAnsweredLocked) {
				uni.showToast({ title: '该题已作答，不可修改', icon: 'none' })
				return
			}
			if (this.submitting) return

			// 校验
			if (this.isChoiceType && this.selectedRanks.length === 0) {
				uni.showToast({ title: '请先选择答案', icon: 'none' })
				return
			}
			if (this.isMultiSelect) {
				const minChosen = Number(this.question.minChosen) || 0
				const maxChosen = Number(this.question.maxChosen) || 0
				if (minChosen > 0 && this.selectedRanks.length < minChosen) {
					uni.showToast({ title: `至少选择 ${minChosen} 项`, icon: 'none' })
					return
				}
				if (maxChosen > 0 && this.selectedRanks.length > maxChosen) {
					uni.showToast({ title: `最多选择 ${maxChosen} 项`, icon: 'none' })
					return
				}
			}
			if (this.question.type === 4 && this.fillAnswers.some(answer => !String(answer).trim())) {
				uni.showToast({ title: '请填写全部空位', icon: 'none' })
				return
			}

			this.submitting = true
			uni.showLoading({ title: '🚀 正在提交答案...', mask: true })

			try {
				const body = {
					courseId: this.courseId,
					questionId: this.questionId,
					questionType: this.question.type,
					ref: this.accountRef,
					answer: {
						selectedRanks: this.selectedRanks,
						selectedContents: this.selectedContents
					},
					answerText: this.question.type === 4
						? [...this.fillAnswers]
						: (this.question.type === 5 ? [this.subjectiveText] : []),
					files: this.uploadedImages.map(i => i.fileKey),
					audio: this.uploadedAudios.map(a => a.fileKey)
				}

				const res = await post('/api/quiz/submit', body)
				uni.hideLoading()
				if (res && res.success) {
					this.question.isAnswered = 1
					this.question.serverAnswer = this.isChoiceType
						? [...this.selectedRanks]
						: (this.question.type === 4 ? [...this.fillAnswers] : [this.subjectiveText])
					uni.showToast({
						title: '🎉 答案已提交！',
						icon: 'success',
						duration: 2000
					})
					uni.$emit('quiz-answer-submitted', {
						courseId: this.courseId,
						questionId: this.questionId
					})
					setTimeout(() => this.loadDetail(true), 400)
				} else {
					uni.showToast({ title: res?.message || '提交失败', icon: 'none' })
				}
			} catch (e) {
				uni.hideLoading()
				uni.showToast({ title: '提交异常: ' + e.message, icon: 'none' })
			} finally {
				this.submitting = false
			}
		}
	}
}
</script>

<style lang="scss" scoped>
.page-container {
	min-height: 100vh;
	background: #F8F9FA;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
}

/* 顶部导航栏 */
.top-app-bar {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	background: rgba(248, 249, 250, 0.96);
	backdrop-filter: blur(12px);
	z-index: 1000;
	border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.app-bar-inner {
	height: 52px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 28rpx;
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

/* 主内容容器 */
.main-content {
	flex: 1;
	width: 100%;
	box-sizing: border-box;
}

.quiz-container {
	width: 100%;
	max-width: 700rpx;
	margin: 0 auto;
	padding: 24rpx 28rpx 120rpx;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	gap: 24rpx;
}

/* 账号身份标识条 */
.account-identity-bar {
	display: flex;
	align-items: center;
	gap: 14rpx;
	padding: 14rpx 22rpx;
	background: #EBF4FF;
	border-radius: 16rpx;
	border: 1px solid rgba(10, 132, 255, 0.2);
}

.id-avatar {
	width: 44rpx;
	height: 44rpx;
	border-radius: 50%;
	background: #fff;
	flex-shrink: 0;
}

.id-text {
	font-size: 24rpx;
	color: #0058BC;
	font-weight: 600;
}

/* 卡片通用样式 */
.glass-card {
	background: #FFFFFF;
	border-radius: 24rpx;
	padding: 32rpx 28rpx;
	box-sizing: border-box;
	border: 1px solid rgba(0, 0, 0, 0.06);
	box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.03);
	width: 100%;
}

/* 题目头部 */
.q-header {
	width: 100%;
}

.q-meta {
	display: flex;
	align-items: center;
	gap: 12rpx;
	margin-bottom: 20rpx;
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
.badge-answered { background: #EBF4FF; color: #0058BC; border: 1px solid rgba(0, 88, 188, 0.2); }

.type-0, .type-1 { background: #E6F2FF; color: #0A84FF; }
.type-2 { background: rgba(108, 92, 231, 0.12); color: #6c5ce7; }
.type-3 { background: #E5F9ED; color: #006E28; }
.type-4 { background: #FFF5DF; color: #D97706; }
.type-5 { background: #FFEBEB; color: #DC2626; }

.q-content {
	font-size: 30rpx;
	line-height: 1.65;
	color: #191C1D;
	word-break: break-word;
}

/* 选项区域 */
.options-area {
	display: flex;
	flex-direction: column;
	gap: 18rpx;
	width: 100%;
}

.option-card {
	display: flex;
	align-items: center;
	gap: 20rpx;
	padding: 26rpx 28rpx;
	transition: all 0.2s ease;
	border: 2rpx solid transparent;
}

.option-selected {
	border-color: #0A84FF;
	background: #F0F7FF;
}

.option-submitted {
	border-color: #0058BC;
	background: #F0F7FF;
}

.option-correct {
	border-color: #34C759;
	background: #EAF9EE;
}

.option-both {
	border-color: #34C759;
	background: #EAF9EE;
}

.option-wrong {
	border-color: #FF3B30;
	background: #FFF1F0;
}

.option-locked {
	cursor: default;
}

.option-letter {
	width: 60rpx;
	height: 60rpx;
	border-radius: 50%;
	background: #F2F2F7;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 28rpx;
	color: #717786;
	font-weight: 700;
	flex-shrink: 0;
	transition: all 0.2s ease;
}

.letter-selected {
	background: linear-gradient(135deg, #0A84FF, #005BB5);
	color: #fff;
}
.letter-submitted {
	background: #0058BC;
	color: #fff;
}
.letter-correct {
	background: linear-gradient(135deg, #34C759, #28A745);
	color: #fff;
}
.letter-both {
	background: linear-gradient(135deg, #006E28 0%, #34C759 100%);
	color: #fff;
}
.letter-wrong {
	background: linear-gradient(135deg, #FF3B30, #DC3545);
	color: #fff;
}

.option-content-box {
	flex: 1;
	min-width: 0;
}

.option-content {
	font-size: 28rpx;
	color: #191C1D;
	line-height: 1.5;
}

.option-tag-list {
	display: flex;
	flex-direction: column;
	gap: 6rpx;
	align-items: flex-end;
	flex-shrink: 0;
}

.opt-tag {
	font-size: 20rpx;
	font-weight: 600;
	padding: 4rpx 12rpx;
	border-radius: 6rpx;
}

.tag-correct-badge {
	background: #E5F9ED;
	color: #006E28;
	border: 1px solid rgba(0, 110, 40, 0.2);
}

.tag-submitted-badge {
	background: #D8E2FF;
	color: #004493;
	border: 1px solid rgba(0, 68, 147, 0.2);
}

.tag-my-badge {
	background: #D8E2FF;
	color: #004493;
}

/* 结果解析卡片 */
.result-summary-card {
	width: 100%;
}

.result-card-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 20rpx;
	padding-bottom: 16rpx;
	border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.result-title-group {
	display: flex;
	align-items: center;
	gap: 10rpx;
}

.result-icon { font-size: 30rpx; }
.result-card-title { font-size: 28rpx; font-weight: 700; color: #191C1D; }

.judge-badge {
	font-size: 22rpx;
	font-weight: 700;
	padding: 4rpx 16rpx;
	border-radius: 20rpx;
}

.judge-correct { background: #E5F9ED; color: #006E28; }
.judge-wrong { background: #FFEBEB; color: #BA1A1A; }
.judge-submitted { background: #D8E2FF; color: #004493; }

.answer-compare-row {
	display: flex;
	align-items: center;
	margin-bottom: 14rpx;
	font-size: 26rpx;
}

.compare-label {
	color: #717786;
	font-weight: 500;
	width: 180rpx;
	flex-shrink: 0;
}

.compare-val { font-weight: 700; font-size: 28rpx; }
.my-answer-val { color: #0058BC; }
.correct-answer-val { color: #006E28; }

.explain-container {
	margin-top: 18rpx;
	padding-top: 16rpx;
	border-top: 1px dashed rgba(0, 0, 0, 0.08);
}

.explain-heading {
	font-size: 26rpx;
	font-weight: 700;
	color: #D97706;
	margin-bottom: 8rpx;
	display: block;
}

.explain-body {
	font-size: 26rpx;
	color: #414755;
	line-height: 1.6;
}

/* 填空题容器 */
.fill-container {
	display: flex;
	flex-direction: column;
	gap: 20rpx;
	width: 100%;
}

.fill-compare-card {
	width: 100%;
	display: flex;
	flex-direction: column;
	gap: 18rpx;
	padding: 26rpx;
	box-sizing: border-box;
}

.fill-card-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.fill-index-pill {
	display: inline-flex;
	align-items: center;
	gap: 8rpx;
	padding: 6rpx 18rpx;
	background: #F2F4F7;
	border-radius: 12rpx;
}

.fill-index-icon {
	font-size: 24rpx;
}

.fill-index-label {
	font-size: 24rpx;
	font-weight: 700;
	color: #191C1D;
}

.fill-sections-wrap {
	display: flex;
	flex-direction: column;
	gap: 14rpx;
	width: 100%;
}

.fill-block {
	display: flex;
	flex-direction: column;
	gap: 8rpx;
	padding: 20rpx 24rpx;
	border-radius: 16rpx;
	box-sizing: border-box;
	width: 100%;
}

.my-fill-block {
	background: #F0F4F9;
	border: 1px solid #D8E2FF;
}

.std-fill-block {
	background: #EAF9EE;
	border: 1px solid rgba(52, 199, 89, 0.25);
}

.block-title-row {
	display: flex;
	align-items: center;
	gap: 8rpx;
}

.block-icon {
	font-size: 24rpx;
}

.block-label {
	font-size: 22rpx;
	font-weight: 700;
}

.my-fill-block .block-label {
	color: #004493;
}

.std-fill-block .block-label {
	color: #006E28;
}

.block-val {
	font-size: 30rpx;
	font-weight: 700;
	word-break: break-word;
	line-height: 1.4;
}

.my-val {
	color: #004493;
}

.std-val {
	color: #006E28;
}

/* 填空编辑态 */
.fill-area {
	width: 100%;
}

.fill-edit-item {
	display: flex;
	align-items: center;
	gap: 16rpx;
	margin-bottom: 20rpx;
}

.fill-edit-label {
	font-size: 26rpx;
	font-weight: 600;
	color: #717786;
	width: 110rpx;
	flex-shrink: 0;
}

.fill-input {
	flex: 1;
	height: 84rpx;
	background: #F8F9FA;
	border: 1px solid rgba(0, 0, 0, 0.08);
	border-radius: 14rpx;
	padding: 0 24rpx;
	color: #191C1D;
	font-size: 28rpx;
}

.add-fill-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 20rpx;
	border: 2rpx dashed #0A84FF;
	border-radius: 14rpx;
	margin-top: 10rpx;
}

.add-fill-text {
	font-size: 26rpx;
	color: #0A84FF;
	font-weight: 600;
}

/* 主观题 */
.subjective-area {
	display: flex;
	flex-direction: column;
	gap: 20rpx;
	width: 100%;
}

.text-input-card {
	width: 100%;
}

.text-input {
	width: 100%;
	min-height: 200rpx;
	background: #F8F9FA;
	border: 1px solid rgba(0, 0, 0, 0.08);
	border-radius: 14rpx;
	padding: 20rpx;
	color: #191C1D;
	font-size: 28rpx;
	box-sizing: border-box;
}

.subjective-readonly-box {
	background: #F0F4F9;
	border-radius: 14rpx;
	padding: 24rpx;
}

.subjective-readonly-text {
	font-size: 28rpx;
	color: #004493;
	line-height: 1.6;
	font-weight: 500;
}

.image-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 16rpx;
}

.image-item {
	position: relative;
	width: 180rpx;
	height: 180rpx;
}

.preview-img {
	width: 100%;
	height: 100%;
	border-radius: 14rpx;
}

.remove-btn {
	position: absolute;
	top: -10rpx;
	right: -10rpx;
	width: 40rpx;
	height: 40rpx;
	background: #FF3B30;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
}

.remove-icon { font-size: 24rpx; color: #fff; }

.image-add {
	width: 180rpx;
	height: 180rpx;
	border: 2rpx dashed #C7C7CC;
	border-radius: 14rpx;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 8rpx;
}

.add-icon { font-size: 48rpx; color: #AEAEB2; }
.add-hint { font-size: 20rpx; color: #AEAEB2; }

.audio-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 18rpx 0;
	border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.audio-name { font-size: 26rpx; color: #191C1D; }
.remove-audio { font-size: 24rpx; color: #DC2626; }
.action-btn { text-align: center; padding: 18rpx; }
.action-text { font-size: 26rpx; color: #0A84FF; font-weight: 600; }
.existing-file-hint { font-size: 24rpx; color: #717786; }

/* 提交与锁定区域 */
.submit-area {
	display: flex;
	justify-content: center;
	align-items: center;
	width: 100%;
	margin-top: 32rpx;
	margin-bottom: 40rpx;
}

.lock-status-card {
	display: flex;
	align-items: center;
	gap: 20rpx;
	padding: 28rpx 32rpx;
	background: #F0F4F9;
	border: 1px solid #D8E2FF;
	border-radius: 24rpx;
	width: 100%;
	box-sizing: border-box;
}

.lock-closed {
	background: #F8F9FA;
	border-color: #E1E3E4;
}

.lock-status-icon {
	font-size: 44rpx;
	flex-shrink: 0;
}

.lock-status-content {
	display: flex;
	flex-direction: column;
	gap: 4rpx;
}

.lock-status-title {
	font-size: 28rpx;
	font-weight: 700;
	color: #004493;
}

.lock-closed .lock-status-title {
	color: #191C1D;
}

.lock-status-desc {
	font-size: 22rpx;
	color: #717786;
	line-height: 1.4;
}

.submit-btn {
	width: 100%;
	max-width: 600rpx;
	height: 92rpx;
	background: linear-gradient(135deg, #0A84FF 0%, #0066CC 100%);
	color: #FFFFFF;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 30rpx;
	font-weight: 700;
	border-radius: 46rpx;
	box-shadow: 0 8rpx 24rpx rgba(10, 132, 255, 0.35);
}

.btn-loading { opacity: 0.78; pointer-events: none; }
.button-spinner { width: 30rpx; height: 30rpx; border: 4rpx solid rgba(255, 255, 255, 0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.75s linear infinite; margin-right: 12rpx; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 提示条 */
.feedback-banner, .sync-banner {
	display: flex;
	align-items: center;
	gap: 14rpx;
	padding: 20rpx 24rpx;
	border-radius: 16rpx;
	font-size: 25rpx;
	width: 100%;
	box-sizing: border-box;
}

.feedback-banner.success { color: #16743A; background: #E8F8EE; }
.feedback-banner.error { color: #B42318; background: #FDECEC; }
.sync-banner.running, .sync-banner.pending { color: #075EA8; background: #EAF4FF; }
.sync-banner.completed { color: #16743A; background: #E8F8EE; }
.sync-banner.warning { color: #9A5B00; background: #FFF5DF; }

/* 骨架屏 */
.skeleton-wrap { display: flex; flex-direction: column; gap: 20rpx; width: 100%; }
.skeleton-card, .skeleton-option { background: #fff; border-radius: 20rpx; overflow: hidden; position: relative; }
.skeleton-card { padding: 32rpx; }
.skeleton-option { height: 112rpx; }
.skeleton-line { height: 24rpx; width: 100%; border-radius: 12rpx; background: #E9E9EE; margin-bottom: 22rpx; }
.skeleton-line.short { width: 28%; }
.skeleton-line.medium { width: 72%; margin-bottom: 0; }
.skeleton-shimmer::after { content: ''; position: absolute; top: 0; bottom: 0; left: -80%; width: 70%; background: linear-gradient(90deg, transparent, rgba(255,255,255,.8), transparent); animation: shimmer 1.35s infinite; }
@keyframes shimmer { to { left: 120%; } }
</style>
