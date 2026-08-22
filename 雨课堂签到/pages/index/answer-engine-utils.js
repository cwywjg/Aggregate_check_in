const firstDefined = (...values) => values.find(value => value !== undefined && value !== null && value !== '');

const numeric = value => {
	if (value === '' || value === undefined || value === null) return null;
	const result = Number(value);
	return Number.isFinite(result) ? result : null;
};

const asObject = value => value && typeof value === 'object' && !Array.isArray(value) ? value : {};

export const createLessonBatchContext = ({ mode = 'batch', expectedLessonId = '' } = {}) => ({
	mode,
	lessonId: String(expectedLessonId || ''),
	startedAt: Date.now()
});

export const lockLessonForBatch = (context, lessonId) => {
	const resolvedLessonId = String(lessonId || '');
	if (!resolvedLessonId) return { accepted: false, reason: 'lesson_id_missing', lessonId: '' };
	if (!context.lessonId) context.lessonId = resolvedLessonId;
	if (String(context.lessonId) !== resolvedLessonId) {
		return { accepted: false, reason: 'lesson_mismatch', lessonId: resolvedLessonId, expectedLessonId: String(context.lessonId) };
	}
	return { accepted: true, lessonId: resolvedLessonId, expectedLessonId: String(context.lessonId) };
};

export const unwrapApiData = body => {
	const source = asObject(body);
	return asObject(source.data);
};

const normalizeTeacherName = teacher => {
	if (typeof teacher === 'string') return teacher;
	const value = asObject(teacher);
	return String(firstDefined(value.name, value.identityName, value.teacherName, '') || '');
};

/**
 * /api/v3/lesson/detail 的字段在不同 App 版本中有一层 data 或 data.data 包装。
 * 本解析器只接受 expectedLessonId 对应的元数据，避免旧 lessonToken 的响应污染当前课堂。
 */
export const extractLessonMetadata = (body, expectedLessonId = '') => {
	const levelOne = unwrapApiData(body);
	const data = Object.keys(asObject(levelOne.data)).length ? asObject(levelOne.data) : levelOne;
	const basic = asObject(firstDefined(data.basic, data.lesson, data.lessonInfo, {}));
	const classroom = asObject(firstDefined(data.classroom, data.course, data.classInfo, {}));
	const lessonId = String(firstDefined(
		basic.lessonId,
		basic.lesson_id,
		data.lessonId,
		data.lesson_id,
		expectedLessonId,
		''
	) || '');
	if (expectedLessonId && lessonId && String(expectedLessonId) !== lessonId) return null;
	const rawStatus = firstDefined(basic.status, basic.lessonStatus, data.status, data.lessonStatus, '');
	const ended = basic.isEnd === true
		|| basic.ended === true
		|| data.isEnd === true
		|| data.ended === true
		|| /(finish|ended|closed|已结束|已关闭)/i.test(String(rawStatus || ''));

	return {
		id: lessonId,
		title: String(firstDefined(basic.title, data.title, '') || ''),
		courseName: String(firstDefined(classroom.courseName, classroom.course_name, data.courseName, '') || ''),
		classroomName: String(firstDefined(classroom.name, classroom.classroomName, data.classroomName, '') || ''),
		teacherName: normalizeTeacherName(firstDefined(basic.teacher, data.teacher, '')),
		startTime: firstDefined(basic.startTime, basic.start_time, data.startTime, null),
		endTime: firstDefined(basic.endTime, basic.end_time, data.endTime, null),
		status: String(rawStatus || ''),
		ended,
		wssUrl: String(firstDefined(
			basic.wssUrl,
			basic.wsUrl,
			basic.websocketUrl,
			data.wssUrl,
			data.wsUrl,
			data.websocketUrl,
			data.socketUrl,
			''
		) || ''),
		updatedAt: Date.now()
	};
};

export const resolveOfficialWebSocketUrl = (candidate, fallbackBaseUrl = '') => {
	const normalize = (value, officialOnly) => {
		let raw = String(value || '').trim();
		if (!raw) return '';
		if (raw.startsWith('//')) raw = `wss:${raw}`;
		else if (/^https:\/\//i.test(raw)) raw = raw.replace(/^https:/i, 'wss:');
		else if (/^http:\/\//i.test(raw)) raw = raw.replace(/^http:/i, 'ws:');
		else if (!/^wss?:\/\//i.test(raw)) raw = `wss://${raw}`;
		try {
			const parsed = new URL(raw);
			if (!['wss:', 'ws:'].includes(parsed.protocol)) return '';
			const host = parsed.hostname.toLowerCase().replace(/\.$/, '');
			if (officialOnly && host !== 'yuketang.cn' && !host.endsWith('.yuketang.cn')) return '';
			if (!parsed.pathname || parsed.pathname === '/') parsed.pathname = '/wsapp/';
			return parsed.toString();
		} catch (_) {
			return '';
		}
	};
	return normalize(candidate, true) || normalize(fallbackBaseUrl, false);
};

const problemIdOf = source => {
	const value = asObject(source);
	return firstDefined(
		value.problemId,
		value.problem_id,
		value.problemid,
		value.prob,
		value.spid,
		typeof value.problem === 'object' ? problemIdOf(value.problem) : value.problem
	);
};

const presentationPayload = body => {
	const root = asObject(body);
	const first = Object.keys(asObject(root.data)).length ? asObject(root.data) : root;
	return Object.keys(asObject(first.data)).length && !Array.isArray(first.slides)
		? asObject(first.data)
		: first;
};

const presentationSlides = data => {
	const presentation = asObject(data.presentation);
	const presentationData = asObject(data.presentationData);
	return [data.slides, presentation.slides, presentationData.slides].find(Array.isArray) || [];
};

const locateSlide = (slides, problemId, slideId, slideIndex) => {
	if (!slides.length) return null;
	const wantedProblemId = String(problemId || '');
	if (wantedProblemId) {
		const match = slides.find(slide => String(problemIdOf(asObject(slide).problem) || '') === wantedProblemId);
		if (match) return match;
	}
	const wantedSlideId = String(slideId ?? '');
	if (wantedSlideId) {
		const match = slides.find(slide => [slide?.id, slide?.lessonSlideID, slide?.lesson_slide_id]
			.some(value => String(value ?? '') === wantedSlideId));
		if (match) return match;
	}
	const index = numeric(slideIndex);
	if (index !== null) return slides.find(slide => Number(slide?.index) === index) || slides[index] || null;
	return null;
};

const findTopLevelProblem = (data, problemId) => {
	const problems = [data.problems, data.presentation?.problems, data.presentationData?.problems].find(Array.isArray) || [];
	return problems.find(problem => String(problemIdOf(problem) || '') === String(problemId || '')) || null;
};

const resourceString = value => {
	if (typeof value === 'string') return value.trim();
	if (!value || typeof value !== 'object') return '';
	return resourceString(firstDefined(
		value.url,
		value.URL,
		value.src,
		value.path,
		value.cover,
		value.coverAlt,
		value.thumbnail,
		value.thumb,
		''
	));
};

export const normalizeCoursewareResourceUrl = (value, baseUrl) => {
	const url = resourceString(value);
	if (!url) return '';
	if (/^(https?:|data:|blob:|file:|wxfile:|_doc\/)/i.test(url)) return url;
	if (url.startsWith('//')) return `https:${url}`;
	return `${String(baseUrl || '').replace(/\/$/, '')}${url.startsWith('/') ? '' : '/'}${url}`;
};

const shapeResource = shapes => {
	if (!Array.isArray(shapes)) return '';
	for (const shape of shapes) {
		const value = asObject(shape);
		const direct = resourceString(firstDefined(value.URL, value.url, value.src, value.image, value.picture, ''));
		if (direct) return direct;
		const nested = shapeResource(firstDefined(value.shapes, value.children, []));
		if (nested) return nested;
	}
	return '';
};

/**
 * 同时兼容新模型的 slides[].problem 与旧响应的顶层 problems[].slideIndex，
 * 并按 cover -> coverAlt -> thumbnail -> shapes 图片的顺序挑选课件画面。
 */
export const extractPresentationFrame = (body, selectors = {}, baseUrl = '') => {
	const data = presentationPayload(body);
	const slides = presentationSlides(data);
	let problem = findTopLevelProblem(data, selectors.problemId);
	let slide = locateSlide(slides, selectors.problemId, selectors.slideId, selectors.slideIndex);

	if (!slide && problem) {
		slide = locateSlide(slides, selectors.problemId, firstDefined(problem.slideId, problem.lessonSlideID, ''), problem.slideIndex);
	}
	if (!problem && slide && typeof slide.problem === 'object') problem = slide.problem;
	if (!slide) return { data, slides, slide: null, problem: problem || {}, title: '', cover: '', thumbnail: '' };

	const thumbnail = normalizeCoursewareResourceUrl(firstDefined(slide.thumbnail, slide.thumb, ''), baseUrl);
	const cover = normalizeCoursewareResourceUrl(firstDefined(
		slide.cover,
		slide.coverAlt,
		slide.thumbnail,
		shapeResource(slide.shapes),
		asObject(problem).cover,
		asObject(problem).image,
		''
	), baseUrl);
	return {
		data,
		slides,
		slide,
		problem: asObject(problem),
		title: String(firstDefined(data.title, data.name, data.presentation?.title, '') || ''),
		cover,
		thumbnail
	};
};
