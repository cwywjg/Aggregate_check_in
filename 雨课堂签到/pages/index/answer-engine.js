import { computed, onUnmounted, ref } from 'vue';
import { extractLessonMetadata, extractPresentationFrame, resolveOfficialWebSocketUrl } from './answer-engine-utils.js';

const WS_RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000];
const ANSWER_CONCURRENCY = 16;
const REQUEST_TIMEOUT = 12000;

// ==================== 后台保活 & 本地通知 ====================
let wakeLock = null;
let isAppInBackground = false;

/** 申请 PARTIAL_WAKE_LOCK 防止 CPU 休眠，保持 WebSocket 连接 */
const acquireWakeLock = () => {
	if (wakeLock) return;
	try {
		if (typeof plus === 'undefined') return;
		const main = plus.android.runtimeMainActivity();
		const Context = plus.android.importClass('android.content.Context');
		const PowerManager = plus.android.importClass('android.os.PowerManager');
		const pm = main.getSystemService(Context.POWER_SERVICE);
		wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, 'yuketang:ws-monitor');
		wakeLock.acquire();
		console.log('[保活] Wake Lock 已获取');
	} catch (error) {
		console.warn('[保活] Wake Lock 获取失败', error);
	}
};

/** 释放 Wake Lock */
const releaseWakeLock = () => {
	if (!wakeLock) return;
	try {
		if (wakeLock.isHeld()) wakeLock.release();
		console.log('[保活] Wake Lock 已释放');
	} catch (_) {}
	wakeLock = null;
};

/** 请求忽略电池优化（Android 6+），让系统不主动杀后台 */
const requestIgnoreBatteryOptimization = () => {
	try {
		if (typeof plus === 'undefined') return;
		if (typeof uni !== 'undefined' && uni.getStorageSync('ykt_battery_prompted_v1') === '1') return;
		const main = plus.android.runtimeMainActivity();
		const Context = plus.android.importClass('android.content.Context');
		const PowerManager = plus.android.importClass('android.os.PowerManager');
		const pm = main.getSystemService(Context.POWER_SERVICE);
		const packageName = main.getPackageName();
		if (!pm.isIgnoringBatteryOptimizations(packageName)) {
			const Intent = plus.android.importClass('android.content.Intent');
			const Settings = plus.android.importClass('android.provider.Settings');
			const Uri = plus.android.importClass('android.net.Uri');
			const intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
			intent.setData(Uri.parse('package:' + packageName));
			main.startActivity(intent);
			if (typeof uni !== 'undefined') uni.setStorageSync('ykt_battery_prompted_v1', '1');
		}
	} catch (error) {
		console.warn('[保活] 电池优化豁免请求失败', error);
	}
};

/** 发送本地推送通知（App 在后台时弹出系统通知栏） */
const pushLocalNotification = (title, content, payload = {}) => {
	try {
		if (typeof plus !== 'undefined' && plus.push) {
			plus.push.createMessage(content, JSON.stringify(payload), { title, cover: true });
		}
	} catch (error) {
		console.warn('[通知] 本地通知发送失败', error);
	}
};

const createEmptyQuestion = () => ({
	id: '',
	type: 0,
	body: '',
	options: [],
	blanks: [],
	pollingCount: 1,
	presentationId: '',
	slideId: '',
	slideIndex: null,
	cover: '',
	thumbnail: '',
	dt: null,
	limit: null,
	extend: 0,
	status: 'waiting',
	isDemo: false,
	submittedCount: 0
});

const firstValue = (...values) => values.find(value => value !== undefined && value !== null && value !== '');

const toNumber = (value, fallback = null) => {
	if (value === '' || value === undefined || value === null) return fallback;
	const number = Number(value);
	return Number.isFinite(number) ? number : fallback;
};

const toWsScalar = value => {
	const text = String(value ?? '');
	if (/^\d+$/.test(text)) {
		const number = Number(text);
		if (Number.isSafeInteger(number)) return number;
	}
	return value;
};

const toApiProblemId = value => {
	const text = String(value ?? '');
	if (/^\d+$/.test(text)) {
		const number = Number(text);
		if (Number.isSafeInteger(number)) return number;
	}
	return value;
};

const buildAnswerPayload = (problemId, dt, problemType, result) => {
	const converted = toApiProblemId(problemId);
	const payload = { problemId: converted, dt, problemType, result };
	const text = String(problemId ?? '');
	if (/^\d+$/.test(text) && typeof converted === 'string') {
		// JS Number cannot represent a 64-bit Flutter/Dart problemId exactly.
		// uni.request accepts a raw JSON string, so preserve the integer literal.
		return JSON.stringify(payload).replace(
			`"problemId":${JSON.stringify(converted)}`,
			`"problemId":${text}`
		);
	}
	return payload;
};

const normalizeEpochMilliseconds = value => {
	const number = toNumber(value);
	if (number === null) return null;
	return Math.abs(number) < 100000000000 ? number * 1000 : number;
};

const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

export function createAnswerEngine({
	accounts,
	currentTab,
	baseUrl,
	wsBaseUrl,
	syncServerUrl,
	getSyncServerUrl,
	getSyncApiKey,
	generateDeviceProfile,
	saveAccounts,
	addLog,
	showProgressDialog,
	isProgressFinished,
	progressMsg,
	runLogs
}) {
	const resolveSyncServerUrl = () => {
		if (typeof getSyncServerUrl === 'function') {
			return getSyncServerUrl();
		}
		if (typeof syncServerUrl === 'function') {
			return syncServerUrl();
		}
		return syncServerUrl || 'http://43.133.67.180:5000';
	};

	const answerProblemId = ref('');
	const answerProblemType = ref(0);
	const answerReceivers = ref([]);
	const toggleAccountAiMode = (account, value) => {
		account.ai_mode = value;
		if (typeof saveAccounts === 'function') {
			saveAccounts();
		}
		syncAnswerReceivers();
		uni.showToast({ title: value ? `[${account.remark || account.name || '终端'}] 已开启托管(排查手动勾选)` : `[${account.remark || account.name || '终端'}] 已关闭托管`, icon: 'none' });
	};

	const testAiConnection = () => {
		const apiKey = typeof getSyncApiKey === 'function' ? getSyncApiKey() : '';
		if (!apiKey) {
			uni.showToast({ title: '请先配置专属云端密钥', icon: 'none' });
			return;
		}
		uni.showLoading({ title: "探测云端 AI..." });
		uni.request({
			url: `${resolveSyncServerUrl()}/api/ai/test`,
			method: "POST",
			timeout: REQUEST_TIMEOUT,
			header: {
				Authorization: apiKey
			},
			success: e => {
				uni.hideLoading();
				const resData = e.data;
				if (resData && typeof resData === 'object' && resData.code === 0) {
					uni.showModal({ title: "AI 引擎测试通过", content: "云端模型连通正常，能够正常推理并解答题目。", showCancel: false });
				} else {
					let detail = "";
					if (typeof resData === 'string') {
						detail = resData.replace(/<[^>]+>/g, '').trim().substring(0, 300) || resData;
					} else if (resData && typeof resData === 'object') {
						detail = resData.msg || resData.message || resData.error || JSON.stringify(resData);
					} else {
						detail = `HTTP 状态码: ${e.statusCode}`;
					}
					uni.showModal({ title: `AI 测试未通过 (${e.statusCode || 'Err'})`, content: detail, showCancel: false });
				}
			},
			fail: (err) => {
				uni.hideLoading();
				uni.showModal({ title: "无法连接云端 API 服务器", content: `请检查服务器 5000 端口及 api_server.py 是否已启动。\n报错: ${err?.errMsg || '网络请求超时'}`, showCancel: false });
			}
		});
	};

	let storedLessonContext = {};
	try {
		storedLessonContext = JSON.parse(uni.getStorageSync('last_lesson_context_v2') || '{}');
	} catch (_) {}
	const currentLessonId = ref(String(storedLessonContext.id || uni.getStorageSync('last_lesson_id') || ''));
	const currentLessonInfo = ref({
		id: currentLessonId.value,
		title: String(storedLessonContext.title || ''),
		courseName: String(storedLessonContext.courseName || ''),
		classroomName: String(storedLessonContext.classroomName || ''),
		teacherName: String(storedLessonContext.teacherName || ''),
		startTime: storedLessonContext.startTime ?? null,
		endTime: storedLessonContext.endTime ?? null,
		status: String(storedLessonContext.status || ''),
		ended: Boolean(storedLessonContext.ended),
		wssUrl: String(storedLessonContext.wssUrl || ''),
		updatedAt: storedLessonContext.updatedAt || 0
	});
	const lessonInfoState = ref(currentLessonInfo.value.courseName || currentLessonInfo.value.title ? 'ready' : 'idle');
	const currentQuestion = ref(createEmptyQuestion());
	const presentationTitle = ref('');
	const selectedAnswerValues = ref([]);
	const fillAnswers = ref(['']);
	const subjectiveAnswer = ref('');
	const submittingAnswer = ref(false);

	const isMonitoring = ref(false);
	const isNewProblemDetected = ref(false);
	const monitorStatusText = ref('等待连接课堂');
	const wsConnectionState = ref('stopped');
	const wsStatusText = ref('未连接');
	const wsLastMessageText = ref('');
	const questionRemaining = ref(0);
	const questionUnlimited = ref(false);
	const lessonSessionEnded = ref(false);
	const failedProbeUids = new Set();

	let socketTask = null;
	let socketOpened = false;
	let socketGeneration = 0;
	let reconnectAttempt = 0;
	let reconnectTimer = null;
	let probeFailoverTimer = null;
	let restoreTimer = null;
	let heartbeatTimer = null;
	let countdownTimer = null;
	let presentationRetryTimer = null;
	let presentationFetchGeneration = 0;
	let manualSocketClose = true;
	let serverClockOffset = 0;
	let questionDeadline = null;
	let lastServerMessageTime = Date.now();
	let lastPresentationId = currentLessonId.value
		? String(uni.getStorageSync(`last_presentation_id_${currentLessonId.value}`) || '')
		: '';
	let lastSlideId = '';
	let lastSlideIndex = null;
	let lessonInfoFetchGeneration = 0;
	let activeProbeUid = '';

	const checkedReceiversCount = computed(() => answerReceivers.value.filter(receiver => receiver.checked && receiver.ready && !receiver.ai_mode).length);
	const aiHostedReceiversCount = computed(() => answerReceivers.value.filter(receiver => receiver.ready && receiver.ai_mode).length);
	const allReadyReceiversChecked = computed(() => {
		const manualReady = answerReceivers.value.filter(receiver => receiver.ready && !receiver.ai_mode);
		return manualReady.length > 0 && manualReady.every(receiver => receiver.checked);
	});

	const currentLessonDisplayName = computed(() => firstValue(
		currentLessonInfo.value.courseName,
		currentLessonInfo.value.title,
		currentLessonInfo.value.classroomName,
		currentLessonId.value ? `课堂 ${currentLessonId.value}` : '待绑定课堂'
	));
	const currentLessonSecondaryText = computed(() => {
		const details = [];
		if (currentLessonInfo.value.title && currentLessonInfo.value.title !== currentLessonDisplayName.value) details.push(currentLessonInfo.value.title);
		if (currentLessonInfo.value.classroomName && currentLessonInfo.value.classroomName !== currentLessonDisplayName.value) details.push(currentLessonInfo.value.classroomName);
		if (currentLessonInfo.value.teacherName) details.push(currentLessonInfo.value.teacherName);
		if (currentLessonId.value) details.push(`ID ${currentLessonId.value}`);
		return details.join(' · ');
	});

	// 官方 presentation_model 中 problemType 为 int：0 单选、1 多选、2 投票、3 填空、4 主观。
	const questionTypeLabel = computed(() => ({
		0: '单选题 / 判断题',
		1: '多选题',
		2: '投票题',
		3: '填空题',
		4: '简答题'
	}[answerProblemType.value] || '课堂题目'));

	const isTextQuestion = computed(() => answerProblemType.value === 3 || answerProblemType.value === 4);
	const isMultipleAnswer = computed(() => {
		if (answerProblemType.value === 1) return true;
		return answerProblemType.value === 2 && Number(currentQuestion.value.pollingCount || 1) > 1;
	});

	const displayedQuestionOptions = computed(() => {
		return currentQuestion.value.options;
	});

	const canAnswerCurrentQuestion = computed(() => {
		if (!answerProblemId.value) return false;
		if (currentQuestion.value.isDemo) return false;
		if (currentQuestion.value.status === 'closed' || currentQuestion.value.status === 'expired') return false;
		if (![0, 1, 2, 3, 4].includes(Number(answerProblemType.value))) return false;
		if ([0, 1, 2].includes(Number(answerProblemType.value)) && currentQuestion.value.options.length === 0) return false;
		if (questionUnlimited.value || questionDeadline === null) return true;
		return questionRemaining.value > 0;
	});

	const hasPreparedAnswer = computed(() => {
		if (answerProblemType.value === 3) {
			const expected = Math.max(1, currentQuestion.value.blanks.length || 1);
			return fillAnswers.value.length === expected
				&& fillAnswers.value.every(value => Boolean(String(value || '').trim()));
		}
		if (answerProblemType.value === 4) return Boolean(subjectiveAnswer.value.trim());
		return selectedAnswerValues.value.length > 0;
	});

	const canSubmitAnswer = computed(() => (
		canAnswerCurrentQuestion.value &&
		hasPreparedAnswer.value &&
		checkedReceiversCount.value > 0 &&
		!submittingAnswer.value
	));

	const questionCountdownLabel = computed(() => {
		if (!answerProblemId.value) return '题目状态';
		if (currentQuestion.value.isDemo) return '演示预览';
		if (currentQuestion.value.status === 'closed' || currentQuestion.value.status === 'expired') return '题目已关闭';
		if (questionUnlimited.value) return '本题不限时';
		if (questionDeadline === null) return '等待计时';
		return '关闭倒计时';
	});

	const questionCountdownText = computed(() => {
		if (currentQuestion.value.isDemo) return 'DEMO';
		if (!answerProblemId.value || questionDeadline === null && !questionUnlimited.value) return '--:--';
		if (questionUnlimited.value) return '∞';
		const seconds = Math.max(0, questionRemaining.value);
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor(seconds % 3600 / 60);
		const rest = seconds % 60;
		if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`;
		return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`;
	});

	const normalizeProblemType = value => {
		const number = toNumber(value);
		if (number !== null && number >= 0 && number <= 4) return number;
		const type = String(value || '').toLowerCase().replace(/[\s_-]/g, '');
		if (type.includes('multiple')) return 1;
		if (type.includes('polling') || type.includes('vote')) return 2;
		if (type.includes('fill') || type.includes('blank')) return 3;
		if (type.includes('short') || type.includes('subjective')) return 4;
		return 0;
	};

	const normalizeRichContent = value => {
		if (value === undefined || value === null) return '';
		if (typeof value === 'string') {
			return value
				.replace(/<(script|iframe|object|embed|style)\b[\s\S]*?<\/\1>/gi, '')
				.replace(/\son\w+\s*=\s*(['"])[\s\S]*?\1/gi, '')
				.replace(/\s(href|src)\s*=\s*(['"])\s*javascript:[\s\S]*?\2/gi, '')
				.replace(/src=(['"])\/\//gi, `src=$1https://`)
				.replace(/src=(['"])\/(?!\/)/gi, `src=$1${baseUrl}/`);
		}
		if (Array.isArray(value)) return value;
		if (typeof value === 'object') return firstValue(value.html, value.content, value.text, value.value, '') || '';
		return String(value);
	};

	const normalizeOptions = options => {
		if (!Array.isArray(options)) return [];
		return options.map((option, index) => {
			const defaultKey = index < 26 ? String.fromCharCode(65 + index) : String(index + 1);
			if (typeof option !== 'object' || option === null) {
				const key = defaultKey;
				return { key, value: normalizeRichContent(option), submitValue: key };
			}
			const key = String(firstValue(option.key, option.label, option.option, option.id, defaultKey));
			return {
				key,
				value: normalizeRichContent(firstValue(option.value, option.content, option.body, option.text, key)),
				submitValue: String(firstValue(option.key, option.label, option.option, key))
			};
		});
	};

	const syncAnswerReceivers = (selectAllReady = false) => {
		const oldSelection = new Map(answerReceivers.value.map(receiver => [String(receiver.id || receiver.phone), receiver.checked]));
		answerReceivers.value = accounts.value.map((account, index) => {
			const identity = String(account.id || account.phone);
			const accountLessonId = String(account.lessonId || account.lessonContext?.id || '');
			// Fix #2: lessonToken 必须属于当前课堂，否则服务器会拒绝
			const lessonMismatch = currentLessonId.value && accountLessonId && accountLessonId !== String(currentLessonId.value);
			const isAiMode = Boolean(account.ai_mode);
			const ready = Boolean(!account.expired && account.cookie && account.lessonToken && !lessonMismatch);
			let readyReason = '需先签到';
			if (account.expired) readyReason = '登录凭证过期';
			else if (lessonMismatch) readyReason = `凭证属于其他课堂`;
			else if (isAiMode) readyReason = '已开启AI托管';
			else if (ready) readyReason = '课堂凭证就绪';
			
			// 只有未开启 AI 托管的就绪账号，才允许勾选进行手动批量答题
			const isChecked = ready && !isAiMode && (selectAllReady || (oldSelection.has(identity) ? oldSelection.get(identity) : true));
			
			return {
				id: account.id || account.phone || `${account.uid || 'account'}-${index}`,
				name: account.name,
				phone: account.phone,
				remark: account.remark,
				lessonToken: account.lessonToken || '',
				lessonId: accountLessonId,
				cookie: account.cookie || '',
				device: account.device,
				uid: account.uid,
				ai_mode: isAiMode,
				ready,
				readyReason,
				checked: isChecked
			};
		});
	};

	// Fix #1: 支持排除已失败的探针账号，自动切换到下一个可用账号
	const getProbeAccount = (excludeUids = failedProbeUids) => accounts.value.find(account => (
		!account.expired && account.cookie && account.lessonToken && account.uid &&
		String(account.lessonId || account.lessonContext?.id || '') === String(currentLessonId.value || '') &&
		!excludeUids.has(String(account.uid))
	));

	const toggleReceiver = receiver => {
		if (receiver.ai_mode) {
			uni.showToast({ title: '已开启AI托管的账号不可手动勾选', icon: 'none' });
			return;
		}
		if (!receiver.ready) {
			uni.showToast({ title: '该账号需先进入当前课堂', icon: 'none' });
			return;
		}
		receiver.checked = !receiver.checked;
	};

	const toggleAllReceivers = () => {
		const nextChecked = !allReadyReceiversChecked.value;
		answerReceivers.value.forEach(receiver => {
			if (receiver.ready && !receiver.ai_mode) receiver.checked = nextChecked;
		});
	};

	const clearPreparedAnswer = () => {
		selectedAnswerValues.value = [];
		subjectiveAnswer.value = '';
		const blankCount = Math.max(1, currentQuestion.value.blanks.length || 1);
		fillAnswers.value = Array.from({ length: blankCount }, () => '');
	};

	const isOptionSelected = value => selectedAnswerValues.value.includes(String(value));

	const selectQuestionOption = option => {
		if (!canAnswerCurrentQuestion.value) return;
		const value = String(option.submitValue);
		if (isMultipleAnswer.value) {
			if (isOptionSelected(value)) {
				selectedAnswerValues.value = selectedAnswerValues.value.filter(item => item !== value);
				return;
			}
			const maxSelect = answerProblemType.value === 2
				? Math.max(1, Number(currentQuestion.value.pollingCount || 1))
				: Number.POSITIVE_INFINITY;
			if (selectedAnswerValues.value.length >= maxSelect) {
				uni.showToast({ title: `本题最多选择 ${maxSelect} 项`, icon: 'none' });
				return;
			}
			selectedAnswerValues.value = [...selectedAnswerValues.value, value];
		} else {
			selectedAnswerValues.value = [value];
		}
	};

	const setFillAnswer = (index, value) => {
		const answers = [...fillAnswers.value];
		answers[index] = value;
		fillAnswers.value = answers;
	};

	const updateCountdown = () => {
		if (!answerProblemId.value || questionUnlimited.value || questionDeadline === null) return;
		const serverNow = Date.now() + serverClockOffset;
		questionRemaining.value = Math.max(0, Math.ceil((questionDeadline - serverNow) / 1000));
		if (questionRemaining.value === 0 && currentQuestion.value.status === 'live') {
			currentQuestion.value.status = 'expired';
			isNewProblemDetected.value = false;
			monitorStatusText.value = `题目 #${answerProblemId.value} 已到关闭时间`;
		}
	};

	const applyQuestionTiming = timing => {
		const dt = firstValue(timing.dt, timing.sendTime, timing.send_time, currentQuestion.value.dt);
		const limit = toNumber(firstValue(
			timing.limit,
			timing.limit_time,
			timing.limitTime,
			timing.timeLimit,
			currentQuestion.value.limit
		));
		const extend = toNumber(firstValue(
			timing.extend,
			timing.extended_time,
			timing.extendTime,
			currentQuestion.value.extend
		), 0) || 0;
		const serverNow = normalizeEpochMilliseconds(firstValue(timing.now, timing.serverTime));
		if (serverNow !== null) serverClockOffset = serverNow - Date.now();

		currentQuestion.value.dt = dt ?? null;
		currentQuestion.value.limit = limit;
		currentQuestion.value.extend = extend;
		questionUnlimited.value = limit === -1;
		if (questionUnlimited.value) {
			questionDeadline = null;
			questionRemaining.value = 0;
			return;
		}

		const start = normalizeEpochMilliseconds(dt);
		if (start !== null && limit !== null) {
			questionDeadline = start + Math.max(0, limit + extend) * 1000;
		} else if (limit !== null && questionDeadline === null) {
			questionDeadline = (serverNow ?? Date.now()) + Math.max(0, limit + extend) * 1000;
		}
		updateCountdown();
	};

	const sendSocket = payload => {
		if (!socketTask || !socketOpened) return false;
		try {
			socketTask.send({ data: JSON.stringify(payload) });
			return true;
		} catch (error) {
			console.warn('[答题 WebSocket] 发送失败', error);
			return false;
		}
	};

	const requestProblemInfo = () => {
		if (!answerProblemId.value || !currentLessonId.value) return;
		sendSocket({
			op: 'probleminfo',
			lessonid: toWsScalar(currentLessonId.value),
			problemid: toWsScalar(answerProblemId.value),
			msgid: '1'
		});
	};

	const closeCurrentQuestion = reason => {
		if (!answerProblemId.value) return;
		currentQuestion.value.status = 'closed';
		questionRemaining.value = 0;
		isNewProblemDetected.value = false;
		monitorStatusText.value = reason || `题目 #${answerProblemId.value} 已关闭`;
	};

	const findProblemId = source => firstValue(
		source?.problemId,
		source?.problem_id,
		source?.problemid,
		source?.prob,
		source?.spid,
		typeof source?.problem === 'object' ? findProblemId(source.problem) : source?.problem
	);

	const mergeSocketProblem = message => (
		message?.problem && typeof message.problem === 'object'
			? { ...message, ...message.problem }
			: message
	);

	const requestLessonApi = (url, method, data, account) => {
		const safeDevice = account.device || generateDeviceProfile();
		let cookie = String(account.cookie || '');
		let csrf = cookie.match(/csrftoken=([^; ]+)/)?.[1] || '';
		if (!csrf) {
			const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
			for (let index = 0; index < 32; index++) csrf += chars.charAt(Math.floor(Math.random() * chars.length));
			cookie += `; csrftoken=${csrf}; django_language=zh-cn;`;
		}
		const header = Object.assign({
			cookie,
			'x-csrftoken': csrf,
			'content-type': 'application/json',
			'x-client': 'app',
			xtbz: 'ykt'
		}, safeDevice);
		// lessonToken 仅用于答题提交 (POST)，fetchPresentation (GET) 不需要
		if (method !== 'GET' && account.lessonToken) header.lessonToken = account.lessonToken;
		if (account.uid) header['x-uid'] = String(account.uid);

		return new Promise(resolve => {
			uni.request({
				url,
				method,
				header,
				data,
				timeout: REQUEST_TIMEOUT,
				success: response => resolve({ status: response.statusCode, data: response.data }),
				fail: error => resolve({ status: -1, error })
			});
		});
	};

	const persistLessonContext = () => {
		if (!currentLessonId.value) return;
		const context = { ...currentLessonInfo.value, id: String(currentLessonId.value) };
		uni.setStorageSync('last_lesson_id', String(currentLessonId.value));
		uni.setStorageSync('last_lesson_context_v2', JSON.stringify(context));
	};

	const clearLessonRealtimeState = () => {
		presentationFetchGeneration++;
		if (presentationRetryTimer) clearTimeout(presentationRetryTimer);
		presentationRetryTimer = null;
		answerProblemId.value = '';
		answerProblemType.value = 0;
		currentQuestion.value = createEmptyQuestion();
		presentationTitle.value = '';
		selectedAnswerValues.value = [];
		fillAnswers.value = [''];
		subjectiveAnswer.value = '';
		questionDeadline = null;
		questionRemaining.value = 0;
		questionUnlimited.value = false;
		lastSlideId = '';
		lastSlideIndex = null;
		isNewProblemDetected.value = false;
	};

	const bindLessonContext = (lessonId, metadata = {}) => {
		const id = String(lessonId || '');
		if (!id) return false;
		const switched = lessonSessionEnded.value || Boolean(currentLessonId.value && String(currentLessonId.value) !== id);
		if (switched) {
			manualSocketClose = true;
			isMonitoring.value = false;
			if (reconnectTimer) clearTimeout(reconnectTimer);
			reconnectTimer = null;
			closeSocketTask();
			clearLessonRealtimeState();
			failedProbeUids.clear();
		}
		lessonSessionEnded.value = false;
		currentLessonId.value = id;
		currentLessonInfo.value = {
			id,
			title: String(metadata.title ?? (switched ? '' : currentLessonInfo.value.title) ?? ''),
			courseName: String(metadata.courseName ?? (switched ? '' : currentLessonInfo.value.courseName) ?? ''),
			classroomName: String(metadata.classroomName ?? (switched ? '' : currentLessonInfo.value.classroomName) ?? ''),
			teacherName: String(metadata.teacherName ?? (switched ? '' : currentLessonInfo.value.teacherName) ?? ''),
			startTime: metadata.startTime ?? (switched ? null : currentLessonInfo.value.startTime),
			endTime: metadata.endTime ?? (switched ? null : currentLessonInfo.value.endTime),
			status: String(metadata.status ?? (switched ? '' : currentLessonInfo.value.status) ?? ''),
			ended: Boolean(metadata.ended ?? (switched ? false : currentLessonInfo.value.ended)),
			wssUrl: String(metadata.wssUrl ?? (switched ? '' : currentLessonInfo.value.wssUrl) ?? ''),
			updatedAt: metadata.updatedAt || currentLessonInfo.value.updatedAt || Date.now()
		};
		lastPresentationId = String(uni.getStorageSync(`last_presentation_id_${id}`) || '');
		lessonInfoState.value = currentLessonInfo.value.courseName || currentLessonInfo.value.title ? 'ready' : 'idle';
		persistLessonContext();
		syncAnswerReceivers();
		return true;
	};

	const isSuccessfulDetailResponse = response => {
		if (response?.status !== 200 || !response.data) return false;
		if (response.data.code !== undefined) return Number(response.data.code) === 0;
		if (response.data.success !== undefined) return response.data.success === true;
		return Boolean(response.data.data);
	};

	const isLessonAuthFailure = response => {
		if ([401, 403].includes(Number(response?.status))) return true;
		const code = String(firstValue(response?.data?.code, response?.data?.status, '') || '').toLowerCase();
		if (['401', '403', 'unauthorized', 'forbidden'].includes(code)) return true;
		const message = String(firstValue(
			response?.data?.msg,
			response?.data?.message,
			response?.data?.error,
			''
		) || '').toLowerCase();
		return /(token|登录|认证|凭证)/i.test(message) && /(失效|过期|无效|expired|invalid)/i.test(message);
	};

	const fetchLessonInfo = async (force = false) => {
		const lessonId = String(currentLessonId.value || '');
		if (!lessonId) return null;
		if (!force && lessonInfoState.value === 'ready' && String(currentLessonInfo.value.id) === lessonId) return currentLessonInfo.value;
		const probe = getProbeAccount();
		if (!probe) return null;
		const generation = ++lessonInfoFetchGeneration;
		lessonInfoState.value = 'loading';
		const endpoints = [
			`${baseUrl}/api/v3/lesson/basic-info?lesson_id=${encodeURIComponent(lessonId)}`,
			`${baseUrl}/api/v3/lesson/detail?lesson_id=${encodeURIComponent(lessonId)}`,
			`${baseUrl}/api/v3/lesson/detail`
		];
		let mergedMetadata = null;
		for (const endpoint of endpoints) {
			const response = await requestLessonApi(endpoint, 'GET', {}, probe);
			if (generation !== lessonInfoFetchGeneration || String(currentLessonId.value) !== lessonId) return null;
			if (!isSuccessfulDetailResponse(response)) continue;
			const metadata = extractLessonMetadata(response.data, lessonId);
			if (!metadata) continue;
			mergedMetadata = {
				...(mergedMetadata || {}),
				...Object.fromEntries(
					Object.entries(metadata).filter(([, value]) => value !== '' && value !== null && value !== undefined)
				),
				id: lessonId,
				updatedAt: Date.now()
			};
		}
		if (mergedMetadata) {
			bindLessonContext(lessonId, mergedMetadata);
			accounts.value.forEach(account => {
				const accountLessonId = String(account.lessonId || account.lessonContext?.id || '');
				if (accountLessonId === lessonId && account.lessonToken) {
					account.lessonId = lessonId;
					account.lessonContext = { ...mergedMetadata, joinedAt: account.lessonContext?.joinedAt || Date.now() };
				}
			});
			saveAccounts();
			if (mergedMetadata.ended === true && String(currentLessonId.value) === lessonId) {
				finishLessonSession();
				return { ...mergedMetadata, id: lessonId };
			}
			lessonInfoState.value = 'ready';
			return mergedMetadata;
		}
		lessonInfoState.value = 'error';
		return null;
	};

	const fetchPresentation = async (presentationId, retry = 0) => {
		const id = String(presentationId || lastPresentationId || '');
		if (!id || !answerProblemId.value) return;
		lastPresentationId = id;
		uni.setStorageSync(`last_presentation_id_${currentLessonId.value}`, id);
		const probe = getProbeAccount();
		if (!probe) return;
		const fetchGeneration = ++presentationFetchGeneration;
		const problemAtStart = String(answerProblemId.value);
		const response = await requestLessonApi(
			`${baseUrl}/api/v3/lesson/presentation/fetch?presentation_id=${encodeURIComponent(id)}`,
			'GET',
			{},
			probe
		);
		if (fetchGeneration !== presentationFetchGeneration || String(answerProblemId.value) !== problemAtStart) return;

		// Fix #4: 403/401 说明探针的 lessonToken 已失效，标记并尝试换探针重试
		if (isLessonAuthFailure(response)) {
			if (probe.uid) failedProbeUids.add(String(probe.uid));
			console.warn(`[课件拉取] 探针 ${probe.uid} 收到 ${response.status}，尝试换探针`);
			const altProbe = getProbeAccount();
			if (altProbe && retry < 2) {
				clearTimeout(presentationRetryTimer);
				presentationRetryTimer = setTimeout(() => fetchPresentation(id, retry + 1), 800);
			}
			return;
		}

		const frame = extractPresentationFrame(response.data || {}, {
			problemId: problemAtStart,
			slideId: currentQuestion.value.slideId || lastSlideId,
			slideIndex: currentQuestion.value.slideIndex ?? lastSlideIndex
		}, baseUrl);
		const { slide, problem } = frame;
		if (response.status === 200 && slide) {
			presentationTitle.value = String(firstValue(frame.title, presentationTitle.value, '实时课堂课件'));
			const fetchedType = normalizeProblemType(firstValue(problem.problemType, problem.type, answerProblemType.value));
			answerProblemType.value = fetchedType;
			currentQuestion.value.type = fetchedType;
			currentQuestion.value.body = normalizeRichContent(firstValue(problem.body, problem.content, problem.title, currentQuestion.value.body));
			const options = normalizeOptions(firstValue(problem.options, problem.choices, []));
			if (options.length) currentQuestion.value.options = options;
			if (Array.isArray(problem.blanks)) currentQuestion.value.blanks = problem.blanks;
			currentQuestion.value.pollingCount = toNumber(firstValue(problem.pollingCount, problem.maxSelect, currentQuestion.value.pollingCount), 1) || 1;
			currentQuestion.value.slideId = String(firstValue(slide.lessonSlideID, slide.id, currentQuestion.value.slideId, ''));
			currentQuestion.value.slideIndex = toNumber(firstValue(slide.index, currentQuestion.value.slideIndex));
			currentQuestion.value.thumbnail = firstValue(frame.thumbnail, currentQuestion.value.thumbnail, '');
			currentQuestion.value.cover = firstValue(frame.cover, currentQuestion.value.cover, '');
			applyQuestionTiming(problem);
			const requiredBlankCount = Math.max(1, currentQuestion.value.blanks.length || 1);
			if (fillAnswers.value.length !== requiredBlankCount || fillAnswers.value.every(value => !value)) {
				fillAnswers.value = Array.from({ length: requiredBlankCount }, (_, index) => fillAnswers.value[index] || '');
			}
			return;
		}

		if (retry < 3 && isMonitoring.value && String(answerProblemId.value) === problemAtStart) {
			clearTimeout(presentationRetryTimer);
			presentationRetryTimer = setTimeout(() => fetchPresentation(id, retry + 1), [1200, 3000, 7000][retry]);
		}
	};

	const activateQuestion = (
		rawQuestion,
		{ keepSelection = false, vibrate = true, requestInfo = true } = {}
	) => {
		if (!rawQuestion) return;
		const source = rawQuestion.problem && typeof rawQuestion.problem === 'object' ? { ...rawQuestion, ...rawQuestion.problem } : rawQuestion;
		const id = findProblemId(source);
		if (id === undefined || id === null || id === '') return;
		const idText = String(id);
		const isNew = idText !== String(answerProblemId.value);
		const presentationId = String(firstValue(source.pres, source.presentationId, source.presentation_id, currentQuestion.value.presentationId, lastPresentationId, ''));
		const slideId = String(firstValue(source.sid, source.slideId, source.lessonSlideID, currentQuestion.value.slideId, lastSlideId, ''));
		const slideIndex = toNumber(firstValue(source.si, source.slideIndex, source.index, currentQuestion.value.slideIndex, lastSlideIndex));
		const type = normalizeProblemType(firstValue(source.problemType, source.type, currentQuestion.value.type));

		if (isNew) {
			presentationFetchGeneration++;
			clearTimeout(presentationRetryTimer);
			currentQuestion.value = createEmptyQuestion();
			answerProblemId.value = idText;
			questionDeadline = null;
			questionRemaining.value = 0;
			questionUnlimited.value = false;
			if (!keepSelection) clearPreparedAnswer();
		}

		answerProblemType.value = type;
		currentQuestion.value.id = idText;
		currentQuestion.value.type = type;
		currentQuestion.value.status = 'live';
		currentQuestion.value.presentationId = presentationId;
		currentQuestion.value.slideId = slideId;
		currentQuestion.value.slideIndex = slideIndex;
		if (source.body || source.content || source.title) currentQuestion.value.body = normalizeRichContent(firstValue(source.body, source.content, source.title));
		const inlineOptions = normalizeOptions(firstValue(source.options, source.choices, []));
		if (inlineOptions.length) currentQuestion.value.options = inlineOptions;
		if (Array.isArray(source.blanks)) currentQuestion.value.blanks = source.blanks;
		currentQuestion.value.pollingCount = toNumber(firstValue(
			source.pollingCount,
			source.maxSelect,
			source.max_select,
			currentQuestion.value.pollingCount
		), 1) || 1;
		if (answerProblemType.value === 3) {
			const requiredBlankCount = Math.max(1, currentQuestion.value.blanks.length || 1);
			if (fillAnswers.value.length !== requiredBlankCount) {
				fillAnswers.value = Array.from(
					{ length: requiredBlankCount },
					(_, index) => fillAnswers.value[index] || ''
				);
			}
		}
		applyQuestionTiming(source);

		if (presentationId) lastPresentationId = presentationId;
		if (slideId) lastSlideId = slideId;
		if (slideIndex !== null) lastSlideIndex = slideIndex;
		isNewProblemDetected.value = isNew || currentQuestion.value.submittedCount === 0;
		monitorStatusText.value = `发现实时题目 #${idText}，等待作答`;
		if (isNew && vibrate && typeof uni.vibrateShort === 'function') uni.vibrateShort();
		// 后台时发送本地推送通知
		if (isNew && isAppInBackground) {
			const typeNames = { 0: '单选题', 1: '多选题', 2: '投票题', 3: '填空题', 4: '简答题' };
			pushLocalNotification('📢 课堂新题目', `${typeNames[type] || '题目'} #${idText} 已发布，点击作答`, { op: 'new_problem', problemId: idText });
		}
		if (requestInfo) requestProblemInfo();
		if (presentationId || lastPresentationId) fetchPresentation(presentationId || lastPresentationId);
	};

	const normalizeSocketMessage = data => {
		if (typeof data === 'object' && data !== null && !(data instanceof ArrayBuffer)) return data;
		let text = data;
		if (data instanceof ArrayBuffer && typeof TextDecoder !== 'undefined') text = new TextDecoder('utf-8').decode(data);
		if (typeof text !== 'string') return null;
		try {
			return JSON.parse(text);
		} catch (_) {
			const messages = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean).map(line => {
				try { return JSON.parse(line); } catch (_) { return null; }
			}).filter(Boolean);
			return messages.length ? messages : null;
		}
	};

	const consumePresentationState = (message, activateUnlocked = true) => {
		lastPresentationId = String(firstValue(
			typeof message.presentation === 'object' ? firstValue(message.presentation.id, message.presentation.presentationId) : message.presentation,
			message.pres,
			message.presentationId,
			lastPresentationId,
			''
		));
		lastSlideId = String(firstValue(message.slideid, message.slideId, message.sid, lastSlideId, ''));
		lastSlideIndex = toNumber(firstValue(message.slideindex, message.slideIndex, message.si, lastSlideIndex));
		if (lastPresentationId) uni.setStorageSync(`last_presentation_id_${currentLessonId.value}`, lastPresentationId);
		const unlocked = Array.isArray(message.unlockedproblem)
			? message.unlockedproblem
			: Array.isArray(message.unlockedProblem)
				? message.unlockedProblem
				: [];
		const latestUnlocked = unlocked.length ? unlocked[unlocked.length - 1] : null;
		const latestProblem = latestUnlocked && typeof latestUnlocked === 'object'
			? {
				...latestUnlocked,
				pres: firstValue(latestUnlocked.pres, lastPresentationId),
				sid: firstValue(latestUnlocked.sid, lastSlideId),
				si: firstValue(latestUnlocked.si, lastSlideIndex)
			}
			: latestUnlocked
				? { problemid: latestUnlocked, pres: lastPresentationId, sid: lastSlideId, si: lastSlideIndex }
				: null;
		const latestProblemId = findProblemId(latestProblem);
		if (
			activateUnlocked &&
			latestProblem &&
			(
				!answerProblemId.value ||
				String(latestProblemId || '') !== String(answerProblemId.value) ||
				currentQuestion.value.status !== 'live'
			)
		) {
			activateQuestion(latestProblem, { vibrate: false });
		} else if (answerProblemId.value && lastPresentationId) {
			fetchPresentation(lastPresentationId);
		}
	};

	const processSocketMessage = message => {
		if (!message || typeof message !== 'object') return;
		if (Array.isArray(message)) {
			message.forEach(processSocketMessage);
			return;
		}
		const nestedData = message.data && typeof message.data === 'object' && !Array.isArray(message.data)
			? message.data
			: null;
		if (nestedData) {
			message = {
				...message,
				...nestedData,
				op: firstValue(message.op, message.operation, nestedData.op, nestedData.operation, ''),
				data: message.data
			};
		}
		const messageLessonId = firstValue(message.lessonid, message.lessonId, message.lesson_id, message.data?.lessonid, '');
		if (messageLessonId && currentLessonId.value && String(messageLessonId) !== String(currentLessonId.value)) {
			console.warn('[答题 WebSocket] 已忽略其他课堂消息', messageLessonId);
			return;
		}
		wsLastMessageText.value = new Date().toLocaleTimeString('zh-CN', { hour12: false });
		lastServerMessageTime = Date.now();
		if (wsConnectionState.value !== 'ready') {
			wsConnectionState.value = 'ready';
			wsStatusText.value = '实时在线';
		}
		const op = String(message.op || message.operation || '').toLowerCase();
		switch (op) {
			case 'hello':
				if (
					message.isEnd === true
					|| message.ended === true
					|| /(finish|ended|closed|已结束|已关闭)/i.test(String(message.lessonStatus || ''))
				) {
					finishLessonSession();
					break;
				}
				if (message.success === false || message.code && Number(message.code) !== 0) {
					const failedUid = String(activeProbeUid || '');
					if (failedUid) failedProbeUids.add(failedUid);
					const nextProbe = getProbeAccount();
					if (nextProbe) {
						console.warn(`[答题 WebSocket] 探针 ${failedUid} 鉴权失败，切换到 ${nextProbe.uid}`);
						monitorStatusText.value = `探针 ${failedUid} 鉴权失败，正在切换账号重连`;
						closeSocketTask();
						if (probeFailoverTimer) clearTimeout(probeFailoverTimer);
						probeFailoverTimer = setTimeout(() => {
							probeFailoverTimer = null;
							if (isMonitoring.value) connectWebSocket();
						}, 500);
					} else {
						wsConnectionState.value = 'error';
						wsStatusText.value = '所有账号鉴权失败';
						monitorStatusText.value = message.msg || '所有可用账号均无法通过课堂鉴权，请重新签到';
						closeSocketTask();
						if (probeFailoverTimer) clearTimeout(probeFailoverTimer);
						probeFailoverTimer = setTimeout(() => {
							probeFailoverTimer = null;
							failedProbeUids.clear();
							if (isMonitoring.value) connectWebSocket();
						}, 15000);
					}
				} else {
					// 鉴权成功，清空失败记录
					failedProbeUids.clear();
					monitorStatusText.value = answerProblemId.value ? `题目 #${answerProblemId.value} 实时同步中` : '已进入课堂，等待教师发布题目';
					consumePresentationState(message, true);
				}
				break;
			case 'unlockproblem':
			case 'unlock_problem':
				activateQuestion(mergeSocketProblem(message));
				break;
			case 'sendproblem':
			case 'sendsproblem': {
				const problem = typeof message.problem === 'object'
					? mergeSocketProblem(message)
					: { ...message, problemid: firstValue(message.problemid, message.spid, message.problem) };
				activateQuestion(problem);
				break;
			}
			case 'sproblemshown':
			case 'problemshown':
				activateQuestion({ ...message, problemid: firstValue(message.problemid, message.spid) });
				break;
			case 'probleminfo': {
				const merged = mergeSocketProblem(message);
				const incomingId = findProblemId(merged);
				if (incomingId) {
					const sameProblem = String(incomingId) === String(answerProblemId.value);
					activateQuestion(merged, {
						keepSelection: sameProblem,
						vibrate: !sameProblem,
						requestInfo: false
					});
				} else {
					applyQuestionTiming(merged);
				}
				break;
			}
			case 'extendtime':
				if (message.problem) activateQuestion(mergeSocketProblem(message), { keepSelection: true, vibrate: false });
				else applyQuestionTiming(message);
				monitorStatusText.value = `题目 #${answerProblemId.value} 已延长作答时间`;
				break;
			case 'problemfinished':
			case 'finishproblem': {
				const finishedId = findProblemId(message);
				if (!finishedId || String(finishedId) === String(answerProblemId.value)) closeCurrentQuestion(`题目 #${answerProblemId.value} 已由教师关闭`);
				break;
			}
			case 'showpresentation': {
				consumePresentationState(message, true);
				break;
			}
			case 'slidenav':
				lastPresentationId = String(firstValue(message.pres, message.presentationId, lastPresentationId, ''));
				lastSlideId = String(firstValue(message.sid, message.slideId, lastSlideId, ''));
				lastSlideIndex = toNumber(firstValue(message.si, message.index, lastSlideIndex));
				if (lastPresentationId) uni.setStorageSync(`last_presentation_id_${currentLessonId.value}`, lastPresentationId);
				if (answerProblemId.value && lastPresentationId) {
					currentQuestion.value.slideId = lastSlideId;
					currentQuestion.value.slideIndex = lastSlideIndex;
					fetchPresentation(lastPresentationId);
				}
				break;
			case 'presentationupdated':
				if (answerProblemId.value) fetchPresentation(firstValue(message.pres, message.presentationId, currentQuestion.value.presentationId, lastPresentationId));
				break;
			case 'lessonfinished':
			case 'finishlesson':
			case 'endlesson':
			case 'lessonend':
				finishLessonSession();
				break;
			default:
				break;
		}
	};

	const clearHeartbeat = () => {
		if (heartbeatTimer) clearInterval(heartbeatTimer);
		heartbeatTimer = null;
	};

	const scheduleReconnect = () => {
		if (manualSocketClose || !isMonitoring.value || reconnectTimer) return;
		const wait = WS_RECONNECT_DELAYS[Math.min(reconnectAttempt, WS_RECONNECT_DELAYS.length - 1)];
		reconnectAttempt++;
		wsConnectionState.value = 'reconnecting';
		wsStatusText.value = `${Math.ceil(wait / 1000)}秒后重连`;
		monitorStatusText.value = '实时通道短暂中断，正在自动恢复';
		reconnectTimer = setTimeout(() => {
			reconnectTimer = null;
			connectWebSocket();
		}, wait);
	};

	const closeSocketTask = () => {
		socketGeneration++;
		clearHeartbeat();
		if (socketTask) {
			try { socketTask.close({ code: 1000, reason: 'switch_or_stop' }); } catch (_) {}
		}
		socketTask = null;
		socketOpened = false;
	};

	const finishLessonSession = () => {
		const finishedLessonId = String(currentLessonId.value || '');
		manualSocketClose = true;
		isMonitoring.value = false;
		releaseWakeLock();
		isNewProblemDetected.value = false;
		lessonSessionEnded.value = true;
		if (reconnectTimer) clearTimeout(reconnectTimer);
		reconnectTimer = null;
		if (probeFailoverTimer) clearTimeout(probeFailoverTimer);
		probeFailoverTimer = null;
		if (restoreTimer) clearTimeout(restoreTimer);
		restoreTimer = null;
		if (countdownTimer) clearInterval(countdownTimer);
		countdownTimer = null;
		if (presentationRetryTimer) clearTimeout(presentationRetryTimer);
		presentationRetryTimer = null;
		closeSocketTask();
		clearLessonRealtimeState();
		currentLessonId.value = '';
		currentLessonInfo.value = {
			...currentLessonInfo.value,
			id: finishedLessonId,
			endedAt: Date.now()
		};
		lessonInfoState.value = 'ended';
		uni.setStorageSync('last_lesson_id', '');
		uni.setStorageSync('last_lesson_context_v2', '{}');
		wsConnectionState.value = 'stopped';
		wsStatusText.value = '课堂已结束';
		monitorStatusText.value = '本次课堂已结束，等待进入下一课堂';
		// Only clear credentials that belong to the finished lesson.
		accounts.value.forEach(account => {
			const accountLessonId = String(account.lessonId || account.lessonContext?.id || '');
			if (accountLessonId === finishedLessonId) {
				account.lessonToken = '';
				account.lessonId = '';
				account.lessonContext = null;
				account.lessonCredentialUpdatedAt = Date.now();
			}
		});
		saveAccounts();
		syncAnswerReceivers();
	};

	function connectWebSocket() {
		if (!isMonitoring.value || !currentLessonId.value) return;
		const probe = getProbeAccount();
		if (!probe) {
			wsConnectionState.value = 'error';
			wsStatusText.value = '缺少课堂凭证';
			monitorStatusText.value = '请先让至少一个账号扫码进入课堂';
			return;
		}

		if (reconnectTimer) clearTimeout(reconnectTimer);
		reconnectTimer = null;
		if (probeFailoverTimer) clearTimeout(probeFailoverTimer);
		probeFailoverTimer = null;
		closeSocketTask();
		const generation = ++socketGeneration;
		activeProbeUid = String(probe.uid || '');
		wsConnectionState.value = reconnectAttempt ? 'reconnecting' : 'connecting';
		wsStatusText.value = reconnectAttempt ? '正在重连' : '正在连接';
		monitorStatusText.value = '正在建立课堂实时通道';
		const socketUrl = resolveOfficialWebSocketUrl(
			currentLessonInfo.value.wssUrl,
			wsBaseUrl || baseUrl
		);

		try {
			socketTask = uni.connectSocket({
				url: socketUrl,
				header: { 'User-Agent': 'Android-mobile' },
				fail: () => {
					if (generation === socketGeneration) scheduleReconnect();
				}
			});
		} catch (error) {
			console.warn('[答题 WebSocket] 创建连接失败', error);
			scheduleReconnect();
			return;
		}

		if (!socketTask || typeof socketTask.onOpen !== 'function') {
			wsConnectionState.value = 'error';
			wsStatusText.value = '实时组件异常';
			scheduleReconnect();
			return;
		}

		socketTask.onOpen(() => {
			if (generation !== socketGeneration) return;
			socketOpened = true;
			lastServerMessageTime = Date.now();
			reconnectAttempt = 0;
			wsConnectionState.value = 'open';
			wsStatusText.value = '课堂鉴权中';
			sendSocket({
				op: 'hello',
				userid: toWsScalar(probe.uid),
				role: 'student',
				auth: probe.lessonToken,
				lessonid: toWsScalar(currentLessonId.value)
			});
			clearHeartbeat();
			heartbeatTimer = setInterval(() => {
				// Quiet classrooms are normal; use a conservative watchdog.
				if (socketOpened && Date.now() - lastServerMessageTime > 90000) {
					console.warn('[答题 WebSocket] 90 秒无任何服务端消息，执行保守重连');
					closeSocketTask();
					scheduleReconnect();
					return;
				}
				sendSocket({ op: 'detectlesson', lessonid: toWsScalar(currentLessonId.value) });
				if (answerProblemId.value && currentQuestion.value.status === 'live') requestProblemInfo();
			}, 15000);
			if (answerProblemId.value) requestProblemInfo();
		});

		socketTask.onMessage(event => {
			if (generation !== socketGeneration) return;
			const message = normalizeSocketMessage(event.data);
			if (message) processSocketMessage(message);
		});

		socketTask.onError(error => {
			if (generation !== socketGeneration) return;
			console.warn('[答题 WebSocket] 连接异常', error);
			wsConnectionState.value = 'error';
			wsStatusText.value = '连接异常';
			scheduleReconnect();
		});

		socketTask.onClose(() => {
			if (generation !== socketGeneration) return;
			socketTask = null;
			socketOpened = false;
			clearHeartbeat();
			if (!manualSocketClose) scheduleReconnect();
		});
	}

	const startProblemMonitor = lessonId => {
		const id = String(lessonId || currentLessonId.value || uni.getStorageSync('last_lesson_id') || '');
		if (!id) return false;
		bindLessonContext(id);
		lessonSessionEnded.value = false;
		syncAnswerReceivers();
		if (!getProbeAccount()) {
			monitorStatusText.value = '当前课堂缺少可用的 lessonToken 或 uid';
			wsConnectionState.value = 'error';
			wsStatusText.value = '需先签到';
			return false;
		}
		manualSocketClose = false;
		isMonitoring.value = true;
		isNewProblemDetected.value = false;
		reconnectAttempt = 0;
		failedProbeUids.clear();
		if (!countdownTimer) countdownTimer = setInterval(updateCountdown, 250);
		fetchLessonInfo(false);
		connectWebSocket();
		acquireWakeLock();
		requestIgnoreBatteryOptimization();
		return true;
	};

	const stopProblemMonitor = () => {
		manualSocketClose = true;
		isMonitoring.value = false;
		isNewProblemDetected.value = false;
		if (reconnectTimer) clearTimeout(reconnectTimer);
		reconnectTimer = null;
		if (probeFailoverTimer) clearTimeout(probeFailoverTimer);
		probeFailoverTimer = null;
		if (presentationRetryTimer) clearTimeout(presentationRetryTimer);
		presentationRetryTimer = null;
		if (countdownTimer) clearInterval(countdownTimer);
		countdownTimer = null;
		closeSocketTask();
		wsConnectionState.value = 'stopped';
		wsStatusText.value = '已断开';
		monitorStatusText.value = '实时检测已断开';
		releaseWakeLock();
	};

	/** 手动强制重连：断开当前连接 → 清空失败记录 → 重新建立 WebSocket + 查询题目 */
	const forceReconnect = () => {
		if (!isMonitoring.value) {
			// 如果未在监控状态，直接启动
			const lessonId = currentLessonId.value || uni.getStorageSync('last_lesson_id');
			if (lessonId) return startProblemMonitor(lessonId);
			return false;
		}
		failedProbeUids.clear();
		reconnectAttempt = 0;
		lastServerMessageTime = Date.now();
		if (reconnectTimer) clearTimeout(reconnectTimer);
		reconnectTimer = null;
		closeSocketTask();
		wsConnectionState.value = 'connecting';
		wsStatusText.value = '手动重连中';
		monitorStatusText.value = '正在手动重新建立实时通道';
		connectWebSocket();
		return true;
	};

	const toggleMonitor = () => {
		if (isMonitoring.value) {
			stopProblemMonitor();
			return;
		}
		const lessonId = currentLessonId.value || uni.getStorageSync('last_lesson_id');
		if (!lessonId) {
			uni.showModal({ title: '暂未绑定课堂', content: '请先在账号管理页扫码签到，成功后会自动绑定课堂。', showCancel: false });
			return;
		}
		if (!startProblemMonitor(lessonId)) uni.showToast({ title: '请先让账号进入当前课堂', icon: 'none' });
	};

	const openAnswerTab = () => {
		if (!accounts.value.length) {
			uni.showToast({ title: '请先添加账号', icon: 'none' });
			return;
		}
		syncAnswerReceivers(true);
		currentTab.value = 'answer';
		const lessonId = currentLessonId.value || uni.getStorageSync('last_lesson_id');
		if (!isMonitoring.value && lessonId && getProbeAccount()) startProblemMonitor(lessonId);
		else if (isMonitoring.value && !socketOpened && !reconnectTimer) connectWebSocket();
		if (lessonId && getProbeAccount()) fetchLessonInfo(false);
	};

	const buildAnswerResult = () => {
		if (answerProblemType.value === 3) return fillAnswers.value.map(value => String(value || '').trim());
		if (answerProblemType.value === 4) return { content: subjectiveAnswer.value.trim(), pics: [], videos: [] };
		const selected = new Set(selectedAnswerValues.value.map(String));
		const result = displayedQuestionOptions.value.filter(option => selected.has(String(option.submitValue))).map(option => String(option.submitValue));
		// 多选题答案按字母升序排序（与官方 Flutter 客户端行为一致）
		if (answerProblemType.value === 1) result.sort();
		return result;
	};

	const isSuccessfulApiResponse = response => response?.status === 200 && (
		(response.data?.code !== undefined && Number(response.data.code) === 0) || response.data?.success === true
	);

	const executeSingleAnswerTask = async (account, result, lessonAtSubmit, problemAtSubmit) => {
		const displayName = account.remark || account.name || account.phone || '未命名账号';
		if (
			String(currentLessonId.value) !== lessonAtSubmit ||
			String(answerProblemId.value) !== problemAtSubmit ||
			!canAnswerCurrentQuestion.value
		) {
			addLog(`[跳过] > ${displayName} | 课堂已切换或题目已关闭`, false);
			return false;
		}
		if (!account.lessonToken || !account.cookie) {
			addLog(`[失败] > ${displayName} | 当前课堂凭证未就绪`, false);
			return false;
		}
		const payload = buildAnswerPayload(
			problemAtSubmit,
			Date.now() + serverClockOffset,
			Number(answerProblemType.value),
			result
		);
		let response;
		for (let attempt = 0; attempt < 2; attempt++) {
			if (
				String(currentLessonId.value) !== lessonAtSubmit ||
				String(answerProblemId.value) !== problemAtSubmit ||
				!canAnswerCurrentQuestion.value
			) return false;
			response = await requestLessonApi(`${baseUrl}/api/v3/lesson/problem/answer`, 'POST', payload, account);
			if (isSuccessfulApiResponse(response)) break;
			if (response.status !== -1 && response.status < 500) break;
			if (attempt === 0) await delay(650);
		}
		if (isSuccessfulApiResponse(response)) {
			addLog(`[成功] > ${displayName} | 题目答案已录入`, true);
			return true;
		}
		// Fix #5: 区分 403（lessonToken 过期需重新签到）和其他错误
		if (isLessonAuthFailure(response)) {
			const sourceAccount = accounts.value.find(item => (
				String(item.id || item.phone || item.uid) === String(account.id || account.phone || account.uid)
			));
			if (sourceAccount && String(sourceAccount.lessonId || '') === lessonAtSubmit) {
				sourceAccount.lessonToken = '';
				sourceAccount.lessonCredentialUpdatedAt = Date.now();
				saveAccounts();
				syncAnswerReceivers();
			}
			addLog(`[失败] > ${displayName} | 课堂凭证已过期(${response?.status || response?.data?.code || 'auth'})，需重新扫码签到`, false);
			return false;
		}
		const message = response?.data?.msg || response?.data?.message || (response?.status === -1 ? '网络连接超时' : `HTTP ${response?.status}`);
		addLog(`[失败] > ${displayName} | ${message}`, false);
		return false;
	};

	const runWithConcurrency = async (items, concurrency, worker) => {
		const results = new Array(items.length).fill(false);
		let cursor = 0;
		const runners = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
			while (cursor < items.length) {
				const index = cursor++;
				try {
					results[index] = await worker(items[index], index);
				} catch (error) {
					console.warn('[批量答题] 单账号任务异常', error);
					results[index] = false;
				}
			}
		});
		await Promise.all(runners);
		return results;
	};

	const doBatchAnswer = async () => {
		if (!canSubmitAnswer.value) return;
		const problemAtSubmit = String(answerProblemId.value);
		const lessonAtSubmit = String(currentLessonId.value);
		const receivers = answerReceivers.value.filter(receiver => receiver.checked && receiver.ready && !receiver.ai_mode);
		const result = buildAnswerResult();
		submittingAnswer.value = true;
		showProgressDialog.value = true;
		isProgressFinished.value = false;
		progressMsg.value = `正在向 ${receivers.length} 个账号提交题目 #${problemAtSubmit}`;
		runLogs.value = [];
		addLog(`[系统] 题目 #${problemAtSubmit} | ${questionTypeLabel.value} | 开始批量提交`, true);
		try {
			if (String(currentLessonId.value) !== lessonAtSubmit) return;
			const results = await runWithConcurrency(receivers, ANSWER_CONCURRENCY, account => executeSingleAnswerTask(account, result, lessonAtSubmit, problemAtSubmit));
			const successCount = results.filter(Boolean).length;
			const failedCount = receivers.length - successCount;
			progressMsg.value = `批量答题完成：成功 ${successCount}，失败 ${failedCount}`;
			addLog(`[完成] 成功 ${successCount}/${receivers.length}${failedCount ? `，${failedCount} 个账号可查看上方原因` : ''}`, failedCount === 0);
			if (String(answerProblemId.value) === problemAtSubmit && successCount > 0) {
				currentQuestion.value.submittedCount = successCount;
				isNewProblemDetected.value = false;
				monitorStatusText.value = `题目 #${problemAtSubmit} 已批量提交 ${successCount} 个账号`;
			}
		} finally {
			submittingAnswer.value = false;
			isProgressFinished.value = true;
		}
	};

	const onSlideCoverError = () => {
		if (currentQuestion.value.thumbnail && currentQuestion.value.cover !== currentQuestion.value.thumbnail) {
			currentQuestion.value.cover = currentQuestion.value.thumbnail;
		} else {
			currentQuestion.value.cover = '';
		}
	};

	const demoCourseware = [
		{
			title: '高等数学 · 极限与连续',
			slideIndex: 0,
			cover: '/static/demo-courseware/limit-intro.svg',
			body: '<div>设 <b>f(x)</b> 在 <i>x = 0</i> 附近有定义，下面哪项最能描述函数在一点处连续？</div>',
			options: [
				{ key: 'A', value: '函数在该点有定义，且左右极限相等并等于函数值', submitValue: 'A' },
				{ key: 'B', value: '函数图像经过该点即可', submitValue: 'B' },
				{ key: 'C', value: '函数导数存在', submitValue: 'C' }
			],
			type: 0
		},
		{
			title: '数据结构 · 二叉树遍历',
			slideIndex: 1,
			cover: '/static/demo-courseware/tree-traversal.svg',
			body: '<div>选择所有属于深度优先遍历的方式。</div>',
			options: [
				{ key: 'A', value: '先序遍历', submitValue: 'A' },
				{ key: 'B', value: '中序遍历', submitValue: 'B' },
				{ key: 'C', value: '后序遍历', submitValue: 'C' },
				{ key: 'D', value: '层序遍历', submitValue: 'D' }
			],
			type: 1
		},
		{
			title: '大学英语 · Academic Writing',
			slideIndex: 2,
			cover: '/static/demo-courseware/writing-structure.svg',
			body: '<div>Complete the sentence: A clear topic sentence helps readers understand the paragraph’s ______.</div>',
			options: [],
			blanks: [{}],
			type: 3
		}
	];
	let demoCoursewareIndex = -1;
	const loadDemoCourseware = () => {
		demoCoursewareIndex = (demoCoursewareIndex + 1) % demoCourseware.length;
		const demo = demoCourseware[demoCoursewareIndex];
		presentationFetchGeneration++;
		clearTimeout(presentationRetryTimer);
		answerProblemId.value = `DEMO-${demoCoursewareIndex + 1}`;
		answerProblemType.value = demo.type;
		currentQuestion.value = {
			...createEmptyQuestion(),
			id: answerProblemId.value,
			type: demo.type,
			body: demo.body,
			options: demo.options,
			blanks: demo.blanks || [],
			slideIndex: demo.slideIndex,
			cover: demo.cover,
			thumbnail: demo.cover,
			status: 'preview',
			isDemo: true
		};
		presentationTitle.value = demo.title;
		selectedAnswerValues.value = [];
		fillAnswers.value = Array.from({ length: Math.max(1, currentQuestion.value.blanks.length || 1) }, () => '');
		subjectiveAnswer.value = '';
		questionDeadline = null;
		questionUnlimited.value = false;
		questionRemaining.value = 0;
		monitorStatusText.value = `正在预览示例课件 ${demoCoursewareIndex + 1}/${demoCourseware.length}`;
	};

	const handleAppShow = () => {
		isAppInBackground = false;
		if (!isMonitoring.value) return;
		if (!socketOpened && !reconnectTimer) connectWebSocket();
		else {
			sendSocket({ op: 'detectlesson', lessonid: toWsScalar(currentLessonId.value) });
			requestProblemInfo();
		}
	};

	const handleAppHide = () => {
		isAppInBackground = true;
	};

	const handleNetworkChange = status => {
		if (status?.isConnected && isMonitoring.value && !socketOpened && !reconnectTimer) connectWebSocket();
	};

	if (typeof uni.onAppHide === 'function') uni.onAppHide(handleAppHide);
	if (typeof uni.onAppShow === 'function') uni.onAppShow(handleAppShow);
	if (typeof uni.onNetworkStatusChange === 'function') uni.onNetworkStatusChange(handleNetworkChange);

	// 冷启动自动恢复：上次有活跃课堂 + 有可用探针 → 自动连接 WebSocket
	const storedContextAge = Date.now() - Number(storedLessonContext.updatedAt || 0);
	if (currentLessonId.value && !lessonSessionEnded.value && storedContextAge >= 0 && storedContextAge < 6 * 60 * 60 * 1000) {
		restoreTimer = setTimeout(() => {
			restoreTimer = null;
			if (!isMonitoring.value && currentLessonId.value && getProbeAccount()) {
				console.log('[自动恢复] 检测到上次活跃课堂', currentLessonId.value, '，自动启动监控');
				startProblemMonitor(currentLessonId.value);
			}
		}, 1500);
	}

	onUnmounted(() => {
		manualSocketClose = true;
		if (reconnectTimer) clearTimeout(reconnectTimer);
		if (probeFailoverTimer) clearTimeout(probeFailoverTimer);
		if (restoreTimer) clearTimeout(restoreTimer);
		if (presentationRetryTimer) clearTimeout(presentationRetryTimer);
		if (countdownTimer) clearInterval(countdownTimer);
		closeSocketTask();
		releaseWakeLock();
		if (typeof uni.offAppHide === 'function') uni.offAppHide(handleAppHide);
		if (typeof uni.offAppShow === 'function') uni.offAppShow(handleAppShow);
		if (typeof uni.offNetworkStatusChange === 'function') uni.offNetworkStatusChange(handleNetworkChange);
	});

	return {
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
		hasPreparedAnswer,
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
	};
}
