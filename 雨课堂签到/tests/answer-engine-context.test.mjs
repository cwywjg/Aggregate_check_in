import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const utilitySource = (await readFile(new URL('../pages/index/answer-engine-utils.js', import.meta.url), 'utf8'))
	.replace(/export\s+/g, '');
const engineSource = (await readFile(new URL('../pages/index/answer-engine.js', import.meta.url), 'utf8'))
	.replace(/^import[^\n]+\n/gm, '');
const runtime = `
const ref = value => ({ value });
const computed = getter => ({ get value() { return getter(); } });
const onUnmounted = () => {};
${utilitySource}
${engineSource}
`;
const { createAnswerEngine } = await import(`data:text/javascript;base64,${Buffer.from(runtime).toString('base64')}`);
const ref = value => ({ value });

const storage = new Map();
const socketHandlers = {};
const socketFrames = [];
const socketUrls = [];
globalThis.setInterval = callback => ({ callback });
globalThis.clearInterval = () => {};
globalThis.uni = {
	getStorageSync: key => storage.get(key) || '',
	setStorageSync: (key, value) => storage.set(key, value),
	showToast: () => {},
	onAppShow: () => {},
	onNetworkStatusChange: () => {},
	offAppShow: () => {},
	offNetworkStatusChange: () => {},
	request: () => {},
	connectSocket: options => {
		socketUrls.push(options.url);
		return ({
		send: ({ data }) => socketFrames.push(JSON.parse(data)),
		close: () => {},
		onOpen: callback => { socketHandlers.open = callback; },
		onMessage: callback => { socketHandlers.message = callback; },
		onError: callback => { socketHandlers.error = callback; },
		onClose: callback => { socketHandlers.close = callback; }
		});
	}
};

const accounts = ref([
	{ id: 1, phone: '1', uid: 1, cookie: 'a=1', lessonToken: 'token-a', lessonId: '100', expired: false },
	{ id: 2, phone: '2', uid: 2, cookie: 'a=2', lessonToken: 'token-b', lessonId: '200', expired: false },
	{ id: 3, phone: '3', uid: 3, cookie: 'a=3', lessonToken: 'token-c', lessonId: '200', expired: false, ai_mode: true }
]);
const engine = createAnswerEngine({
	accounts,
	currentTab: ref('home'),
	baseUrl: 'https://www.yuketang.cn',
	generateDeviceProfile: () => ({}),
	saveAccounts: () => {},
	addLog: () => {},
	showProgressDialog: ref(false),
	isProgressFinished: ref(false),
	progressMsg: ref(''),
	runLogs: ref([])
});

engine.bindLessonContext('100', { courseName: '课程 A', title: '场次 A' });
engine.syncAnswerReceivers();
assert.equal(engine.currentLessonDisplayName.value, '课程 A');
assert.equal(engine.answerReceivers.value[0].ready, true);
assert.equal(engine.answerReceivers.value[1].ready, false);
assert.match(engine.answerReceivers.value[1].readyReason, /其他课堂/);

engine.bindLessonContext('200', { courseName: '课程 B', wssUrl: 'wss://live.yuketang.cn/wsapp/' });
engine.syncAnswerReceivers();
assert.equal(engine.currentLessonId.value, '200');
assert.equal(engine.answerReceivers.value[0].ready, false);
assert.equal(engine.answerReceivers.value[1].ready, true);
assert.equal(engine.answerReceivers.value[2].ready, true);
assert.equal(engine.answerReceivers.value[2].checked, false, 'AI 托管账号必须排除在手动提交选择之外');
assert.equal(engine.aiHostedReceiversCount.value, 1);
assert.equal(JSON.parse(storage.get('last_lesson_context_v2')).id, '200');

assert.equal(engine.startProblemMonitor('200'), true);
assert.equal(socketUrls[0], 'wss://live.yuketang.cn/wsapp/');
socketHandlers.open();
assert.deepEqual(socketFrames[0], { op: 'hello', userid: 2, role: 'student', auth: 'token-b', lessonid: 200 });

socketHandlers.message({ data: JSON.stringify({ op: 'unlockproblem', lessonid: 100, problem: { prob: 7, type: 'multiple' } }) });
assert.equal(engine.answerProblemId.value, '', '其他课堂的 WebSocket 题目必须被忽略');
socketHandlers.message({ data: JSON.stringify({
	op: 'hello',
	code: 0,
	data: {
		lessonid: 200,
		presentation_id: 'pres-live',
		sid: 'slide-live',
		si: 4,
		unlockedproblem: [7]
	}
}) });
assert.equal(engine.answerProblemId.value, '7', '重连 hello 必须恢复嵌套 data 中的未关闭题目');
assert.equal(socketFrames.at(-1).op, 'probleminfo');
assert.equal(socketFrames.at(-1).problemid, 7);
const framesBeforeProblemInfo = socketFrames.length;
socketHandlers.message({ data: JSON.stringify({
	op: 'probleminfo',
	lessonid: 200,
	problem: {
		problemid: 7,
		problemType: 0,
		body: '恢复后的题干',
		options: [{ key: 'A', value: '甲' }, { key: 'B', value: '乙' }]
	}
}) });
assert.match(engine.currentQuestion.value.body, /恢复后的题干/);
assert.equal(engine.displayedQuestionOptions.value.length, 2);
assert.equal(socketFrames.length, framesBeforeProblemInfo, 'probleminfo 响应不能递归请求自身');
socketHandlers.message({ data: JSON.stringify({ op: 'unlockproblem', lessonid: 200, problem: { prob: 8, type: 'multiple', limit: -1 } }) });
assert.equal(engine.answerProblemId.value, '8');
assert.equal(engine.answerProblemType.value, 1, 'multiple 必须映射到官方 problemType=1');
assert.equal(engine.displayedQuestionOptions.value.length, 0, '元数据缺失时不得伪造 A-F 选项');
socketHandlers.message({ data: JSON.stringify({ op: 'unlockproblem', lessonid: 200, problem: { prob: 9, type: 'single', limit: 30 } }) });
assert.equal(engine.answerProblemId.value, '9');
assert.equal(engine.questionCountdownText.value, '00:30', '新题不能继承上一题的无限时/旧截止时间');
socketHandlers.message({ data: JSON.stringify({
	op: 'unlockproblem',
	lessonid: 200,
	problem: { prob: 10, type: 'fill_blank', limit_time: -1, blanks: [{}, {}] }
}) });
assert.equal(engine.fillAnswers.value.length, 2);
engine.setFillAnswer(0, '第一空');
assert.equal(engine.hasPreparedAnswer.value, false, '填空题不能带着未填写的空提交');
engine.setFillAnswer(1, '第二空');
assert.equal(engine.hasPreparedAnswer.value, true);
socketHandlers.message({ data: JSON.stringify({
	op: 'unlockproblem',
	lessonid: 200,
	problem: {
		prob: 11,
		type: 'vote',
		limit: -1,
		pollingCount: 2,
		options: [{ key: 'A', value: '甲' }, { key: 'B', value: '乙' }, { key: 'C', value: '丙' }]
	}
}) });
engine.selectQuestionOption(engine.displayedQuestionOptions.value[0]);
engine.selectQuestionOption(engine.displayedQuestionOptions.value[1]);
engine.selectQuestionOption(engine.displayedQuestionOptions.value[2]);
assert.equal(engine.isOptionSelected('A'), true);
assert.equal(engine.isOptionSelected('B'), true);
assert.equal(engine.isOptionSelected('C'), false, '投票题选择数必须受 pollingCount 限制');
socketHandlers.message({ data: JSON.stringify({ op: 'lessonfinished', lessonid: 200 }) });
assert.equal(engine.lessonSessionEnded.value, true);
assert.equal(engine.isMonitoring.value, false);
assert.equal(engine.currentLessonId.value, '');
assert.equal(engine.answerProblemId.value, '');
assert.equal(engine.wsStatusText.value, '课堂已结束');
assert.equal(storage.get('last_lesson_id'), '');
assert.equal(accounts.value[0].lessonToken, 'token-a', '课堂结束只清理当前 lessonId 的凭证');
assert.equal(accounts.value[1].lessonToken, '');

engine.bindLessonContext('300', { courseName: '课程 C' });
assert.equal(engine.lessonSessionEnded.value, false);
assert.equal(engine.currentLessonId.value, '300');

engine.loadDemoCourseware();
assert.equal(engine.currentQuestion.value.isDemo, true);
assert.equal(engine.presentationTitle.value, '高等数学 · 极限与连续');
assert.match(engine.currentQuestion.value.cover, /limit-intro\.svg$/);
assert.equal(engine.canAnswerCurrentQuestion.value, false, '示例课件只用于界面预览，不触发提交');
engine.loadDemoCourseware();
assert.equal(engine.answerProblemType.value, 1);
engine.loadDemoCourseware();
assert.equal(engine.answerProblemType.value, 3);

console.log('answer-engine-context: 50 assertions passed');
