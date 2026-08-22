import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../pages/index/answer-engine-utils.js', import.meta.url), 'utf8');
const utils = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

const lesson = utils.extractLessonMetadata({
	code: 0,
	data: {
		basic: { lessonId: 9527, title: '第 6 次课', teacher: { name: '张老师' } },
		classroom: { name: '2026 春季班', courseName: '高等数学' }
	}
}, '9527');
assert.deepEqual(
	{ id: lesson.id, title: lesson.title, courseName: lesson.courseName, classroomName: lesson.classroomName, teacherName: lesson.teacherName },
	{ id: '9527', title: '第 6 次课', courseName: '高等数学', classroomName: '2026 春季班', teacherName: '张老师' }
);
assert.equal(utils.extractLessonMetadata({ data: { basic: { lessonId: 7 } } }, '8'), null, '其他课堂详情必须被隔离');
const websocketLesson = utils.extractLessonMetadata({
	data: {
		basic: {
			lessonId: 9527,
			wssUrl: 'wss://live.yuketang.cn/wsapp/'
		}
	}
}, '9527');
assert.equal(websocketLesson.wssUrl, 'wss://live.yuketang.cn/wsapp/');
assert.equal(
	utils.extractLessonMetadata({ data: { basic: { lessonId: 9527, status: 'finished' } } }, '9527').ended,
	true
);
assert.equal(
	utils.resolveOfficialWebSocketUrl('https://live.yuketang.cn/', 'https://changjiang.yuketang.cn'),
	'wss://live.yuketang.cn/wsapp/'
);
assert.equal(
	utils.resolveOfficialWebSocketUrl('wss://evil.example/wsapp/', 'https://changjiang.yuketang.cn'),
	'wss://changjiang.yuketang.cn/wsapp/'
);

const directFrame = utils.extractPresentationFrame({
	success: true,
	data: {
		title: '函数极限',
		slides: [{
			index: 3,
			lessonSlideID: 'slide-4',
			cover: '//rain-private-qn.yuketang.cn/slide-4.png',
			problem: { problemId: 'p-1', problemType: 1, options: [{ key: 'A', value: '1' }] }
		}]
	}
}, { problemId: 'p-1' }, 'https://www.yuketang.cn');
assert.equal(directFrame.title, '函数极限');
assert.equal(directFrame.slide.lessonSlideID, 'slide-4');
assert.equal(directFrame.problem.problemType, 1);
assert.equal(directFrame.cover, 'https://rain-private-qn.yuketang.cn/slide-4.png');

const shapeFrame = utils.extractPresentationFrame({
	data: {
		slides: [{ id: 12, index: 0, shapes: [{ URL: '/media/first-slide.jpg' }] }],
		problems: [{ problemId: 99, problemType: 0, slideIndex: 0 }]
	}
}, { problemId: 99 }, 'https://www.yuketang.cn');
assert.equal(shapeFrame.slide.id, 12);
assert.equal(shapeFrame.problem.problemId, 99);
assert.equal(shapeFrame.cover, 'https://www.yuketang.cn/media/first-slide.jpg');

const objectResource = utils.normalizeCoursewareResourceUrl({ src: 'https://fe-static-yuketang.yuketang.cn/a.png' }, 'https://www.yuketang.cn');
assert.equal(objectResource, 'https://fe-static-yuketang.yuketang.cn/a.png');

const rescueBatch = utils.createLessonBatchContext({ mode: 'rescue', expectedLessonId: '9527' });
assert.equal(utils.lockLessonForBatch(rescueBatch, '9527').accepted, true);
assert.equal(utils.lockLessonForBatch(rescueBatch, '9528').accepted, false);
assert.equal(rescueBatch.lessonId, '9527', '其他账号的扫码结果不得改写补签批次课堂');

const freshBatch = utils.createLessonBatchContext();
assert.equal(utils.lockLessonForBatch(freshBatch, '10001').accepted, true);
assert.equal(freshBatch.lessonId, '10001');

console.log('answer-engine-utils: 20 assertions passed');
