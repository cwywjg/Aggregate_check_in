<template>
	<view class="container">
		<!-- 账号管理 Tab 主界面 -->
		<view class="hero" v-if="currentTab === 'home'">
			<view class="hero-bg-decoration"></view> 
			
			<view class="hero-content">
				<view class="hero-title-wrap">
					<text class="hero-title">雨课堂签到助手</text>
					<view class="hero-badge">PRO</view>
				</view>
				<view class="title-underline"></view>
				<view class="subtitle-wrapper">
					<text class="hero-subtitle">云端中央数据库同步架构</text>
					<view class="author-tag" @click="showAuthorDialog = true" style="display: flex; flex-direction: row; align-items: center; gap: 5px; background: rgba(10, 132, 255, 0.1); border: 0.5px solid rgba(10, 132, 255, 0.25); padding: 4px 10px; border-radius: 12px; backdrop-filter: blur(10px);">
						<text style="font-size: 12px;">✨</text>
						<text style="color: #0A84FF; font-size: 11px; font-weight: 700; letter-spacing: 0.2px;">作者寄语</text>
					</view>
				</view>
			</view>
		</view>

		<view class="content-wrapper" v-if="currentTab === 'home'">
			<!-- 首页高阶 Dashboard：本地数据 Metric 与 批量扫码旗舰 CTA -->
			<view class="dashboard-hero-grid" style="display: flex; flex-direction: row; gap: 12px; margin-bottom: 16px;">
				<!-- 左侧数据卡片 -->
				<view class="metric-card-dark" style="flex: 1; background: linear-gradient(135deg, #1C1C1E, #2C2C2E); border-radius: 20px; padding: 14px 16px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 8px 24px rgba(0,0,0,0.12); display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden;">
					<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center;">
						<text style="font-size: 10px; font-weight: 800; color: rgba(255,255,255,0.6); letter-spacing: 0.8px;">TERMINALS</text>
						<view style="width: 22px; height: 22px; border-radius: 11px; background: rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center;">
							<text style="font-size: 12px; line-height: 1;">👥</text>
						</view>
					</view>

					<view style="margin-top: 10px;">
						<text style="font-size: 32px; font-weight: 900; color: #FFFFFF; font-family: monospace; letter-spacing: -1px; line-height: 1;">{{ totalAccounts }}</text>
						<text style="font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 6px; display: block; font-weight: 600;">本地缓存终端</text>
					</view>
				</view>

				<!-- 右侧【批量扫码签到】旗舰 CTA 按钮 (蓝色高光渐变) -->
				<view class="scan-cta-card-vibrant" @click="startBatchScan" style="flex: 1.6; background: linear-gradient(135deg, #0A84FF 0%, #0056B3 100%); border-radius: 20px; padding: 14px 16px; box-shadow: 0 10px 28px rgba(10, 132, 255, 0.4); display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden; cursor: pointer;">
					<!-- 装饰型背景水印 -->
					<text style="position: absolute; right: -6px; bottom: -12px; font-size: 64px; color: #FFFFFF; opacity: 0.18; pointer-events: none; line-height: 1;">📷</text>

					<!-- 顶部 Micro-Pill 与 Icon 组合 -->
					<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; position: relative; z-index: 1;">
						<view style="display: flex; flex-direction: row; align-items: center; gap: 4px; background: rgba(255,255,255,0.22); padding: 3px 8px; border-radius: 10px; backdrop-filter: blur(10px);">
							<view style="width: 5px; height: 5px; border-radius: 50%; background: #FFFFFF; box-shadow: 0 0 6px #FFF;"></view>
							<text style="font-size: 9px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;">⚡ BATCH SCANNER</text>
						</view>

						<!-- 专属扫码圆环图标 -->
						<view style="width: 32px; height: 32px; border-radius: 16px; background: rgba(255, 255, 255, 0.25); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(10px); box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
							<text style="font-size: 16px; line-height: 1;">📷</text>
						</view>
					</view>

					<!-- 核心标题与按键-in-按键箭头 -->
					<view style="margin-top: 12px; position: relative; z-index: 1;">
						<text style="font-size: 18px; font-weight: 900; color: #FFFFFF; letter-spacing: -0.3px; display: block; line-height: 1.2;">批量扫码签到</text>
						<view style="display: flex; flex-direction: row; align-items: center; gap: 4px; margin-top: 6px;">
							<text style="font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.95);">启动高能引擎</text>
							<text style="font-size: 13px; font-weight: 900; color: #FFFFFF; line-height: 1;">➔</text>
						</view>
					</view>
				</view>
			</view>

			<scroll-view scroll-y class="group-flow" :show-scrollbar="false">
				<view class="card">
					<view class="card-header" style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px;">
						<!-- 顶栏第一行：设备终端标题 (左) + 刷新/密钥配置/管理员 (右) -->
						<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; width: 100%;">
							<view style="display: flex; flex-direction: row; align-items: center; gap: 6px;">
								<text class="card-title" style="font-size: 18px; font-weight: 800; color: #1C1C1E;">设备终端</text>
								<text class="validity-refresh" :class="{ checking: accountValidityChecking }" @click="refreshAccountValidity(true)" style="color: #0A84FF; font-size: 10.5px; font-weight: 700; background: rgba(10,132,255,0.08); padding: 3px 7px; border-radius: 8px; cursor: pointer;">{{ accountValidityChecking ? '校验中…' : '⟳ 刷新' }}</text>
							</view>
							<view style="display: flex; flex-direction: row; align-items: center;">
								<view @click="openKeyConfigModal" style="background: rgba(255,149,0,0.1); padding: 5px 9px; border-radius: 9px; cursor: pointer; border: 0.5px solid rgba(255,149,0,0.25); display: flex; flex-direction: row; align-items: center; gap: 4px; max-width: 150px;">
									<text style="color: #FF9500; font-size: 10.5px; font-weight: 800; white-space: nowrap;">🔑 {{ userApiKey ? (currentGroupRemark || '云端已连接') : '设置云端密钥' }}</text>
									<text style="color: #FF9500; font-size: 10px;">›</text>
								</view>
							</view>
						</view>

						<!-- 云端拉取与上传 极客云端按键组 (带有 100% 显性云朵元素 + 巨型云朵背景水印) -->
						<view class="card-actions-row" style="display: flex; flex-direction: row; gap: 10px; width: 100%;">
							<!-- 从云端拉取 (iOS 极客蓝 Cloud Sync 胶囊) -->
							<view class="ios-cloud-btn pull-btn" @click="fetchCloudList" style="flex: 1; display: flex; flex-direction: row; align-items: center; justify-content: center; gap: 8px; background: linear-gradient(135deg, #0A84FF, #0056B3); padding: 9px 12px; border-radius: 14px; box-shadow: 0 4px 14px rgba(10,132,255,0.35); cursor: pointer; position: relative; overflow: hidden;">
								<!-- 背景巨型 ☁️ 云朵水印 -->
								<text style="position: absolute; right: 2px; bottom: -10px; font-size: 42px; color: #FFFFFF; opacity: 0.18; pointer-events: none;">☁️</text>

								<!-- 前景云朵 + ⬇️ 图标 -->
								<view style="display: flex; flex-direction: row; align-items: center; justify-content: center; gap: 2px; background: rgba(255,255,255,0.22); padding: 3px 8px; border-radius: 10px; backdrop-filter: blur(4px); position: relative; z-index: 1;">
									<text style="font-size: 14px; line-height: 1;">☁️</text>
									<text style="font-size: 11px; font-weight: 900; color: #FFFFFF; line-height: 1;">↓</text>
								</view>

								<view style="display: flex; flex-direction: column; position: relative; z-index: 1;">
									<text style="font-size: 13px; font-weight: 800; color: #FFFFFF; line-height: 1.1;">从云端拉取</text>
									<text style="font-size: 8.5px; font-weight: 700; color: rgba(255,255,255,0.9); letter-spacing: 0.5px;">PULL CLOUD</text>
								</view>
							</view>

							<!-- 上传至云端 (iOS 翡翠绿 Cloud Backup 胶囊) -->
							<view class="ios-cloud-btn push-btn" @click="pushToCloud" style="flex: 1; display: flex; flex-direction: row; align-items: center; justify-content: center; gap: 8px; background: linear-gradient(135deg, #34C759, #248A3D); padding: 9px 12px; border-radius: 14px; box-shadow: 0 4px 14px rgba(52,199,89,0.35); cursor: pointer; position: relative; overflow: hidden;">
								<!-- 背景巨型 ☁️ 云朵水印 -->
								<text style="position: absolute; right: 2px; bottom: -10px; font-size: 42px; color: #FFFFFF; opacity: 0.18; pointer-events: none;">☁️</text>

								<!-- 前景云朵 + ⬆️ 图标 -->
								<view style="display: flex; flex-direction: row; align-items: center; justify-content: center; gap: 2px; background: rgba(255,255,255,0.22); padding: 3px 8px; border-radius: 10px; backdrop-filter: blur(4px); position: relative; z-index: 1;">
									<text style="font-size: 14px; line-height: 1;">☁️</text>
									<text style="font-size: 11px; font-weight: 900; color: #FFFFFF; line-height: 1;">↑</text>
								</view>

								<view style="display: flex; flex-direction: column; position: relative; z-index: 1;">
									<text style="font-size: 13px; font-weight: 800; color: #FFFFFF; line-height: 1.1;">上传至云端</text>
									<text style="font-size: 8.5px; font-weight: 700; color: rgba(255,255,255,0.9); letter-spacing: 0.5px;">PUSH BACKUP</text>
								</view>
							</view>
						</view>
					</view>

					<!-- iOS 典雅极客用户群组状态条 (Ultra-Clean Group Badge & Section Divider) -->
					<view v-if="userApiKey || currentGroupRemark" style="background: #FFFFFF; border-radius: 14px; padding: 10px 14px; margin-bottom: 14px; border: 1px solid rgba(0,0,0,0.06); box-shadow: 0 4px 14px rgba(0,0,0,0.03); display: flex; flex-direction: row; align-items: center; justify-content: space-between;">
						<view style="display: flex; flex-direction: row; align-items: center; gap: 8px; flex: 1; min-width: 0;">
							<view style="width: 26px; height: 26px; border-radius: 8px; background: linear-gradient(135deg, rgba(10,132,255,0.15), rgba(88,86,214,0.15)); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
								<text style="font-size: 13px;"></text>
							</view>
							<view style="display: flex; flex-direction: row; align-items: center; gap: 6px; flex: 1; min-width: 0;">
								<text style="font-size: 12px; font-weight: 600; color: #8E8E93; flex-shrink: 0;">您当前所属群组:</text>
								<text style="font-size: 13px; font-weight: 800; color: #1C1C1E; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ currentGroupRemark || '专属加密群组' }}</text>
							</view>
						</view>
						<view @click="openKeyConfigModal" style="display: flex; flex-direction: row; align-items: center; gap: 4px; background: rgba(10,132,255,0.08); padding: 4px 10px; border-radius: 8px; cursor: pointer; flex-shrink: 0;">
							<text style="font-size: 11px; font-weight: 700; color: #0A84FF;">切换群组</text>
						</view>
					</view>

					<view class="terminals-list">
						<view class="terminal-item" v-for="(acc, accIndex) in accounts" :key="acc.id">
							<view class="terminal-left">
								<view class="avatar-circle">
									{{ (acc.remark || acc.name || '?').charAt(0) }}
								</view>
								<view class="terminal-meta">
									<view class="t-name-row">
										<text class="t-name">{{ acc.remark || acc.name || '未命名终端' }}</text>
										<text v-if="accountValidityChecking" class="status-checking">校验中</text>
										<text v-else-if="acc.expired" class="status-expired">已失效</text>
										<text v-else class="status-active">凭证有效</text>
									</view>
									<text class="t-sub">手机号: {{ acc.phone }}</text>
								</view>
							</view>
							<view class="terminal-right" style="display: flex; flex-direction: row; align-items: center; gap: 6px; flex-shrink: 0;">
								<!-- 横向小字 AI 托管 Pill 状态组件 -->
								<view class="account-ai-pill" style="display: flex; flex-direction: row; align-items: center; gap: 2px; background: rgba(10, 132, 255, 0.08); border: 0.5px solid rgba(10, 132, 255, 0.2); padding: 2px 6px; border-radius: 12px; flex-shrink: 0;">
									<text style="font-size: 10px; font-weight: 700; color: #0A84FF; white-space: nowrap;">AI托管</text>
									<switch :checked="acc.ai_mode" @change="e => toggleAccountAiMode(acc, e.detail.value)" color="#0A84FF" style="transform: scale(0.55); margin: -4px -6px -4px -6px;"/>
								</view>

								<!-- 透明红色移除按钮 -->
								<view class="t-remove-btn" @click="deleteAccount(accIndex)" style="display: flex; align-items: center; justify-content: center; background: rgba(255, 59, 48, 0.1); border: 0.5px solid rgba(255, 59, 48, 0.25); padding: 4px 8px; border-radius: 10px; cursor: pointer; flex-shrink: 0;">
									<text style="font-size: 11px; font-weight: 700; color: #FF3B30; white-space: nowrap;">移除</text>
								</view>
							</view>
						</view>
						
						<view class="dashed-add-zone" @click="openLoginModal">
							<view class="add-circle">+</view>
							<text>添加新账号凭证</text>
						</view>
					</view>
				</view>

				<view class="empty-state" v-if="accounts.length === 0">
					<view class="empty-graphic" style="display:flex; justify-content:center; margin-bottom:12px;">
						<text style="font-size: 40px; line-height: 1;">☁️</text>
					</view>
					<text class="empty-text">暂无本地账号</text>
					<text class="empty-subtext">点击 [从云端拉取] 获取数据库中的账号</text>
				</view>
				
				<view style="height: 60px;"></view>
			</scroll-view>
		</view>

		<view class="blur-mask" :class="{ 'mask-active': showCloudPullDialog }">
			<view class="sheet-modal high-modal" v-if="showCloudPullDialog">
				<view class="sheet-header">
					<text class="sheet-title">选择要拉取的账号</text>
					<text class="sheet-close" @click="showCloudPullDialog = false">取消</text>
				</view>
				<view class="sheet-body">
					<view class="import-preview-box">
						<view class="select-all-row" @click="toggleSelectAllCloud">
							<text class="select-all-text">全选 / 全不选</text>
							<view class="check-circle" :class="{'is-checked': isAllCloudSelected}"></view>
						</view>
						
						<scroll-view scroll-y class="preview-scroll">
							<view class="preview-item" v-for="(acc, idx) in cloudAccountsList" :key="idx" @click="acc.selected = !acc.selected">
								<view class="preview-info">
									<text class="p-name">{{ acc.remark || acc.name || '未命名' }}</text>
									<text class="p-sub">{{ acc.phone }}</text>
								</view>
								<view class="check-circle" :class="{'is-checked': acc.selected}"></view>
							</view>
						</scroll-view>

						<view class="import-actions" style="margin-top: 24px;">
							<button class="ios-btn vibrant" @click="confirmCloudPull('merge')">
								合并导入选中的 {{ selectedCloudCount }} 个账号
							</button>
							<button class="ios-btn dark-btn" @click="confirmCloudPull('replace')">
								仅保留选中的 {{ selectedCloudCount }} 个 (清空本地)
							</button>
						</view>
					</view>
				</view>
			</view>
		</view>

		<view class="blur-mask" :class="{ 'mask-active': showLoginDialog }">
			<view class="sheet-modal high-modal" v-if="showLoginDialog">
				<view class="sheet-header">
					<view style="display: flex; flex-direction: column;">
						<text class="sheet-title">{{ loginMode === 'sms' ? '新增账号' : '密码登录' }}</text>
						<text style="font-size: 11px; color: #8E8E93; margin-top: 2px;">{{ loginMode === 'sms' ? '验证码快捷登录并自动上云' : '雨课堂账号密码登录并自动上云' }}</text>
					</view>
					<text class="sheet-close" @click="closeLoginModal">关闭</text>
				</view>
				<view class="sheet-body">
					<view class="form-group">
						<text class="form-lbl">账号备注 (必填)</text>
						<input class="ios-input" placeholder="如：[室友] 张三" v-model="loginRemark" />
					</view>

					<view class="form-group">
						<text class="form-lbl">雨课堂绑定手机号</text>
						<input class="ios-input" type="number" placeholder="请输入雨课堂绑定手机号" v-model="loginPhone" />
					</view>

					<!-- 密码输入项（仅在密码模式下展示） -->
					<view class="form-group" v-if="loginMode === 'password'">
						<text class="form-lbl">雨课堂登录密码</text>
						<input class="ios-input" type="password" placeholder="请输入雨课堂登录密码" v-model="loginPassword" />
					</view>

					<!-- 安全核验 -->
					<view class="form-group" v-if="loginPhone.length >= 11">
						<text class="form-lbl">安全核验</text>
						<view class="captcha-box" @click="openCaptchaWebView" :class="{'captcha-done': captchaFinished, 'captcha-opening': captchaOpening}">
							<text v-if="captchaOpening">正在打开验证页面...</text>
							<text v-else-if="!captchaFinished">点击唤起点选验证码</text>
							<text v-else style="color: #10b981; font-weight: bold;">点选验证码核验通过</text>
						</view>
					</view>

					<!-- 短信验证码（仅在验证码模式下展示） -->
					<view class="form-group" v-if="loginMode === 'sms' && captchaFinished">
						<text class="form-lbl">短信验证码</text>
						<view class="code-row">
							<input class="ios-input code-input" type="number" placeholder="输入6位手机验证码" v-model="loginSmsCode" />
							<button class="code-btn" :disabled="smsCountDown > 0 || smsSending" @click="sendSmsCode">
								{{ smsSending ? '发送中...' : (smsCountDown > 0 ? smsCountDown + 's 后重置' : '重新发送验证码') }}
							</button>
						</view>
					</view>

					<!-- 右下角兜底切换入口 -->
					<view class="login-switch-row">
						<text
							v-if="loginMode === 'sms'"
							class="login-switch-link"
							@click="loginMode = 'password'"
						>收不到验证码？试试密码登录</text>
						<text
							v-else
							class="login-switch-link"
							@click="loginMode = 'sms'"
						>返回使用短信验证码登录</text>
					</view>

					<button
						class="ios-btn vibrant"
						v-if="loginMode === 'sms' && captchaFinished && loginSmsCode.length >= 4"
						@click="doAppLoginFlow"
					>
						登录并自动上云
					</button>
					<button
						class="ios-btn vibrant"
						v-else-if="loginMode === 'password' && captchaFinished && loginPassword.trim().length > 0"
						@click="doPasswordLoginFlow"
					>
						密码登录并自动上云
					</button>
				</view>
			</view>
		</view>

		<!-- 课堂答题 Tab：紧凑布局，优先展示选项 -->
		<view class="answer-page" v-if="currentTab === 'answer'">
			<!-- 极简顶栏：课程名 + WS状态 + 连接按钮，一行搞定 -->
			<view class="answer-topbar">
				<view class="answer-topbar-left">
					<view class="ws-chip" :class="wsConnectionState">
						<view class="ws-chip-dot"></view>
						<text>{{ wsStatusText }}</text>
					</view>
					<text class="answer-topbar-course">{{ currentLessonDisplayName || '未绑定课堂' }}</text>
				</view>
				<view class="answer-topbar-actions">
					<button class="demo-courseware-btn" @click="loadDemoCourseware">示例</button>
					<button v-if="isMonitoring" class="refresh-ws-btn" @click="forceReconnect">⟳</button>
					<button class="monitor-toggle-btn" @click="toggleMonitor">{{ isMonitoring ? '断开' : '连接' }}</button>
				</view>
			</view>

			<scroll-view scroll-y class="answer-scroll" :show-scrollbar="false">
				<!-- 课程明细身份名片（进入课堂后全自动拉取并完美展示课程名、教师与班级） -->
				<view v-if="currentLessonId" class="lesson-identity-banner" style="display: flex; flex-direction: row; align-items: center; justify-content: space-between; padding: 10px 12px; background: #FFFFFF; border-radius: 14px; margin-bottom: 10px; border-left: 4px solid #0A84FF; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
					<view style="display: flex; flex-direction: row; align-items: center; gap: 10px; min-width: 0; flex: 1;">
						<view style="width: 32px; height: 32px; border-radius: 10px; background: rgba(10,132,255,0.1); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
							<text style="font-size: 16px;">📖</text>
						</view>
						<view style="display: flex; flex-direction: column; min-width: 0; flex: 1;">
							<text style="font-size: 14px; font-weight: 800; color: #1C1C1E; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ currentLessonDisplayName || '在带课堂' }}</text>
							<text style="font-size: 11px; font-weight: 600; color: #8E8E93; margin-top: 1px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ currentLessonSecondaryText || `课堂 ID: ${currentLessonId}` }}</text>
						</view>
					</view>
					<view style="flex-shrink: 0; padding: 3px 8px; border-radius: 8px; background: #E5F9ED; border: 1px solid rgba(52,199,89,0.2); margin-left: 8px;">
						<text style="font-size: 10px; font-weight: 800; color: #248A3D;">● 课堂已联通</text>
					</view>
				</view>

				<!-- 题目信息条（有题目时才显示） -->
				<view v-if="answerProblemId" class="question-info-strip">
					<view class="question-info-left">
						<text class="question-type-tag">{{ questionTypeLabel }}</text>
						<text class="question-info-id">#{{ answerProblemId }}</text>
						<text v-if="currentQuestion.slideIndex !== null" class="question-info-slide">第{{ Number(currentQuestion.slideIndex) + 1 }}页</text>
					</view>
					<view class="countdown-pill" :class="{ urgent: questionRemaining <= 10 && !questionUnlimited, closed: !canAnswerCurrentQuestion }">
						<text class="countdown-label">{{ questionCountdownLabel }}</text>
						<text class="countdown-value">{{ questionCountdownText }}</text>
					</view>
				</view>

				<!-- 课件封面（全宽铺满，点击可预览大图） -->
				<view v-if="answerProblemId && currentQuestion.cover" class="compact-slide" @click="previewSlideImage(currentQuestion.cover)">
					<image class="compact-slide-img" :src="currentQuestion.cover" mode="aspectFill" @error="onSlideCoverError"></image>
					<view class="slide-preview-hint"><text>点击查看大图</text></view>
				</view>

				<!-- 题干（独立展示，不遮挡课件） -->
				<view v-if="answerProblemId && currentQuestion.body" class="question-body-card">
					<rich-text class="question-body-text" :nodes="currentQuestion.body"></rich-text>
				</view>

				<!-- 选项区域（核心操作区，给最大空间） -->
				<view v-if="answerProblemId" class="question-editor">
					<view v-if="!isTextQuestion" class="rich-options-list">
						<view v-for="option in displayedQuestionOptions" :key="option.key" class="rich-option" :class="{ selected: isOptionSelected(option.submitValue) }" @click="selectQuestionOption(option)">
							<view class="rich-option-key">{{ option.key }}</view>
							<rich-text class="rich-option-value" :nodes="option.value || option.key"></rich-text>
							<view class="rich-option-check">✓</view>
						</view>
					</view>
					<view v-else-if="answerProblemType === 3" class="text-answer-zone">
						<view v-for="(_, index) in fillAnswers" :key="index" class="fill-answer-row">
							<text class="fill-number">{{ index + 1 }}</text>
							<input class="fill-input" :value="fillAnswers[index]" :placeholder="`填写第 ${index + 1} 空`" @input="setFillAnswer(index, $event.detail.value)" />
						</view>
					</view>
					<view v-else class="text-answer-zone">
						<textarea class="subjective-input" v-model="subjectiveAnswer" placeholder="输入本题答案"></textarea>
					</view>

					<view v-if="currentQuestion.submittedCount > 0" class="submitted-tip">已为 {{ currentQuestion.submittedCount }} 个账号提交本题</view>
					<button class="batch-answer-btn" :disabled="!canSubmitAnswer" @click="doBatchAnswer">
						{{ submittingAnswer ? '正在批量提交…' : (aiHostedReceiversCount > 0 ? `提交到 ${checkedReceiversCount} 个手动账号 (已忽略 ${aiHostedReceiversCount} 个托管)` : `批量提交到 ${checkedReceiversCount} 个账号`) }}
					</button>
				</view>
				<view v-else class="waiting-question">
					<text class="waiting-question-title">{{ lessonSessionEnded ? '本次课堂已结束' : '等待教师发布题目' }}</text>
					<text class="waiting-question-sub">{{ lessonSessionEnded ? '下次扫码进入课堂后自动载入' : '连接课堂后，题目出现会自动载入选项与倒计时' }}</text>
				</view>

				<view class="card receiver-card">
					<view class="receiver-card-header" :class="{ expanded: answerReceiverExpanded }" @click="answerReceiverExpanded = !answerReceiverExpanded">
						<view>
							<text class="card-title">批量答题账号</text>
							<text class="receiver-count">已选 {{ checkedReceiversCount }} / {{ answerReceivers.length }}</text>
						</view>
						<view class="receiver-header-actions">
							<text class="receiver-select-all" @click.stop="toggleAllReceivers">{{ allReadyReceiversChecked ? '取消全选' : '全选就绪账号' }}</text>
							<text class="receiver-expand-arrow" :class="{ expanded: answerReceiverExpanded }">⌄</text>
						</view>
					</view>
					<view v-if="answerReceiverExpanded" class="terminals-list">
						<view class="terminal-item receiver-item" :class="{ disabled: !acc.ready }" v-for="acc in answerReceivers" :key="acc.id" @click="toggleReceiver(acc)">
							<view class="terminal-left">
								<view class="avatar-circle answer-avatar" :class="{ checked: acc.checked }">{{ (acc.remark || acc.name || '?').charAt(0) }}</view>
								<view class="terminal-meta">
									<view class="t-name-row">
										<text class="t-name">{{ acc.remark || acc.name || '未命名账号' }}</text>
										<text v-if="acc.ready" class="status-active">本课堂就绪</text>
										<text v-else class="status-expired">{{ acc.lessonToken ? '凭证待刷新' : '需先签到' }}</text>
									</view>
									<text class="t-sub">{{ acc.phone }} · {{ acc.readyReason }}</text>
								</view>
							</view>
							<view class="check-circle" :class="{ 'is-checked': acc.checked }"></view>
						</view>
					</view>
				</view>
				<view style="height: 120px;"></view>
			</scroll-view>

			<!-- 全屏课件预览蒙层 -->
			<view v-if="slidePreviewVisible" class="slide-fullscreen-mask" @click="closeSlidePreview">
				<image class="slide-fullscreen-img" :src="currentQuestion.cover" mode="aspectFit"></image>
				<view class="slide-fullscreen-close"><text>✕ 点击任意位置关闭</text></view>
			</view>
		</view>

		<view class="content-wrapper" v-if="currentTab === 'ai'">
			<!-- 顶部精致卡片框：标题 + 状态 + 刷新按键 -->
			<view class="card" style="margin-bottom: 14px; padding: 14px 16px;">
				<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center;">
					<view class="ai-module-heading">
						<view style="display: flex; flex-direction: row; align-items: center; gap: 8px;">
							<text style="font-size: 17px; font-weight: 800; color: #1C1C1E; letter-spacing: -0.4px; line-height: 1;">AI 答题日志</text>
							<view class="ai-ready-badge" :style="`display:flex;flex-direction:row;align-items:center;gap:5px;padding:4px 8px;border-radius:12px;background:${aiStatusState.ready ? 'rgba(52,199,89,0.12)' : 'rgba(255,149,0,0.12)'};border:0.5px solid ${aiStatusState.ready ? 'rgba(52,199,89,0.3)' : 'rgba(255,149,0,0.35)'};`">
								<view class="ready-dot" :style="`width:6px;height:6px;border-radius:50%;background:${aiStatusState.ready ? '#34C759' : '#FF9500'};`"></view>
								<text :style="`font-size:11px;font-weight:700;line-height:1;color:${aiStatusState.ready ? '#248A3D' : '#B25D00'};`">{{ aiStatusState.msg || '尚未检测 AI 状态' }}</text>
							</view>
						</view>
						<view class="active-ai-model-row">
							<text class="active-ai-model-label">三模型路由</text>
							<view class="dual-ai-model-chips">
								<text
									v-for="model in activeAiModelChips"
									:key="model.name"
									class="ai-model-chip"
									:class="model.tone"
								>{{ model.name }}</text>
							</view>
						</view>
						<view class="ai-health-probes-list">
							<view
								v-for="probe in aiHealthProbes"
								:key="probe.displayName"
								class="ai-health-record"
								:class="[probe.success === true ? 'success' : (probe.success === false ? 'failed' : 'pending'), probe.tone]"
							>
								<view class="ai-health-left">
									<view class="ai-health-dot" :class="probe.tone"></view>
									<text class="ai-health-name" :class="probe.tone">{{ probe.displayName }} 连通性</text>
								</view>
								<view class="ai-health-right">
									<text class="ai-health-result">{{ probe.success === true ? '在线' : (probe.success === false ? '异常' : '待测') }}</text>
									<text v-if="probe.checkedAtText" class="ai-health-time">{{ probe.checkedAtText }} · {{ probe.elapsedSeconds || 0 }}s</text>
								</view>
							</view>
						</view>
						<view v-if="activeAiTask" class="active-ai-task-row">
							<view class="active-ai-task-dot"></view>
							<text class="active-ai-task-stage">{{ activeAiTaskStageLabel }}</text>
							<text class="active-ai-task-time">已过 {{ activeAiTaskElapsed }}s</text>
							<text class="active-ai-task-deadline">最迟剩 {{ activeAiTaskRemaining }}s</text>
						</view>
					</view>

					<view class="ai-top-actions">
						<view class="ai-action-btn ai-refresh-btn" @click="fetchAiHistory(true)">
							<text style="font-size: 13px; color: #FFFFFF; font-weight: 900; line-height: 1;">⟳</text>
							<text>刷新</text>
						</view>
						<view class="ai-action-btn ai-demo-history-btn" @click="loadDemoAiHistory">
							<text>演示</text>
						</view>
					</view>
				</view>
			</view>

			<!-- 可视化答题记录流（支持按日期折叠） -->
			<view style="margin-top: 4px;">
				<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 0 4px;">
					<text style="font-size: 15px; font-weight: bold; color: #1c1c1e;">答题历史记录</text>
					<view style="display:flex;flex-direction:row;align-items:center;gap:6px;">
						<text v-if="aiDemoMode" class="ai-demo-data-badge">演示数据</text>
						<text style="font-size: 12px; color: #8e8e93;">共 {{ aiHistoryList.length }} 条解答记录</text>
					</view>
				</view>

				<view v-if="aiHistoryList.length === 0" class="empty-state" style="padding: 40px 0;">
					<view style="display:flex; justify-content:center; margin-bottom:12px;">
						<text style="font-size: 38px; line-height: 1;">🧠</text>
					</view>
					<text class="empty-text">暂无云端 AI 答题记录</text>
					<text class="empty-subtext">当教师在课堂发布题目时，云端 AI 将自动捕捉并在此记录</text>
				</view>

				<!-- 课程大类 -> 课堂主题/章节小类 -> 题目按时间顺序排列 -->
				<view v-for="course in groupedCourseAiHistory" :key="course.courseName" style="margin-bottom: 16px;">
					<!-- 📖 大类折叠头：课程名称 -->
					<view @click="toggleCourseCollapse(course.courseName)"
						style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; background: linear-gradient(135deg, #0A84FF, #0056B3); padding: 12px 16px; border-radius: 16px; margin-bottom: 10px; box-shadow: 0 5px 16px rgba(10,132,255,0.28); cursor: pointer;">
						<view style="display: flex; flex-direction: row; align-items: center; gap: 10px;">
							<view style="width: 32px; height: 32px; border-radius: 10px; background: rgba(10,132,255,0.22); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
								<text style="font-size: 16px;">📖</text>
							</view>
							<view style="display: flex; flex-direction: column;">
								<text style="font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.3px;">{{ course.courseName }}</text>
								<text style="font-size: 10px; color: rgba(255,255,255,0.65); font-weight: 700; margin-top: 1px;">包含 {{ course.lessons.length }} 个课堂主题 · 共 {{ course.totalCount }} 题</text>
							</view>
						</view>

						<view style="display: flex; flex-direction: row; align-items: center; gap: 6px;">
							<text style="font-size: 11px; color: rgba(255,255,255,0.7); font-weight: 600;">{{ collapsedCourses[course.courseName] ? '展开课程' : '折叠课程' }}</text>
							<text style="font-size: 14px; color: #FFFFFF; transition: transform 0.2s;" :style="{ transform: collapsedCourses[course.courseName] ? 'rotate(-90deg)' : 'rotate(0deg)' }">⌄</text>
						</view>
					</view>

					<!-- 大类展开：小类列表 (课堂主题) -->
					<view v-if="!collapsedCourses[course.courseName]">
						<!-- 📌 小类分组：每节课的课堂主题 / 章节 -->
						<view v-for="lesson in course.lessons" :key="lesson.lessonKey" style="margin-bottom: 12px;">
							<!-- 小类折叠头：课堂主题 -->
							<view @click="toggleLessonCollapse(lesson.lessonKey)"
								style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; background: #FFFFFF; padding: 10px 14px; border-radius: 14px; margin-bottom: 8px; border: 1px solid rgba(0,0,0,0.06); box-shadow: 0 2px 8px rgba(0,0,0,0.02); cursor: pointer;">
								<view style="display: flex; flex-direction: row; align-items: center; gap: 8px; min-width: 0; flex: 1;">
									<text style="font-size: 13px; font-weight: 800; color: #0A84FF;">📌</text>
									<text style="font-size: 13.5px; font-weight: 800; color: #1C1C1E; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ lesson.lessonTitle }}</text>
									<text style="font-size: 10px; color: #0A84FF; background: rgba(10,132,255,0.1); padding: 2px 7px; border-radius: 8px; font-weight: 800; flex-shrink: 0;">{{ lesson.items.length }} 题</text>
								</view>

								<view style="display: flex; flex-direction: row; align-items: center; gap: 6px; flex-shrink: 0; margin-left: 6px;">
									<text style="font-size: 11px; color: #8E8E93; font-weight: 600;">{{ lesson.date }}</text>
									<text style="font-size: 13px; color: #8E8E93; transition: transform 0.2s;" :style="{ transform: collapsedLessons[lesson.lessonKey] ? 'rotate(-90deg)' : 'rotate(0deg)' }">⌄</text>
								</view>
							</view>

							<!-- 小类展开：答题记录卡片流 (按时间顺序排列) -->
							<view v-if="!collapsedLessons[lesson.lessonKey]">
								<view v-for="item in lesson.items" :key="item.id" class="card" style="margin-bottom: 10px; padding: 14px 16px;">
									<!-- 顶栏：题型 + ID + 耗时 + 时间 -->
									<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; margin-bottom: 12px;">
										<view style="display: flex; flex-direction: row; align-items: center; gap: 6px;">
											<text style="font-size: 12px; font-weight: bold; color: #0A84FF; background: rgba(10,132,255,0.1); padding: 2px 8px; border-radius: 6px;">{{ item.problemType || '题目' }}</text>
											<text style="font-size: 12px; color: #8e8e93;">ID #{{ item.problemId }}</text>
										</view>
										<view style="display: flex; flex-direction: row; align-items: center; gap: 8px;">
											<text style="font-size: 11px; font-weight: 700; color: #FF9500; background: rgba(255,149,0,0.1); padding: 2px 6px; border-radius: 6px;">⚡ 耗时 {{ item.elapsedSeconds === undefined || item.elapsedSeconds === null ? '--' : item.elapsedSeconds }}s</text>
											<text style="font-size: 12px; color: #8e8e93;">{{ item.time }}</text>
										</view>
									</view>

									<view class="history-ai-model-row">
										<text class="history-ai-model-label">AI 模型</text>
										<text class="ai-model-chip" :class="historyAiModelTone(item)">{{ shortAiModelName(item.aiModel, item.aiProvider) }}</text>
									</view>
									<view class="history-timing-row">
										<text class="history-timing-pill">{{ historyAiPhaseLabel(item) }}</text>
										<text class="history-timing-pill">尝试 {{ item.aiAttemptCount || (item.aiAttempts || []).length || 1 }} 次</text>
										<text class="history-timing-pill">答案 {{ item.answerReadySeconds ?? '--' }}s</text>
										<text class="history-timing-pill strong">提交 {{ item.submittedSeconds ?? item.elapsedSeconds ?? '--' }}s</text>
									</view>

									<!-- 各 AI 模型决策与作答明细 -->
									<view v-if="item.aiAttempts && item.aiAttempts.length > 0" class="history-attempts-box" style="margin-bottom: 10px; padding: 8px 10px; background: #F8F9FB; border-radius: 10px; border: 1px solid rgba(0,0,0,0.04);">
										<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; margin-bottom: 6px;">
											<text style="font-size: 11px; font-weight: 700; color: #8E8E93;">AI 模型解题决策明细</text>
											<text v-if="isModelConsensus(item)" style="font-size: 10px; font-weight: 700; color: #248A3D; background: #E5F9ED; padding: 1px 6px; border-radius: 6px;">✓ 双模型一致</text>
											<text v-else-if="item.aiFallbackUsed" style="font-size: 10px; font-weight: 700; color: #8944AB; background: rgba(191,90,242,0.1); padding: 1px 6px; border-radius: 6px;">⚡ 仲裁/保底采纳</text>
										</view>
										<view style="display: flex; flex-direction: column; gap: 4px;">
											<view v-for="(att, aIdx) in item.aiAttempts" :key="aIdx" style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; font-size: 11.5px;">
												<view style="display: flex; flex-direction: row; align-items: center; gap: 6px;">
													<text class="ai-model-chip-mini" :class="aiModelTone(att.model, att.provider)">{{ shortAiModelName(att.model, att.provider) }}</text>
													<text style="color: #636366; font-size: 10.5px;">{{ att.elapsedSeconds !== undefined && att.elapsedSeconds !== null ? att.elapsedSeconds + 's' : '' }}</text>
												</view>
												<view style="display: flex; flex-direction: row; align-items: center; gap: 4px;">
													<text v-if="att.status === 'success'" style="font-weight: 700; color: #1C1C1E; font-size: 11.5px;">
														选 <text style="color: #0A84FF; font-weight: 800;">[{{ formatAttemptAnswers(att.answers) }}]</text>
													</text>
													<text v-else-if="att.status === 'cutoff'" style="color: #FF9500; font-size: 10.5px; font-weight: 600;">
														25s 超时
													</text>
													<text v-else style="color: #FF3B30; font-size: 10.5px; font-weight: 600;">
														解析失败
													</text>
												</view>
											</view>
										</view>
									</view>

									<!-- 题干描述 -->
									<view style="margin-bottom: 12px;">
										<rich-text style="font-size: 14.5px; color: #1C1C1E; font-weight: 700; line-height: 1.5;" :nodes="item.body || '无题干描述'"></rich-text>
									</view>

									<!-- 选项列表（带 AI 答案与正确答案直观色彩高亮） -->
									<view v-if="item.options && item.options.length > 0" style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px;">
										<view v-for="opt in item.options" :key="opt.key"
											style="padding: 10px 12px; border-radius: 12px; display: flex; flex-direction: row; align-items: center; justify-content: space-between; transition: all 0.2s;"
											:style="getOptionBoxStyle(item, opt.key)">
											<view style="display: flex; flex-direction: row; align-items: center; gap: 10px; flex: 1; min-width: 0;">
												<view style="width: 24px; height: 24px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 800;"
													:style="getOptionKeyStyle(item, opt.key)">
													{{ opt.key }}
												</view>
												<text style="font-size: 13.5px; font-weight: 600; flex: 1; min-width: 0;" :style="getOptionTextStyle(item, opt.key)">
													{{ opt.value }}
												</text>
											</view>

											<!-- 选项高光 Badge 标注 -->
											<view v-if="getOptionBadge(item, opt.key)" style="font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 8px; flex-shrink: 0;"
												:style="getOptionBadgeStyle(item, opt.key)">
												{{ getOptionBadge(item, opt.key) }}
											</view>
										</view>
									</view>

									<!-- 无选项题型 (如填空题 / 简答题) 的显示 -->
									<view v-else style="margin-bottom: 12px; display: flex; flex-direction: column; gap: 8px;">
										<view style="padding: 10px 12px; border-radius: 10px; display: flex; flex-direction: row; justify-content: space-between; align-items: center;"
											:style="answerCorrectness(item) === 'correct' ? 'background: #E5F9ED; border: 1px solid #34C759;' : answerCorrectness(item) === 'incorrect' ? 'background: #FFEBEB; border: 1px solid #FF3B30;' : 'background: #EAF3FF; border: 1px solid #0A84FF;'">
											<view style="display: flex; flex-direction: row; align-items: center; gap: 6px;">
												<text style="font-size: 12px; font-weight: 800;" :style="answerCorrectness(item) === 'correct' ? 'color: #248A3D;' : answerCorrectness(item) === 'incorrect' ? 'color: #D70015;' : 'color: #0A67C7;'">
													AI 提交: {{ Array.isArray(item.aiAnswer) ? item.aiAnswer.join(', ') : item.aiAnswer }}
												</text>
											</view>
											<text style="font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 6px;"
												:style="answerCorrectness(item) === 'correct' ? 'background: #34C759; color: #FFF;' : answerCorrectness(item) === 'incorrect' ? 'background: #FF3B30; color: #FFF;' : 'background: #0A84FF; color: #FFF;'">
												{{ answerCorrectness(item) === 'correct' ? '✓ 答对' : answerCorrectness(item) === 'incorrect' ? '✕ 答错' : '待公布答案' }}
											</text>
										</view>
										<view v-if="hasKnownCorrectAnswer(item) && !isAnswerCorrect(item)" style="padding: 8px 12px; background: #FFF8ED; border: 1px solid #FF9500; border-radius: 10px; font-size: 12px; font-weight: 700; color: #D97706;">
											★ 官方正确答案: {{ Array.isArray(item.correctAnswer) ? item.correctAnswer.join(', ') : item.correctAnswer }}
										</view>
									</view>

									<!-- 底栏：成功账号统计 + 一键展开按钮 -->
									<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; border-top: 1px dashed #eee; padding-top: 8px;">
										<text style="font-size: 12px; color: #666;">课堂 ID: {{ item.lessonId || '默认课堂' }}</text>
										<view style="display: flex; flex-direction: row; align-items: center; gap: 6px;">
											<text style="font-size: 12px; color: #34C759; font-weight: bold;">✓ 成功交卷 {{ item.successCount }} / {{ item.totalAccounts }} 个账号</text>
											<view @click="toggleAccountExpand(item)" style="display: flex; flex-direction: row; align-items: center; gap: 2px; background: rgba(10,132,255,0.1); border: 0.5px solid rgba(10,132,255,0.25); padding: 3px 8px; border-radius: 10px; cursor: pointer;">
												<text style="font-size: 11px; font-weight: 700; color: #0A84FF;">{{ item.showAccounts ? '折叠账号' : '一键展开' }}</text>
												<text style="font-size: 12px; color: #0A84FF; transition: transform 0.2s;" :style="{ transform: item.showAccounts ? 'rotate(180deg)' : 'rotate(0deg)' }">▾</text>
											</view>
										</view>
									</view>

									<!-- 展开显示的成功答题具体账号内嵌列表 -->
									<view v-if="item.showAccounts" style="margin-top: 10px; background: #F9F9FB; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(0,0,0,0.05);">
										<view style="font-size: 11px; font-weight: 700; color: #8E8E93; margin-bottom: 8px; display: flex; justify-content: space-between;">
											<text>成功提交此题的具体终端</text>
											<text style="color: #34C759;">共 {{ (item.successAccounts || []).length }} 个设备</text>
										</view>

										<view v-if="!item.successAccounts || item.successAccounts.length === 0" style="font-size: 12px; color: #8E8E93; text-align: center; padding: 6px 0;">
											暂无具体账号明细
										</view>
										<view v-else style="display: flex; flex-direction: column; gap: 6px;">
											<view v-for="(subAcc, sIdx) in item.successAccounts" :key="sIdx" style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; background: #FFFFFF; padding: 8px 10px; border-radius: 10px; border: 0.5px solid rgba(0,0,0,0.04);">
												<view style="display: flex; flex-direction: row; align-items: center; gap: 8px;">
													<view style="width: 26px; height: 26px; border-radius: 13px; background: linear-gradient(135deg, #0A84FF, #0056B3); color: #FFF; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center;">
														{{ (subAcc.remark || subAcc.name || '?').charAt(0) }}
													</view>
													<view style="display: flex; flex-direction: column;">
														<text style="font-size: 12px; font-weight: 700; color: #1C1C1E;">{{ subAcc.remark || subAcc.name || '托管账号' }}</text>
														<text style="font-size: 10px; color: #8E8E93;">手机号: {{ subAcc.phone || '已安全脱敏' }}</text>
													</view>
												</view>
												<view style="display: flex; flex-direction: row; align-items: center; gap: 3px; background: #E5F9ED; padding: 2px 6px; border-radius: 6px;">
													<text style="font-size: 10px; font-weight: 700; color: #34C759;">✓ 已自动交卷</text>
												</view>
											</view>
										</view>
									</view>
								</view>
							</view>
						</view>
					</view>
				</view>
			</view>
			<view style="height: 80px;"></view>
		</view>

		<!-- 云端自动签到会话进度弹窗 -->
		<view class="blur-mask" :class="{ 'mask-active': showProgressDialog }">
			<view class="shell-modal" v-if="showProgressDialog">
				<view class="shell-header">
					<view class="mac-dots">
						<view class="dot red"></view>
						<view class="dot yellow"></view>
						<view class="dot green"></view>
					</view>
					<text class="shell-title">云端自动签到并发引擎</text>
				</view>
				<view class="shell-body">
					<text class="shell-status">> Status: {{ progressMsg }}</text>
					<scroll-view scroll-y class="shell-logs" :scroll-top="scrollTop">
						<view class="log-line" v-for="(log, idx) in runLogs" :key="idx">
							<text class="log-time">[{{ log.time }}]</text>
							<text :class="log.success ? 'log-good' : 'log-bad'">{{ log.text }}</text>
						</view>
					</scroll-view>
				</view>
				<view class="shell-footer" v-if="isProgressFinished">
					<button class="shell-btn" @click="showProgressDialog = false">关闭会话窗口</button>
				</view>
			</view>
		</view>

		<!-- 高阶 iOS 典雅【作者寄语】弹窗 -->
		<view class="blur-mask" :class="{ 'mask-active': showAuthorDialog }">
			<view class="sheet-modal high-end-author-modal" v-if="showAuthorDialog" style="background: #F9F9FB; border-radius: 24px; padding: 16px;">
				<!-- 头部标题栏 -->
				<view class="sheet-header" style="padding-bottom: 12px; border-bottom: 1px solid rgba(0,0,0,0.06); display: flex; flex-direction: row; justify-content: space-between; align-items: center;">
					<view style="display: flex; flex-direction: row; align-items: center; gap: 8px;">
						<view style="width: 32px; height: 32px; border-radius: 10px; background: linear-gradient(135deg, #0A84FF, #0056B3); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(10,132,255,0.3);">
							<text style="font-size: 16px; line-height: 1;">✨</text>
						</view>
						<view style="display: flex; flex-direction: column;">
							<text class="sheet-title" style="font-size: 16px; font-weight: 800; color: #1C1C1E; line-height: 1.2;">作者寄语</text>
							<text style="font-size: 9px; color: #8E8E93; font-weight: 700; letter-spacing: 0.5px;">DEVELOPER NOTE · ARCHITECT MESSAGE</text>
						</view>
					</view>
					<text class="sheet-close" @click="showAuthorDialog = false" style="font-size: 12px; font-weight: 700; color: #0A84FF; background: rgba(10,132,255,0.1); padding: 5px 12px; border-radius: 12px;">合上</text>
				</view>

				<!-- 寄语正文双层 Doppelrand 双嵌套卡片 -->
				<view class="sheet-body author-body" style="padding: 16px 4px 10px 4px;">
					<scroll-view scroll-y class="author-scroll-view" :show-scrollbar="false">
						<!-- 第一段寄语卡片 -->
						<view class="author-quote-card" style="margin-bottom: 10px; padding: 14px 16px; background: #FFFFFF; border-radius: 16px; border: 1px solid rgba(0,0,0,0.06); box-shadow: 0 4px 16px rgba(0,0,0,0.03); position: relative; overflow: hidden;">
							<view style="position: absolute; top: -8px; right: 10px; font-size: 50px; color: rgba(10,132,255,0.08); font-family: Georgia, serif; font-weight: bold; line-height: 1;">“</view>
							<text style="font-size: 13.5px; color: #2C3E50; line-height: 1.8; letter-spacing: 0.4px; font-weight: 500; text-align: justify; display: block; position: relative; z-index: 1;">
								世间最大的遗憾，往往不是洞悉世事后的那份疏离，而是习惯了规则的缠绕，最终在无形的茧房里安之若素。
							</text>
						</view>

						<!-- 第二段寄语卡片 -->
						<view class="author-quote-card" style="margin-bottom: 14px; padding: 14px 16px; background: rgba(10,132,255,0.04); border-radius: 16px; border: 1px solid rgba(10,132,255,0.15); box-shadow: 0 4px 16px rgba(10,132,255,0.04); position: relative; overflow: hidden;">
							<view style="position: absolute; top: -8px; right: 10px; font-size: 50px; color: rgba(10,132,255,0.1); font-family: Georgia, serif; font-weight: bold; line-height: 1;">”</view>
							<text style="font-size: 13.5px; color: #0A84FF; line-height: 1.8; letter-spacing: 0.4px; font-weight: 600; text-align: justify; display: block; position: relative; z-index: 1;">
								我所做的，只是在这按部就班的轨道旁，为不甘平庸的你递上一把挣脱繁文缛节的钥匙。
							</text>
						</view>

						<!-- 作者 Profile 名片卡 -->
						<view class="author-profile-box" style="display: flex; flex-direction: row; align-items: center; justify-content: space-between; background: #FFFFFF; padding: 12px 14px; border-radius: 16px; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 6px 20px rgba(0,0,0,0.04);">
							<view style="display: flex; flex-direction: row; align-items: center; gap: 10px;">
								<image class="author-avatar" src="https://cdn.phototourl.com/uploads/2026-03-06-60069b3d-c8ee-4d41-9955-4ab1669067d7.jpg" mode="aspectFill" style="width: 42px; height: 42px; border-radius: 21px; border: 2px solid #FFFFFF; box-shadow: 0 4px 10px rgba(0,0,0,0.1);"></image>
								<view style="display: flex; flex-direction: column;">
									<view style="display: flex; flex-direction: row; align-items: center; gap: 4px;">
										<text style="font-size: 13.5px; font-weight: 800; color: #1C1C1E;">相濡以沫</text>
										<text style="font-size: 10px; color: #0A84FF; background: rgba(10,132,255,0.12); padding: 1px 6px; border-radius: 6px; font-weight: 700;">核心开发者</text>
									</view>
									<text style="font-size: 10.5px; color: #8E8E93; margin-top: 2px;">雨课堂签到助手 PRO 架构师</text>
								</view>
							</view>

							<view class="copy-email-pill" @click="copyContact" style="display: flex; flex-direction: row; align-items: center; gap: 4px; background: #F2F2F7; padding: 6px 10px; border-radius: 12px; border: 1px solid rgba(0,0,0,0.05);">
								<text style="font-size: 12px; line-height: 1;">📋</text>
								<text style="font-size: 11px; font-weight: 700; color: #0A84FF;">复制邮箱</text>
							</view>
						</view>
						<view style="height: 10px;"></view>
					</scroll-view>
				</view>
			</view>
		</view>

		<!-- 课件原图全屏预览蒙层 -->
		<view class="slide-fullscreen-mask" v-if="slidePreviewVisible" @click.stop="closeSlidePreview">
			<image class="slide-fullscreen-img" :src="previewSlideUrl || currentQuestion?.cover" mode="aspectFit"></image>
			<view class="slide-fullscreen-close" @click.stop="closeSlidePreview">
				<text>点击任意位置关闭大图</text>
			</view>
		</view>

		<!-- 精简云端密钥设置：验证成功后再替换本地密钥 -->
		<view class="blur-mask" :class="{ 'mask-active': showKeyConfigModal }">
			<view class="sheet-modal compact-settings-sheet" v-if="showKeyConfigModal">
				<view class="compact-sheet-header">
					<view>
						<text class="compact-sheet-title">云端密钥</text>
						<text class="compact-sheet-sub">{{ userApiKey ? `当前：${currentGroupRemark || '已连接'}` : '输入管理员分配的密钥' }}</text>
					</view>
					<text @click="closeKeyConfigModal" class="compact-close">✕</text>
				</view>
				<input class="compact-key-input" v-model="keyInputVal" maxlength="128" placeholder="输入新密钥，内容不限" />
				<text v-if="keyValidationMsg" class="key-validation-msg">{{ keyValidationMsg }}</text>
				<view class="compact-action-row">
					<button v-if="userApiKey" @click="clearKeyConfig" class="compact-secondary-btn">清除</button>
					<button @click="saveKeyConfig" :disabled="savingKeyConfig" class="compact-primary-btn">
						{{ savingKeyConfig ? '验证中…' : (userApiKey ? '验证并更新' : '验证并保存') }}
					</button>
				</view>
				<view class="admin-entry-row" @click="openAdminFromKey">
					<text>管理员创建或修改密钥</text>
					<text>›</text>
				</view>
			</view>
		</view>

		<!-- 👑 管理员控制台弹窗 (仅管理员可创建生成新密钥) -->
		<view class="blur-mask" :class="{ 'mask-active': showAdminModal }">
			<view class="sheet-modal" v-if="showAdminModal" style="background: #F9F9FB; border-radius: 24px; padding: 20px; width: 88%; max-width: 360px; max-height: 80vh; overflow-y: auto; box-shadow: 0 20px 50px rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.8); margin: auto;">
				<view style="display: flex; flex-direction: row; align-items: center; justify-content: space-between; margin-bottom: 14px; border-bottom: 1px solid rgba(0,0,0,0.06); padding-bottom: 12px;">
					<view style="display: flex; flex-direction: row; align-items: center; gap: 10px;">
						<view style="width: 38px; height: 38px; border-radius: 12px; background: linear-gradient(135deg, #AF52DE, #5856D6); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(175,82,222,0.3);">
							<text style="font-size: 20px;">👑</text>
						</view>
						<view style="display: flex; flex-direction: column;">
							<text style="font-size: 16px; font-weight: 800; color: #1C1C1E; line-height: 1.2;">密钥管理</text>
							<text style="font-size: 9.5px; color: #8E8E93; font-weight: 700; letter-spacing: 0.5px;">ADMIN KEY MANAGER</text>
						</view>
					</view>
					<view style="display: flex; flex-direction: row; align-items: center; gap: 8px;">
						<text v-if="isAdminAuthenticated" @click="adminLogout" style="font-size: 10.5px; color: #FF3B30; background: rgba(255,59,48,0.1); padding: 2px 6px; border-radius: 6px; font-weight: bold; cursor: pointer;">退出登录</text>
						<text @click="showAdminModal = false" style="font-size: 16px; color: #8E8E93; font-weight: bold; cursor: pointer; padding: 4px;">✕</text>
					</view>
				</view>

				<!-- 阶段一：管理员身份口令验证 -->
				<view v-if="!isAdminAuthenticated" style="padding: 10px 0;">
					<text style="font-size: 12.5px; color: #666; line-height: 1.5; margin-bottom: 14px; display: block;">
						输入管理员密码后即可创建、修改或废除用户密钥。
					</text>

					<view style="margin-bottom: 14px;">
						<input class="ios-input" type="password" v-model="adminPassInput" placeholder="输入管理员特权口令" style="background: #FFFFFF; border: 1.5px solid #E5E5EA; border-radius: 12px; padding: 10px 12px; font-size: 14px; font-weight: 700; color: #1C1C1E; width: 100%; box-sizing: border-box;" />
					</view>

					<button @click="verifyAdminPassword" style="width: 100%; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #AF52DE, #5856D6); color: #FFFFFF; font-size: 13.5px; font-weight: 800; border: none; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(175,82,222,0.3);">
						验证管理员身份
					</button>
				</view>

				<!-- 阶段二：管理员专属特权面板（自主创建密钥） -->
				<view v-else style="display: flex; flex-direction: column; gap: 14px;">
					<!-- 新建和修改共用一个紧凑表单 -->
					<view style="background: #FFFFFF; padding: 14px; border-radius: 16px; border: 1px solid rgba(0,0,0,0.06);">
						<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; margin-bottom: 8px;">
							<text style="font-size: 13px; font-weight: 800; color: #1C1C1E;">{{ (editingOriginalKey || editingKeyId) ? '修改密钥' : '创建密钥' }}</text>
							<view style="display: flex; flex-direction: row; gap: 10px;">
								<text v-if="editingOriginalKey || editingKeyId" @click="cancelEditAdminKey" style="font-size: 11px; color: #8E8E93; font-weight: 700;">取消修改</text>
								<text @click="generateRandomCustomKey" style="font-size: 11px; color: #0A84FF; font-weight: 700; cursor: pointer;">随机</text>
							</view>
						</view>

						<input class="ios-input" v-model="customKeyInput" maxlength="128" placeholder="任意非空密钥，最长 128 字符" style="background: #F9F9FB; border: 1px solid #E5E5EA; border-radius: 10px; padding: 8px 10px; font-size: 12.5px; font-weight: 700; color: #1C1C1E; margin-bottom: 8px; width: 100%; box-sizing: border-box;" />
						<input class="ios-input" v-model="newKeyRemarkInput" placeholder="账号组备注，例如：软件1班" style="background: #F9F9FB; border: 1px solid #E5E5EA; border-radius: 10px; padding: 8px 10px; font-size: 12.5px; color: #1C1C1E; margin-bottom: 10px; width: 100%; box-sizing: border-box;" />

						<button @click="adminCreateNewKey" style="width: 100%; height: 36px; border-radius: 10px; background: linear-gradient(135deg, #34C759, #248A3D); color: #FFFFFF; font-size: 12.5px; font-weight: 800; border: none; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(52,199,89,0.3);">
							{{ (editingOriginalKey || editingKeyId) ? '保存修改' : '创建并保存' }}
						</button>

						<!-- 生成成功显示 -->
						<view v-if="newlyCreatedKey" style="margin-top: 12px; padding: 10px; background: #E5F9ED; border: 1px dashed #34C759; border-radius: 10px;">
							<text style="font-size: 10px; color: #248A3D; font-weight: bold; display: block; margin-bottom: 4px;">专属密钥已添加就绪:</text>
							<text style="font-size: 13px; font-weight: 900; color: #1C1C1E; font-family: monospace; display: block; margin-bottom: 6px;">{{ newlyCreatedKey }}</text>
							<button @click="copyCreatedKey(newlyCreatedKey)" style="height: 26px; border-radius: 6px; background: #34C759; color: #FFF; font-size: 11px; font-weight: bold; border: none;">复制颁发给用户</button>
						</view>
					</view>

					<!-- 块 2：已颁发密钥池 -->
					<view style="background: #FFFFFF; padding: 14px; border-radius: 16px; border: 1px solid rgba(0,0,0,0.06);">
						<view style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; margin-bottom: 10px;">
							<text style="font-size: 13px; font-weight: 800; color: #1C1C1E;">📋 已生成密钥库 ({{ adminCreatedKeysList.length }})</text>
						</view>

						<view v-if="adminCreatedKeysList.length === 0" style="font-size: 11.5px; color: #8E8E93; text-align: center; padding: 10px 0;">
							暂未创建任何用户密钥
						</view>
						<view v-else style="display: flex; flex-direction: column; gap: 8px;">
							<view v-for="(kItem, kIdx) in adminCreatedKeysList" :key="kIdx" style="background: #F9F9FB; padding: 8px 10px; border-radius: 10px; display: flex; flex-direction: row; justify-content: space-between; align-items: center; border: 0.5px solid rgba(0,0,0,0.04);">
								<view style="display: flex; flex-direction: column; min-width: 0; flex: 1;">
									<text style="font-size: 12px; font-weight: 800; color: #1C1C1E;">{{ kItem.remark }}</text>
									<text style="font-size: 11px; font-weight: bold; color: #AF52DE; font-family: monospace;">{{ kItem.key || kItem.keyHint || '***' }}</text>
								</view>
								<view style="display: flex; flex-direction: row; gap: 6px; flex-shrink: 0;">
									<text v-if="kItem.key" @click="copyCreatedKey(kItem.key)" style="font-size: 10px; color: #0A84FF; background: rgba(10,132,255,0.1); padding: 3px 6px; border-radius: 6px; font-weight: bold; cursor: pointer;">复制</text>
									<text @click="editAdminKey(kIdx)" style="font-size: 10px; color: #FF9500; background: rgba(255,149,0,0.1); padding: 3px 6px; border-radius: 6px; font-weight: bold; cursor: pointer;">修改</text>
									<text @click="deleteAdminKey(kIdx)" style="font-size: 10px; color: #FF3B30; background: rgba(255,59,48,0.1); padding: 3px 6px; border-radius: 6px; font-weight: bold; cursor: pointer;">废除</text>
								</view>
							</view>
						</view>
					</view>
				</view>
			</view>
		</view>

		<!-- iOS 风格常驻全显示长条胶囊底栏 (Custom Tabbar) -->
		<view class="custom-tabbar">
			<view class="tabbar-item" :class="{ active: currentTab === 'home' }" @click="currentTab = 'home'">
				<view class="tabbar-pill pill-home">
					<text style="font-size: 15px; line-height: 1;">👥</text>
					<text class="tabbar-pill-text">账号管理</text>
				</view>
			</view>

			<view class="tabbar-item" :class="{ active: currentTab === 'answer' }" @click="openAnswerTab">
				<view class="tabbar-pill pill-answer" :class="{ 'pulse-orange': isNewProblemDetected }">
					<text style="font-size: 15px; line-height: 1;">✏️</text>
					<text class="tabbar-pill-text">课堂答题</text>
				</view>
				<view v-if="isNewProblemDetected" class="tabbar-badge"></view>
			</view>

			<view class="tabbar-item" :class="{ active: currentTab === 'ai' }" @click="currentTab = 'ai'; fetchAiHistory()">
				<view class="tabbar-pill pill-ai">
					<text style="font-size: 15px; line-height: 1;">🧠</text>
					<text class="tabbar-pill-text">AI 答题</text>
				</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { onBackPress, onShow } from '@dcloudio/uni-app';
import { createAnswerEngine } from './answer-engine.js';
import { createLessonBatchContext, lockLessonForBatch } from './answer-engine-utils.js';
import { applyValidityResult, findCloudAccount, inspectUserInfoResponse, normalizeExpiredFlag } from './account-validity.js';
import { getSyncServerUrl, setSyncServerUrl, refreshServerConfigFromRemote, getServerConfigMeta } from './server-config.js';

const BASE_URL = 'https://www.yuketang.cn';
const WS_BASE_URL = 'https://changjiang.yuketang.cn';
// GitCode 远程动态配置中心：优先从 GitCode 拉取，离线/失败时自动回退至本地缓存
const SYNC_SERVER_URL = {
	toString: () => getSyncServerUrl(),
	valueOf: () => getSyncServerUrl()
};
const BATCH_CONCURRENCY = 16;
const API_TIMEOUT = 12000;

const safeJsonParse = (raw, fallback) => {
	try {
		const parsed = JSON.parse(raw);
		return parsed ?? fallback;
	} catch (_) {
		return fallback;
	}
};

const sanitizeRichHtml = value => String(value || '')
	.replace(/<(script|iframe|object|embed|style)\b[\s\S]*?<\/\1>/gi, '')
	.replace(/\son\w+\s*=\s*(['"])[\s\S]*?\1/gi, '')
	.replace(/\s(href|src)\s*=\s*(['"])\s*javascript:[\s\S]*?\2/gi, '');

const normalizeHistoryRecords = records => (Array.isArray(records) ? records : []).map(record => ({
	...record,
	body: sanitizeRichHtml(record?.body),
	options: Array.isArray(record?.options)
		? record.options.map(option => typeof option === 'object' && option !== null
			? { ...option, value: sanitizeRichHtml(option.value || option.content || '') }
			: option)
		: []
}));

const accounts = ref([]);
const currentTab = ref('home');
const answerReceiverExpanded = ref(false);
const accountValidityChecking = ref(false);
let lastValidityCheckAt = 0;

const aiHistoryList = ref([]);
const aiDemoMode = ref(false);
const aiActiveTasks = ref([]);
const aiHealthState = ref(null);
const aiClockMs = ref(Date.now());
const aiServerOffsetMs = ref(0);
const aiStatusState = ref({
	ready: false,
	provider: '',
	model: '',
	msg: '尚未检测 AI 状态'
});
const formatAiProvider = provider => {
	const value = String(provider || '').trim().toLowerCase();
	const labels = {
		gemini: 'Google Gemini',
		openai: 'OpenAI',
		nvidia: 'NVIDIA NIM',
		nim: 'NVIDIA NIM',
		siliconflow: 'SiliconFlow',
		silicon_flow: 'SiliconFlow',
		sf: 'SiliconFlow',
		cloudflare: 'Cloudflare AI',
		cf: 'Cloudflare AI',
		compatible: '兼容渠道'
	};
	return labels[value] || String(provider || '').trim() || 'AI';
};
const shortAiModelName = (model, provider = '') => {
	const value = `${model || ''} ${provider || ''}`.toLowerCase();
	if (value.includes('gemma') || value.includes('nvidia')) return 'Gemma-4';
	if (value.includes('3.8') || value.includes('qwen3.8') || value.includes('cloudflare')) return 'Qwen3.8';
	if (value.includes('3.5') || value.includes('qwen3.5') || value.includes('siliconflow')) return 'Qwen3.5';
	if (value.includes('qwen')) return 'Qwen';
	const fallback = String(model || '').split('/').pop().trim();
	return fallback ? fallback.slice(0, 16) : '未知模型';
};
const aiModelTone = (model, provider = '') => {
	const value = `${model || ''} ${provider || ''}`.toLowerCase();
	if (value.includes('3.8') || value.includes('qwen3.8') || value.includes('cloudflare')) return 'purple';
	if (value.includes('qwen') || value.includes('siliconflow')) return 'purple';
	return 'blue';
};
const activeAiModelChips = computed(() => {
	const routes = Array.isArray(aiStatusState.value?.routes)
		? aiStatusState.value.routes.filter(route => route?.configured !== false)
		: [];
	const source = routes.length > 0
		? routes
		: [
			{ provider: 'nvidia', model: 'google/gemma-4-31b-it' },
			{ provider: 'cloudflare', model: '@cf/qwen/qwen3.8-27b' },
			{ provider: 'siliconflow', model: 'Qwen/Qwen3.5-27B' }
		];
	const unique = [];
	source.forEach(route => {
		const name = shortAiModelName(route?.model, route?.provider);
		if (!unique.some(item => item.name === name)) {
			unique.push({
				name,
				tone: aiModelTone(route?.model, route?.provider)
			});
		}
	});
	return unique.slice(0, 3);
});
const aiHealthProbes = computed(() => {
	const rawProbes = aiHealthState.value?.probes;
	if (Array.isArray(rawProbes) && rawProbes.length > 0) {
		return rawProbes.map(p => ({
			displayName: p.displayName || shortAiModelName(p.model, p.provider),
			success: p.success,
			checkedAtText: p.checkedAtText || '',
			elapsedSeconds: p.elapsedSeconds || 0,
			tone: p.tone || aiModelTone(p.model, p.provider)
		}));
	}
	if (aiHealthState.value) {
		const p = aiHealthState.value.latest || aiHealthState.value;
		if (p && (p.displayName || p.provider || p.model)) {
			return [{
				displayName: p.displayName || shortAiModelName(p.model, p.provider) || 'Gemma-4',
				success: p.success,
				checkedAtText: p.checkedAtText || '',
				elapsedSeconds: p.elapsedSeconds || 0,
				tone: p.tone || aiModelTone(p.model, p.provider)
			}];
		}
	}
	return [
		{ displayName: 'Gemma-4', success: null, checkedAtText: '', elapsedSeconds: 0, tone: 'blue' },
		{ displayName: 'Qwen3.8', success: null, checkedAtText: '', elapsedSeconds: 0, tone: 'purple' }
	];
});
const activeAiTask = computed(() => aiActiveTasks.value[0] || null);
const activeAiNowMs = computed(() => aiClockMs.value + aiServerOffsetMs.value);
const activeAiTaskElapsed = computed(() => {
	if (!activeAiTask.value?.problemStartedAt) return 0;
	return Math.max(0, Math.floor((activeAiNowMs.value - Number(activeAiTask.value.problemStartedAt)) / 1000));
});
const activeAiTaskRemaining = computed(() => {
	if (!activeAiTask.value?.hardDeadlineAt) return 0;
	return Math.max(0, Math.ceil((Number(activeAiTask.value.hardDeadlineAt) - activeAiNowMs.value) / 1000));
});
const activeAiTaskStageLabel = computed(() => {
	const task = activeAiTask.value || {};
	if (task.stage === 'submitting') return '正在批量提交';
	if (task.stage === 'waiting_submit') {
		const wait = Math.max(0, Math.ceil((Number(task.submitNotBeforeAt || 0) - activeAiNowMs.value) / 1000));
		return wait > 0 ? `答案已就绪，${wait}s 后提交` : '答案已就绪，准备提交';
	}
	if (task.stage === 'ai_analyzing') {
		return activeAiNowMs.value < Number(task.thinkingCutoffAt || 0)
			? '双模型 Thinking 竞速'
			: 'Thinking 超时，Fast 交替重试';
	}
	return '正在解析题目';
});
const historyAiModelTone = item => aiModelTone(item?.aiModel, item?.aiProvider);
const historyAiPhaseLabel = item => {
	const attempts = Array.isArray(item?.aiAttempts) ? item.aiAttempts : [];
	const successful = attempts.find(attempt => attempt?.status === 'success');
	if (successful?.phase === 'thinking') return 'Thinking 命中';
	if (successful?.phase === 'fast') return item?.aiFallbackUsed ? 'Fast 切换命中' : 'Fast 命中';
	return item?.aiFallbackUsed ? '已切换模型' : '历史策略';
};
const buildDemoAiHistory = () => {
	const now = new Date();
	const date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
	const accounts = Array.from({ length: 15 }, (_, index) => {
		const number = String(index + 1).padStart(2, '0');
		return {
			remark: `演示账号${number}`,
			phone: `138****${String(index + 1).padStart(4, '0')}`
		};
	});
	const attempt = (provider, model, phase, seconds, status = 'success', answers = ['B']) => ({
		attempt: 1,
		provider,
		model,
		phase,
		thinking: phase === 'thinking',
		elapsedSeconds: seconds,
		status,
		answers: status === 'success' ? answers : []
	});
	return [
		{
			id: 'demo_math_001',
			timestamp: now.getTime() - 1000 * 60 * 35,
			date,
			time: '10:18:26',
			courseName: '高等数学',
			lessonTitle: '导数与微分',
			lessonId: 'DEMO-MATH-01',
			problemId: '80126',
			problemType: '单选题',
			body: '函数 <b>f(x)=x²+3x</b> 在 x=2 处的导数是？',
			options: [
				{ key: 'A', value: '5' },
				{ key: 'B', value: '7' },
				{ key: 'C', value: '8' },
				{ key: 'D', value: '10' }
			],
			aiAnswer: ['B'],
			correctAnswer: ['B'],
			aiProvider: 'nvidia',
			aiModel: 'google/gemma-4-31b-it',
			aiAttempts: [
				{ ...attempt('nvidia', 'google/gemma-4-31b-it', 'thinking', 4.8, 'success', ['B']), attempt: 1 },
				{ ...attempt('cloudflare', '@cf/qwen/qwen3.8-27b', 'thinking', 5.3, 'success', ['B']), attempt: 2 }
			],
			aiAttemptCount: 2,
			aiFallbackUsed: false,
			answerReadySeconds: 5.3,
			submittedSeconds: 35.1,
			elapsedSeconds: 35.1,
			totalAccounts: 15,
			successCount: 15,
			successAccounts: accounts,
			status: 'success'
		},
		{
			id: 'demo_code_002',
			timestamp: now.getTime() - 1000 * 60 * 25,
			date,
			time: '10:23:41',
			courseName: 'C语言程序设计',
			lessonTitle: '循环结构与累加',
			lessonId: 'DEMO-CODE-02',
			problemId: '80131',
			problemType: '单选题',
			body: '程序执行 <b>for(i=1;i&lt;=4;i++) s += i*i;</b>，最终输出什么？',
			options: [
				{ key: 'A', value: '20' },
				{ key: 'B', value: '30' },
				{ key: 'C', value: '32' },
				{ key: 'D', value: '54' }
			],
			aiAnswer: ['B'],
			correctAnswer: ['B'],
			aiProvider: 'siliconflow',
			aiModel: 'Qwen/Qwen3.5-27B',
			aiAttempts: [
				{ ...attempt('nvidia', 'google/gemma-4-31b-it', 'thinking', 25.0, 'cutoff', []), attempt: 1 },
				{ ...attempt('cloudflare', '@cf/qwen/qwen3.8-27b', 'thinking', 25.0, 'cutoff', []), attempt: 2 },
				{ ...attempt('siliconflow', 'Qwen/Qwen3.5-27B', 'fast', 2.1, 'success', ['B']), attempt: 3 }
			],
			aiAttemptCount: 3,
			aiFallbackUsed: true,
			answerReadySeconds: 27.1,
			submittedSeconds: 40.2,
			elapsedSeconds: 40.2,
			totalAccounts: 15,
			successCount: 15,
			successAccounts: accounts,
			status: 'success'
		},
		{
			id: 'demo_english_003',
			timestamp: now.getTime() - 1000 * 60 * 15,
			date,
			time: '14:06:12',
			courseName: '大学英语',
			lessonTitle: '虚拟语气',
			lessonId: 'DEMO-ENG-03',
			problemId: '80208',
			problemType: '单选题',
			body: 'If I ____ enough time, I would travel around the world.',
			options: [
				{ key: 'A', value: 'have' },
				{ key: 'B', value: 'had' },
				{ key: 'C', value: 'will have' },
				{ key: 'D', value: 'am having' }
			],
			aiAnswer: ['B'],
			correctAnswer: ['B'],
			aiProvider: 'cloudflare',
			aiModel: '@cf/qwen/qwen3.8-27b',
			aiAttempts: [
				{ ...attempt('nvidia', 'google/gemma-4-31b-it', 'thinking', 4.2, 'success', ['A']), attempt: 1 },
				{ ...attempt('cloudflare', '@cf/qwen/qwen3.8-27b', 'thinking', 4.9, 'success', ['B']), attempt: 2 }
			],
			aiAttemptCount: 2,
			aiFallbackUsed: true,
			answerReadySeconds: 4.9,
			submittedSeconds: 35.0,
			elapsedSeconds: 35.0,
			totalAccounts: 15,
			successCount: 14,
			successAccounts: accounts.slice(0, 14),
			status: 'success'
		},
		{
			id: 'demo_physics_004',
			timestamp: now.getTime() - 1000 * 60 * 5,
			date,
			time: '15:32:54',
			courseName: '大学物理',
			lessonTitle: '牛顿运动定律',
			lessonId: 'DEMO-PHY-04',
			problemId: '80315',
			problemType: '多选题',
			body: '关于作用力和反作用力，下列说法正确的是？',
			options: [
				{ key: 'A', value: '大小相等' },
				{ key: 'B', value: '方向相反' },
				{ key: 'C', value: '作用在同一物体上' },
				{ key: 'D', value: '同时产生、同时消失' }
			],
			aiAnswer: ['A', 'B', 'D'],
			correctAnswer: ['A', 'B', 'D'],
			aiProvider: 'nvidia',
			aiModel: 'google/gemma-4-31b-it',
			aiAttempts: [
				{ ...attempt('nvidia', 'google/gemma-4-31b-it', 'thinking', 3.9, 'success', ['A', 'B', 'D']), attempt: 1 },
				{ ...attempt('cloudflare', '@cf/qwen/qwen3.8-27b', 'thinking', 4.5, 'success', ['A', 'B', 'D']), attempt: 2 }
			],
			aiAttemptCount: 2,
			aiFallbackUsed: false,
			answerReadySeconds: 4.5,
			submittedSeconds: 35.2,
			elapsedSeconds: 35.2,
			totalAccounts: 15,
			successCount: 15,
			successAccounts: accounts,
			status: 'success'
		},
		{
			id: 'demo_history_005',
			timestamp: now.getTime() - 1000 * 30,
			date,
			time: '16:48:09',
			courseName: '中国近现代史纲要',
			lessonTitle: '新文化运动',
			lessonId: 'DEMO-HIS-05',
			problemId: '80402',
			problemType: '单选题',
			body: '新文化运动兴起的标志是下列哪一事件？',
			options: [
				{ key: 'A', value: '《新青年》创刊' },
				{ key: 'B', value: '五四运动爆发' },
				{ key: 'C', value: '中国共产党成立' },
				{ key: 'D', value: '辛亥革命爆发' }
			],
			aiAnswer: ['A'],
			correctAnswer: ['A'],
			aiProvider: 'cloudflare',
			aiModel: '@cf/qwen/qwen3.8-27b',
			aiAttempts: [
				{ ...attempt('nvidia', 'google/gemma-4-31b-it', 'thinking', 3.1, 'success', ['A']), attempt: 1 },
				{ ...attempt('cloudflare', '@cf/qwen/qwen3.8-27b', 'thinking', 3.4, 'success', ['A']), attempt: 2 }
			],
			aiAttemptCount: 2,
			aiFallbackUsed: false,
			answerReadySeconds: 3.4,
			submittedSeconds: 35.0,
			elapsedSeconds: 35.0,
			totalAccounts: 15,
			successCount: 15,
			successAccounts: accounts,
			status: 'success'
		}
	];
};
const loadDemoAiHistory = () => {
	aiDemoMode.value = true;
	aiActiveTasks.value = [];
	aiHealthState.value = {
		probes: [
			{
				success: true,
				status: 'success',
				provider: 'nvidia',
				model: 'google/gemma-4-31b-it',
				displayName: 'Gemma-4',
				tone: 'blue',
				checkedAtText: '刚刚',
				elapsedSeconds: 0.8
			},
			{
				success: true,
				status: 'success',
				provider: 'cloudflare',
				model: '@cf/qwen/qwen3.8-27b',
				displayName: 'Qwen3.8',
				tone: 'purple',
				checkedAtText: '刚刚',
				elapsedSeconds: 1.2
			}
		],
		latest: {
			success: true,
			status: 'success',
			provider: 'nvidia',
			model: 'google/gemma-4-31b-it',
			displayName: 'Gemma-4',
			checkedAtText: '刚刚',
			elapsedSeconds: 0.8
		}
	};
	aiHistoryList.value = normalizeHistoryRecords(buildDemoAiHistory());
	collapsedCourses.value = {};
	collapsedLessons.value = {};
	aiStatusState.value = {
		...aiStatusState.value,
		ready: true,
		msg: '三模型演示模式',
		routes: [
			{ provider: 'nvidia', model: 'google/gemma-4-31b-it', configured: true },
			{ provider: 'cloudflare', model: '@cf/qwen/qwen3.8-27b', configured: true },
			{ provider: 'siliconflow', model: 'Qwen/Qwen3.5-27B', configured: true }
		]
	};
	uni.showToast({ title: '已载入 5 条演示记录', icon: 'none' });
};
const collapsedDates = ref({});

const toggleDateCollapse = (dateStr) => {
	collapsedDates.value[dateStr] = !collapsedDates.value[dateStr];
};

const toggleAccountExpand = (item) => {
	item.showAccounts = !item.showAccounts;
};

const checkInAnswer = (ansList, key) => {
	if (!ansList) return false;
	if (Array.isArray(ansList)) return ansList.includes(key);
	return String(ansList) === String(key);
};

const hasKnownCorrectAnswer = item => (
	Array.isArray(item?.correctAnswer)
		? item.correctAnswer.length > 0
		: String(item?.correctAnswer || '').trim().length > 0
);

const answerCorrectness = item => {
	if (!hasKnownCorrectAnswer(item)) return 'unknown';
	const aiStr = Array.isArray(item.aiAnswer) ? item.aiAnswer.slice().sort().join(',') : String(item.aiAnswer);
	const corStr = Array.isArray(item.correctAnswer) ? item.correctAnswer.slice().sort().join(',') : String(item.correctAnswer);
	return aiStr === corStr ? 'correct' : 'incorrect';
};
const isAnswerCorrect = item => answerCorrectness(item) === 'correct';

const getOptionBoxStyle = (item, key) => {
	const isAi = checkInAnswer(item.aiAnswer, key);
	const isCor = checkInAnswer(item.correctAnswer, key);
	if (!hasKnownCorrectAnswer(item) && isAi) return 'background: #EAF3FF; border: 1.5px solid #0A84FF;';
	if (isAi && isCor) return 'background: #E5F9ED; border: 1.5px solid #34C759;';
	if (isAi && !isCor) return 'background: #FFEBEB; border: 1.5px solid #FF3B30;';
	if (!isAi && isCor) return 'background: #FFF8ED; border: 1.5px solid #FF9500;';
	return 'background: #F9F9FB; border: 1px solid #E5E5EA;';
};

const getOptionKeyStyle = (item, key) => {
	const isAi = checkInAnswer(item.aiAnswer, key);
	const isCor = checkInAnswer(item.correctAnswer, key);
	if (!hasKnownCorrectAnswer(item) && isAi) return 'background: #0A84FF; color: #FFFFFF;';
	if (isAi && isCor) return 'background: #34C759; color: #FFFFFF;';
	if (isAi && !isCor) return 'background: #FF3B30; color: #FFFFFF;';
	if (!isAi && isCor) return 'background: #FF9500; color: #FFFFFF;';
	return 'background: #E5E5EA; color: #1C1C1E;';
};

const getOptionTextStyle = (item, key) => {
	const isAi = checkInAnswer(item.aiAnswer, key);
	const isCor = checkInAnswer(item.correctAnswer, key);
	if (!hasKnownCorrectAnswer(item) && isAi) return 'color: #0A67C7; font-weight: 700;';
	if (isAi && isCor) return 'color: #248A3D; font-weight: 700;';
	if (isAi && !isCor) return 'color: #D70015; font-weight: 700;';
	if (!isAi && isCor) return 'color: #D97706; font-weight: 700;';
	return 'color: #1C1C1E;';
};

const getOptionBadge = (item, key) => {
	const isAi = checkInAnswer(item.aiAnswer, key);
	const isCor = checkInAnswer(item.correctAnswer, key);
	if (!hasKnownCorrectAnswer(item) && isAi) return 'AI已选（待公布答案）';
	if (isAi && isCor) return '✓ AI已选 (正确)';
	if (isAi && !isCor) return '✕ AI误选 (错误)';
	if (!isAi && isCor) return '★ 官方正确答案';
	return '';
};

const getOptionBadgeStyle = (item, key) => {
	const isAi = checkInAnswer(item.aiAnswer, key);
	const isCor = checkInAnswer(item.correctAnswer, key);
	if (!hasKnownCorrectAnswer(item) && isAi) return 'background: #0A84FF; color: #FFFFFF;';
	if (isAi && isCor) return 'background: #34C759; color: #FFFFFF;';
	if (isAi && !isCor) return 'background: #FF3B30; color: #FFFFFF;';
	if (!isAi && isCor) return 'background: #FF9500; color: #FFFFFF;';
	return '';
};

const getRecordTimestamp = (item) => {
	if (item?.timestamp && Number(item.timestamp) > 0) return Number(item.timestamp);
	if (item?.problemStartedAt && Number(item.problemStartedAt) > 0) return Number(item.problemStartedAt);
	if (item?.date && item?.time) {
		const parsed = new Date(`${item.date} ${item.time}`).getTime();
		if (!isNaN(parsed) && parsed > 0) return parsed;
	}
	return 0;
};

const formatAttemptAnswers = (answers) => {
	if (!answers) return '--';
	if (Array.isArray(answers)) {
		return answers.length > 0 ? answers.join(', ') : '--';
	}
	return String(answers) || '--';
};

const isModelConsensus = (item) => {
	const attempts = Array.isArray(item?.aiAttempts) ? item.aiAttempts : [];
	const successAttempts = attempts.filter(att => att?.status === 'success' && Array.isArray(att.answers) && att.answers.length > 0);
	if (successAttempts.length < 2) return false;
	const firstAns = successAttempts[0].answers.slice().sort().join(',');
	return successAttempts.every(att => att.answers.slice().sort().join(',') === firstAns);
};

const collapsedCourses = ref({});
const collapsedLessons = ref({});

const toggleCourseCollapse = (courseName) => {
	collapsedCourses.value[courseName] = !collapsedCourses.value[courseName];
};

const toggleLessonCollapse = (lessonKey) => {
	collapsedLessons.value[lessonKey] = !collapsedLessons.value[lessonKey];
};

const groupedCourseAiHistory = computed(() => {
	const courseMap = {};
	const list = aiHistoryList.value || [];

	list.forEach(item => {
		// 1. 大类：课程名称
		const courseName = item.courseName || item.course_name || '常规课程';
		if (!courseMap[courseName]) {
			courseMap[courseName] = {
				courseName,
				totalCount: 0,
				latestTimestamp: 0,
				lessonsMap: {}
			};
		}
		courseMap[courseName].totalCount++;

		const itemTs = getRecordTimestamp(item);
		if (itemTs > courseMap[courseName].latestTimestamp) {
			courseMap[courseName].latestTimestamp = itemTs;
		}

		// 2. 小类：课堂主题 / 章节
		const lessonTitle = item.lessonTitle || item.lesson_title || item.title || (item.lessonId ? `课堂 #${item.lessonId}` : '综合答题');
		const lessonDate = item.date || '今天';
		const lessonKey = `${courseName}___${lessonDate}___${item.lessonId || lessonTitle}`;

		if (!courseMap[courseName].lessonsMap[lessonKey]) {
			courseMap[courseName].lessonsMap[lessonKey] = {
				lessonKey,
				lessonTitle,
				date: lessonDate,
				latestTimestamp: 0,
				items: []
			};
		}
		const lessonGroup = courseMap[courseName].lessonsMap[lessonKey];
		if (itemTs > lessonGroup.latestTimestamp) {
			lessonGroup.latestTimestamp = itemTs;
		}
		lessonGroup.items.push(item);
	});

	// 课程按最近做题时间倒序排列（优先展示最近有新答题记录的课程学科）
	return Object.keys(courseMap)
		.map(courseName => {
			const courseGroup = courseMap[courseName];
			// 章节按最近做题时间倒序排列
			const lessons = Object.keys(courseGroup.lessonsMap)
				.map(lessonKey => {
					const lessonGroup = courseGroup.lessonsMap[lessonKey];
					// 题卡按精确时间倒序排列 (最新题目排在最前)
					lessonGroup.items.sort((a, b) => {
						const tsA = getRecordTimestamp(a);
						const tsB = getRecordTimestamp(b);
						if (tsA !== tsB) return tsB - tsA;
						return String(b.id || '').localeCompare(String(a.id || ''));
					});
					return lessonGroup;
				})
				.sort((la, lb) => lb.latestTimestamp - la.latestTimestamp);

			return {
				courseName,
				totalCount: courseGroup.totalCount,
				latestTimestamp: courseGroup.latestTimestamp,
				lessons
			};
		})
		.sort((ca, cb) => cb.latestTimestamp - ca.latestTimestamp);
});

const userApiKey = ref(uni.getStorageSync('yuketang_user_api_key') || '');
const currentGroupRemark = ref(uni.getStorageSync('ykt_user_key_remark') || '');
const showKeyConfigModal = ref(false);
const keyInputVal = ref('');
const savingKeyConfig = ref(false);
const keyValidationMsg = ref('');

// ================== 管理员控制台 (专属密钥生成权限) ==================
const showAdminModal = ref(false);
const isAdminAuthenticated = ref(false);
const adminPassInput = ref('');
const adminApiToken = ref('');
const adminCreatedKeysList = ref(safeJsonParse(uni.getStorageSync('ykt_admin_keys_pool') || '[]', []));
const customKeyInput = ref('');
const newKeyRemarkInput = ref('');
const newlyCreatedKey = ref('');
const editingOriginalKey = ref('');
const editingKeyId = ref('');

const openAdminModal = () => {
	adminPassInput.value = '';
	customKeyInput.value = '';
	newKeyRemarkInput.value = '';
	newlyCreatedKey.value = '';
	editingOriginalKey.value = '';
	editingKeyId.value = '';
	showAdminModal.value = true;
	if (isAdminAuthenticated.value) loadAdminKeysFromServer();
};

const openAdminFromKey = () => {
	showKeyConfigModal.value = false;
	openAdminModal();
};

const adminLogout = () => {
	isAdminAuthenticated.value = false;
	adminApiToken.value = '';
	adminPassInput.value = '';
	editingOriginalKey.value = '';
	editingKeyId.value = '';
	uni.showToast({ title: '已退出管理员模式', icon: 'none' });
};

const generateRandomCustomKey = () => {
	const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
	let res = 'key_';
	const random = new Uint32Array(24);
	if (globalThis.crypto?.getRandomValues) globalThis.crypto.getRandomValues(random);
	else for (let i = 0; i < random.length; i++) random[i] = Math.floor(Math.random() * 0xFFFFFFFF);
	for (let i = 0; i < random.length; i++) res += chars.charAt(random[i] % chars.length);
	customKeyInput.value = res;
};

const validateUserKeyInput = (rawKey) => {
	if (!rawKey) return '密钥不能为空';
	if (rawKey.length > 128) return '密钥最长 128 个字符';
	if (/[\u0000-\u001F\u007F]/.test(rawKey)) return '密钥不能包含控制字符';
	return '';
};

const formatUserKeyHint = (rawKey) => {
	if (rawKey.length <= 2) return '*'.repeat(rawKey.length);
	if (rawKey.length <= 6) return `${rawKey[0]}…${rawKey[rawKey.length - 1]}`;
	return `${rawKey.slice(0, 3)}…${rawKey.slice(-3)}`;
};

const loadAdminKeysFromServer = () => {
	if (!adminApiToken.value) return;
	uni.request({
		url: `${SYNC_SERVER_URL}/api/sync/keys`,
		method: 'GET',
		timeout: API_TIMEOUT,
		header: { Authorization: adminApiToken.value },
		success: (res) => {
			if (res.statusCode !== 200 || res.data?.code !== 0 || !Array.isArray(res.data?.data)) return;
			const localKeys = adminCreatedKeysList.value.slice();
			adminCreatedKeysList.value = res.data.data.map(serverItem => {
				const local = localKeys.find(item => (
					(item.id && item.id === serverItem.id) ||
					(item.key && formatUserKeyHint(item.key) === serverItem.key_hint)
				));
				return {
					id: serverItem.id || '',
					key: local?.key || '',
					keyHint: serverItem.key_hint || '***',
					remark: serverItem.remark || '通用用户密钥',
					createdAt: serverItem.created_at || ''
				};
			});
			uni.setStorageSync('ykt_admin_keys_pool', JSON.stringify(adminCreatedKeysList.value));
		}
	});
};

// ================== Salted SHA-256 安全加密校验引擎 ==================
const calculateSha256 = (str) => {
	function rightRotate(value, amount) {
		return (value >>> amount) | (value << (32 - amount));
	}
	var mathPow = Math.pow;
	var maxWord = mathPow(2, 32);
	var lengthProperty = 'length';
	var i, j;
	var result = '';
	var words = [];
	var asciiBitLength = str[lengthProperty] * 8;

	var hash = [
		0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
		0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
	];
	var k = [
		0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
		0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
		0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
		0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
		0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
		0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
		0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
		0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
	];

	str += '\x80';
	while (str[lengthProperty] % 64 !== 56) str += '\x00';
	for (i = 0; i < str[lengthProperty]; i++) {
		j = str.charCodeAt(i);
		words[i >> 2] |= j << ((3 - i) % 4 * 8);
	}
	words[words[lengthProperty]] = (asciiBitLength / maxWord) | 0;
	words[words[lengthProperty]] = asciiBitLength;

	for (j = 0; j < words[lengthProperty]; ) {
		var w = words.slice(j, j += 16);
		var oldHash = hash.slice(0);

		for (i = 0; i < 64; i++) {
			var w15 = w[i - 15], w2 = w[i - 2];
			var s0 = rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3);
			var s1 = rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10);

			w[i] = i < 16 ? w[i] : (w[i - 16] + s0 + w[i - 7] + s1) | 0;
			var a = hash[0], e = hash[4];
			var temp1 = hash[7]
				+ (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25))
				+ ((e & hash[5]) ^ (~e & hash[6]))
				+ k[i]
				+ w[i];
			var temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22))
				+ ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2]));

			hash = [(temp1 + temp2) | 0].concat(hash);
			hash[4] = (hash[4] + temp1) | 0;
		}

		for (i = 0; i < 8; i++) {
			hash[i] = (hash[i] + oldHash[i]) | 0;
		}
	}

	for (i = 0; i < 8; i++) {
		for (j = 3; j >= 0; j--) {
			var b = (hash[i] >> (j * 8)) & 255;
			result += (b < 16 ? '0' : '') + b.toString(16);
		}
	}
	return result;
};

const verifyAdminPassword = () => {
	const inputPass = adminPassInput.value ? adminPassInput.value.trim() : '';
	if (!inputPass) {
		uni.showToast({ title: '请输入口令', icon: 'none' });
		return;
	}
	uni.showLoading({ title: '验证服务器口令...' });
	uni.request({
		url: `${SYNC_SERVER_URL}/api/admin/verify`,
		method: 'POST',
		timeout: API_TIMEOUT,
		header: { 'Authorization': inputPass },
		success: (res) => {
			uni.hideLoading();
			if (res.statusCode === 200 && res.data?.code === 0) {
				adminApiToken.value = inputPass;
				adminPassInput.value = '';
				isAdminAuthenticated.value = true;
				loadAdminKeysFromServer();
				uni.showToast({ title: '管理员身份已验证', icon: 'success' });
			} else {
				uni.showToast({ title: res.data?.msg || '管理员口令错误', icon: 'none' });
			}
		},
		fail: () => {
			uni.hideLoading();
			uni.showToast({ title: '管理员验证请求失败', icon: 'none' });
		}
	});
};

const adminCreateNewKey = () => {
	const rawKey = customKeyInput.value.trim();
	const validationError = validateUserKeyInput(rawKey);
	if (validationError) {
		uni.showToast({ title: validationError, icon: 'none' });
		return;
	}

	const remarkStr = newKeyRemarkInput.value.trim() || '通用用户密钥';
	const originalKey = editingOriginalKey.value;
	const originalKeyId = editingKeyId.value;
	const isEditing = !!(originalKey || originalKeyId);
	uni.showLoading({ title: '写入服务器...' });
	uni.request({
		url: `${SYNC_SERVER_URL}${isEditing ? '/api/sync/update_key' : '/api/sync/create_key'}`,
		method: 'POST',
		timeout: API_TIMEOUT,
		header: { 'Content-Type': 'application/json', 'Authorization': adminApiToken.value },
		data: isEditing
			? { old_key: originalKey, key_id: originalKeyId, new_key: rawKey, remark: remarkStr }
			: { key: rawKey, remark: remarkStr },
		success: (res) => {
			uni.hideLoading();
			if (res.statusCode !== 200 || res.data?.code !== 0) {
				uni.showToast({ title: res.data?.msg || '保存密钥失败', icon: 'none' });
				return;
			}
			const keyObj = {
				id: res.data?.key_id || originalKeyId || '',
				key: rawKey,
				keyHint: formatUserKeyHint(rawKey),
				remark: remarkStr,
				createdAt: new Date().toLocaleDateString()
			};
			const existsIdx = adminCreatedKeysList.value.findIndex(item => (
				(originalKeyId && item.id === originalKeyId) ||
				(originalKey && item.key === originalKey) ||
				(!isEditing && item.key === rawKey)
			));
			if (existsIdx !== -1) adminCreatedKeysList.value[existsIdx] = keyObj;
			else adminCreatedKeysList.value.unshift(keyObj);
			uni.setStorageSync('ykt_admin_keys_pool', JSON.stringify(adminCreatedKeysList.value));
			if (isEditing && userApiKey.value === originalKey) {
				userApiKey.value = rawKey;
				currentGroupRemark.value = remarkStr;
				uni.setStorageSync('yuketang_user_api_key', rawKey);
				uni.setStorageSync('ykt_user_key_remark', remarkStr);
			}
			newlyCreatedKey.value = rawKey;
			customKeyInput.value = '';
			newKeyRemarkInput.value = '';
			editingOriginalKey.value = '';
			editingKeyId.value = '';
			uni.showToast({ title: isEditing ? '密钥已修改' : '密钥已创建', icon: 'success' });
		},
		fail: () => {
			uni.hideLoading();
			uni.showToast({ title: '保存密钥请求失败', icon: 'none' });
		}
	});
};

const editAdminKey = (index) => {
	const item = adminCreatedKeysList.value[index];
	if (!item) return;
	editingOriginalKey.value = item.key || '';
	editingKeyId.value = item.id || '';
	customKeyInput.value = item.key || '';
	newKeyRemarkInput.value = item.remark || '';
	newlyCreatedKey.value = '';
};

const cancelEditAdminKey = () => {
	editingOriginalKey.value = '';
	editingKeyId.value = '';
	customKeyInput.value = '';
	newKeyRemarkInput.value = '';
};

const copyCreatedKey = (keyStr) => {
	uni.setClipboardData({
		data: keyStr,
		success: () => uni.showToast({ title: '密钥已复制到剪贴板', icon: 'success' })
	});
};

const deleteAdminKey = (index) => {
	const keyObj = adminCreatedKeysList.value[index];
	const keyToDelete = keyObj ? keyObj.key : '';
	const keyIdToDelete = keyObj ? keyObj.id : '';
	if (keyToDelete || keyIdToDelete) {
		uni.showLoading({ title: '删除服务器密钥...' });
		uni.request({
			url: `${SYNC_SERVER_URL}/api/sync/delete_key`,
			method: 'POST',
			timeout: API_TIMEOUT,
			header: { 'Content-Type': 'application/json', 'Authorization': adminApiToken.value },
			data: { key: keyToDelete, key_id: keyIdToDelete },
			success: (res) => {
				uni.hideLoading();
				if (res.statusCode !== 200 || res.data?.code !== 0) {
					uni.showToast({ title: res.data?.msg || '删除密钥失败', icon: 'none' });
					return;
				}
				adminCreatedKeysList.value.splice(index, 1);
				uni.setStorageSync('ykt_admin_keys_pool', JSON.stringify(adminCreatedKeysList.value));
				if (
					(editingOriginalKey.value && editingOriginalKey.value === keyToDelete) ||
					(editingKeyId.value && editingKeyId.value === keyIdToDelete)
				) cancelEditAdminKey();
				if (userApiKey.value === keyToDelete) clearKeyConfig();
				uni.showToast({ title: '服务器密钥已删除', icon: 'success' });
			},
			fail: () => {
				uni.hideLoading();
				uni.showToast({ title: '删除密钥请求失败', icon: 'none' });
			}
		});
	}
};

const updateGroupRemarkFromKey = (key) => {
	if (!key) {
		currentGroupRemark.value = '';
		uni.removeStorageSync('ykt_user_key_remark');
		return;
	}
	const kStr = key.trim();
	// 优先在管理员创建的密钥库中精确匹配管理员录入的专属备注名
	const matched = adminCreatedKeysList.value.find(item => item.key === kStr);
	if (matched && matched.remark) {
		currentGroupRemark.value = matched.remark;
		uni.setStorageSync('ykt_user_key_remark', matched.remark);
	} else {
		currentGroupRemark.value = `专属密钥组 (${kStr.slice(0, 6)}…)`;
		uni.removeStorageSync('ykt_user_key_remark');
	}
};

// 普通用户配置密钥 (仅配置/填入，自动关联管理员备注)
const openKeyConfigModal = () => {
	keyInputVal.value = userApiKey.value;
	keyValidationMsg.value = '';
	showKeyConfigModal.value = true;
};

const closeKeyConfigModal = () => {
	showKeyConfigModal.value = false;
	keyValidationMsg.value = '';
};

const saveKeyConfig = () => {
	const val = keyInputVal.value.trim();
	const validationError = validateUserKeyInput(val);
	if (validationError) {
		keyValidationMsg.value = validationError;
		return;
	}
	keyValidationMsg.value = '';
	savingKeyConfig.value = true;
	uni.showLoading({ title: '验证密钥...' });
	uni.request({
		url: `${SYNC_SERVER_URL}/api/sync/profile`,
		method: 'GET',
		timeout: API_TIMEOUT,
		header: { Authorization: val },
		success: (res) => {
			if (res.statusCode !== 200 || res.data?.code !== 0) {
				keyValidationMsg.value = res.data?.msg || '密钥无效，请检查后重试';
				return;
			}
			if (res.data?.data?.role !== 'tenant') {
				keyValidationMsg.value = '管理员口令不能作为普通账号组密钥使用';
				return;
			}
			const remark = res.data?.data?.remark || '专属账号组';
			userApiKey.value = val;
			currentGroupRemark.value = remark;
			uni.setStorageSync('yuketang_user_api_key', val);
			uni.setStorageSync('ykt_user_key_remark', remark);
			discardLegacyCloudDeleteQueue(val);
			showKeyConfigModal.value = false;
			uni.showToast({ title: '密钥已生效', icon: 'success' });
			fetchAiHistory(false);
		},
		fail: () => {
			keyValidationMsg.value = '服务器连接失败，未修改当前密钥';
		},
		complete: () => {
			savingKeyConfig.value = false;
			uni.hideLoading();
		}
	});
};

const clearKeyConfig = () => {
	const previousKey = userApiKey.value || uni.getStorageSync('yuketang_user_api_key') || '';
	discardLegacyCloudDeleteQueue(previousKey);
	userApiKey.value = '';
	currentGroupRemark.value = '';
	keyInputVal.value = '';
	aiHistoryList.value = [];
	uni.removeStorageSync('yuketang_user_api_key');
	uni.removeStorageSync('ykt_user_key_remark');
	showKeyConfigModal.value = false;
	uni.showToast({ title: '云端密钥已清除', icon: 'none' });
};

const getEffectiveApiKey = () => {
	const key = userApiKey.value || uni.getStorageSync('yuketang_user_api_key') || '';
	if (!key) {
		uni.showModal({
			title: '需先配置云端私有密钥',
			content: '为保障你的账号数据隔离与云端数据库安全，使用【从云端拉取】与【上传至云端】前必须先设置专属私有密钥。\n\n是否现在前往设置？',
			confirmText: '立即设置',
			cancelText: '取消',
			success: (res) => {
				if (res.confirm) openKeyConfigModal();
			}
		});
		return null;
	}
	return key;
};

const cloudDeleteStorageKey = apiKey => (
	`ykt_cloud_delete_queue_${calculateSha256(String(apiKey || '')).slice(0, 16)}`
);

// v2.6.1 起，“移除账号”严格限定为本机操作。清除旧版本遗留的
// tombstone，防止升级后下一次同步继续误删服务器数据库。
const discardLegacyCloudDeleteQueue = apiKey => {
	if (!apiKey) return;
	uni.removeStorageSync(cloudDeleteStorageKey(apiKey));
};

let aiHistoryRequestPending = false;
let aiStatusTimer = null;
let lastAiStatusPollAt = 0;

const fetchAiHistory = (showToast = false) => {
	if (aiDemoMode.value && !showToast) return;
	if (showToast) aiDemoMode.value = false;
	if (aiHistoryRequestPending) return;
	if (showToast) uni.showLoading({ title: '拉取历史...' });
	const apiKey = userApiKey.value || uni.getStorageSync('yuketang_user_api_key') || '';
	if (!apiKey) {
		if (showToast) {
			uni.hideLoading();
			uni.showToast({ title: '请先配置专属密钥', icon: 'none' });
		}
		aiHistoryList.value = [];
		aiActiveTasks.value = [];
		return;
	}
	const historyCacheKey = `ykt_ai_history_cache_${calculateSha256(apiKey).slice(0, 16)}`;

	// 先从本地离线缓存尝试加载
	const savedCache = uni.getStorageSync(historyCacheKey);
	if (savedCache) {
		try {
			aiHistoryList.value = normalizeHistoryRecords(JSON.parse(savedCache));
		} catch(e) {}
	}

	aiHistoryRequestPending = true;
	uni.request({
		url: `${SYNC_SERVER_URL}/api/ai/history`,
		method: 'GET',
		timeout: API_TIMEOUT,
		header: {
			Authorization: apiKey
		},
		success: (res) => {
			if (showToast) uni.hideLoading();
			if (aiDemoMode.value && !showToast) return;
			if (res.data && res.data.code === 0) {
				aiHistoryList.value = normalizeHistoryRecords(res.data.data);
				uni.setStorageSync(historyCacheKey, JSON.stringify(aiHistoryList.value));
				if (res.data.ai_status) {
					aiStatusState.value = res.data.ai_status;
				}
				aiHealthState.value = res.data.ai_health || null;
				aiActiveTasks.value = Array.isArray(res.data.active_tasks)
					? res.data.active_tasks
					: [];
				if (Number(res.data.server_time) > 0) {
					aiServerOffsetMs.value = Number(res.data.server_time) - Date.now();
				}
				if (showToast) uni.showToast({ title: '历史记录已同步', icon: 'success' });
			} else if (showToast) {
				uni.showToast({ title: '已载入本地历史记录', icon: 'none' });
			}
		},
		fail: () => {
			if (showToast) {
				uni.hideLoading();
				uni.showToast({ title: '已载入本地历史模式', icon: 'none' });
			}
		},
		complete: () => {
			aiHistoryRequestPending = false;
		}
	});
};

const handleValidityAppShow = () => refreshAccountValidity(false);

onMounted(() => {
	// App 启动时默认从 GitCode 拉取一次最新服务器配置；失败则静默回退本地缓存
	refreshServerConfigFromRemote().then(() => {
		fetchAiHistory(false);
	}).catch(() => {});

	discardLegacyCloudDeleteQueue(
		userApiKey.value || uni.getStorageSync('yuketang_user_api_key') || ''
	);
	fetchAiHistory(false);
	aiStatusTimer = setInterval(() => {
		aiClockMs.value = Date.now();
		if (currentTab.value === 'ai' && Date.now() - lastAiStatusPollAt >= 2500) {
			lastAiStatusPollAt = Date.now();
			fetchAiHistory(false);
		}
	}, 1000);
	const savedAccounts = uni.getStorageSync('ykt_accounts_data_v1');
	if (savedAccounts) {
		const parsedAccounts = safeJsonParse(savedAccounts, []);
		accounts.value = (Array.isArray(parsedAccounts) ? parsedAccounts : []).map(account => ({
			...account,
			expired: normalizeExpiredFlag(account.expired)
		}));
		// 云端状态为主，本地身份接口作为断网回退。
		refreshAccountValidity(true);
	}
	uni.onAppShow(handleValidityAppShow);
	uni.$on('captchaPageResult', handleCaptchaPageResult);
});

const persistAccountsLocally = () => {
	uni.setStorageSync('ykt_accounts_data_v1', JSON.stringify(accounts.value));
};

const runBounded = async (items, concurrency, worker) => {
	const results = new Array(items.length);
	let cursor = 0;
	const runners = Array.from({ length: Math.min(Math.max(1, concurrency), items.length) }, async () => {
		while (cursor < items.length) {
			const index = cursor++;
			try {
				results[index] = await worker(items[index], index);
			} catch (error) {
				results[index] = { ok: false, error };
			}
		}
	});
	await Promise.all(runners);
	return results;
};

// Local probes use bounded concurrency; explicit auth failures expire immediately,
// while gateway/WAF/network responses remain unknown.
const verifyLocalAccounts = async (targets = accounts.value) => {
	if (!targets.length) return;
	let needSave = false;
	await runBounded(targets, BATCH_CONCURRENCY, acc => new Promise((resolve) => {
			if (!acc.cookie) {
				applyValidityResult(acc, { state: 'expired', reason: 'cookie_missing' });
				needSave = true;
				resolve();
				return;
			}
			uni.request({
				url: BASE_URL + '/v/course_meta/user_info',
				method: 'GET',
				timeout: API_TIMEOUT,
				header: { 
                    'cookie': acc.cookie, 
                    'user-agent': acc.device ? acc.device['user-agent'] : 'Android', 
                    'x-client': 'app', 
                    'xtbz': 'ykt' 
                },
				success: (res) => {
					const result = inspectUserInfoResponse(res);
					const previous = `${acc.expired}|${acc.validityState}`;
					applyValidityResult(acc, result);
					if (previous !== `${acc.expired}|${acc.validityState}`) needSave = true;
					resolve();
				},
				fail: () => {
					applyValidityResult(acc, { state: 'unknown', reason: 'network' });
					resolve();
				}
			});
		}));
	
	if (needSave) persistAccountsLocally();
};
const totalAccounts = computed(() => accounts.value.length);

let silentSyncTimer = null;
const saveAccounts = () => {
	persistAccountsLocally();
	if (silentSyncTimer) clearTimeout(silentSyncTimer);
	silentSyncTimer = setTimeout(() => {
		silentSyncTimer = null;
		silentPushToCloud();
	}, 500);
};

const toggleAccountAiMode = (acc, val) => {
	acc.ai_mode = !!val;
	saveAccounts();
	syncAnswerReceivers();
	uni.showToast({
		title: val ? `[${acc.remark || acc.name || '终端'}] 已开启 AI 托管` : `[${acc.remark || acc.name || '终端'}] 已关闭 AI 托管`,
		icon: 'none'
	});
};

// ================== 全新按需选择拉取引擎 ==================

const showCloudPullDialog = ref(false);
const cloudAccountsList = ref([]);
const selectedCloudCount = computed(() => cloudAccountsList.value.filter(a => a.selected).length);
const isAllCloudSelected = computed(() => cloudAccountsList.value.length > 0 && cloudAccountsList.value.every(a => a.selected));

// 第一步：点击拉取时，先从云端抓取列表并打开弹窗
const fetchCloudList = () => {
	const apiKey = getEffectiveApiKey();
	if (!apiKey) return;

	uni.showLoading({ title: '连接私有云端库...' });

	const loadLocalCloudBackup = () => {
		const backupData = uni.getStorageSync(`ykt_cloud_db_${apiKey}`);
		if (backupData) {
			try {
				const parsed = JSON.parse(backupData);
				if (parsed && parsed.length > 0) {
					cloudAccountsList.value = parsed.map(acc => ({ ...acc, expired: normalizeExpiredFlag(acc.expired), selected: true }));
					showCloudPullDialog.value = true;
					return true;
				}
			} catch(e) {}
		}
		return false;
	};

	uni.request({
		url: `${SYNC_SERVER_URL}/api/sync/download`,
		method: 'GET',
		timeout: API_TIMEOUT,
		header: { 'Authorization': apiKey },
		success: (res) => {
			uni.hideLoading();
			if (res.data && res.data.code === 0) {
				// 实时从云端更新该 Key 对应群组备注
				if (res.data.remark) {
					currentGroupRemark.value = res.data.remark;
					uni.setStorageSync('ykt_user_key_remark', res.data.remark);
				}

				const data = Array.isArray(res.data.data) ? res.data.data : (res.data.accounts || []);
				if (!data || data.length === 0) {
					if (!loadLocalCloudBackup()) {
						uni.showToast({ title: '当前密钥对应的私有库为空', icon: 'none' });
					}
					return;
				}
				// 载入列表，默认全部勾选
				cloudAccountsList.value = data.map(acc => ({ ...acc, expired: normalizeExpiredFlag(acc.expired), selected: true }));
				showCloudPullDialog.value = true;
			} else {
				// 若云端拦截或无记录，平滑降级加载该密钥的专属私有库
				if (loadLocalCloudBackup()) {
					uni.showToast({ title: '服务器返回异常，当前显示本地备份', icon: 'none' });
				} else {
					uni.showToast({ title: '当前密钥库为空，请先上传账号', icon: 'none' });
				}
			}
		},
		fail: () => {
			uni.hideLoading();
			if (loadLocalCloudBackup()) {
				uni.showToast({ title: '服务器连接失败，当前显示本地备份', icon: 'none' });
			} else {
				uni.showToast({ title: '服务器连接失败且没有本地备份', icon: 'none' });
			}
		}
	});
};

// 全选/全不选 切换
const toggleSelectAllCloud = () => {
	const newState = !isAllCloudSelected.value;
	cloudAccountsList.value.forEach(acc => acc.selected = newState);
};

// 第二步：用户选完后确认拉取入库
const confirmCloudPull = (mode) => {
	const finalAccounts = cloudAccountsList.value.filter(a => a.selected);
	if (finalAccounts.length === 0) {
		uni.showToast({ title: '请至少勾选一个账号', icon: 'none' });
		return;
	}

	// 补全由于跨版本或意外缺失的设备指纹
	finalAccounts.forEach(acc => {
		delete acc.selected; // 移除UI辅助状态
		if (!acc.device || !acc.device.brand) {
			acc.device = generateDeviceProfile();
		}
	});

	if (mode === 'replace') {
		accounts.value = finalAccounts;
	} else {
		// 合并模式：以手机号为主键去重
		const phoneMap = {};
		accounts.value.forEach(a => { phoneMap[a.phone] = a; });
		finalAccounts.forEach(a => { phoneMap[a.phone] = a; });
		accounts.value = Object.values(phoneMap);
	}

	// 保存本地并触发一次静默同步对齐时间线
	saveAccounts();
	showCloudPullDialog.value = false;
	uni.showToast({ title: `成功挂载 ${finalAccounts.length} 个终端`, icon: 'success' });
};

// ================== 云端数据上行与静默热更新逻辑 ==================

// 手动点击全量强制上云
const pushToCloud = () => {
	const apiKey = getEffectiveApiKey();
	if (!apiKey) return;
	discardLegacyCloudDeleteQueue(apiKey);

	if (accounts.value.length === 0) {
		uni.showToast({ title: '本地无账号可同步', icon: 'none' });
		return;
	}
	uni.showLoading({ title: '正在同步至私有库...' });

	// 双向安全锁：同步静默归档该 Key 的专属私有数据库
	uni.setStorageSync(`ykt_cloud_db_${apiKey}`, JSON.stringify(accounts.value));

	uni.request({
		url: `${SYNC_SERVER_URL}/api/sync/upload`,
		method: 'POST',
		timeout: API_TIMEOUT,
		header: { 'Content-Type': 'application/json', 'Authorization': apiKey },
		data: {
			accounts: accounts.value,
			remark: currentGroupRemark.value
		},
		success: (res) => {
			uni.hideLoading();
			if (res.statusCode === 200 && res.data?.code === 0) {
				uni.showToast({ title: '私有云端库已成功写入', icon: 'success' });
			} else {
				uni.showToast({ title: res.data?.msg || `同步失败 HTTP ${res.statusCode}`, icon: 'none' });
			}
		},
		fail: (error) => {
			uni.hideLoading();
			uni.showToast({ title: error?.errMsg || '同步请求失败', icon: 'none' });
		}
	});
};

// 静默上云（跟随每次本地 saveAccounts 触发）
const silentPushToCloud = () => {
	const apiKey = userApiKey.value || uni.getStorageSync('yuketang_user_api_key') || '';
	if (!apiKey) return;
	discardLegacyCloudDeleteQueue(apiKey);
	if (accounts.value.length === 0) return;

	// 双向安全锁：同步静默归档该 Key 的专属私有缓存库
	if (apiKey) {
		uni.setStorageSync(`ykt_cloud_db_${apiKey}`, JSON.stringify(accounts.value));
	}

	uni.request({
		url: `${SYNC_SERVER_URL}/api/sync/upload`,
		method: 'POST',
		timeout: API_TIMEOUT,
		header: { 'Content-Type': 'application/json', 'Authorization': apiKey },
		data: {
			accounts: accounts.value,
			remark: currentGroupRemark.value
		}
	});
};

// 静默拉取以服务器 expired 字段为权威状态，并返回已匹配的本地账号。
const silentPullFromCloud = () => new Promise(resolve => {
	if (accounts.value.length === 0) {
		resolve({ ok: true, matched: new Set() });
		return;
	}
	const apiKey = userApiKey.value || uni.getStorageSync('yuketang_user_api_key') || '';
	if (!apiKey) {
		resolve({ ok: false, matched: new Set(), reason: 'key_missing' });
		return;
	}
	uni.request({
		url: `${SYNC_SERVER_URL}/api/sync/download`,
		method: 'GET',
		timeout: API_TIMEOUT,
		header: { 'Authorization': apiKey },
		success: (res) => {
			if (!(res.data && res.data.code === 0 && Array.isArray(res.data.data))) {
				resolve({ ok: false, matched: new Set() });
				return;
			}
			const cloudAccounts = res.data.data;
			const matched = new Set();
			let needSave = false;
			accounts.value.forEach(localAcc => {
				const cloudAcc = findCloudAccount(cloudAccounts, localAcc);
				if (!cloudAcc) return;
				matched.add(String(localAcc.id || localAcc.phone || localAcc.uid));
				const cookieChanged = Boolean(cloudAcc.cookie) && localAcc.cookie !== cloudAcc.cookie;
				const nextExpired = normalizeExpiredFlag(cloudAcc.expired);
				if (localAcc.expired !== nextExpired || cookieChanged) needSave = true;
				localAcc.expired = nextExpired;
				localAcc.validityState = nextExpired ? 'expired' : 'valid';
				localAcc.validitySource = 'cloud';
				localAcc.validityCheckedAt = Date.now();
				if (cloudAcc.cookie) localAcc.cookie = cloudAcc.cookie;
				if (cloudAcc.device) localAcc.device = cloudAcc.device;
				localAcc.remark = cloudAcc.remark || localAcc.remark;
				const localCredentialUpdatedAt = Number(localAcc.lessonCredentialUpdatedAt || 0);
				const cloudCredentialUpdatedAt = Number(cloudAcc.lessonCredentialUpdatedAt || 0);
				const cloudHasCredential = Boolean(cloudAcc.lessonToken && (cloudAcc.lessonId || cloudAcc.lessonContext?.id));
				const shouldApplyCloudCredential = (
					cloudCredentialUpdatedAt > localCredentialUpdatedAt ||
					(!localAcc.lessonToken && cloudHasCredential)
				);
				if (cookieChanged || shouldApplyCloudCredential) {
					localAcc.lessonToken = cloudAcc.lessonToken || '';
					localAcc.lessonId = String(cloudAcc.lessonId || cloudAcc.lessonContext?.id || '');
					localAcc.lessonContext = cloudAcc.lessonContext || (localAcc.lessonId ? { id: localAcc.lessonId } : null);
					localAcc.lessonCredentialUpdatedAt = cloudCredentialUpdatedAt || Date.now();
					needSave = true;
				}
			});
			// 始终持久化：即使 needSave===false，也确保云端状态写入本地缓存
			persistAccountsLocally();
			resolve({ ok: true, matched });
		},
		fail: () => resolve({ ok: false, matched: new Set() })
	});
});

const refreshAccountValidity = async (force = false) => {
	if (!accounts.value.length || accountValidityChecking.value) return;
	if (!force && Date.now() - lastValidityCheckAt < 60000) return;
	accountValidityChecking.value = true;
	try {
		// 第一步：从云端同步 cookie / device / remark（但不信任云端的 expired 字段）
		await silentPullFromCloud();
		// 第二步：所有账号都走本地 API 探针验证有效性（这才是唯一可靠来源）
		await verifyLocalAccounts(accounts.value);
		persistAccountsLocally();
		lastValidityCheckAt = Date.now();
		syncAnswerReceivers();
		if (force) {
			const validCount = accounts.value.filter(a => !a.expired).length;
			const expiredCount = accounts.value.filter(a => a.expired).length;
			uni.showToast({ title: `${validCount}个有效 / ${expiredCount}个过期`, icon: 'none', duration: 2000 });
		}
	} finally {
		accountValidityChecking.value = false;
	}
};


// ================== 添加终端 / 登录引擎 ==================

const showLoginDialog = ref(false);
const loginMode = ref('sms'); // 'sms' | 'password'
const loginRemark = ref(''); 
const loginPhone = ref('');
const loginSmsCode = ref('');
const loginPassword = ref('');
const captchaFinished = ref(false);
const showAuthorDialog = ref(false);

const copyContact = () => {
	uni.setClipboardData({
		data: '2768484926@qq.com',
		success: () => uni.showToast({ title: '邮箱已复制', icon: 'success' })
	});
};

const captchaTicket = ref('');
const captchaRandstr = ref('');
const captchaOpening = ref(false);
const smsCountDown = ref(0);
const smsSending = ref(false);
let smsTimer = null;
let smsAutoSendTimer = null;
let captchaPageWatchdog = null;

const showScannerView = ref(false);
let barcodeInstance = null;
const pendingScanMode = ref('');
const pendingRescueAccounts = ref([]);
const pendingRescueLessonId = ref('');
let monitorStartTimer = null;

const openLoginModal = () => { showLoginDialog.value = true; resetLoginForm(); };
const closeLoginModal = () => { showLoginDialog.value = false; resetLoginForm(); };
const clearCaptchaPageWatchdog = () => {
	if (captchaPageWatchdog) clearTimeout(captchaPageWatchdog);
	captchaPageWatchdog = null;
};
const resetLoginForm = () => {
	loginMode.value = 'sms';
	loginRemark.value = ''; loginPhone.value = ''; loginSmsCode.value = ''; loginPassword.value = '';
	captchaFinished.value = false; captchaTicket.value = ''; captchaRandstr.value = '';
	captchaOpening.value = false;
	smsSending.value = false;
	clearCaptchaPageWatchdog();
	if (smsAutoSendTimer) clearTimeout(smsAutoSendTimer);
	smsAutoSendTimer = null;
	if(smsTimer) clearInterval(smsTimer); smsCountDown.value = 0;
};

const isValidCaptchaResult = result => (
	typeof result?.ticket === 'string' &&
	typeof result?.randstr === 'string' &&
	result.ticket.length >= 16 &&
	result.ticket.length <= 4096 &&
	result.randstr.length >= 4 &&
	result.randstr.length <= 256
);

const handleCaptchaPageResult = result => {
	clearCaptchaPageWatchdog();
	captchaOpening.value = false;
	if (!result || result.type !== 'success') return;
	if (!isValidCaptchaResult(result)) {
		uni.showToast({ title: '验证码返回数据无效，请重试', icon: 'none' });
		return;
	}
	captchaTicket.value = result.ticket;
	captchaRandstr.value = result.randstr;
	captchaFinished.value = true;
	if (smsAutoSendTimer) clearTimeout(smsAutoSendTimer);
	smsAutoSendTimer = setTimeout(() => {
		smsAutoSendTimer = null;
		if (
			showLoginDialog.value &&
			loginMode.value === 'sms' &&
			captchaFinished.value &&
			smsCountDown.value <= 0
		) {
			sendSmsCode();
		}
	}, 300);
};

const openCaptchaWebView = () => {
	if (captchaOpening.value) return;
	if (captchaFinished.value) {
		uni.showToast({ title: '当前验证码已经通过', icon: 'none' });
		return;
	}
	captchaOpening.value = true;
	clearCaptchaPageWatchdog();
	captchaPageWatchdog = setTimeout(() => {
		captchaOpening.value = false;
		const pages = getCurrentPages();
		const currentPage = pages[pages.length - 1];
		const route = String(currentPage?.route || '');
		if (route === 'pages/captcha/captcha' && pages.length > 1) {
			uni.navigateBack({ delta: 1 });
		}
		uni.showToast({ title: '验证页面等待超时，已解除锁定', icon: 'none' });
	}, 100000);
	uni.navigateTo({
		url: '/pages/captcha/captcha',
		fail: () => {
			clearCaptchaPageWatchdog();
			captchaOpening.value = false;
			uni.showToast({ title: '无法打开验证页面，请重试', icon: 'none' });
		}
	});
};

// 即使设备丢失了 web-view 消息，返回本页时也必须解除“正在验证”锁。
onShow(() => {
	const pages = getCurrentPages();
	const currentPage = pages[pages.length - 1];
	if (
		captchaOpening.value &&
		String(currentPage?.route || '') !== 'pages/captcha/captcha'
	) {
		clearCaptchaPageWatchdog();
		captchaOpening.value = false;
	}
});

const sendSmsCode = () => {
	if (smsSending.value || smsCountDown.value > 0) return;
	if(!/^1\d{10}$/.test(String(loginPhone.value || '').trim())) {
		uni.showToast({ title: '请输入有效的11位手机号', icon: 'none' });
		return;
	}
	if(!captchaTicket.value) {
		uni.showToast({ title: '请先完成人机验证', icon: 'none' });
		return;
	}
	smsSending.value = true;
	const requestPhone = String(loginPhone.value || '').trim();
	const requestTicket = captchaTicket.value;
	const requestRandstr = captchaRandstr.value;
	uni.showLoading({title: '正在自动发送验证码...'});
	uni.request({
		url: BASE_URL + '/api/v3/user/code/send',
		method: 'POST',
		timeout: API_TIMEOUT,
		header: { 'user-agent': 'Android', 'x-client': 'app', 'xtbz': 'ykt', 'content-type': 'application/json' },
		data: { phoneNumber: requestPhone, email: "", ticket: requestTicket, rand: requestRandstr },
		success: (res) => {
			if(res.data && res.data.code === 0) {
				smsCountDown.value = 60;
				if(smsTimer) clearInterval(smsTimer);
				smsTimer = setInterval(() => {
					smsCountDown.value--;
					if(smsCountDown.value <= 0) clearInterval(smsTimer);
				}, 1000);
				uni.showToast({ title: '短信验证码已发送', icon: 'success' });
			} else {
				uni.showToast({title: res.data?.msg || '短信验证码发送失败', icon: 'none'});
			}
		},
		fail: () => {
			uni.showToast({title: '网关超时，可点击重新发送', icon: 'none'});
		},
		complete: () => {
			smsSending.value = false;
			uni.hideLoading();
		}
	});
};

const doAppLoginFlow = () => {
	if(!loginRemark.value.trim()) { uni.showToast({title: '终端备注不可为空', icon: 'none'}); return; }
	if(!/^1\d{10}$/.test(String(loginPhone.value || '').trim())) { uni.showToast({title: '手机号格式错误', icon: 'none'}); return; }
	if(!/^\d{4,8}$/.test(String(loginSmsCode.value || '').trim())) { uni.showToast({title: '验证码格式错误', icon: 'none'}); return; }
	uni.showLoading({title: '解析凭证中...'});
	uni.request({
		url: BASE_URL + '/api/v3/user/login/app',
		method: 'POST',
		timeout: API_TIMEOUT,
		header: { 'user-agent': 'Android', 'x-client': 'app', 'xtbz': 'ykt', 'content-type': 'application/json' },
		data: { type: 3, phoneNumber: loginPhone.value, email: "", code: loginSmsCode.value, pushDeviceId: "", ticket: captchaTicket.value, rand: captchaRandstr.value },
		success: (res) => {
			if (res.statusCode === 200 && res.data && res.data.code === 0) {
				let cookiesStr = Array.isArray(res.cookies) && res.cookies.length
					? res.cookies
					: res.header?.['set-cookie'] || res.header?.['Set-Cookie'];
				let finalCookie = extractCookie(cookiesStr);
				if(finalCookie) { fetchUserInfoAndAdd(finalCookie, loginPhone.value); } else {
					uni.hideLoading(); uni.showToast({title: '认证异常缺失', icon: 'none'});
				}
			} else {
				fallbackRegisterApp();
			}
		},
		fail: () => { uni.hideLoading(); uni.showToast({title: '网络断开', icon: 'none'}); }
	});
};

const fallbackRegisterApp = () => {
	uni.request({
		url: BASE_URL + '/api/v3/user/register/app',
		method: 'POST',
		timeout: API_TIMEOUT,
		header: { 'user-agent': 'Android', 'x-client': 'app', 'xtbz': 'ykt', 'content-type': 'application/json' },
		data: { email: "", phoneNumber: loginPhone.value, password: "", userId: "", code: loginSmsCode.value, wechatToken: "", pushDeviceId: "" },
		success: (res) => {
			if (res.data && res.data.code === 0) {
				let cookiesStr = Array.isArray(res.cookies) && res.cookies.length
					? res.cookies
					: res.header?.['set-cookie'] || res.header?.['Set-Cookie'];
				let finalCookie = extractCookie(cookiesStr);
				if(finalCookie) { fetchUserInfoAndAdd(finalCookie, loginPhone.value); } else {
					uni.hideLoading(); uni.showToast({title: '通道异常', icon:'none'});
				}
			} else {
				uni.hideLoading(); uni.showModal({title: '强登未遂', content: res.data.msg || '无法登入'});
			}
		},
		fail: () => { uni.hideLoading(); uni.showToast({title: '网络断开', icon: 'none'}); }
	});
};

const doPasswordLoginFlow = () => {
	if (!loginRemark.value.trim()) { uni.showToast({ title: '终端备注不可为空', icon: 'none' }); return; }
	if (!/^1\d{10}$/.test(String(loginPhone.value || '').trim())) { uni.showToast({ title: '手机号格式错误', icon: 'none' }); return; }
	if (!loginPassword.value.trim()) { uni.showToast({ title: '请输入雨课堂密码', icon: 'none' }); return; }
	if (!captchaTicket.value || !captchaRandstr.value) {
		uni.showToast({ title: '请先完成安全核验', icon: 'none' });
		return;
	}
	uni.showLoading({ title: '密码认证中...' });
	const device = generateDeviceProfile();
	uni.request({
		url: BASE_URL + '/api/v3/user/login/app',
		method: 'POST',
		timeout: API_TIMEOUT,
		header: {
			'user-agent': 'Android',
			'x-client': 'app',
			'xtbz': 'ykt',
			'content-type': 'application/json',
			'brand': device.brand,
			'buildnumber': '1610',
			'xtua': 'client=app&tag=1.3.3&platform=Android',
			'systemversion': device.systemversion,
			'incremental': device.incremental,
			'version': '1.3.3',
			'isphysicaldevice': 'true'
		},
		data: {
			type: 1,
			phoneNumber: String(loginPhone.value).trim(),
			password: String(loginPassword.value).trim(),
			email: "",
			code: "",
			pushDeviceId: "",
			ticket: captchaTicket.value,
			rand: captchaRandstr.value
		},
		success: (res) => {
			if (res.statusCode === 200 && res.data && res.data.code === 0) {
				let cookiesStr = Array.isArray(res.cookies) && res.cookies.length
					? res.cookies
					: res.header?.['set-cookie'] || res.header?.['Set-Cookie'];
				let finalCookie = extractCookie(cookiesStr);
				if (finalCookie) {
					fetchUserInfoAndAdd(finalCookie, loginPhone.value);
				} else {
					uni.hideLoading();
					uni.showToast({ title: '认证异常缺失', icon: 'none' });
				}
			} else {
				uni.hideLoading();
				const msg = res.data?.msg || res.data?.message || '密码或安全核验错误';
				uni.showModal({ title: '密码登录失败', content: msg, showCancel: false });
			}
		},
		fail: () => {
			uni.hideLoading();
			uni.showToast({ title: '网络断开，请重试', icon: 'none' });
		}
	});
};

const extractCookie = (strOrArray) => {
	if(!strOrArray) return '';
	let str = Array.isArray(strOrArray) ? strOrArray.join(';') : strOrArray;
	let sessionidMatch = str.match(/sessionid=([^;,]+)/);
	let sidMatch = str.match(/sid=([^;,]+)/);
	let csrfMatch = str.match(/csrftoken=([^;,]+)/);
	let res = '';
	if(sessionidMatch) res += `sessionid=${sessionidMatch[1]}; `;
	if(sidMatch) res += `sid=${sidMatch[1]}; `;
	if(csrfMatch) res += `csrftoken=${csrfMatch[1]}; `;
	res += 'django_language=zh-cn;';
	return res;
};

const generateDeviceProfile = () => {
	const brandTemplates = [`Xiaomi 1${Math.floor(Math.random() * 4) + 1} Pro`, `HUAWEI Mate ${Math.floor(Math.random() * 4) + 3}0 Pro`, `vivo X${Math.floor(Math.random() * 4) + 6}0 Pro`, `OPPO Find X${Math.floor(Math.random() * 4) + 3} Pro`, `google Pixel ${Math.floor(Math.random() * 4) + 4}` ];
	return {
		'brand': brandTemplates[Math.floor(Math.random() * brandTemplates.length)],
		'uuid': '', 'buildnumber': '1610', 'x-client': 'app', 'xtua': 'client=app&tag=1.3.3&platform=Android',
		'systemversion': String(Math.floor(Math.random() * 5) + 10),
		'incremental': String(Math.floor(Math.random() * 89999999) + 10000000),
		'version': '1.3.3', 'isphysicaldevice': 'true', 'xtbz': 'ykt', 'user-agent': 'Android'
	};
};

const fetchUserInfoAndAdd = (cookieStr, phoneNum) => {
	uni.request({
		url: BASE_URL + '/v/course_meta/user_info',
		method: 'GET',
		timeout: API_TIMEOUT,
		header: { 'cookie': cookieStr, 'user-agent': 'Android', 'x-client': 'app', 'xtbz': 'ykt' },
		success: (res) => {
			uni.hideLoading();
			const inspection = inspectUserInfoResponse(res);
			if (inspection.state !== 'valid') {
				uni.showModal({
					title: inspection.state === 'expired' ? '登录凭证已失效' : '账号状态待复核',
					content: `身份接口未返回有效用户资料（${inspection.reason}），本次不会写入账号库。`,
					showCancel: false
				});
				return;
			}
			const profile = inspection.profile || {};
			const name = profile.nickname || profile.name || '';
			const school = profile.school || '';
			const uid = profile.user_id || profile.uid || '';
			let exists = accounts.value.find(a => a.phone === phoneNum);
			if(exists) {
				const loginSessionChanged = exists.cookie !== cookieStr;
				exists.cookie = cookieStr;
				exists.name = name || exists.name;
				exists.school = school || exists.school;
				exists.uid = uid || exists.uid;
				exists.remark = loginRemark.value.trim() || exists.remark;
				applyValidityResult(exists, inspection);
				if (loginSessionChanged) {
					exists.lessonToken = '';
					exists.lessonId = '';
					exists.lessonContext = null;
					exists.lessonCredentialUpdatedAt = Date.now();
				}
				uni.showToast({title: '终端实名已覆盖更新', icon: 'none'});
			} else {
				const account = {
					id: Date.now(), remark: loginRemark.value.trim(), name, school, phone: phoneNum,
					uid, cookie: cookieStr, device: generateDeviceProfile(), expired: false
				};
				applyValidityResult(account, inspection);
				accounts.value.push(account);
				uni.showToast({ title: '账号登录成功！', icon: 'success' });
			}
			saveAccounts();
			closeLoginModal(); 
		},
		fail: (error) => {
			uni.hideLoading();
			uni.showModal({
				title: '身份校验请求失败',
				content: error?.errMsg || '网络异常，本次没有写入账号。',
				showCancel: false
			});
		}
	});
};

const deleteAccount = (accIndex) => {
	uni.showModal({
		title: '移除确认',
		content: '只会从当前手机移除此账号，服务器数据库中的账号会完整保留，之后仍可从云端重新拉取。是否继续？',
		success: (res) => {
			if(res.confirm) {
				accounts.value.splice(accIndex, 1);
				saveAccounts();
				uni.showToast({ title: '已从本机移除，云端账号已保留', icon: 'none' });
			}
		}
	});
};

// ================== 云端引擎与并发控制 ================== 

const showProgressDialog = ref(false);
const isProgressFinished = ref(false);
const progressMsg = ref('');
const runLogs = ref([]);
const scrollTop = ref(0);

const getLogTime = () => {
	const now = new Date();
	return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
};

const openScannerWebview = (mode, rescueAccs, expectedLessonId = '') => {
	pendingScanMode.value = mode;
	if (rescueAccs) pendingRescueAccounts.value = rescueAccs;
	pendingRescueLessonId.value = mode === 'rescue' ? String(expectedLessonId || '') : '';

	if (typeof plus === 'undefined') { uni.showToast({ title: '非 App 环境，无法扫码', icon: 'none' }); return; }
	showScannerView.value = true;

	if (!barcodeInstance) {
		const pages = getCurrentPages();
		const currentWebview = pages[pages.length - 1].$getAppWebview();
		
		barcodeInstance = plus.barcode.create('barcode', [plus.barcode.QR], {
			top: '0px', left: '0px', width: '100%', height: '100%', position: 'static', frameColor: '#0A84FF', scanbarColor: '#0A84FF',
		});
		
		barcodeInstance.onmarked = function(type, result) { closeScannerWebview(); handleScanResultSuccess(result); };
		barcodeInstance.onerror = function(error) {
			console.warn("扫码引擎发生错误", error);
			closeScannerWebview();
			uni.showModal({
				title: '扫码组件异常',
				content: error?.message || error?.code || '摄像头启动失败，已自动退出扫码页。',
				showCancel: false
			});
		};

		currentWebview.append(barcodeInstance);
		barcodeInstance.start();
		
		closeButtonView = new plus.nativeObj.View('closeBtn', {
			top: '40px', right: '20px', width: '44px', height: '44px', backgroundColor: 'rgba(0,0,0,0.5)'
		}, [ {tag:'font', id:'icon', text:'✕', color:'#FFFFFF', position:{top:'0px',left:'0px',width:'100%',height:'100%'}, textStyles:{size:'20px', weight:'bold'}} ]);
		
		closeButtonView.drawRect({color:'rgba(0,0,0,0)',radius:'22px'}, {top:'0px',left:'0px',width:'100%',height:'100%'});
		closeButtonView.addEventListener('click', () => { closeScannerWebview(); handleScanResultCancel(); }, false);
		currentWebview.append(closeButtonView);
	}
};

let closeButtonView = null;

const closeScannerWebview = () => {
	showScannerView.value = false;
	const pages = getCurrentPages();
	let currentWebview = null;
	if (pages.length > 0) currentWebview = pages[pages.length - 1].$getAppWebview();

	if (barcodeInstance) {
		try { if (currentWebview) currentWebview.remove(barcodeInstance); } catch(e){}
		barcodeInstance.cancel(); barcodeInstance.close(); barcodeInstance = null;
	}
	if (closeButtonView) {
		try { if (currentWebview) currentWebview.remove(closeButtonView); } catch(e){}
		closeButtonView.hide(); closeButtonView.close(); closeButtonView = null;
	}
};

const handleScanResultSuccess = (qrUrl) => {
	uni.vibrateShort();
	let validQr = false;
	try {
		const parsed = new URL(String(qrUrl || ''));
		const host = parsed.hostname.toLowerCase();
		validQr = (host === 'yuketang.cn' || host.endsWith('.yuketang.cn')) &&
			(parsed.pathname.includes('/lesson/check-in') || parsed.pathname.includes('/dynamic-qr-code'));
	} catch (_) {}
	if (validQr) {
		if (pendingScanMode.value === 'rescue') {
			const expectedLessonId = String(pendingRescueLessonId.value || '');
			const rescueTargets = pendingRescueAccounts.value.filter(account => !account.expired && account.cookie);
			openProgress('掉队打捞专列', qrUrl);
			executeBatchTasks(rescueTargets, qrUrl, { mode: 'rescue', expectedLessonId });
		} else {
			const targets = accounts.value.filter(account => !account.expired && account.cookie);
			if (!targets.length) {
				uni.showToast({ title: '没有有效且已登录的账号', icon: 'none' });
				return;
			}
			openProgress('全部账号', qrUrl);
			executeBatchTasks(targets, qrUrl, { mode: 'batch', expectedLessonId: '' });
		}
	} else {
		uni.showModal({ title: '二维码无法识别', content: '请扫描雨课堂专属的课堂动态防逃课二维码', showCancel: false });
	}
};

const handleScanResultCancel = () => {
	if (pendingScanMode.value === 'rescue') {
		uni.showToast({ title: '放弃补签打捞', icon: 'none' });
		showProgressDialog.value = true; isProgressFinished.value = true;
	} else {
		uni.showToast({ title: '扫码取消', icon: 'none' });
	}
};

const startBatchScan = () => {
	if (accounts.value.length === 0) { uni.showToast({ title: '无账号，需先添加', icon: 'none' }); return; }
	openScannerWebview('batch');
};

const openProgress = (grpName, url) => {
	showProgressDialog.value = true; isProgressFinished.value = false;
	progressMsg.value = `正在载入调度组别 [${grpName}] ...`; runLogs.value = [];
	addLog(`[系统] 成功捕获并解密动态二维码实体链接。`, true);
};

const addLog = (text, success) => {
	runLogs.value.push({ time: getLogTime(), text, success });
	scrollTop.value = runLogs.value.length * 60; 
};

const requestApi = (url, method, data, cookie, deviceProfile, uid) => {
	const safeDevice = deviceProfile || generateDeviceProfile();
	let safeCookie = String(cookie || '');
	if (!safeCookie) return Promise.resolve({ status: 401, data: { msg: '账号 Cookie 缺失' } });
	let csrf = ''; const csrfMatch = safeCookie.match(/csrftoken=([^; ]+)/);
	if (csrfMatch && csrfMatch[1]) { csrf = csrfMatch[1]; } else {
		const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
		for(let j=0; j<32; j++) csrf += chars.charAt(Math.floor(Math.random()*chars.length));
		safeCookie += `; csrftoken=${csrf}; django_language=zh-cn;`;
	}

	const headerParams = Object.assign({ 'cookie': safeCookie, 'x-csrftoken': csrf, 'content-type': 'application/json' }, safeDevice);
	if (uid) headerParams['x-uid'] = String(uid);

	return new Promise((resolve) => {
		uni.request({
			url, method, header: headerParams, data, timeout: API_TIMEOUT,
			success: (res) => resolve({ status: res.statusCode, data: res.data }),
			fail: (err) => resolve({ status: -1, error: err })
		});
	});
};

const shouldRetryRequest = response => response?.status === -1 || response?.status >= 500;

const executeSingleTaskWithRetry = async (acc, qrUrl, batchContext) => {
	const displayName = acc.remark || acc.name || acc.phone || '未命名账号';
	addLog(`--- 尝试桥接账号: ${displayName} [伪装机型: ${acc.device.brand}] ---`, true);

	let scanRes;
	for (let i = 0; i < 3; i++) {
		scanRes = await requestApi(BASE_URL + '/api/v3/app/scan', 'POST', { url: qrUrl }, acc.cookie, acc.device, acc.uid);
		if (scanRes.status === 200 && scanRes.data && scanRes.data.code === 0) break;
		if (i < 2 && shouldRetryRequest(scanRes)) await new Promise(r => setTimeout(r, 500 * (i + 1)));
		else break;
	}
	
	if (scanRes.status !== 200 || !scanRes.data || scanRes.data.code !== 0) {
		addLog(`[拦截] > ${displayName} | 请求风控拦截或失效 (重试3次失败)。`, false);
		return { ok: false, reason: 'scan_failed' };
	}

	const lessonId = String(scanRes.data?.data?.value ?? '');
	const lessonLock = lockLessonForBatch(batchContext, lessonId);
	if (!lessonLock.accepted && lessonLock.reason === 'lesson_id_missing') {
		addLog(`[拦截] > ${displayName} | 扫码响应缺少 lessonId。`, false);
		return { ok: false, reason: 'lesson_id_missing' };
	}
	// 一个批次只允许绑定一个课堂。补签批次从发车时就锁定原课堂，账号响应不得改写全局 lessonId。
	if (!lessonLock.accepted) {
		addLog(`[隔离] > ${displayName} | 二维码解析到课堂 ${lessonId}，当前批次锁定课堂 ${batchContext.lessonId}，已跳过。`, false);
		return { ok: false, reason: 'lesson_mismatch', lessonId };
	}
	
	const lessonIdPayload = /^\d+$/.test(lessonId) && Number.isSafeInteger(Number(lessonId)) ? Number(lessonId) : lessonId;
	const checkinData = { source: 21, lessonId: lessonIdPayload, joinIfNotIn: true };
	
	let checkRes;
	for (let i = 0; i < 3; i++) {
		checkRes = await requestApi(BASE_URL + '/api/v3/lesson/checkin', 'POST', checkinData, acc.cookie, acc.device, acc.uid);
		if (checkRes.status === 200 && checkRes.data && checkRes.data.code === 0) break;
		if (i < 2 && shouldRetryRequest(checkRes)) await new Promise(r => setTimeout(r, 500 * (i + 1)));
		else break;
	}
	
	if (checkRes.status !== 200 || !checkRes.data || checkRes.data.code !== 0) {
		addLog(`[错误] > ${displayName} | 签到请求被云端防火墙挡回。`, false);
		return { ok: false, reason: 'checkin_failed', lessonId };
	} else {
		const stuName = checkRes.data?.data?.identityName || displayName;
		const lessonToken = checkRes.data?.data?.lessonToken || '';
		if (!lessonToken) {
			addLog(`[错误] > ${displayName} | 签到成功响应缺少 lessonToken。`, false);
			return { ok: false, reason: 'token_missing', lessonId };
		}
		acc.lessonToken = lessonToken;
		acc.lessonId = lessonId;
		acc.lessonContext = { id: lessonId, joinedAt: Date.now() };
		acc.lessonCredentialUpdatedAt = Date.now();
		addLog(`[成功] > ${acc.name || stuName} | 已成功进入《${currentLessonDisplayName.value || lessonId}》(ID: ${lessonId})`, true);
		return { ok: true, lessonId, account: acc };
	}
};

const executeBatchTasks = async (accounts, qrUrl, options = {}) => {
	if (!Array.isArray(accounts) || accounts.length === 0) {
		progressMsg.value = '没有可执行的有效账号';
		isProgressFinished.value = true;
		return;
	}
	let successCount = 0;
	progressMsg.value = `引擎启动，正在并发扫描 ${accounts.length} 个终端...`;
	const batchContext = createLessonBatchContext(options);
	if (batchContext.lessonId) addLog(`[系统] 补签批次已锁定原课堂 ${batchContext.lessonId}，扫码结果只用于更新掉队账号凭证。`, true);
	
	let needSave = false;
	for (const acc of accounts) {
		if (!acc.device || !acc.device.brand) {
			acc.device = generateDeviceProfile();
			needSave = true;
		}
	}
	if (needSave) saveAccounts();
	
	const results = new Array(accounts.length);
	let pendingIndexes = accounts.map((_, index) => index);
	if (!batchContext.lessonId) {
		// 新课堂先由账号列表中的首个可解析终端建立唯一锚点，再放行其余并发任务。
		for (const index of pendingIndexes) {
			results[index] = await executeSingleTaskWithRetry(accounts[index], qrUrl, batchContext);
			if (batchContext.lessonId) {
				pendingIndexes = pendingIndexes.filter(item => item !== index && results[item] === undefined);
				addLog(`[系统] 批次课堂锚点已确定为 ${batchContext.lessonId}，其余终端开始并发入课。`, true);
				break;
			}
		}
		if (!batchContext.lessonId) pendingIndexes = [];
	}
	const parallelResults = await runBounded(
		pendingIndexes,
		BATCH_CONCURRENCY,
		index => executeSingleTaskWithRetry(accounts[index], qrUrl, batchContext)
	);
	pendingIndexes.forEach((index, offset) => { results[index] = parallelResults[offset]; });

	successCount = results.filter(result => result?.ok).length;
	// lessonToken 是 WebSocket 入课和后续批量答题的核心凭证，签到成功后立即持久化。
	if (successCount > 0) saveAccounts();
	const failedAccounts = accounts.filter((_, index) => !results[index]?.ok);
	
	if (successCount > 0 && batchContext.lessonId) {
		// 所有账号任务结束后只提交一次课堂上下文，彻底消除并发账号相互覆盖 lessonId 的竞态。
		bindLessonContext(batchContext.lessonId);
		await fetchLessonInfo(true);
		// 至少有一台终端签入成功，即刻自动开启课堂课件雷达监视
		if (monitorStartTimer) clearTimeout(monitorStartTimer);
		monitorStartTimer = setTimeout(() => {
			monitorStartTimer = null;
			if (String(currentLessonId.value) === String(batchContext.lessonId)) startProblemMonitor(batchContext.lessonId);
		}, 1000);
	}
	
	if (failedAccounts.length > 0) {
		progressMsg.value = `执行中断: 成功 ${successCount}/${accounts.length}，有 ${failedAccounts.length} 个失败待打捞`;
		addLog(`======= 发现落网之终端，准备启动补网程序 =======`, false);
		
		setTimeout(() => {
			uni.showModal({
				title: '部分终端签到失败',
				content: `遇到网络抖动或二维码云端变位，有 ${failedAccounts.length} 个终端掉队。\n\n是否重新唤起摄像头，扫描最新的课堂二维码只为它们补签？`,
				confirmText: '扫新码补签',
				cancelText: '不管了',
				success: (res) => {
					if (res.confirm) {
						showProgressDialog.value = false;
						openScannerWebview('rescue', failedAccounts, batchContext.lessonId);
					} else {
						isProgressFinished.value = true;
					}
				}
			});
		}, 800);
	} else {
		progressMsg.value = `并发签到队列执行圆满结束: 零掉队，共写入 ${successCount} 个终端。`;
		addLog(`======= 批量云签引擎连接闭合 =======`, true);
		isProgressFinished.value = true;
	}
};

// ================== 独立课件答题引擎 ==================

const {
	answerProblemId,
	answerProblemType,
	answerReceivers,
	currentLessonId,
	currentLessonInfo,
	currentLessonDisplayName,
	currentLessonSecondaryText,
	lessonInfoState,
	currentQuestion,
	presentationTitle,
	fillAnswers,
	subjectiveAnswer,
	submittingAnswer,
	isMonitoring,
	isNewProblemDetected,
	monitorStatusText,
	wsConnectionState,
	wsStatusText,
	wsLastMessageText,
	lessonSessionEnded,
	questionRemaining,
	questionUnlimited,
	checkedReceiversCount,
	allReadyReceiversChecked,
	questionTypeLabel,
	isTextQuestion,
	displayedQuestionOptions,
	canAnswerCurrentQuestion,
	canSubmitAnswer,
	questionCountdownLabel,
	questionCountdownText,
	isOptionSelected,
	selectQuestionOption,
	setFillAnswer,
	toggleReceiver,
	toggleAllReceivers,
	toggleMonitor,
	startProblemMonitor,
	stopProblemMonitor,
	openAnswerTab,
	doBatchAnswer,
	onSlideCoverError,
	loadDemoCourseware,
	syncAnswerReceivers,
	bindLessonContext,
	fetchLessonInfo,
	forceReconnect,
	aiHostedReceiversCount,
	testAiConnection
} = createAnswerEngine({
	accounts,
	currentTab,
	baseUrl: BASE_URL,
	wsBaseUrl: WS_BASE_URL,
	getSyncServerUrl,
	syncServerUrl: () => getSyncServerUrl(),
	getSyncApiKey: () => userApiKey.value || uni.getStorageSync('yuketang_user_api_key') || '',
	generateDeviceProfile,
	saveAccounts,
	addLog,
	showProgressDialog,
	isProgressFinished,
	progressMsg,
	runLogs
});

onUnmounted(() => {
	if (smsTimer) clearInterval(smsTimer);
	if (smsAutoSendTimer) clearTimeout(smsAutoSendTimer);
	if (aiStatusTimer) clearInterval(aiStatusTimer);
	if (silentSyncTimer) clearTimeout(silentSyncTimer);
	if (monitorStartTimer) clearTimeout(monitorStartTimer);
	clearCaptchaPageWatchdog();
	uni.$off('captchaPageResult', handleCaptchaPageResult);
	if (typeof uni.offAppShow === 'function') uni.offAppShow(handleValidityAppShow);
	closeScannerWebview();
});

// 课件封面点击全屏预览（采用 100% 稳定纯正 Vue 高阶沉浸蒙层，支持物理/侧滑返回键退出）
const slidePreviewVisible = ref(false);
const previewSlideUrl = ref('');

const previewSlideImage = (urlOrEvent) => {
	let targetUrl = '';
	if (typeof urlOrEvent === 'string' && urlOrEvent) {
		targetUrl = urlOrEvent;
	} else if (currentQuestion.value?.cover) {
		targetUrl = currentQuestion.value.cover;
	} else if (previewSlideUrl.value) {
		targetUrl = previewSlideUrl.value;
	}

	if (!targetUrl) return;

	previewSlideUrl.value = targetUrl;
	slidePreviewVisible.value = true;
};
const closeSlidePreview = () => {
	slidePreviewVisible.value = false;
};

// 监听手机物理/手势侧滑返回键 (拦截返回键优先关闭全屏大图预览)
onBackPress((options) => {
	if (showScannerView.value || barcodeInstance) {
		closeScannerWebview();
		handleScanResultCancel();
		return true;
	}
	if (slidePreviewVisible.value) {
		slidePreviewVisible.value = false;
		return true;
	}
	if (showAuthorDialog.value) {
		showAuthorDialog.value = false;
		return true;
	}
	if (showProgressDialog.value) {
		showProgressDialog.value = false;
		return true;
	}
	if (showLoginDialog.value) {
		closeLoginModal();
		return true;
	}
	return false;
});
</script>

<style>
/* ================== Apple UI / 高级感设计 ================== */
page { background-color: #F2F2F7; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; }
.container { padding: 0; min-height: 100vh; box-sizing: border-box; }
.hero { position: relative; padding: calc(32px + var(--status-bar-height, 0px)) 20px 24px 20px; background: #FFFFFF; box-shadow: 0 16px 40px rgba(44, 62, 80, 0.04); overflow: hidden; margin-bottom: 16px; }
.hero-bg-decoration { position: absolute; top: -40px; right: -20px; width: 180px; height: 180px; background: radial-gradient(circle, rgba(10, 132, 255, 0.08) 0%, rgba(10, 132, 255, 0) 70%); border-radius: 50%; z-index: 1; }
.hero-content { position: relative; z-index: 2; max-width: 560px; margin: 0 auto; }
.hero-title-wrap { display: flex; align-items: center; gap: 12px; }
.hero-title { font-size: 32px; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(90deg, #1C1C1E 0%, #3A3A3C 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; color: transparent; }
.hero-badge { background: linear-gradient(135deg, #0A84FF 0%, #005BB5 100%); color: #FFFFFF; font-size: 13px; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-style: italic; box-shadow: 0 6px 12px rgba(10, 132, 255, 0.25), inset 0 1px 1px rgba(255, 255, 255, 0.4); letter-spacing: 0.5px; }
.title-underline { width: 44px; height: 5px; background: linear-gradient(90deg, #0A84FF 0%, #30B0C7 100%); border-radius: 3px; margin-top: 14px; margin-bottom: 14px; }
.subtitle-wrapper { display: flex; justify-content: space-between; align-items: center; }
.hero-subtitle { font-size: 14px; color: #A1A1A6; font-weight: 400; letter-spacing: 2.5px; display: block; }
.author-tag { display: flex; align-items: center; gap: 4px; padding: 4px 12px; background: rgba(28, 28, 30, 0.03); border: 0.5px solid rgba(28, 28, 30, 0.08); border-radius: 100px; transition: all 0.2s ease; }
.author-tag:active { background: rgba(28, 28, 30, 0.08); transform: scale(0.96); }
.author-tag text { font-size: 11px; font-weight: 500; color: #5C5C5F; letter-spacing: 0.5px; }
.content-wrapper { padding: 0 16px calc(115px + constant(safe-area-inset-bottom)) 16px; padding: 0 16px calc(115px + env(safe-area-inset-bottom)) 16px; box-sizing: border-box; width: 100%; max-width: 560px; margin: 0 auto; }
.dashboard { display: flex; gap: 12px; margin-bottom: 24px; }
.dash-item { flex: 1; border-radius: 16px; padding: 16px 20px; display: flex; flex-direction: column; justify-content: center; }
.accent-bg { background-color: #0A84FF; box-shadow: 0 8px 16px rgba(10, 132, 255, 0.2); }
.dark-bg { background-color: #1C1C1E; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15); }
.dash-val { font-size: 28px; font-weight: 700; color: #FFFFFF; }
.dash-lbl { font-size: 12px; font-weight: 500; color: rgba(255,255,255,0.7); margin-top: 4px; }
.group-flow { height: calc(100vh - 230px); }
.card { background: #FFFFFF; border-radius: 20px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.card-title-box { display: flex; flex-direction: column; position: relative; padding: 4px 0; }
.validity-refresh { margin-top: 5px; color: #0A84FF; font-size: 10px; font-weight: 650; }
.validity-refresh.checking { color: #8E8E93; }
.card-title { font-size: 18px; font-weight: 700; color: #1C1C1E; }
.card-actions { display: flex; align-items: center; gap: 12px; }
.pill-btn { padding: 8px 16px; border-radius: 30px; }
.pill-btn text { font-size: 13px; font-weight: 600; }
.pill-btn.primary { background-color: #F2F2F7; }
.pill-btn.primary text { color: #0A84FF; }
.pill-btn.primary:active { background-color: #E5E5EA; }
.terminals-list { display: flex; flex-direction: column; gap: 12px; }
.terminal-item { display: flex; flex-direction: row; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #F2F2F7; }
.terminal-item:last-child { border-bottom: none; }
.terminal-left { flex: 1; min-width: 0; display: flex; flex-direction: row; align-items: center; gap: 10px; margin-right: 6px; }
.avatar-circle { width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #0A84FF, #0056B3); color: #FFFFFF; font-size: 15px; font-weight: 800; display: flex; justify-content: center; align-items: center; text-transform: uppercase; flex-shrink: 0; box-shadow: 0 3px 8px rgba(10, 132, 255, 0.3); }
.terminal-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.t-name-row { display: flex; flex-direction: row; align-items: center; gap: 6px; overflow: hidden; }
.t-name { font-size: 14px; font-weight: 700; color: #1C1C1E; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-expired { font-size: 9px; background: #FFEBEB; color: #FF3B30; padding: 2px 5px; border-radius: 4px; font-weight: bold; flex-shrink: 0; }
.status-active { font-size: 9px; background: #E5F9ED; color: #34C759; padding: 2px 5px; border-radius: 4px; font-weight: bold; flex-shrink: 0; }
.status-checking { font-size: 9px; background: #EEF4FF; color: #0A84FF; padding: 2px 5px; border-radius: 4px; font-weight: bold; flex-shrink: 0; }
.t-sub { font-size: 11px; font-weight: 500; color: #8E8E93; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.t-remove { font-size: 12px; color: #C7C7CC; font-weight: 500; }
.dashed-add-zone { margin-top: 4px; padding: 12px; border-radius: 12px; background-color: #F2F2F7; display: flex; align-items: center; gap: 12px; }
.dashed-add-zone:active { background-color: #E5E5EA; }
.add-circle { width: 28px; height: 28px; border-radius: 14px; background: #D1D1D6; color: #FFF; font-weight: bold; display: flex; justify-content: center; align-items: center; font-size: 16px; }
.dashed-add-zone text { font-size: 14px; color: #000; font-weight: 500; }
.empty-state { text-align: center; margin-top: 60px; display: flex; flex-direction: column; align-items: center; opacity: 0.6; }
.emoji-huge { font-size: 48px; }
.empty-text { font-size: 18px; font-weight: 600; color: #1C1C1E; margin-top: 10px; }
.empty-subtext { font-size: 13px; color: #8E8E93; margin-top: 4px; }
.blur-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); z-index: 9999; display: flex; flex-direction: column; justify-content: center; align-items: center; opacity: 0; pointer-events: none; transition: opacity 0.25s ease; }
.blur-mask.mask-active { opacity: 1; pointer-events: auto; }
.sheet-modal {
	background: #FFFFFF !important;
	opacity: 1 !important;
	border-radius: 24px !important;
	padding: 22px 20px !important;
	width: 90% !important;
	max-width: 380px !important;
	max-height: 86vh !important;
	overflow-y: auto !important;
	-webkit-overflow-scrolling: touch !important;
	box-sizing: border-box !important;
	margin: auto !important;
	box-shadow: 0 20px 50px rgba(0,0,0,0.35) !important;
	border: 1px solid rgba(255,255,255,0.9) !important;
	position: relative !important;
	z-index: 10000 !important;
}
.compact-settings-sheet { padding: 18px !important; border-radius: 20px !important; }
.compact-sheet-header { display: flex; flex-direction: row; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.compact-sheet-title { display: block; font-size: 17px; font-weight: 850; color: #1C1C1E; }
.compact-sheet-sub { display: block; max-width: 260px; margin-top: 3px; font-size: 10.5px; font-weight: 600; color: #8E8E93; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.compact-close { padding: 2px 4px; font-size: 16px; font-weight: 700; color: #8E8E93; }
.compact-key-input { box-sizing: border-box; width: 100%; height: 44px; padding: 0 12px; border-radius: 12px; border: 1.5px solid #E5E5EA; background: #F9F9FB; color: #1C1C1E; font-size: 14px; font-weight: 700; }
.key-validation-msg { display: block; margin: 7px 2px 0; color: #FF3B30; font-size: 11px; font-weight: 650; }
.compact-action-row { display: flex; flex-direction: row; gap: 8px; margin-top: 12px; }
.compact-primary-btn, .compact-secondary-btn { height: 38px; margin: 0; border: none; border-radius: 11px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; }
.compact-primary-btn { flex: 1; color: #FFFFFF; background: linear-gradient(135deg, #FF9500, #D97706); }
.compact-primary-btn[disabled] { opacity: 0.55; }
.compact-secondary-btn { width: 72px; color: #FF3B30; background: #FFF0EF; }
.compact-primary-btn::after, .compact-secondary-btn::after { border: none; }
.admin-entry-row { display: flex; flex-direction: row; justify-content: space-between; align-items: center; margin-top: 13px; padding-top: 12px; border-top: 1px solid #F0F0F2; color: #AF52DE; font-size: 11.5px; font-weight: 750; }
.sheet-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.sheet-title { font-size: 20px; font-weight: 700; color: #000; }
.sheet-close { font-size: 15px; font-weight: 600; color: #0A84FF; }
.ios-input { background: #F2F2F7; height: 50px; border-radius: 12px; padding: 0 16px; font-size: 15px; color: #1C1C1E; }
.ios-btn { height: 50px; border-radius: 14px; font-size: 16px; font-weight: 600; display: flex; justify-content: center; align-items: center; margin-top: 24px; }
.ios-btn.vibrant { background: #0A84FF; color: #FFF; box-shadow: 0 4px 12px rgba(10,132,255,0.3);}
.ios-btn.vibrant::after { border: none;}
.form-group { margin-bottom: 16px; }
.form-lbl { font-size: 13px; font-weight: 600; color: #8E8E93; margin-bottom: 8px; display: block; text-transform: uppercase;}
.captcha-box { height: 50px; border-radius: 12px; border: 1.5px dashed #C7C7CC; display: flex; justify-content: center; align-items: center; }
.captcha-box text { font-size: 14px; font-weight: 600; color: #8E8E93; }
.captcha-done { border: 1.5px solid #10b981; background: #D1FAE5; }
.captcha-opening { pointer-events: none; border-color: #0A84FF; background: rgba(10,132,255,0.08); }
.code-row { display: flex; gap: 12px; }
.code-input { flex: 1; }
.code-btn { width: 120px; height: 50px; background: #E5E5EA; color: #1C1C1E; font-size: 13px; font-weight: 600; border-radius: 12px; line-height: 50px; padding:0; border: none; }
.code-btn::after{ border:none; }
.login-switch-row { display: flex; justify-content: flex-end; align-items: center; margin-top: 10px; margin-bottom: 2px; }
.login-switch-link { font-size: 12px; font-weight: 600; color: #0A84FF; padding: 4px 0; }
.login-switch-link:active { opacity: 0.7; }
.shell-modal { margin: auto; background: #1E1E1E; width: 90%; border-radius: 12px; padding: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
.shell-header { display: flex; align-items: center; margin-bottom: 12px; }
.mac-dots { display: flex; gap: 6px; margin-right: 12px;}
.dot { width: 12px; height: 12px; border-radius: 6px; }
.dot.red { background: #FF5F56; } .dot.yellow { background: #FFBD2E; } .dot.green { background: #27C93F; }
.shell-title { font-size: 12px; color: #8E8E93; font-weight: 500; font-family: monospace; }
.shell-body { background: #000; border-radius: 8px; padding: 12px; }
.shell-status { color: #0A84FF; font-family: monospace; font-size: 12px; display: block; margin-bottom: 10px; font-weight: bold;}
.shell-logs { height: 260px; }
.log-line { display: flex; margin-bottom: 6px; font-family: monospace; font-size: 11px; }
.log-time { color: #8E8E93; margin-right: 8px; }
.log-good { color: #34C759; }
.log-bad { color: #FF3B30; }
.shell-footer { display: flex; justify-content: center; margin-top: 16px; }
.shell-btn { height: 36px; line-height:36px; background: rgba(255,255,255,0.1); color: #FFF; font-size: 12px; border-radius: 18px; font-family: monospace; font-weight: bold;}
.shell-btn::after { border: none; }
.dark-btn { background: #1C1C1E !important; color: #FFF !important; }
.dark-btn::after { border: none; }

/* 导入/导出选择预览相关样式 */
.import-preview-box { display: flex; flex-direction: column; }
.select-all-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #F2F2F7; border-radius: 12px; margin-bottom: 12px; }
.select-all-text { font-size: 14px; font-weight: 600; color: #1C1C1E; }
.preview-scroll { max-height: 220px; border-radius: 12px; background: #FFF; border: 1px solid #E5E5EA; }
.preview-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #F2F2F7; transition: background-color 0.2s; }
.preview-item:last-child { border-bottom: none; }
.preview-item:active { background-color: #F9F9F9; }
.preview-info { display: flex; flex-direction: column; }
.p-name { font-size: 15px; font-weight: 600; color: #1C1C1E; }
.p-sub { font-size: 12px; color: #8E8E93; margin-top: 2px; }

/* iOS风格复选框 */
.check-circle { width: 22px; height: 22px; border-radius: 11px; border: 2px solid #C7C7CC; box-sizing: border-box; position: relative; transition: all 0.2s; }
.check-circle.is-checked { border-color: #0A84FF; background-color: #0A84FF; }
.check-circle.is-checked::after { content: ''; position: absolute; left: 6px; top: 2px; width: 5px; height: 10px; border: solid white; border-width: 0 2px 2px 0; transform: rotate(45deg); }

/* 寄语样式 */
.author-body { padding: 10px 10px 30px 10px; position: relative; overflow: hidden; }
.quote-mark { font-size: 80px; color: rgba(10, 132, 255, 0.06); font-family: Georgia, serif; position: absolute; top: -20px; left: -10px; line-height: 1; z-index: 0; }
.author-scroll-view { max-height: 60vh; width: 100%; }
.author-text-container { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 20px; }
.paragraph { font-size: 15px; color: #3A3A3C; line-height: 2.2; letter-spacing: 1.5px; font-weight: 400; text-align: justify; }
.author-profile { position: relative; z-index: 1; margin-top: 40px; display: flex; justify-content: flex-end; align-items: center; gap: 12px; }
.author-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.author-name { font-size: 14px; color: #1C1C1E; font-weight: 600; font-style: italic; letter-spacing: 1px; }
.author-contact { font-size: 11px; color: #8E8E93; font-family: monospace; letter-spacing: 0.5px; background: rgba(28, 28, 30, 0.04); padding: 3px 8px; border-radius: 6px; transition: background 0.2s; }
.author-avatar { width: 48px; height: 48px; border-radius: 24px; background-color: #F2F2F7; border: 0.5px solid rgba(0, 0, 0, 0.05); box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06); flex-shrink: 0; }

/* AI 渠道与实际模型名称：顶部状态和每条历史记录均保留 */
.ai-module-heading { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 7px; }
.active-ai-model-row { max-width: 100%; display: flex; flex-direction: row; align-items: center; flex-wrap: wrap; gap: 6px; }
.active-ai-model-label { flex: 0 0 auto; font-size: 10px; font-weight: 800; color: #0A84FF; background: rgba(10,132,255,0.1); padding: 2px 6px; border-radius: 6px; }
.dual-ai-model-chips { min-width: 0; display: flex; flex-direction: row; align-items: center; flex-wrap: wrap; gap: 5px; }
.ai-model-chip { display: inline-flex; align-items: center; justify-content: center; white-space: nowrap; padding: 3px 7px; border-radius: 7px; font-size: 10px; line-height: 1; font-weight: 800; letter-spacing: 0.1px; }
.ai-model-chip.blue { color: #0064D2; background: rgba(10,132,255,0.11); border: 1px solid rgba(10,132,255,0.35); box-shadow: 0 2px 6px rgba(10,132,255,0.08); }
.ai-model-chip.purple { color: #8944AB; background: rgba(191,90,242,0.11); border: 1px solid rgba(191,90,242,0.35); box-shadow: 0 2px 6px rgba(191,90,242,0.08); }
.ai-model-chip-mini { display: inline-flex; align-items: center; justify-content: center; white-space: nowrap; padding: 2px 5px; border-radius: 5px; font-size: 9.5px; line-height: 1; font-weight: 800; }
.ai-model-chip-mini.blue { color: #0064D2; background: rgba(10,132,255,0.11); border: 1px solid rgba(10,132,255,0.3); }
.ai-model-chip-mini.purple { color: #8944AB; background: rgba(191,90,242,0.11); border: 1px solid rgba(191,90,242,0.3); }

/* 上下堆叠连通性列表 */
.ai-health-probes-list { width: 100%; display: flex; flex-direction: column; gap: 5px; }
.ai-health-record { width: 100%; box-sizing: border-box; display: flex; flex-direction: row; justify-content: space-between; align-items: center; padding: 4px 8px; border-radius: 8px; border: 1px solid rgba(142,142,147,0.2); background: rgba(142,142,147,0.06); }
.ai-health-record.success { border-color: rgba(52,199,89,0.3); background: rgba(52,199,89,0.08); }
.ai-health-record.failed { border-color: rgba(255,149,0,0.32); background: rgba(255,149,0,0.08); }
.ai-health-record.purple { border-color: rgba(191,90,242,0.25); background: rgba(191,90,242,0.05); }
.ai-health-record.purple.success { border-color: rgba(52,199,89,0.35); background: rgba(191,90,242,0.07); }

.ai-health-left { display: flex; flex-direction: row; align-items: center; gap: 5px; flex-shrink: 0; }
.ai-health-dot { width: 6px; height: 6px; flex: 0 0 6px; border-radius: 50%; background: #8E8E93; }
.ai-health-dot.purple { background: #BF5AF2; }
.ai-health-record.success .ai-health-dot { background: #34C759; box-shadow: 0 0 0 2px rgba(52,199,89,0.15); }
.ai-health-record.failed .ai-health-dot { background: #FF9500; }
.ai-health-name { color: #3A3A3C; font-size: 10.5px; font-weight: 800; white-space: nowrap; }
.ai-health-name.purple { color: #8944AB; }

.ai-health-right { display: flex; flex-direction: row; align-items: center; gap: 6px; min-width: 0; }
.ai-health-result { font-size: 10px; font-weight: 850; white-space: nowrap; }
.ai-health-record.success .ai-health-result { color: #248A3D; }
.ai-health-record.failed .ai-health-result { color: #B25D00; }
.ai-health-time { color: #8E8E93; font-size: 9.5px; font-weight: 600; white-space: nowrap; }

/* 右侧操作按钮：固定宽度防变形 */
.ai-top-actions { width: 56px; flex: 0 0 56px; display: flex; flex-direction: column; align-items: stretch; justify-content: center; gap: 6px; margin-left: 10px; }
.ai-action-btn { box-sizing: border-box; width: 100%; height: 28px; min-height: 28px; padding: 0; margin: 0; border-radius: 8px; display: flex; flex-direction: row; align-items: center; justify-content: center; line-height: 1; flex-shrink: 0; }
.ai-demo-history-btn { color: #8944AB; background: rgba(191,90,242,0.1); border: 1px solid rgba(191,90,242,0.25); font-size: 11px; font-weight: 800; }
.ai-refresh-btn { gap: 3px; border: 1px solid #0A84FF; background: #0A84FF; box-shadow: 0 2px 6px rgba(10,132,255,0.25); }
.ai-refresh-btn text { color: #FFFFFF; font-size: 11px; font-weight: 800; line-height: 1; }
.ai-demo-data-badge { padding: 2px 7px; border-radius: 7px; color: #8944AB; background: rgba(191,90,242,0.1); border: 1px solid rgba(191,90,242,0.22); font-size: 9.5px; font-weight: 800; }
.active-ai-task-row { max-width: 100%; display: flex; flex-direction: row; align-items: center; gap: 6px; padding: 5px 8px; border-radius: 9px; background: rgba(191,90,242,0.08); border: 1px solid rgba(191,90,242,0.18); }
.active-ai-task-dot { width: 6px; height: 6px; flex: 0 0 6px; border-radius: 50%; background: #BF5AF2; animation: answerPulse 1.1s infinite; }
.active-ai-task-stage { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 10.5px; font-weight: 800; color: #8944AB; }
.active-ai-task-time, .active-ai-task-deadline { flex: 0 0 auto; font-size: 10px; font-weight: 750; color: #636366; }
.active-ai-task-deadline { color: #D97706; }
.history-ai-model-row { display: flex; flex-direction: row; align-items: center; gap: 7px; margin: -3px 0 10px; padding: 6px 9px; border-radius: 9px; background: #F5F7FA; border: 1px solid rgba(10,132,255,0.08); }
.history-ai-model-label { flex: 0 0 auto; font-size: 10px; font-weight: 800; color: #0A84FF; }
.history-timing-row { display: flex; flex-direction: row; flex-wrap: wrap; gap: 5px; margin: -4px 0 11px; }
.history-timing-pill { padding: 3px 7px; border-radius: 7px; background: #F2F2F7; color: #636366; font-size: 9.5px; font-weight: 750; }
.history-timing-pill.strong { background: rgba(52,199,89,0.11); color: #248A3D; }

/* ================== 紧凑答题页 ================== */
.answer-page { min-height: 100vh; background: #F2F2F7; color: #1C1C1E; }

/* 极简固定浮动顶栏卡片 */
.answer-topbar {
	position: fixed;
	top: calc(var(--status-bar-height, 0px) + 6px);
	left: 50%;
	transform: translateX(-50%);
	width: calc(100% - 24px);
	max-width: 560px;
	z-index: 100;
	padding: 8px 12px;
	background: rgba(255, 255, 255, 0.95);
	backdrop-filter: blur(20px) saturate(180%);
	-webkit-backdrop-filter: blur(20px) saturate(180%);
	border-radius: 16px;
	border: 1px solid rgba(0, 0, 0, 0.08);
	box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 6px;
	box-sizing: border-box;
}
.answer-topbar-left { min-width: 0; flex: 1; display: flex; align-items: center; gap: 8px; }
.answer-topbar-course { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #1C1C1E; font-size: 14px; font-weight: 800; }

/* WebSocket 芯片（小型） */
.ws-chip { flex: 0 0 auto; height: 26px; box-sizing: border-box; padding: 0 10px; border-radius: 13px; display: flex; align-items: center; gap: 5px; background: #F2F2F7; border: 1px solid rgba(0,0,0,0.06); color: #1C1C1E; font-size: 11px; font-weight: 700; white-space: nowrap; }
.ws-chip-dot { width: 6px; height: 6px; border-radius: 50%; background: #8E8E93; }
.ws-chip.connecting .ws-chip-dot, .ws-chip.reconnecting .ws-chip-dot, .ws-chip.open .ws-chip-dot { background: #FF9F0A; animation: answerPulse 1.2s infinite; }
.ws-chip.ready { background: rgba(52, 199, 89, 0.12); color: #248A3D; border-color: rgba(52, 199, 89, 0.3); }
.ws-chip.ready .ws-chip-dot { background: #34C759; box-shadow: 0 0 6px rgba(52, 199, 89, 0.8); }
.ws-chip.error { background: rgba(255, 59, 48, 0.12); color: #D70015; border-color: rgba(255, 59, 48, 0.3); }
.ws-chip.error .ws-chip-dot { background: #FF3B30; }

/* 顶栏中的按钮组 */
.answer-topbar-actions { flex: 0 0 auto; display: flex; align-items: center; gap: 6px; }
.demo-courseware-btn { flex: 0 0 auto; height: 28px; line-height: 28px; padding: 0 10px; margin: 0; border-radius: 9px; font-size: 11px; font-weight: 700; background: rgba(10,132,255,0.1); color: #0A84FF; border: none; }
.demo-courseware-btn::after { border: none; }
.refresh-ws-btn { flex: 0 0 auto; width: 28px; height: 28px; line-height: 28px; padding: 0; margin: 0; border-radius: 50%; font-size: 14px; font-weight: 700; background: #F2F2F7; color: #1C1C1E; text-align: center; border: 1px solid rgba(0,0,0,0.06); }
.refresh-ws-btn::after { border: none; }
.refresh-ws-btn:active { background: #E5E5EA; transform: rotate(180deg); }
.monitor-toggle-btn { flex: 0 0 auto; height: 28px; line-height: 28px; padding: 0 12px; margin: 0; border-radius: 9px; font-size: 11px; font-weight: 700; background: linear-gradient(135deg, #0A84FF, #0056B3); color: #FFFFFF; box-shadow: 0 3px 10px rgba(10,132,255,0.3); }
.monitor-toggle-btn::after, .batch-answer-btn::after { border: none; }

/* 滚动区域（紧跟顶栏下方） */
.answer-scroll {
	height: 100vh;
	min-height: 400px;
	box-sizing: border-box;
	padding: calc(var(--status-bar-height, 0px) + 58px) 12px calc(115px + constant(safe-area-inset-bottom)) 12px;
	padding: calc(var(--status-bar-height, 0px) + 58px) 12px calc(115px + env(safe-area-inset-bottom)) 12px;
	max-width: 560px;
	margin: 0 auto;
}

/* iOS 科技美双重双嵌套按键架构 (Doppelrand & Nested Icon Badge) */
.ios-action-btn {
	height: 34px;
	padding: 0 12px;
	border-radius: 17px;
	display: flex;
	flex-direction: row;
	align-items: center;
	gap: 6px;
	transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
	cursor: pointer;
}
.ios-action-btn:active {
	transform: scale(0.94);
}
.pull-btn {
	background: linear-gradient(135deg, #0A84FF, #0056B3);
	box-shadow: 0 4px 12px rgba(10, 132, 255, 0.35);
}
.push-btn {
	background: linear-gradient(135deg, #34C759, #248A3D);
	box-shadow: 0 4px 12px rgba(52, 199, 89, 0.35);
}
.btn-icon-wrapper {
	width: 20px;
	height: 20px;
	border-radius: 10px;
	background: rgba(255, 255, 255, 0.22);
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}
.btn-text {
	font-size: 12px;
	font-weight: 700;
	color: #FFFFFF;
	letter-spacing: 0.2px;
	white-space: nowrap;
}

/* 题目信息条 */
.question-info-strip { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; margin-bottom: 10px; background: #FFFFFF; border-radius: 12px; border: 1px solid rgba(60,60,67,0.08); }
.question-info-left { display: flex; align-items: center; gap: 6px; min-width: 0; }
.question-type-tag { padding: 3px 7px; border-radius: 6px; background: #FF9F0A; color: #FFFFFF; font-size: 9px; font-weight: 800; flex: 0 0 auto; }
.question-info-id { color: #8E8E93; font-size: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.question-info-slide { color: #8E8E93; font-size: 10px; }

/* 倒计时 */
.countdown-pill { flex: 0 0 auto; min-width: 60px; padding: 4px 8px; box-sizing: border-box; border-radius: 10px; background: #EEF7FF; color: #0A84FF; display: flex; flex-direction: column; align-items: flex-end; }
.countdown-pill.urgent { background: #FFF2E5; color: #FF7A00; animation: countdownGlow 1s infinite; }
.countdown-pill.closed { background: #F2F2F7; color: #8E8E93; animation: none; }
.countdown-label { font-size: 8px; font-weight: 600; }
.countdown-value { font-size: 15px; line-height: 1; font-weight: 850; font-variant-numeric: tabular-nums; }

/* 课件封面（全宽铺满，点击可预览） */
.compact-slide { position: relative; width: 100%; height: 180px; overflow: hidden; border-radius: 14px; margin-bottom: 10px; background: #F2F2F7; border: 1px solid rgba(0,0,0,0.08); display: flex; justify-content: center; align-items: center; }
.compact-slide-img { width: 100%; height: 100%; }
.slide-preview-hint { position: absolute; right: 8px; bottom: 8px; padding: 4px 10px; border-radius: 8px; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); }
.slide-preview-hint text { color: #FFFFFF; font-size: 10px; font-weight: 700; }

/* 全屏课件预览 */
.slide-fullscreen-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999; background: rgba(0,0,0,0.95); display: flex; flex-direction: column; justify-content: center; align-items: center; }
.slide-fullscreen-img { width: 100%; height: 80vh; }
.slide-fullscreen-close { margin-top: 20px; }
.slide-fullscreen-close text { color: rgba(255,255,255,0.6); font-size: 13px; font-weight: 500; }

/* 题干卡片（独立于课件图片下方） */
.question-body-card { padding: 10px 12px; margin-bottom: 10px; background: #FFFFFF; border-radius: 12px; border-left: 3px solid #FF9F0A; }
.question-body-text { display: block; color: #1C1C1E; font-size: 13px; line-height: 1.5; font-weight: 600; }

/* 选项编辑区 */
.question-editor { padding: 12px; background: #FFFFFF; border-radius: 14px; margin-bottom: 10px; }
.rich-options-list { display: flex; flex-direction: column; gap: 8px; }
.rich-option { min-height: 44px; padding: 8px 10px; box-sizing: border-box; border: 1.5px solid #E5E5EA; border-radius: 12px; display: flex; align-items: center; gap: 9px; background: #FFFFFF; transition: transform 0.14s ease, border-color 0.14s ease, background 0.14s ease; }
.rich-option:active { transform: scale(0.985); }
.rich-option.selected { border-color: #FF9F0A; background: #FFF8ED; box-shadow: inset 0 0 0 0.5px #FF9F0A; }
.rich-option-key { width: 28px; height: 28px; flex: 0 0 28px; border-radius: 50%; background: #F2F2F7; color: #3A3A3C; display: flex; justify-content: center; align-items: center; font-size: 12px; font-weight: 800; }
.rich-option.selected .rich-option-key { background: #FF9F0A; color: #FFFFFF; }
.rich-option-value { min-width: 0; flex: 1; color: #1C1C1E; font-size: 13px; line-height: 1.4; }
.rich-option-check { width: 18px; height: 18px; flex: 0 0 18px; border-radius: 50%; background: #FF9F0A; color: #FFFFFF; display: flex; justify-content: center; align-items: center; font-size: 10px; font-weight: 900; opacity: 0; }
.rich-option.selected .rich-option-check { opacity: 1; }
.text-answer-zone { display: flex; flex-direction: column; gap: 8px; }
.fill-answer-row { display: flex; align-items: center; gap: 8px; }
.fill-number { width: 26px; height: 26px; flex: 0 0 26px; border-radius: 8px; background: #FF9F0A; color: #FFFFFF; display: flex; justify-content: center; align-items: center; font-size: 11px; font-weight: 800; }
.fill-input { height: 42px; flex: 1; padding: 0 12px; box-sizing: border-box; border-radius: 10px; background: #F2F2F7; color: #1C1C1E; font-size: 14px; }
.subjective-input { width: 100%; height: 100px; padding: 10px 12px; box-sizing: border-box; border-radius: 12px; background: #F2F2F7; color: #1C1C1E; font-size: 14px; line-height: 1.5; }
.submitted-tip { margin-top: 8px; padding: 7px 10px; border-radius: 8px; background: #EAF8EE; color: #248A3D; font-size: 11px; font-weight: 650; text-align: center; }
.batch-answer-btn { height: 46px; line-height: 46px; margin: 10px 0 0; border-radius: 13px; background: linear-gradient(135deg, #FF9F0A, #FF6B00); color: #FFFFFF; font-size: 14px; font-weight: 800; box-shadow: 0 5px 14px rgba(255,126,0,0.22); }
.batch-answer-btn[disabled] { background: #D1D1D6; color: #FFFFFF; box-shadow: none; opacity: 1; }
.waiting-question { padding: 40px 20px; display: flex; flex-direction: column; align-items: center; gap: 6px; background: #FFFFFF; border-radius: 14px; text-align: center; }
.waiting-question-title { color: #1C1C1E; font-size: 15px; font-weight: 750; }
.waiting-question-sub { max-width: 260px; color: #8E8E93; font-size: 11px; line-height: 1.5; }
.receiver-card { padding: 14px 12px; border-radius: 16px; }
.receiver-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0; }
.receiver-card-header.expanded { margin-bottom: 12px; }
.receiver-card-header > view:first-child { display: flex; flex-direction: column; gap: 3px; }
.receiver-count { color: #8E8E93; font-size: 10px; }
.receiver-header-actions { display: flex; align-items: center; gap: 8px; }
.receiver-select-all { padding: 5px 8px; border-radius: 7px; background: #FFF3E2; color: #FF7A00; font-size: 10px; font-weight: 700; }
.receiver-expand-arrow { color: #8E8E93; font-size: 18px; line-height: 1; transform: rotate(0deg); transition: transform 0.18s ease; }
.receiver-expand-arrow.expanded { transform: rotate(180deg); }
.receiver-item { min-height: 42px; }
.receiver-item.disabled { opacity: 0.5; }
.answer-avatar { background: #D1D1D6; transition: background 0.18s ease; }
.answer-avatar.checked { background: linear-gradient(135deg, #FF9F0A, #FF6B00); }
@keyframes answerPulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.58; transform: scale(0.8); } }
@keyframes countdownGlow { 0%, 100% { box-shadow: 0 0 0 rgba(255,126,0,0); } 50% { box-shadow: 0 0 0 4px rgba(255,126,0,0.08); } }

/* iOS 风格常驻炫彩长条胶囊底栏 */
.custom-tabbar {
	position: fixed;
	bottom: calc(16px + constant(safe-area-inset-bottom));
	bottom: calc(16px + env(safe-area-inset-bottom));
	left: 50%;
	transform: translateX(-50%);
	width: calc(100% - 24px);
	max-width: 480px;
	height: 64px;
	background: rgba(255, 255, 255, 0.95);
	backdrop-filter: blur(25px) saturate(180%);
	-webkit-backdrop-filter: blur(25px) saturate(180%);
	border: 1px solid rgba(255, 255, 255, 0.8);
	border-radius: 32px;
	box-shadow: 0 16px 40px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.04);
	display: flex;
	justify-content: space-around;
	align-items: center;
	z-index: 998;
	padding: 0 4px;
	box-sizing: border-box;
}
.tabbar-item {
	flex: 1;
	flex-shrink: 0;
	display: flex;
	justify-content: center;
	align-items: center;
	position: relative;
	transition: all 0.25s ease;
	padding: 0 2px;
}
.tabbar-pill {
	height: 40px;
	width: 95%;
	padding: 0 4px;
	border-radius: 20px;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 4px;
	color: #FFFFFF;
	transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.pill-home {
	background: linear-gradient(135deg, #0A84FF, #0056B3) !important;
	box-shadow: 0 4px 12px rgba(10, 132, 255, 0.35) !important;
}
.pill-answer {
	background: linear-gradient(135deg, #FF9500, #FF6B00) !important;
	box-shadow: 0 4px 12px rgba(255, 149, 0, 0.35) !important;
}
.pill-ai {
	background: linear-gradient(135deg, #BF5AF2, #5856D6) !important;
	box-shadow: 0 4px 12px rgba(191, 90, 242, 0.35) !important;
}
.tabbar-pill-text {
	font-size: 11px;
	font-weight: 700;
	color: #FFFFFF !important;
	white-space: nowrap;
	letter-spacing: 0.1px;
}
.tab-svg {
	display: block;
	stroke: #FFFFFF !important;
}
.tabbar-item:active {
	transform: scale(0.92);
}
.tabbar-item.active .tabbar-pill {
	transform: scale(1.06);
	box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28) !important;
	border: 2px solid #FFFFFF;
}
.tab-svg {
	display: block;
}
.tabbar-item.active .tab-svg {
	stroke: #FFFFFF !important;
}
.tabbar-badge {
	position: absolute;
	top: 4px;
	right: 12px;
	width: 7px;
	height: 7px;
	border-radius: 50%;
	background-color: #FF9500;
	box-shadow: 0 0 8px rgba(255, 149, 0, 0.9);
}
.pulse-orange {
	animation: iconPulse 1.2s infinite;
}
@keyframes iconPulse {
	0% { transform: scale(1); }
	50% { transform: scale(1.2); }
	100% { transform: scale(1); }
}
.ai-control-bar { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: #F2F2F7; border-bottom: 1px solid #E5E5EA; }
.ai-switch-wrap { display: flex; align-items: center; gap: 8px; }
.ai-switch-label { font-size: 14px; font-weight: 600; color: #1C1C1E; }
.ai-test-btn { height: 32px; background: #FFF; border: 1px solid #C7C7CC; color: #1C1C1E; font-size: 13px; font-weight: 600; border-radius: 16px; display: flex; justify-content: center; align-items: center; padding: 0 12px; margin: 0; }
.ai-test-btn::after { border: none; }
</style>
