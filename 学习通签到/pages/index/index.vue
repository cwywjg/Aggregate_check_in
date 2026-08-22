<template>
	<view class="container">
		<!-- 顶部 Apple 质感 Hero 区域 (经典赤红主题) -->
		<view class="hero">
			<view class="hero-bg-decoration"></view> 
			<view class="hero-content">
				<view class="hero-title-wrap">
					<text class="hero-title">学习通签到助手</text>
					<view class="hero-badge">PRO</view>
				</view>
				<view class="title-underline"></view>
				<view class="subtitle-wrapper">
					<text class="hero-subtitle">纯本地存储 · 零服务器依赖</text>
					<view class="author-tag" @click="showAuthorDialog = true">
						<text class="author-tag-text">作者寄语</text>
					</view>
				</view>
			</view>
		</view>

		<view class="content-wrapper">
			<!-- 首页高阶 Dashboard：本地数据 Metric 与 批量扫码旗舰 CTA -->
			<view class="dashboard-hero-grid">
				<!-- 左侧数据卡片 -->
				<view class="metric-card-dark">
					<view class="metric-card-top">
						<text class="metric-tag-label">TERMINALS</text>
						<view class="metric-tag-badge">
							<text class="metric-tag-badge-text">LOCAL</text>
						</view>
					</view>

					<view class="metric-card-bottom">
						<text class="metric-number">{{ accounts.length }}</text>
						<text class="metric-sublabel">本地隔离指纹终端</text>
					</view>
				</view>

				<!-- 右侧【批量扫码签到】旗舰 CTA 按钮 (赤红高光渐变) -->
				<view class="scan-cta-card-vibrant" @click="startBatchScan">
					<view class="scan-cta-top">
						<view class="scan-micro-pill">
							<view class="scan-pulse-dot"></view>
							<text class="scan-pill-text">BATCH SCANNER</text>
						</view>

						<view class="scan-badge">
							<text class="scan-badge-text">扫码</text>
						</view>
					</view>

					<view class="scan-cta-bottom">
						<text class="scan-cta-title">批量扫码签到</text>
						<view class="scan-cta-subtitle-row">
							<text class="scan-cta-subtitle">启动高能引擎</text>
							<text class="scan-cta-arrow">></text>
						</view>
					</view>
				</view>
			</view>

			<scroll-view scroll-y class="group-flow" :show-scrollbar="false">
				<!-- 设备终端主卡片 (始终有完整的 Apple 质感边框卡片外壳) -->
				<view class="card">
					<view class="card-header">
						<view class="card-header-left">
							<text class="card-title">设备终端</text>
							<text class="validity-refresh" :class="{ checking: accountValidityChecking }" @click="refreshAccountValidity(true)">
								{{ accountValidityChecking ? '校验中…' : '刷新有效性' }}
							</text>
						</view>
						<text class="card-count-text">共 {{ accounts.length }} 个账号</text>
					</view>

					<!-- 账号列表：紧凑子标签微胶囊展示 (含独立硬件设备伪装展示) -->
					<view class="terminals-list" v-if="accounts.length > 0">
						<view class="terminal-item" v-for="(acc, accIndex) in accounts" :key="accIndex">
							<view class="terminal-left">
								<view class="avatar-circle">
									{{ (acc.remark || acc.name || '学').charAt(0) }}
								</view>
								<view class="terminal-meta">
									<view class="t-name-row">
										<text class="t-name" @click="openEditRemarkModal(accIndex)">{{ acc.remark || acc.name || '未命名终端' }}</text>
										<text v-if="acc.name && acc.name !== acc.remark" class="t-name-alias">({{ acc.name }})</text>
										<text v-if="accountValidityChecking" class="status-checking">校验中</text>
										<text v-else-if="acc.expired" class="status-expired">已失效</text>
										<text v-else class="status-active">凭证有效</text>
									</view>
									
									<!-- 紧凑微标签流 (展示真实设备伪装) -->
									<view class="t-tags-row">
										<view class="t-sub-pill primary">
											<text class="pill-k">手机</text>
											<text class="pill-v">{{ acc.phone || '未绑定' }}</text>
										</view>
										<view class="t-sub-pill device-pill" v-if="acc.device?.marketingName">
											<text class="pill-k">机型</text>
											<text class="pill-v">{{ acc.device.marketingName }}</text>
										</view>
										<view class="t-sub-pill" v-if="acc.schoolname">
											<text class="pill-k">学校</text>
											<text class="pill-v">{{ acc.schoolname }}</text>
										</view>
										<view class="t-sub-pill" v-if="acc.uname">
											<text class="pill-k">学号</text>
											<text class="pill-v">{{ acc.uname }}</text>
										</view>
										<view class="t-sub-pill" v-if="acc.uid">
											<text class="pill-k">UID</text>
											<text class="pill-v">{{ acc.uid }}</text>
										</view>
									</view>
								</view>
							</view>

							<view class="terminal-right">
								<view class="t-btn-small edit" @click="openEditRemarkModal(accIndex)">
									<text>备注</text>
								</view>
								<view class="t-btn-small remove" @click="deleteAccount(accIndex)">
									<text>移除</text>
								</view>
							</view>
						</view>
					</view>

					<!-- 空状态提示 (账号列表为空时显示在卡片内部) -->
					<view class="empty-state-inner" v-else>
						<view class="empty-icon-circle">
							<text class="empty-icon-text">0</text>
						</view>
						<text class="empty-title">暂未添加学习通账号</text>
						<text class="empty-desc">添加账号后即可参与一键全自动批量扫码签到</text>
					</view>
					
					<!-- 添加新账号按钮：赤红质感虚线边框与高亮反馈 -->
					<view class="add-terminal-card-btn" @click="openLoginModal">
						<view class="add-circle">+</view>
						<text class="add-btn-text">添加新账号凭证</text>
					</view>
				</view>
				
				<view style="height: 60px;"></view>
			</scroll-view>
		</view>

		<!-- 登录与添加账号弹窗 (固定在屏幕舒适高度，彻底杜绝软键盘弹出导致的弹跳与上移) -->
		<view class="blur-mask" :class="{ 'mask-active': showLoginDialog }" @touchmove.stop.prevent>
			<view class="fixed-center-modal" v-if="showLoginDialog">
				<view class="sheet-header">
					<view class="sheet-title-group">
						<text class="sheet-title">{{ loginMode === 'sms' ? '验证码快捷登录' : '学习通密码登录' }}</text>
						<text class="sheet-subtitle">{{ loginMode === 'sms' ? '短信验证码登录并存入本地' : '输入手机号与密码登录并存入本地' }}</text>
					</view>
					<text class="sheet-close" @click="closeLoginModal">关闭</text>
				</view>
				
				<view class="sheet-body">
					<!-- 账号备注（必填） -->
					<view class="form-group">
						<text class="form-lbl">账号备注 (必填)</text>
						<input class="ios-input" placeholder="如：[室友] 张三" v-model="loginRemark" :adjust-position="false" :cursor-spacing="0" />
					</view>

					<!-- 手机号/账号 -->
					<view class="form-group">
						<text class="form-lbl">{{ loginMode === 'sms' ? '学习通绑定手机号' : '手机号 / 学号 / 账号' }}</text>
						<input class="ios-input" :type="loginMode === 'sms' ? 'number' : 'text'" maxlength="20" :placeholder="loginMode === 'sms' ? '请输入11位手机号' : '请输入登录账号'" v-model="loginUname" :adjust-position="false" :cursor-spacing="0" />
					</view>

					<!-- 密码输入项（仅在密码模式下展示） -->
					<view class="form-group" v-if="loginMode === 'password'">
						<text class="form-lbl">学习通登录密码</text>
						<input class="ios-input" password="true" placeholder="请输入学习通登录密码" v-model="loginPassword" :adjust-position="false" :cursor-spacing="0" />
					</view>

					<!-- 短信验证码（仅在短信模式下展示） -->
					<view class="form-group" v-if="loginMode === 'sms'">
						<text class="form-lbl">短信验证码</text>
						<view class="code-row">
							<input class="ios-input code-input" type="number" maxlength="6" placeholder="4-6 位验证码" v-model="loginSmsCode" :adjust-position="false" :cursor-spacing="0" />
							<button class="code-btn" :disabled="smsCountDown > 0 || !loginUname || smsSending" @click="sendSmsCode">
								{{ smsCountDown > 0 ? `${smsCountDown}s` : '获取验证码' }}
							</button>
						</view>
					</view>

					<!-- 登录方式切换 -->
					<view class="login-switch-row">
						<text v-if="loginMode === 'sms'" class="login-switch-link" @click="loginMode = 'password'">收不到验证码？试试密码登录</text>
						<text v-else class="login-switch-link" @click="loginMode = 'sms'">返回使用短信验证码登录</text>
					</view>

					<!-- 提交按键 (赤红质感) -->
					<button
						class="ios-btn vibrant"
						v-if="loginMode === 'sms' && loginSmsCode.length >= 4"
						@click="doSmsLogin"
					>
						完成登录并存入本地
					</button>
					<button
						class="ios-btn vibrant"
						v-else-if="loginMode === 'password' && loginPassword.trim().length > 0"
						@click="doPasswordLogin"
					>
						密码登录并存入本地
					</button>
				</view>
			</view>
		</view>

		<!-- 修改账号备注弹窗 -->
		<view class="blur-mask" :class="{ 'mask-active': showRemarkDialog }" @touchmove.stop.prevent>
			<view class="fixed-center-modal mini" v-if="showRemarkDialog">
				<view class="sheet-header">
					<text class="sheet-title">修改账号备注</text>
					<text class="sheet-close" @click="showRemarkDialog = false">取消</text>
				</view>
				<view class="sheet-body">
					<view class="form-group">
						<text class="form-lbl">新备注名称</text>
						<input class="ios-input" placeholder="输入新的备注名" v-model="editRemarkValue" :adjust-position="false" :cursor-spacing="0" />
					</view>
					<button class="ios-btn vibrant" @click="saveAccountRemark">保存修改</button>
				</view>
			</view>
		</view>

		<!-- 批量签到执行进度控制台 Shell 弹窗 (极简清爽黑客控制台，规整输出 + 智能打捞按键) -->
		<view class="blur-mask" :class="{ 'mask-active': showProgressDialog }" @touchmove.stop.prevent>
			<view class="shell-modal" v-if="showProgressDialog">
				<view class="shell-header">
					<view class="mac-dots">
						<view class="dot red"></view>
						<view class="dot yellow"></view>
						<view class="dot green"></view>
					</view>
					<text class="shell-title">学习通批量扫码签到引擎</text>
				</view>

				<view class="shell-body">
					<!-- 顶部状态指示栏 (赤红高光) -->
					<view class="shell-status-bar">
						<text class="shell-status-arrow">></text>
						<text class="shell-status-text">{{ progressMsg }}</text>
					</view>

					<!-- 日志滚动窗口 -->
					<scroll-view scroll-y class="shell-logs" :scroll-top="scrollTop">
						<view class="clean-log-row" v-for="(log, idx) in runLogs" :key="idx">
							<text class="c-time">{{ log.time }}</text>
							<text class="c-tag" :class="log.type">{{ log.tag }}</text>
							<text class="c-msg" :class="log.type">{{ log.text }}</text>
						</view>
					</scroll-view>
				</view>

				<!-- 底部操作栏：支持一键打捞未签上账号 -->
				<view class="shell-footer" v-if="isProgressFinished">
					<button class="shell-btn secondary" @click="showProgressDialog = false">关闭控制台</button>
					<button class="shell-btn salvage-btn" v-if="failedAccountList.length > 0" @click="startSalvageScan">
						🎯 扫新码打捞 (剩余 {{ failedAccountList.length }} 人)
					</button>
				</view>
			</view>
		</view>

		<!-- 作者寄语弹窗 -->
		<view class="blur-mask" :class="{ 'mask-active': showAuthorDialog }">
			<view class="fixed-center-modal author-modal" v-if="showAuthorDialog">
				<view class="sheet-header">
					<text class="sheet-title">致每一位使用者</text>
					<text class="sheet-close" @click="showAuthorDialog = false">关闭</text>
				</view>
				<view class="author-body">
					<text class="quote-mark">“</text>
					<scroll-view scroll-y class="author-scroll-view">
						<view class="author-text-container">
							<text class="paragraph">
								这是一个完全基于本地存储的学习通多账号助手。您的所有登录凭据只存储在当前设备的本地沙盒中，不会上传到任何服务器。
							</text>
							<text class="paragraph">
								每次打开 App 时，它会自动在本地帮您向官方服务器校验每个账号的有效性，助您轻松打理多账号批量签到。
							</text>
						</view>
						
						<view class="author-profile">
							<view class="author-meta">
								<text class="author-name">学习通签到助手 · 纯本地版</text>
								<text class="author-contact">100% 独立离线架构</text>
							</view>
						</view>
					</scroll-view>
				</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { onShow, onBackPress } from '@dcloudio/uni-app';

// ============================ 核心常量与配置 ============================
const STORAGE_KEY = 'xxt_accounts_data_v1';
const PASSPORT_API = 'https://passport2-api.chaoxing.com';
const SSO_API = 'https://sso.chaoxing.com';
const MOBILE_LEARN_API = 'https://mobilelearn.chaoxing.com';
const CAPTCHA_SALT = 'jsDyctOCnay7uotq';
const API_TIMEOUT = 5000;
const BATCH_CONCURRENCY = 16;

// 真实国内主流真实物理设备硬件指纹数据库 (覆盖小米/华为/vivo/OPPO/一加/荣耀/三星/魅族等 40+ 经典与最新主流旗舰)
const DEVICE_DATABASE = [
	// 小米 / 红米
	{ brand: 'Xiaomi', model: '23127PN0CC', marketingName: 'Xiaomi 14', androidVer: '14' },
	{ brand: 'Xiaomi', model: '24031PN0DC', marketingName: 'Xiaomi 14 Ultra', androidVer: '14' },
	{ brand: 'Xiaomi', model: '2211133C', marketingName: 'Xiaomi 13', androidVer: '13' },
	{ brand: 'Xiaomi', model: '2210132C', marketingName: 'Xiaomi 13 Pro', androidVer: '13' },
	{ brand: 'Xiaomi', model: '23117RK66C', marketingName: 'Redmi K70', androidVer: '14' },
	{ brand: 'Xiaomi', model: '23113RKC6C', marketingName: 'Redmi K70 Pro', androidVer: '14' },
	{ brand: 'Xiaomi', model: '24069RA21C', marketingName: 'Redmi Turbo 3', androidVer: '14' },
	{ brand: 'Xiaomi', model: '23090RA98C', marketingName: 'Redmi Note 13 Pro', androidVer: '13' },
	{ brand: 'Xiaomi', model: '22127RK46C', marketingName: 'Redmi K60', androidVer: '13' },
	// 华为
	{ brand: 'HUAWEI', model: 'ALN-AL00', marketingName: 'Mate 60 Pro', androidVer: '12' },
	{ brand: 'HUAWEI', model: 'ALN-AL10', marketingName: 'Mate 60', androidVer: '12' },
	{ brand: 'HUAWEI', model: 'BRA-AL00', marketingName: 'Pura 70', androidVer: '12' },
	{ brand: 'HUAWEI', model: 'HBP-AL00', marketingName: 'Pura 70 Pro', androidVer: '12' },
	{ brand: 'HUAWEI', model: 'CET-AL00', marketingName: 'Mate 50 Pro', androidVer: '12' },
	{ brand: 'HUAWEI', model: 'MNA-AL00', marketingName: 'P60 Pro', androidVer: '12' },
	{ brand: 'HUAWEI', model: 'FIN-AL60', marketingName: 'Nova 12 Pro', androidVer: '12' },
	// vivo / iQOO
	{ brand: 'vivo', model: 'V2309A', marketingName: 'vivo X100', androidVer: '14' },
	{ brand: 'vivo', model: 'V2324A', marketingName: 'vivo X100 Pro', androidVer: '14' },
	{ brand: 'vivo', model: 'V2241A', marketingName: 'vivo X90', androidVer: '13' },
	{ brand: 'vivo', model: 'V2329A', marketingName: 'iQOO Neo9', androidVer: '14' },
	{ brand: 'vivo', model: 'V2307A', marketingName: 'iQOO 12', androidVer: '14' },
	{ brand: 'vivo', model: 'V2338A', marketingName: 'iQOO Z9 Turbo', androidVer: '14' },
	{ brand: 'vivo', model: 'V2302A', marketingName: 'vivo S18', androidVer: '14' },
	// OPPO / 一加
	{ brand: 'OPPO', model: 'PHY110', marketingName: 'OPPO Find X7', androidVer: '14' },
	{ brand: 'OPPO', model: 'PGEM10', marketingName: 'OPPO Find X6 Pro', androidVer: '13' },
	{ brand: 'OPPO', model: 'PJG110', marketingName: 'OPPO Reno11', androidVer: '14' },
	{ brand: 'OPPO', model: 'PJD110', marketingName: 'OnePlus 12', androidVer: '14' },
	{ brand: 'OPPO', model: 'PJE110', marketingName: 'OnePlus Ace 3', androidVer: '14' },
	{ brand: 'OPPO', model: 'PHP110', marketingName: 'OnePlus Ace 2 Pro', androidVer: '13' },
	// 荣耀
	{ brand: 'HONOR', model: 'BVL-AN00', marketingName: 'HONOR Magic6', androidVer: '14' },
	{ brand: 'HONOR', model: 'BVL-AN16', marketingName: 'HONOR Magic6 Pro', androidVer: '14' },
	{ brand: 'HONOR', model: 'PGT-AN10', marketingName: 'HONOR Magic5 Pro', androidVer: '13' },
	{ brand: 'HONOR', model: 'MAA-AN00', marketingName: 'HONOR 100 Pro', androidVer: '13' },
	{ brand: 'HONOR', model: 'REP-AN00', marketingName: 'HONOR 90 Pro', androidVer: '13' },
	{ brand: 'HONOR', model: 'ELP-AN00', marketingName: 'HONOR 200', androidVer: '14' },
	// 三星 / 魅族
	{ brand: 'samsung', model: 'SM-S9280', marketingName: 'Galaxy S24 Ultra', androidVer: '14' },
	{ brand: 'samsung', model: 'SM-S9210', marketingName: 'Galaxy S24', androidVer: '14' },
	{ brand: 'samsung', model: 'SM-S9180', marketingName: 'Galaxy S23 Ultra', androidVer: '13' },
	{ brand: 'MEIZU', model: 'M468Q', marketingName: 'Meizu 21', androidVer: '14' }
];

const CHROME_VERSIONS = [
	'116.0.5845.163', '118.0.5993.111', '120.0.6099.144',
	'121.0.6167.164', '122.0.6261.90', '124.0.6367.113',
	'126.0.6478.133', '128.0.6613.88'
];

const BUILD_PREFIXES = [
	'UKQ1.230804', 'UKQ1.230924', 'UP1A.231005', 'UP1A.231105',
	'TP1A.220624', 'TP1A.220905', 'SKQ1.211006'
];

// 动态排列组合生成器 (理论组合空间超千万级，绝对零重复)
const generateChaoxingDeviceProfile = () => {
	const dev = DEVICE_DATABASE[Math.floor(Math.random() * DEVICE_DATABASE.length)];
	const chromeVer = CHROME_VERSIONS[Math.floor(Math.random() * CHROME_VERSIONS.length)];
	const buildPrefix = dev.brand === 'HUAWEI' 
		? `HUAWEI${dev.model}`
		: dev.brand === 'HONOR'
			? `HONOR${dev.model}`
			: `${BUILD_PREFIXES[Math.floor(Math.random() * BUILD_PREFIXES.length)]}.${String(Math.floor(Math.random() * 899) + 100).padStart(3, '0')}`;
	
	const appVer = '7.0.0';
	const appBuild = `109${Math.floor(Math.random() * 10) + 80}_${Math.floor(Math.random() * 50) + 320}`;
	
	const dalvikUa = `Dalvik/2.1.0 (Linux; U; Android ${dev.androidVer}; ${dev.model} Build/${buildPrefix}) (device:${dev.model}) Language/zh_CN_#Hans com.chaoxing.mobile/ChaoXingStudy_3_${appVer}_android_phone_${appBuild}`;
	
	const webUa = `Mozilla/5.0 (Linux; Android ${dev.androidVer}; ${dev.model} Build/${buildPrefix}; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/${chromeVer} Mobile Safari/537.36 com.chaoxing.mobile/ChaoXingStudy_3_${appVer}_android_phone_${appBuild}`;
	
	return {
		brand: dev.brand,
		model: dev.model,
		marketingName: dev.marketingName,
		androidVer: dev.androidVer,
		buildId: buildPrefix,
		dalvikUa: dalvikUa,
		webUa: webUa
	};
};

const DEFAULT_DEVICE = generateChaoxingDeviceProfile();

// ============================ 状态定义 ============================
const accounts = ref([]);
const accountValidityChecking = ref(false);
const showAuthorDialog = ref(false);

// 登录弹窗状态
const showLoginDialog = ref(false);
const loginMode = ref('sms'); // 'sms' | 'password'
const loginRemark = ref('');
const loginUname = ref('');
const loginPassword = ref('');
const loginSmsCode = ref('');
const smsCountDown = ref(0);
const smsSending = ref(false);
let smsTimer = null;

// 修改备注弹窗
const showRemarkDialog = ref(false);
const editRemarkIndex = ref(-1);
const editRemarkValue = ref('');

// 批量扫码进度与打捞队列
const showProgressDialog = ref(false);
const isProgressFinished = ref(false);
const progressMsg = ref('');
const runLogs = ref([]);
const scrollTop = ref(0);
const failedAccountList = ref([]); // 记录本次未成功的账号打捞队列

// ============================ 规整时间格式化与日志输出 ============================
const formatTime = () => {
	const d = new Date();
	const hh = String(d.getHours()).padStart(2, '0');
	const mm = String(d.getMinutes()).padStart(2, '0');
	const ss = String(d.getSeconds()).padStart(2, '0');
	return `${hh}:${mm}:${ss}`;
};

const addCleanLog = (tag, text, type = 'info') => {
	const time = formatTime();
	runLogs.value.push({ time, tag: `[${tag}]`, text, type });
	scrollTop.value = runLogs.value.length * 100;
};

// ============================ 纯 JS 标准 RFC1321 MD5 实现 (零依赖、100% 精确) ============================
function md5(str) {
	function safeAdd(x, y) {
		var lsw = (x & 0xffff) + (y & 0xffff);
		var msw = (x >> 16) + (y >> 16) + (lsw >> 16);
		return (msw << 16) | (lsw & 0xffff);
	}
	function bitRotateLeft(num, cnt) {
		return (num << cnt) | (num >>> (32 - cnt));
	}
	function md5cmn(q, a, b, x, s, t) {
		return safeAdd(bitRotateLeft(safeAdd(safeAdd(a, q), safeAdd(x, t)), s), b);
	}
	function md5ff(a, b, c, d, x, s, t) {
		return md5cmn((b & c) | (~b & d), a, b, x, s, t);
	}
	function md5gg(a, b, c, d, x, s, t) {
		return md5cmn((b & d) | (c & ~d), a, b, x, s, t);
	}
	function md5hh(a, b, c, d, x, s, t) {
		return md5cmn(b ^ c ^ d, a, b, x, s, t);
	}
	function md5ii(a, b, c, d, x, s, t) {
		return md5cmn(c ^ (b | ~d), a, b, x, s, t);
	}
	function binlMD5(x, len) {
		x[len >> 5] |= 0x80 << (len % 32);
		x[(((len + 64) >>> 9) << 4) + 14] = len;

		var i;
		var olda;
		var oldb;
		var oldc;
		var oldd;
		var a = 1732584193;
		var b = -271733879;
		var c = -1732584194;
		var d = 271733878;

		for (i = 0; i < x.length; i += 16) {
			olda = a;
			oldb = b;
			oldc = c;
			oldd = d;

			a = md5ff(a, b, c, d, x[i], 7, -680876936);
			d = md5ff(d, a, b, c, x[i + 1], 12, -389564586);
			c = md5ff(c, d, a, b, x[i + 2], 17, 606105819);
			b = md5ff(b, c, d, a, x[i + 3], 22, -1044525330);
			a = md5ff(a, b, c, d, x[i + 4], 7, -176418897);
			d = md5ff(d, a, b, c, x[i + 5], 12, 1200080426);
			c = md5ff(c, d, a, b, x[i + 6], 17, -1473231341);
			b = md5ff(b, c, d, a, x[i + 7], 22, -45705983);
			a = md5ff(a, b, c, d, x[i + 8], 7, 1770035416);
			d = md5ff(d, a, b, c, x[i + 9], 12, -1958414417);
			c = md5ff(c, d, a, b, x[i + 10], 17, -42063);
			b = md5ff(b, c, d, a, x[i + 11], 22, -1990404162);
			a = md5ff(a, b, c, d, x[i + 12], 7, 1804603682);
			d = md5ff(d, a, b, c, x[i + 13], 12, -40341101);
			c = md5ff(c, d, a, b, x[i + 14], 17, -1502002290);
			b = md5ff(b, c, d, a, x[i + 15], 22, 1236535329);

			a = md5gg(a, b, c, d, x[i + 1], 5, -165796510);
			d = md5gg(d, a, b, c, x[i + 6], 9, -1069501632);
			c = md5gg(c, d, a, b, x[i + 11], 14, 643717713);
			b = md5gg(b, c, d, a, x[i], 20, -373897302);
			a = md5gg(a, b, c, d, x[i + 5], 5, -701558691);
			d = md5gg(d, a, b, c, x[i + 10], 9, 38016083);
			c = md5gg(c, d, a, b, x[i + 15], 14, -660478335);
			b = md5gg(b, c, d, a, x[i + 4], 20, -405537848);
			a = md5gg(a, b, c, d, x[i + 9], 5, 568446438);
			d = md5gg(d, a, b, c, x[i + 14], 9, -1019803690);
			c = md5gg(c, d, a, b, x[i + 3], 14, -187363961);
			b = md5gg(b, c, d, a, x[i + 8], 20, 1163531501);
			a = md5gg(a, b, c, d, x[i + 13], 5, -1444681467);
			d = md5gg(d, a, b, c, x[i + 2], 9, -51403784);
			c = md5gg(c, d, a, b, x[i + 7], 14, 1735328473);
			b = md5gg(b, c, d, a, x[i + 12], 20, -1926607734);

			a = md5hh(a, b, c, d, x[i + 5], 4, -378558);
			d = md5hh(d, a, b, c, x[i + 8], 11, -2022574463);
			c = md5hh(c, d, a, b, x[i + 11], 16, 1839030562);
			b = md5hh(b, c, d, a, x[i + 14], 23, -35309556);
			a = md5hh(a, b, c, d, x[i + 1], 4, -1530992060);
			d = md5hh(d, a, b, c, x[i + 4], 11, 1272893353);
			c = md5hh(c, d, a, b, x[i + 7], 16, -155497632);
			b = md5hh(b, c, d, a, x[i + 10], 23, -1094730640);
			a = md5hh(a, b, c, d, x[i + 13], 4, 681279174);
			d = md5hh(d, a, b, c, x[i + 0], 11, -358537222);
			c = md5hh(c, d, a, b, x[i + 3], 16, -722521979);
			b = md5hh(b, c, d, a, x[i + 6], 23, 76029189);
			a = md5hh(a, b, c, d, x[i + 9], 4, -640364487);
			d = md5hh(d, a, b, c, x[i + 12], 11, -421815835);
			c = md5hh(c, d, a, b, x[i + 15], 16, 530742520);
			b = md5hh(b, c, d, a, x[i + 2], 23, -995338651);

			a = md5ii(a, b, c, d, x[i + 0], 6, -198630844);
			d = md5ii(d, a, b, c, x[i + 7], 10, 1126891415);
			c = md5ii(c, d, a, b, x[i + 14], 15, -1416354905);
			b = md5ii(b, c, d, a, x[i + 5], 21, -57434055);
			a = md5ii(a, b, c, d, x[i + 12], 6, 1700485571);
			d = md5ii(d, a, b, c, x[i + 3], 10, -1894986606);
			c = md5ii(c, d, a, b, x[i + 10], 15, -1051523);
			b = md5ii(b, c, d, a, x[i + 1], 21, -2054922799);
			a = md5ii(a, b, c, d, x[i + 8], 6, 1873313359);
			d = md5ii(d, a, b, c, x[i + 15], 10, -30611744);
			c = md5ii(c, d, a, b, x[i + 6], 15, -1560198380);
			b = md5ii(b, c, d, a, x[i + 13], 21, 1309151649);
			a = md5ii(a, b, c, d, x[i + 4], 6, -145523070);
			d = md5ii(d, a, b, c, x[i + 11], 10, -1120210379);
			c = md5ii(c, d, a, b, x[i + 2], 15, 718787259);
			b = md5ii(b, c, d, a, x[i + 9], 21, -343485551);

			a = safeAdd(a, olda);
			b = safeAdd(b, oldb);
			c = safeAdd(c, oldc);
			d = safeAdd(d, oldd);
		}
		return [a, b, c, d];
	}
	function rstr2binl(input) {
		var i;
		var output = [];
		output[(input.length >> 2) - 1] = undefined;
		for (i = 0; i < output.length; i += 1) {
			output[i] = 0;
		}
		var length8 = input.length * 8;
		for (i = 0; i < length8; i += 8) {
			output[i >> 5] |= (input.charCodeAt(i / 8) & 0xff) << (i % 32);
		}
		return output;
	}
	function binl2rstr(input) {
		var i;
		var output = '';
		var length32 = input.length * 32;
		for (i = 0; i < length32; i += 8) {
			output += String.fromCharCode((input[i >> 5] >>> (i % 32)) & 0xff);
		}
		return output;
	}
	function rstr2hex(input) {
		var hexTab = '0123456789abcdef';
		var output = '';
		var x;
		var i;
		for (i = 0; i < input.length; i += 1) {
			x = input.charCodeAt(i);
			output += hexTab.charAt((x >>> 4) & 0x0f) + hexTab.charAt(x & 0x0f);
		}
		return output;
	}
	function str2rstrUTF8(input) {
		return unescape(encodeURIComponent(input));
	}
	return rstr2hex(binl2rstr(binlMD5(rstr2binl(str2rstrUTF8(str)), str2rstrUTF8(str).length * 8)));
}

// ============================ Cookie 解析与工具函数 ============================
const safeJsonParse = (raw, fallback) => {
	if (typeof raw === 'object' && raw !== null) return raw;
	try {
		return JSON.parse(raw) ?? fallback;
	} catch (_) {
		return fallback;
	}
};

// 全场景健壮 Cookie 提取器 (兼容 Array of Objects, Array of Strings, Header 对象)
const extractCookies = (resOrCookies) => {
	if (!resOrCookies) return '';
	let map = {};
	
	const processCookieString = (str) => {
		if (!str || typeof str !== 'string') return;
		const parts = str.split(/,(?=\s*[\w-]+=)|;/);
		parts.forEach(part => {
			const match = part.match(/^\s*([^=;]+)=([^;]*)/);
			if (match) {
				const k = match[1].trim();
				const v = match[2].trim();
				if (k && !['path', 'domain', 'expires', 'max-age', 'httponly', 'samesite', 'secure', 'version'].includes(k.toLowerCase())) {
					map[k] = v;
				}
			}
		});
	};

	let raw = resOrCookies;
	if (typeof resOrCookies === 'object' && !Array.isArray(resOrCookies)) {
		if (resOrCookies.cookies) {
			raw = resOrCookies.cookies;
		} else if (resOrCookies.header) {
			raw = resOrCookies.header['Set-Cookie'] || resOrCookies.header['set-cookie'] || '';
		}
	}

	if (Array.isArray(raw)) {
		raw.forEach(item => {
			if (typeof item === 'string') {
				processCookieString(item);
			} else if (typeof item === 'object' && item !== null) {
				const k = item.name || item.key;
				const v = item.value;
				if (k && v) map[k] = v;
			}
		});
	} else if (typeof raw === 'string') {
		processCookieString(raw);
	}

	return Object.entries(map).map(([k, v]) => `${k}=${v}`).join('; ');
};

const persistAccountsLocally = () => {
	uni.setStorageSync(STORAGE_KEY, JSON.stringify(accounts.value));
};

// 纯 JS URL 参数解析器
const parseQuery = (str) => {
	let res = {};
	if (!str) return res;
	let query = str.indexOf('?') >= 0 ? str.split('?')[1] : str;
	query.split('&').forEach(pair => {
		if (!pair) return;
		let parts = pair.split('=');
		let k = decodeURIComponent(parts[0] || '').trim();
		let v = decodeURIComponent(parts[1] || '').trim();
		if (k) res[k] = v;
	});
	return res;
};

// 16 并发高效任务调度器
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

// ================== 本地账号有效性秒级检测 (SSO 权威认证接口) ==================
const verifyLocalAccounts = async (targets = accounts.value) => {
	if (!targets.length) return;
	accountValidityChecking.value = true;
	let needSave = false;

	// 并发向 SSO 官方鉴权中心同步状态 (携带各账号专属 Dalvik 独立指纹)
	await runBounded(targets, BATCH_CONCURRENCY, acc => new Promise((resolve) => {
		if (!acc.cookie) {
			acc.expired = true;
			needSave = true;
			resolve();
			return;
		}
		
		const dalvikUa = acc.device?.dalvikUa || DEFAULT_DEVICE.dalvikUa;
		
		uni.request({
			url: `${SSO_API}/apis/login/userLogin4Uname.do?_from=passport`,
			method: 'POST',
			timeout: API_TIMEOUT,
			header: {
				'cookie': acc.cookie,
				'user-agent': dalvikUa,
				'content-type': 'application/x-www-form-urlencoded'
			},
			success: (res) => {
				const parsed = safeJsonParse(res.data, {});
				const msg = parsed.msg;
				// 超星 SSO 鉴权成功标志：result===1 或 msg 内含有效用户信息对象
				const isValid = parsed.result === 1 || (typeof msg === 'object' && msg !== null && (Boolean(msg.uid) || Boolean(msg.name) || Boolean(msg.uname)));
				if (isValid) {
					if (acc.expired !== false) {
						acc.expired = false;
						needSave = true;
					}
					if (typeof msg === 'object' && msg !== null) {
						if (msg.name && !acc.name) acc.name = msg.name;
						if (msg.schoolname && !acc.schoolname) acc.schoolname = msg.schoolname;
						if (msg.uname && !acc.uname) acc.uname = msg.uname;
					}
				} else {
					if (acc.expired !== true) {
						acc.expired = true;
						needSave = true;
					}
				}
				resolve();
			},
			fail: () => {
				// 网络波动时不误判失效，保持原状态
				resolve();
			}
		});
	}));

	accountValidityChecking.value = false;
	if (needSave) {
		persistAccountsLocally();
	}
};

const refreshAccountValidity = async (manual = false) => {
	if (accounts.value.length === 0) return;
	if (manual) uni.showLoading({ title: '正在校验凭证…' });
	await verifyLocalAccounts();
	if (manual) {
		uni.hideLoading();
		uni.showToast({ title: '本地校验完成', icon: 'success' });
	}
};

// ================== 登录与添加账号 ==================
const resetLoginForm = () => {
	loginMode.value = 'sms';
	loginRemark.value = '';
	loginUname.value = '';
	loginSmsCode.value = '';
	loginPassword.value = '';
	smsSending.value = false;
	if (smsTimer) clearInterval(smsTimer);
	smsCountDown.value = 0;
};

const openLoginModal = () => {
	resetLoginForm();
	showLoginDialog.value = true;
};

const closeLoginModal = () => {
	showLoginDialog.value = false;
	resetLoginForm();
};

// 1. 发送短信验证码
const sendSmsCode = () => {
	if (smsSending.value) return;
	const phone = String(loginUname.value || '').trim();
	if (!/^1\d{10}$/.test(phone)) {
		uni.showToast({ title: '请输入有效的11位手机号', icon: 'none' });
		return;
	}

	smsSending.value = true;
	const timestamp = Date.now();
	const enc = md5(`${phone}${CAPTCHA_SALT}${timestamp}`);

	uni.showLoading({ title: '正在发送验证码...' });
	uni.request({
		url: `${PASSPORT_API}/api/sendcaptcha`,
		method: 'POST',
		timeout: API_TIMEOUT,
		header: {
			'user-agent': DEFAULT_DEVICE.dalvikUa,
			'content-type': 'application/x-www-form-urlencoded'
		},
		data: {
			to: phone,
			countrycode: '86',
			time: String(timestamp),
			enc: enc
		},
		success: (res) => {
			const resData = safeJsonParse(res.data, {});
			if (resData && resData.status === true) {
				smsCountDown.value = 60;
				if (smsTimer) clearInterval(smsTimer);
				smsTimer = setInterval(() => {
					smsCountDown.value--;
					if (smsCountDown.value <= 0) clearInterval(smsTimer);
				}, 1000);
				uni.showToast({ title: '短信验证码已发送', icon: 'success' });
			} else {
				uni.showToast({ title: resData?.mes || resData?.errorMsg || '短信验证码发送失败', icon: 'none' });
			}
		},
		fail: () => {
			uni.showToast({ title: '网关超时，可重试', icon: 'none' });
		},
		complete: () => {
			smsSending.value = false;
			uni.hideLoading();
		}
	});
};

// 2. 执行登录
const executeLoginRequest = (dataObj) => {
	uni.showLoading({ title: '正在登录认证...' });
	uni.request({
		url: `${PASSPORT_API}/v11/loginregister?cx_xxt_passport=json`,
		method: 'POST',
		timeout: API_TIMEOUT,
		header: {
			'user-agent': DEFAULT_DEVICE.dalvikUa,
			'content-type': 'application/x-www-form-urlencoded'
		},
		data: dataObj,
		success: (res) => {
			const resData = safeJsonParse(res.data, {});
			if (resData && (resData.status === true || resData.result === 1)) {
				let finalCookie = extractCookies(res);
				fetchSsoUserInfo(finalCookie, resData.url);
			} else {
				uni.hideLoading();
				uni.showModal({
					title: '登录失败',
					content: resData?.mes || resData?.errorMsg || '账号或验证码/密码错误',
					showCancel: false
				});
			}
		},
		fail: () => {
			uni.hideLoading();
			uni.showToast({ title: '网络异常，请重试', icon: 'none' });
		}
	});
};

const doSmsLogin = () => {
	if (!loginRemark.value.trim()) {
		uni.showToast({ title: '终端备注不可为空', icon: 'none' });
		return;
	}
	const phone = String(loginUname.value || '').trim();
	const code = String(loginSmsCode.value || '').trim();
	if (!/^1\d{10}$/.test(phone)) {
		uni.showToast({ title: '手机号格式错误', icon: 'none' });
		return;
	}
	if (!/^\d{4,6}$/.test(code)) {
		uni.showToast({ title: '请输入正确的验证码', icon: 'none' });
		return;
	}

	executeLoginRequest({
		uname: phone,
		code: code,
		loginType: '2',
		countrycode: '86',
		roleSelect: 'true'
	});
};

const doPasswordLogin = () => {
	if (!loginRemark.value.trim()) {
		uni.showToast({ title: '终端备注不可为空', icon: 'none' });
		return;
	}
	const uname = String(loginUname.value || '').trim();
	const pwd = String(loginPassword.value || '').trim();
	if (!uname) {
		uni.showToast({ title: '账号不能为空', icon: 'none' });
		return;
	}
	if (!pwd) {
		uni.showToast({ title: '密码不能为空', icon: 'none' });
		return;
	}

	executeLoginRequest({
		uname: uname,
		code: pwd,
		loginType: '1',
		countrycode: '86',
		roleSelect: 'true'
	});
};

const fetchSsoUserInfo = (cookieStr, ssoUrl) => {
	// 为新账号绑定专属随机物理硬件机型指纹
	const deviceProfile = generateChaoxingDeviceProfile();
	const targetUrl = ssoUrl || `${SSO_API}/apis/login/userLogin4Uname.do?_from=passport`;
	
	uni.request({
		url: targetUrl,
		method: 'POST',
		timeout: API_TIMEOUT,
		header: {
			'cookie': cookieStr,
			'user-agent': deviceProfile.dalvikUa,
			'content-type': 'application/x-www-form-urlencoded'
		},
		success: (res) => {
			uni.hideLoading();
			const parsed = safeJsonParse(res.data, {});
			const msg = parsed.msg || {};
			const uidMatch = cookieStr.match(/(?:UID|_uid)=([^;]+)/);
			const uid = String(msg.uid || msg.puid || (uidMatch ? uidMatch[1] : ''));

			const newAcc = {
				id: uid || ('acc_' + Date.now()),
				uid: uid,
				puid: String(msg.puid || uid || ''),
				name: msg.name || msg.nick || '学习通用户',
				remark: loginRemark.value.trim() || msg.name || '终端',
				schoolname: msg.schoolname || '未认证高校',
				uname: msg.uname || '',
				phone: msg.phone || (loginMode.value === 'sms' ? loginUname.value : ''),
				fid: String(msg.fid || msg.dxfid || ''),
				cookie: cookieStr,
				expired: false,
				device: deviceProfile, // 绑定专属独立设备指纹
				updated_at: new Date().toISOString()
			};

			let existIdx = accounts.value.findIndex(a => String(a.uid) === String(newAcc.uid) || (newAcc.phone && String(a.phone) === String(newAcc.phone)));
			if (existIdx >= 0) {
				accounts.value[existIdx] = { ...accounts.value[existIdx], ...newAcc, expired: false };
			} else {
				accounts.value.push(newAcc);
			}
			persistAccountsLocally();
			closeLoginModal();
			uni.showToast({ title: '账号挂载成功！', icon: 'success' });
		},
		fail: () => {
			uni.hideLoading();
			uni.showToast({ title: '拉取身份档案超时', icon: 'none' });
		}
	});
};

// ================== 修改备注与移除账号 ==================
const openEditRemarkModal = (index) => {
	editRemarkIndex.value = index;
	editRemarkValue.value = accounts.value[index].remark || accounts.value[index].name || '';
	showRemarkDialog.value = true;
};

const saveAccountRemark = () => {
	if (!editRemarkValue.value.trim()) {
		uni.showToast({ title: '备注不能为空', icon: 'none' });
		return;
	}
	if (editRemarkIndex.value >= 0 && editRemarkIndex.value < accounts.value.length) {
		accounts.value[editRemarkIndex.value].remark = editRemarkValue.value.trim();
		persistAccountsLocally();
		showRemarkDialog.value = false;
		uni.showToast({ title: '备注已更新', icon: 'success' });
	}
};

const deleteAccount = (index) => {
	uni.showModal({
		title: '确认移除账号',
		content: `确认从当前手机移除账号「${accounts.value[index].remark || accounts.value[index].name}」吗？`,
		success: (r) => {
			if (r.confirm) {
				accounts.value.splice(index, 1);
				persistAccountsLocally();
				uni.showToast({ title: '已成功移除', icon: 'none' });
			}
		}
	});
};

// ================== 精准解析签到响应结果 ==================
const extractSignResult = (html) => {
	if (!html) return { success: false, msg: '无响应内容' };

	// 1. 成功标识
	if (html.includes('zsign_success') || html.includes('签到成功') || html.includes('已成功签到')) {
		return { success: true, msg: '签到成功！' };
	}

	// 2. 提取 statuscontent 提示文本
	let match = html.match(/id=["']statuscontent["'][^>]*>([\s\S]*?)<\/h1>/i);
	if (match) {
		let text = match[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
		if (text) {
			let isSuccess = text.includes('已签到') || text.includes('您已签到过了');
			return { success: isSuccess, msg: text };
		}
	}

	// 3. 常见关键字
	if (html.includes('您已签到过了') || html.includes('已签到')) {
		return { success: true, msg: '此前已签到过' };
	}
	if (html.includes('已过老师设置的截止时间') || html.includes('下次早点来')) {
		return { success: false, msg: '签到已截止 (教师已结束签到)' };
	}
	if (html.includes('请在指定范围内签到') || html.includes('不在签到范围')) {
		return { success: false, msg: '签到受限: 需要指定 GPS 范围' };
	}
	if (html.includes('二维码已失效') || html.includes('二维码过期')) {
		return { success: false, msg: '二维码已失效 (可打捞)' };
	}
	if (html.includes('未加入该班级') || html.includes('未找到活动')) {
		return { success: false, msg: '未加入此班级课程' };
	}

	return { success: false, msg: '签到未通过' };
};

// ================== 二维码解析与批量签到 ==================
const parseQrText = (rawText) => {
	const text = String(rawText || '').trim();
	let params = {};
	if (text.includes('http')) {
		let qs = parseQuery(text);
		params.id = qs.id || qs.activePrimaryId || qs.aid || '';
		params.enc = qs.enc || '';
		params.c = qs.c || qs.Code || '';
	} else if (text.includes('SIGNIN:')) {
		let clean = text.replace('SIGNIN:', '');
		let qs = parseQuery(clean);
		params.id = qs.aid || qs.id || '';
		params.enc = qs.enc || '';
		params.c = qs.Code || qs.c || '';
	} else {
		let aidMatch = text.match(/(?:id|aid|activePrimaryId)=(\d+)/);
		let encMatch = text.match(/enc=([A-Fa-f0-9]+)/);
		let cMatch = text.match(/(?:c|Code)=(\w+)/);
		if (aidMatch) params.id = aidMatch[1];
		if (encMatch) params.enc = encMatch[1];
		if (cMatch) params.c = cMatch[1];
	}
	return params;
};

// 发起普通全量扫码
const startBatchScan = () => {
	if (accounts.value.length === 0) {
		uni.showToast({ title: '请先添加学习通账号', icon: 'none' });
		return;
	}

	uni.scanCode({
		scanType: ['qrCode'],
		success: (res) => {
			if (res.result) {
				doBatchSign(res.result, null);
			}
		},
		fail: () => {
			// 用户取消扫码
		}
	});
};

// 发起精准打捞扫码（仅针对上一轮未签成功的账号）
const startSalvageScan = () => {
	if (failedAccountList.value.length === 0) {
		uni.showToast({ title: '暂无待打捞账号', icon: 'none' });
		return;
	}

	uni.scanCode({
		scanType: ['qrCode'],
		success: (res) => {
			if (res.result) {
				doBatchSign(res.result, [...failedAccountList.value]);
			}
		},
		fail: () => {
			// 用户取消扫码
		}
	});
};

// 核心批量/打捞签到执行器 (0 延时全速并发)
const doBatchSign = async (qrContent, specificTargetAccounts = null) => {
	showProgressDialog.value = true;
	isProgressFinished.value = false;
	runLogs.value = [];

	const isSalvageMode = Array.isArray(specificTargetAccounts) && specificTargetAccounts.length > 0;
	progressMsg.value = isSalvageMode ? '正在启动精准打捞协议…' : '正在解析二维码并启动引擎…';

	const signParams = parseQrText(qrContent);
	if (!signParams.id || !signParams.enc) {
		addCleanLog('系统', '无法识别出有效的签到 ID 与 enc 签名', 'bad');
		progressMsg.value = '解析失败：非有效签到二维码';
		isProgressFinished.value = true;
		return;
	}

	addCleanLog('系统', `识别到签到活动 ID: ${signParams.id}`, 'info');

	// 确定执行账号列表
	const targetAccounts = isSalvageMode
		? specificTargetAccounts.filter(a => !a.expired && a.cookie)
		: accounts.value.filter(a => !a.expired && a.cookie);

	if (targetAccounts.length === 0) {
		addCleanLog('系统', '无可执行的有效账号', 'bad');
		progressMsg.value = '暂无可用的有效账号';
		isProgressFinished.value = true;
		return;
	}

	if (isSalvageMode) {
		addCleanLog('系统', `🎯 正在为未成功的 ${targetAccounts.length} 个终端注入最新签名…`, 'info');
	} else {
		addCleanLog('系统', `⚡ 正在调度 ${targetAccounts.length} 个终端并发执行 (独立硬件伪装)…`, 'info');
	}

	let successCount = 0;
	let newFailedAccounts = [];

	const signUrl = `${MOBILE_LEARN_API}/widget/sign/e?id=${signParams.id}&c=${signParams.c || ''}&enc=${signParams.enc}&DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=id`;

	// 16 线程高并发 + 独立物理设备指纹 (0 延时全速并发)
	await runBounded(targetAccounts, BATCH_CONCURRENCY, async (acc, index) => {
		const name = acc.remark || acc.name || `账号${index + 1}`;
		progressMsg.value = `正在为 [${name}] 提交签到 (${index + 1}/${targetAccounts.length})`;

		// 提取该账号绑定的专属原生 Webview UA
		const webUa = acc.device?.webUa || DEFAULT_DEVICE.webUa;

		try {
			const res = await new Promise((resolve) => {
				uni.request({
					url: signUrl,
					method: 'GET',
					timeout: 8000,
					header: {
						'cookie': acc.cookie,
						'user-agent': webUa,
						'x-requested-with': 'com.chaoxing.mobile',
						'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
						'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
						'Upgrade-Insecure-Requests': '1'
					},
					success: r => resolve(r),
					fail: e => resolve({ fail: true, error: e })
				});
			});

			const body = typeof res?.data === 'string' ? res.data : JSON.stringify(res?.data || '');
			const outcome = extractSignResult(body);

			if (outcome.success) {
				successCount++;
				addCleanLog(name, outcome.msg, 'good');
			} else {
				newFailedAccounts.push(acc);
				addCleanLog(name, outcome.msg, 'bad');
			}
		} catch (err) {
			newFailedAccounts.push(acc);
			addCleanLog(name, `请求异常: ${err?.message || err}`, 'bad');
		}
	});

	// 更新打捞队列
	failedAccountList.value = newFailedAccounts;

	if (newFailedAccounts.length === 0) {
		progressMsg.value = `全部 ${targetAccounts.length} 人签到成功！`;
		addCleanLog('系统', `✅ 全员签到圆满完成 (成功率 100%)`, 'good');
	} else {
		progressMsg.value = `执行完毕：成功 ${successCount}，失败 ${newFailedAccounts.length} (剩余可打捞)`;
		addCleanLog('系统', `⚠️ 尚有 ${newFailedAccounts.length} 个账号未成功，点击下方按钮待老师二维码刷新后一键打捞`, 'bad');
	}

	isProgressFinished.value = true;
};

// ================== 生命周期与事件监听 ==================
onMounted(() => {
	try {
		const saved = uni.getStorageSync(STORAGE_KEY);
		if (saved) {
			const list = safeJsonParse(saved, []);
			let needUpdateStorage = false;
			// 自动为旧版没有设备指纹的账号补充独立硬件设备指纹
			accounts.value = (Array.isArray(list) ? list : []).map(acc => {
				if (!acc.device || !acc.device.dalvikUa) {
					acc.device = generateChaoxingDeviceProfile();
					needUpdateStorage = true;
				}
				return acc;
			});
			if (needUpdateStorage) {
				persistAccountsLocally();
			}
		}
		refreshAccountValidity(false);
	} catch (e) {
		console.error('onMounted error:', e);
	}
});

onShow(() => {
	try {
		refreshAccountValidity(false);
	} catch (e) {}
});

onUnmounted(() => {
	if (smsTimer) clearInterval(smsTimer);
});

onBackPress(() => {
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
	if (showRemarkDialog.value) {
		showRemarkDialog.value = false;
		return true;
	}
	return false;
});
</script>

<style>
/* ================== Apple UI / 经典赤红主题设计 ================== */
page { background-color: #F2F2F7; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; }
.container { padding: 0; min-height: 100vh; box-sizing: border-box; }

/* 顶部 Hero 区域 */
.hero { position: relative; padding: calc(32px + var(--status-bar-height, 0px)) 20px 24px 20px; background: #FFFFFF; box-shadow: 0 16px 40px rgba(44, 62, 80, 0.04); overflow: hidden; margin-bottom: 16px; }
.hero-bg-decoration { position: absolute; top: -40px; right: -20px; width: 180px; height: 180px; background: radial-gradient(circle, rgba(255, 59, 48, 0.08) 0%, rgba(255, 59, 48, 0) 70%); border-radius: 50%; z-index: 1; }
.hero-content { position: relative; z-index: 2; max-width: 560px; margin: 0 auto; }
.hero-title-wrap { display: flex; align-items: center; gap: 12px; }
.hero-title { font-size: 32px; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(90deg, #1C1C1E 0%, #3A3A3C 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; color: transparent; }
.hero-badge { background: linear-gradient(135deg, #FF3B30 0%, #D70015 100%); color: #FFFFFF; font-size: 13px; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-style: italic; box-shadow: 0 6px 12px rgba(255, 59, 48, 0.25), inset 0 1px 1px rgba(255, 255, 255, 0.4); letter-spacing: 0.5px; }
.title-underline { width: 44px; height: 5px; background: linear-gradient(90deg, #FF3B30 0%, #FF6482 100%); border-radius: 3px; margin-top: 14px; margin-bottom: 14px; }
.subtitle-wrapper { display: flex; justify-content: space-between; align-items: center; }
.hero-subtitle { font-size: 14px; color: #A1A1A6; font-weight: 400; letter-spacing: 2.5px; display: block; }
.author-tag { display: flex; align-items: center; justify-content: center; padding: 5px 12px; background: rgba(255, 59, 48, 0.08); border: 0.5px solid rgba(255, 59, 48, 0.25); border-radius: 12px; cursor: pointer; }
.author-tag-text { font-size: 11px; font-weight: 700; color: #FF3B30; letter-spacing: 0.3px; }

.content-wrapper { padding: 0 16px calc(40px + env(safe-area-inset-bottom)) 16px; box-sizing: border-box; width: 100%; max-width: 560px; margin: 0 auto; }

/* Dashboard 旗舰网格 */
.dashboard-hero-grid { display: flex; flex-direction: row; gap: 12px; margin-bottom: 16px; }

.metric-card-dark {
	flex: 1;
	background: linear-gradient(135deg, #1C1C1E, #2C2C2E);
	border-radius: 20px;
	padding: 14px 16px;
	border: 1px solid rgba(255,255,255,0.1);
	box-shadow: 0 8px 24px rgba(0,0,0,0.12);
	display: flex;
	flex-direction: column;
	justify-content: space-between;
}
.metric-card-top { display: flex; flex-direction: row; justify-content: space-between; align-items: center; }
.metric-tag-label { font-size: 10px; font-weight: 800; color: rgba(255,255,255,0.6); letter-spacing: 0.8px; }
.metric-tag-badge { padding: 2px 6px; border-radius: 6px; background: rgba(255,255,255,0.12); }
.metric-tag-badge-text { font-size: 9px; color: #FFF; font-weight: 700; }
.metric-card-bottom { margin-top: 10px; }
.metric-number { font-size: 32px; font-weight: 900; color: #FFFFFF; font-family: monospace; letter-spacing: -1px; line-height: 1; display: block; }
.metric-sublabel { font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 6px; display: block; font-weight: 600; }

.scan-cta-card-vibrant {
	flex: 1.6;
	background: linear-gradient(135deg, #FF3B30 0%, #D70015 100%);
	border-radius: 20px;
	padding: 14px 16px;
	box-shadow: 0 10px 28px rgba(255, 59, 48, 0.4);
	display: flex;
	flex-direction: column;
	justify-content: space-between;
	cursor: pointer;
}
.scan-cta-card-vibrant:active { transform: scale(0.98); }
.scan-cta-top { display: flex; flex-direction: row; justify-content: space-between; align-items: center; }
.scan-micro-pill { display: flex; flex-direction: row; align-items: center; gap: 4px; background: rgba(255,255,255,0.22); padding: 3px 8px; border-radius: 10px; backdrop-filter: blur(10px); }
.scan-pulse-dot { width: 5px; height: 5px; border-radius: 50%; background: #FFFFFF; box-shadow: 0 0 6px #FFF; }
.scan-pill-text { font-size: 9px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px; }
.scan-badge { padding: 3px 8px; border-radius: 12px; background: rgba(255, 255, 255, 0.25); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(10px); }
.scan-badge-text { font-size: 10px; font-weight: 800; color: #FFFFFF; }
.scan-cta-bottom { margin-top: 12px; }
.scan-cta-title { font-size: 18px; font-weight: 900; color: #FFFFFF; letter-spacing: -0.3px; display: block; line-height: 1.2; }
.scan-cta-subtitle-row { display: flex; flex-direction: row; align-items: center; gap: 4px; margin-top: 6px; }
.scan-cta-subtitle { font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.95); }
.scan-cta-arrow { font-size: 12px; font-weight: 900; color: #FFFFFF; line-height: 1; }

.group-flow { height: auto; }

/* 主卡片：始终具备清晰的 Apple 质感外框与投影 */
.card {
	background: #FFFFFF;
	border-radius: 24px;
	padding: 20px;
	margin-bottom: 20px;
	box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
	border: 1px solid rgba(0, 0, 0, 0.04);
}
.card-header { display: flex; flex-direction: row; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 16px; }
.card-header-left { display: flex; flex-direction: row; align-items: center; gap: 8px; }
.card-title { font-size: 18px; font-weight: 800; color: #1C1C1E; }
.validity-refresh { color: #FF3B30; font-size: 11px; font-weight: 700; background: rgba(255, 59, 48, 0.08); padding: 4px 10px; border-radius: 8px; cursor: pointer; }
.validity-refresh.checking { color: #8E8E93; }
.card-count-text { font-size: 12px; color: #8E8E93; font-weight: 600; }

/* 账号列表 */
.terminals-list { display: flex; flex-direction: column; gap: 8px; }
.terminal-item {
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: center;
	padding: 10px 0;
	border-bottom: 1px solid #F2F2F7;
}
.terminal-item:last-child { border-bottom: none; }
.terminal-left { flex: 1; min-width: 0; display: flex; flex-direction: row; align-items: flex-start; gap: 10px; margin-right: 8px; }
.avatar-circle {
	width: 36px;
	height: 36px;
	border-radius: 18px;
	background: linear-gradient(135deg, #FF3B30, #D70015);
	color: #FFFFFF;
	font-size: 15px;
	font-weight: 800;
	display: flex;
	justify-content: center;
	align-items: center;
	text-transform: uppercase;
	flex-shrink: 0;
	margin-top: 2px;
	box-shadow: 0 2px 6px rgba(255, 59, 48, 0.25);
}
.terminal-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.t-name-row { display: flex; flex-direction: row; align-items: center; gap: 6px; flex-wrap: wrap; }
.t-name { font-size: 14px; font-weight: 800; color: #1C1C1E; }
.t-name-alias { font-size: 11px; color: #8E8E93; font-weight: 600; }
.status-expired { font-size: 9px; background: #FFEBEB; color: #FF3B30; padding: 1.5px 5px; border-radius: 4px; font-weight: bold; }
.status-active { font-size: 9px; background: #E5F9ED; color: #34C759; padding: 1.5px 5px; border-radius: 4px; font-weight: bold; }
.status-checking { font-size: 9px; background: #FFF0F0; color: #FF3B30; padding: 1.5px 5px; border-radius: 4px; font-weight: bold; }

/* 紧凑子标签流 (展示真实设备伪装) */
.t-tags-row { display: flex; flex-direction: row; flex-wrap: wrap; gap: 4px 6px; align-items: center; }
.t-sub-pill { display: flex; flex-direction: row; align-items: center; gap: 3px; background: #F2F2F7; padding: 2px 6px; border-radius: 4px; border: 0.5px solid rgba(0, 0, 0, 0.04); }
.t-sub-pill.primary { background: rgba(255, 59, 48, 0.06); border: 0.5px solid rgba(255, 59, 48, 0.15); }
.t-sub-pill.device-pill { background: rgba(0, 122, 255, 0.06); border: 0.5px solid rgba(0, 122, 255, 0.15); }
.t-sub-pill.device-pill .pill-k { color: #007AFF; }
.t-sub-pill.device-pill .pill-v { color: #007AFF; font-weight: 700; }
.pill-k { font-size: 9.5px; font-weight: 600; color: #8E8E93; }
.t-sub-pill.primary .pill-k { color: #FF3B30; }
.pill-v { font-size: 10.5px; font-weight: 600; color: #3A3A3C; }
.t-sub-pill.primary .pill-v { color: #FF3B30; font-weight: 700; }

.terminal-right { display: flex; flex-direction: row; align-items: center; gap: 6px; flex-shrink: 0; }
.t-btn-small { padding: 4px 8px; border-radius: 6px; cursor: pointer; }
.t-btn-small.edit { background: rgba(255, 59, 48, 0.08); border: 0.5px solid rgba(255, 59, 48, 0.2); }
.t-btn-small.edit text { font-size: 11px; font-weight: 700; color: #FF3B30; white-space: nowrap; }
.t-btn-small.remove { background: rgba(142, 142, 147, 0.1); border: 0.5px solid rgba(142, 142, 147, 0.2); }
.t-btn-small.remove text { font-size: 11px; font-weight: 700; color: #8E8E93; white-space: nowrap; }

/* 卡片内部空状态 */
.empty-state-inner { text-align: center; padding: 24px 0 16px 0; display: flex; flex-direction: column; align-items: center; }
.empty-icon-circle { width: 44px; height: 44px; border-radius: 22px; background: #F2F2F7; display: flex; justify-content: center; align-items: center; margin-bottom: 10px; }
.empty-icon-text { font-size: 16px; font-weight: 800; color: #8E8E93; }
.empty-title { font-size: 16px; font-weight: 700; color: #1C1C1E; margin-bottom: 4px; }
.empty-desc { font-size: 12px; color: #8E8E93; }

/* 添加账号按钮：赤红质感边框卡片形态 */
.add-terminal-card-btn {
	margin-top: 14px;
	padding: 14px 16px;
	border-radius: 16px;
	border: 1.5px dashed #FF3B30;
	background: rgba(255, 59, 48, 0.05);
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: center;
	gap: 10px;
	cursor: pointer;
	box-sizing: border-box;
}
.add-terminal-card-btn:active {
	background: rgba(255, 59, 48, 0.15);
	transform: scale(0.99);
}
.add-circle {
	width: 26px;
	height: 26px;
	border-radius: 13px;
	background: #FF3B30;
	color: #FFFFFF;
	font-weight: 800;
	display: flex;
	justify-content: center;
	align-items: center;
	font-size: 16px;
	box-shadow: 0 3px 8px rgba(255, 59, 48, 0.35);
}
.add-btn-text { font-size: 14px; color: #FF3B30; font-weight: 700; letter-spacing: 0.2px; }

/* ================== 弹窗系统：固定顶部距离，杜绝软键盘弹出时向上晃动/上移 ================== */
.blur-mask {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.55);
	backdrop-filter: blur(14px);
	-webkit-backdrop-filter: blur(14px);
	z-index: 9999;
	opacity: 0;
	pointer-events: none;
	transition: opacity 0.2s ease;
}
.blur-mask.mask-active {
	opacity: 1;
	pointer-events: auto;
}

/* 固定在顶部适中高度，无论软键盘如何呼出，绝对保持固定位置，零位移、零晃动 */
.fixed-center-modal {
	position: fixed;
	top: 110px;
	left: 5%;
	right: 5%;
	max-width: 380px;
	margin: 0 auto;
	background: #FFFFFF;
	border-radius: 24px;
	padding: 24px 20px;
	box-sizing: border-box;
	box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
	border: 1px solid rgba(255, 255, 255, 0.8);
	overflow-y: auto;
	z-index: 10000;
}
.fixed-center-modal.mini { max-width: 340px; top: 140px; }
.fixed-center-modal.author-modal { top: 100px; max-height: 75vh; }

.sheet-header { display: flex; flex-direction: row; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.sheet-title-group { display: flex; flex-direction: column; }
.sheet-title { font-size: 20px; font-weight: 800; color: #1C1C1E; }
.sheet-subtitle { font-size: 11px; color: #8E8E93; margin-top: 2px; }
.sheet-close { font-size: 15px; font-weight: 600; color: #FF3B30; cursor: pointer; padding: 4px; }
.ios-input { background: #F2F2F7; height: 48px; border-radius: 12px; padding: 0 16px; font-size: 15px; color: #1C1C1E; }
.ios-btn { height: 50px; border-radius: 14px; font-size: 16px; font-weight: 700; display: flex; justify-content: center; align-items: center; margin-top: 22px; border: none; }
.ios-btn.vibrant { background: linear-gradient(135deg, #FF3B30, #D70015); color: #FFF; box-shadow: 0 6px 16px rgba(255, 59, 48, 0.35); }
.ios-btn.vibrant::after { border: none; }
.form-group { margin-bottom: 14px; }
.form-lbl { font-size: 12.5px; font-weight: 700; color: #8E8E93; margin-bottom: 6px; display: block; text-transform: uppercase; }
.code-row { display: flex; gap: 10px; }
.code-input { flex: 1; }
.code-btn { width: 110px; height: 48px; background: #E5E5EA; color: #1C1C1E; font-size: 13px; font-weight: 700; border-radius: 12px; line-height: 48px; padding: 0; border: none; }
.code-btn::after { border: none; }
.login-switch-row { display: flex; justify-content: flex-end; align-items: center; margin-top: 8px; }
.login-switch-link { font-size: 12px; font-weight: 600; color: #FF3B30; cursor: pointer; padding: 2px 0; }

/* ================== 批量扫码 Shell 控制台 (赤红排版 + 打捞按键) ================== */
.shell-modal {
	position: fixed;
	top: 50%;
	left: 50%;
	transform: translate(-50%, -50%);
	width: 92%;
	max-width: 400px;
	background: #1C1C1E;
	border-radius: 20px;
	padding: 16px;
	box-shadow: 0 28px 70px rgba(0, 0, 0, 0.6);
	border: 1px solid rgba(255, 255, 255, 0.12);
	box-sizing: border-box;
	z-index: 10000;
}
.shell-header { display: flex; flex-direction: row; align-items: center; margin-bottom: 12px; }
.mac-dots { display: flex; flex-direction: row; gap: 6px; margin-right: 12px; }
.dot { width: 11px; height: 11px; border-radius: 50%; }
.dot.red { background: #FF5F56; } .dot.yellow { background: #FFBD2E; } .dot.green { background: #27C93F; }
.shell-title { font-size: 12px; color: #A1A1A6; font-weight: 600; font-family: monospace; letter-spacing: 0.5px; }

.shell-body { background: #000000; border-radius: 12px; padding: 12px 14px; border: 1px solid rgba(255, 255, 255, 0.06); }
.shell-status-bar { display: flex; flex-direction: row; align-items: center; gap: 6px; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.shell-status-arrow { color: #FF453A; font-family: monospace; font-size: 13px; font-weight: 900; }
.shell-status-text { color: #FF453A; font-family: monospace; font-size: 12px; font-weight: 700; flex: 1; }

.shell-logs { height: 230px; }

/* 规整的单行日志排版 */
.clean-log-row {
	display: flex;
	flex-direction: row;
	align-items: flex-start;
	gap: 6px;
	margin-bottom: 6px;
	font-family: -apple-system, monospace, "Courier New";
	font-size: 11.5px;
	line-height: 1.4;
}
.c-time { color: #636366; flex-shrink: 0; font-size: 10.5px; }
.c-tag { font-weight: 700; flex-shrink: 0; }
.c-tag.info { color: #FF9F0A; }
.c-tag.good { color: #30D158; }
.c-tag.bad { color: #FF453A; }
.c-msg { flex: 1; word-break: break-all; }
.c-msg.info { color: #E5E5EA; }
.c-msg.good { color: #30D158; font-weight: 600; }
.c-msg.bad { color: #FF453A; }

.shell-footer { display: flex; flex-direction: row; gap: 10px; justify-content: center; margin-top: 14px; }
.shell-btn { height: 40px; line-height: 40px; color: #FFF; font-size: 12.5px; border-radius: 20px; font-weight: 700; padding: 0 16px; border: none; flex: 1; text-align: center; }
.shell-btn::after { border: none; }
.shell-btn.secondary { background: rgba(255, 255, 255, 0.14); }
.shell-btn.salvage-btn { background: linear-gradient(135deg, #FF3B30 0%, #D70015 100%); box-shadow: 0 4px 14px rgba(255, 59, 48, 0.5); flex: 1.5; }

/* 寄语样式 */
.author-body { padding: 10px 10px 30px 10px; position: relative; overflow: hidden; }
.quote-mark { font-size: 80px; color: rgba(255, 59, 48, 0.08); font-family: Georgia, serif; position: absolute; top: -20px; left: -10px; line-height: 1; z-index: 0; }
.author-scroll-view { max-height: 60vh; width: 100%; }
.author-text-container { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 16px; }
.paragraph { font-size: 14.5px; color: #3A3A3C; line-height: 2.0; letter-spacing: 1px; font-weight: 400; text-align: justify; }
.author-profile { position: relative; z-index: 1; margin-top: 30px; display: flex; justify-content: flex-end; align-items: center; }
.author-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.author-name { font-size: 13px; color: #1C1C1E; font-weight: 700; font-style: italic; }
.author-contact { font-size: 10.5px; color: #8E8E93; font-family: monospace; }
</style>
