'use strict';

const { parseAscendcSignaturesFromContent } = require('./ascendc-signatures');

function escapeRegex(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function extractSection(content, heading) {
    const match = content.match(new RegExp(`(?:^|\\n)## ${escapeRegex(heading)}\\s*\\n([\\s\\S]*?)(?=\\n## |$)`, 'u'));
    return match ? match[1].trim() : '';
}

function normalizeMemberNames(apiName, memberApis) {
    const names = (memberApis || []).map(member => typeof member === 'string' ? member : member.name).filter(Boolean);
    if (names.length === 0) names.push(apiName);
    return [...new Set(names)];
}

function collectApiSignatures(content, apiNames) {
    const names = new Set(Array.isArray(apiNames) ? apiNames : [apiNames]);
    return parseAscendcSignaturesFromContent(content)
        .filter(signature => names.has(signature.funcName));
}

function normalizePrototypeSemicolons({ apiName, memberApis, prototypeDoc, finalDoc, callingConvention }) {
    const memberNames = normalizeMemberNames(apiName, memberApis);
    const memberSet = new Set(memberNames);
    const expectedKeys = new Set(collectApiSignatures(prototypeDoc, memberNames)
        .filter(signature => !callingConvention || signature.callingConvention === callingConvention)
        .map(signature => signature.key));
    const sectionPattern = /((?:^|\n)## 函数原型\s*\n)([\s\S]*?)(?=\n## |$)/u;

    return finalDoc.replace(sectionPattern, (section, heading, body) => {
        const normalizedBody = body.replace(/(```(?:cpp|c\+\+|c)?\s*\n)([\s\S]*?)(```)/gi,
            (block, opening, code, closing) => {
                const lines = code.split(/\r?\n/);
                const normalizedCode = lines.map((line, index) => {
                    if (/;\s*$/.test(line) || !/\)\s*$/.test(line)) return line;
                    const candidateLine = line.replace(/\s*$/, ';');
                    const previousLine = index > 0 ? lines[index - 1] : '';
                    const candidate = /^\s*template\s*</.test(previousLine)
                        ? `${previousLine}\n${candidateLine}`
                        : candidateLine;
                    const signatures = parseAscendcSignaturesFromContent(candidate)
                        .filter(signature => memberSet.has(signature.funcName) &&
                            (!callingConvention || signature.callingConvention === callingConvention));
                    return signatures.length === 1 && expectedKeys.has(signatures[0].key) ? candidateLine : line;
                }).join('\n');
                return `${opening}${normalizedCode}${closing}`;
            });
        return `${heading}${normalizedBody}`;
    });
}

function validatePrototypeCompleteness({ apiName, memberApis, prototypeDoc, finalDoc, callingConvention }) {
    const prototypeSection = extractSection(finalDoc, '函数原型');
    if (!prototypeSection) throw new Error('最终文档缺少“## 函数原型”章节');
    if (/^#{3,6}\s+/m.test(prototypeSection)) {
        throw new Error('函数原型章节禁止包含子标题，请使用普通列表项组织原型');
    }
    if (/参数集合(?:为)?\s*(?:<code>|[A-Za-z_])/.test(prototypeSection)) {
        throw new Error('函数原型禁止使用参数集合进行机械分组，请使用有代码证据的功能模式名称或真实函数名');
    }

    const memberNames = normalizeMemberNames(apiName, memberApis);
    const memberSet = new Set(memberNames);
    const expected = collectApiSignatures(prototypeDoc, memberNames);
    const allActual = parseAscendcSignaturesFromContent(prototypeSection);
    const actual = allActual.filter(signature => memberSet.has(signature.funcName));
    const unexpectedMembers = allActual.filter(signature => !memberSet.has(signature.funcName));
    if (expected.length === 0) throw new Error(`0_prototype.md中未解析到文档成员 ${memberNames.join(', ')} 的原型`);

    for (const memberName of memberNames) {
        if (!expected.some(signature => signature.funcName === memberName)) {
            throw new Error(`0_prototype.md缺少文档成员 ${memberName} 的原型`);
        }
    }

    const expectedKeys = new Set(expected.map(signature => signature.key));
    const actualKeys = new Set(actual.map(signature => signature.key));
    const missing = expected.filter(signature => !actualKeys.has(signature.key));
    const extra = actual.filter(signature => !expectedKeys.has(signature.key));
    if (actual.length !== expected.length || missing.length > 0 || extra.length > 0 || unexpectedMembers.length > 0) {
        const details = [`函数原型不完整：0_prototype.md为${expected.length}个，最终文档为${actual.length}个`];
        if (missing.length > 0) details.push(`缺少${missing.length}个原型`);
        if (extra.length > 0) details.push(`多出或被改写${extra.length}个原型`);
        if (unexpectedMembers.length > 0) {
            details.push(`混入非文档成员原型：${[...new Set(unexpectedMembers.map(item => item.funcName))].join(', ')}`);
        }
        throw new Error(details.join('；'));
    }

    const memberPattern = new RegExp(`\\b(?:${memberNames.map(escapeRegex).join('|')})\\s*\\(`);
    const declarationLines = prototypeSection.split(/\r?\n/).filter(line => memberPattern.test(line));
    if (declarationLines.length !== expected.length || declarationLines.some(line => !/;\s*$/.test(line))) {
        throw new Error('函数原型格式错误：每个函数声明必须独占一行并保留末尾分号');
    }

    if (callingConvention) {
        const mismatched = actual.filter(signature => signature.callingConvention !== callingConvention);
        if (mismatched.length > 0) {
            throw new Error(`最终文档混入${mismatched.length}个非${callingConvention}调用约定原型`);
        }
    }
    if (/以[^\n]{0,40}为例|其余类型同|同样包含/.test(prototypeSection)) {
        throw new Error('函数原型章节使用了代表性原型压缩表述，必须逐个展示0_prototype.md中的全部原型');
    }
}
function requiredExampleMemberNames(apiName, memberApis) {
    const requiredMembers = (memberApis || []).filter(member =>
        typeof member === 'string' || member.relation !== 'source-document-group');
    return normalizeMemberNames(apiName, requiredMembers);
}

function validateCallExample(finalDoc, apiName, memberApis) {
    const section = extractSection(finalDoc, '调用示例');
    if (!section) throw new Error('最终文档缺少“## 调用示例”章节');

    const codeBlocks = [...section.matchAll(/```(?:cpp|c\+\+|c)?\s*\n([\s\S]*?)```/gi)]
        .map(match => match[1]);
    if (/【待开发补齐】缺少可验证调用示例/.test(section)) {
        throw new Error('调用示例不能使用缺失占位，必须根据代码生成模型示例');
    }
    if (codeBlocks.length === 0) {
        throw new Error('调用示例没有代码块，必须根据代码生成模型示例');
    }

    const code = codeBlocks.join('\n');
    if (/\.\.\.|=\s*\.\.\.|伪地址/.test(code)) throw new Error('调用示例包含省略号或伪地址占位内容');
    if (/(?:__cbuf__|__gm__|__ubuf__|__ca__|__cb__|__cc__)\s+[^;\n=]+\b[A-Za-z_]\w*\s*;/.test(code)) {
        throw new Error('调用示例包含未初始化的地址空间指针');
    }
    const memberNames = requiredExampleMemberNames(apiName, memberApis);
    const missingMembers = memberNames.filter(memberName =>
        !new RegExp(`\\b${escapeRegex(memberName)}\\s*\\(`).test(code));
    if (missingMembers.length > 0) {
        throw new Error(`调用示例代码块未覆盖文档成员：${missingMembers.join(', ')}`);
    }
    if (!/结果示例如下：\s*\n\s*```text[\s\S]*?```/u.test(section)) {
        throw new Error('存在调用示例代码时，必须提供text代码块格式的结果示例');
    }
}

function mapOutsideFencedCodeBlocks(content, transform) {
    const fencePattern = /```[\s\S]*?```/g;
    let cursor = 0;
    let result = '';

    for (const match of content.matchAll(fencePattern)) {
        result += transform(content.slice(cursor, match.index));
        result += match[0];
        cursor = match.index + match[0].length;
    }
    return result + transform(content.slice(cursor));
}

function validateTableSyntax(finalDoc) {
    const groupedProse = finalDoc.replace(/\x60\x60\x60[\s\S]*?\x60\x60\x60/g, '');
    if (/参数集合(?:为)?\s*(?:<code>|[A-Za-z_])/.test(groupedProse)) {
        throw new Error('最终文档禁止使用参数集合进行机械分组，请使用有代码证据的功能模式名称或真实函数名');
    }
    const parameterSection = extractSection(finalDoc, '参数说明');
    if (/\$[^\n$]+\$|\\le\b|\\ge\b|\\_[A-Za-z0-9]/.test(parameterSection)) {
        throw new Error('参数说明表格包含不允许的LaTeX表达');
    }

    const prose = finalDoc.replace(/```[\s\S]*?```/g, '');
    if (/`[^`\n]+`/.test(prose)) {
        throw new Error('最终正文包含Markdown行内代码，请改用<code>...</code>');
    }

    const htmlTables = [...finalDoc.matchAll(/<table\b[\s\S]*?<\/table>/gi)].map(match => match[0]);
    for (const table of htmlTables) {
        if (/\*\*[^*\n]+\*\*/.test(table) || /\[[^\]\n]+\]\([^\)\n]+\)/.test(table)) {
            throw new Error('HTML表格内包含Markdown强调或链接语法，请使用对应HTML标签');
        }
    }
}

function normalizeInlineCodeOutsideFences(content) {
    return mapOutsideFencedCodeBlocks(content, prose =>
        prose.replace(/`([^`\n]+)`/g, '<code>$1</code>'));
}

function normalizeInlineCodeInHtmlTables(content) {
    return content.replace(/<table\b[\s\S]*?<\/table>/gi, table =>
        table.replace(/`([^`\n]+)`/g, '<code>$1</code>'));
}
function validateFinalDocument(options) {
    validatePrototypeCompleteness(options);
    validateCallExample(options.finalDoc, options.apiName, options.memberApis);
    validateTableSyntax(options.finalDoc);
}

module.exports = {
    collectApiSignatures,
    extractSection,
    normalizeInlineCodeInHtmlTables,
    normalizeInlineCodeOutsideFences,
    normalizeMemberNames,
    normalizePrototypeSemicolons,
    validateCallExample,
    validateFinalDocument,
    validatePrototypeCompleteness,
    validateTableSyntax,
};
