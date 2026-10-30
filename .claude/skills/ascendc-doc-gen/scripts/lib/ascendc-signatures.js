'use strict';

const CALLING_CONVENTIONS = [
    '__aicore__',
    '__simd_callee__',
    '__SIMT_DEVICE_FUNCTIONS_DECL__',
    'unqualified'
];

function removeComments(source) {
    return source
        .replace(/\/\/.*$/gm, '')
        .replace(/\/\*[\s\S]*?\*\//g, '');
}

function normalizeSpaces(value) {
    return value.replace(/\s+/g, ' ').trim();
}

// Split only at the outermost level so template arguments remain intact.
function splitTopLevel(value, delimiter = ',') {
    const parts = [];
    let start = 0;
    let quote = '';
    let escaped = false;
    const depth = { '(': 0, '[': 0, '{': 0, '<': 0 };
    const closing = { ')': '(', ']': '[', '}': '{', '>': '<' };
    for (let index = 0; index < value.length; index++) {
        const char = value[index];
        if (quote) {
            if (escaped) escaped = false;
            else if (char === '\\') escaped = true;
            else if (char === quote) quote = '';
            continue;
        }
        if (char === '"' || char === "'") {
            quote = char;
            continue;
        }
        if (Object.prototype.hasOwnProperty.call(depth, char)) depth[char]++;
        else if (Object.prototype.hasOwnProperty.call(closing, char)) {
            const open = closing[char];
            if (depth[open] > 0) depth[open]--;
        } else if (char === delimiter && Object.values(depth).every(item => item === 0)) {
            parts.push(value.slice(start, index).trim());
            start = index + 1;
        }
    }
    const tail = value.slice(start).trim();
    if (tail || parts.length > 0) parts.push(tail);
    return parts;
}

function stripTopLevelDefaultValue(param) {
    let quote = '';
    let escaped = false;
    const depth = { '(': 0, '[': 0, '{': 0, '<': 0 };
    const closing = { ')': '(', ']': '[', '}': '{', '>': '<' };
    for (let index = 0; index < param.length; index++) {
        const char = param[index];
        if (quote) {
            if (escaped) escaped = false;
            else if (char === '\\') escaped = true;
            else if (char === quote) quote = '';
            continue;
        }
        if (char === '"' || char === "'") {
            quote = char;
            continue;
        }
        if (Object.prototype.hasOwnProperty.call(depth, char)) {
            depth[char]++;
            continue;
        }
        if (Object.prototype.hasOwnProperty.call(closing, char)) {
            const open = closing[char];
            if (depth[open] > 0) depth[open]--;
            continue;
        }
        if (char === '=' && Object.values(depth).every(item => item === 0)) {
            return param.slice(0, index).trim();
        }
    }
    return param.trim();
}

function extractParameterName(param) {
    const declaration = stripTopLevelDefaultValue(param)
        .replace(/\[\s*[^\]]*\s*\]\s*$/g, '')
        .trim();
    if (!declaration || declaration === 'void') return '';

    const functionPointer = declaration.match(/\(\s*[*&]\s*([A-Za-z_]\w*)\s*\)/);
    if (functionPointer) return functionPointer[1];
    const match = declaration.match(/([A-Za-z_]\w*)\s*$/);
    return match ? match[1] : '';
}

function getParameterNames(rawParams) {
    if (!rawParams || rawParams === 'void') return [];
    return splitTopLevel(rawParams).map(extractParameterName);
}

function signatureShapeKey(signature) {
    return [
        normalizeSpaces(signature.templateParams || ''),
        normalizeSpaces(signature.qualifiers || ''),
        normalizeSpaces(signature.returnType || ''),
        normalizeSpaces(signature.rawParams || '')
    ].join('|');
}

function findClosingParen(source, openParenIdx) {
    let depth = 1;
    let closeParenIdx = openParenIdx + 1;
    while (closeParenIdx < source.length && depth > 0) {
        if (source[closeParenIdx] === '(') depth++;
        if (source[closeParenIdx] === ')') depth--;
        closeParenIdx++;
    }
    return depth === 0 ? closeParenIdx - 1 : -1;
}

function getCallingConvention(qualifiers) {
    for (const convention of CALLING_CONVENTIONS.slice(0, -1)) {
        if (new RegExp(`(?:^|\\s)${convention}(?:\\s|$)`).test(qualifiers)) {
            return convention;
        }
    }
    return 'unqualified';
}

function parseAscendcSignaturesFromContent(content) {
    const source = removeComments(content);
    const results = [];

    function addSignature({ templateParams = '', qualifiers = '', returnType, funcName, openParenIdx }) {
        const closeParenIdx = findClosingParen(source, openParenIdx);
        if (closeParenIdx === -1) return;
        const rawParams = source.slice(openParenIdx + 1, closeParenIdx).trim();
        const afterParen = source.slice(closeParenIdx + 1).trimStart();
        const normalizedQualifiers = normalizeSpaces(qualifiers);
        const key = [
            normalizeSpaces(templateParams),
            normalizedQualifiers,
            normalizeSpaces(returnType),
            funcName,
            normalizeSpaces(rawParams)
        ].join('|');

        if (!results.some(result => result.key === key)) {
            results.push({
                funcName,
                returnType: normalizeSpaces(returnType),
                qualifiers: normalizedQualifiers,
                callingConvention: getCallingConvention(normalizedQualifiers),
                templateParams: normalizeSpaces(templateParams),
                rawParams: normalizeSpaces(rawParams),
                isDefinition: afterParen.startsWith('{') || afterParen.startsWith(':'),
                key
            });
        }
    }

    const templateFuncRegex = /template\s*<([^>]*)>\s*((?:(?:__aicore__|__simd_callee__|__SIMT_DEVICE_FUNCTIONS_DECL__|static|inline|__in_pipe__\([^)]*\)|__out_pipe__\([^)]*\)|__inout_pipe__\([^)]*\))\s+)*)\s*([A-Za-z_][A-Za-z0-9_:<>*&]*|void|bool|auto|int\d+_t|uint\d+_t|float|double)\s+(\w+)\s*\(/g;
    let match;
    while ((match = templateFuncRegex.exec(source)) !== null) {
        addSignature({
            templateParams: match[1],
            qualifiers: match[2],
            returnType: match[3],
            funcName: match[4],
            openParenIdx: source.indexOf('(', match.index + match[0].length - 1)
        });
    }

    const plainFuncRegex = /(?:^|[;{}]\s*|\n\s*)((?:(?:__aicore__|__simd_callee__|__SIMT_DEVICE_FUNCTIONS_DECL__|static|inline|__in_pipe__\([^)]*\)|__out_pipe__\([^)]*\)|__inout_pipe__\([^)]*\))\s+)*)\s*([A-Za-z_][A-Za-z0-9_:<>*&]*|void|bool|auto|int\d+_t|uint\d+_t|float|double)\s+(\w+)\s*\(/gm;
    let plainMatch;
    while ((plainMatch = plainFuncRegex.exec(source)) !== null) {
        const before = source.slice(Math.max(0, plainMatch.index - 200), plainMatch.index);
        if (/template\s*<[^;{}]*>\s*$/.test(before)) continue;
        addSignature({
            qualifiers: plainMatch[1],
            returnType: plainMatch[2],
            funcName: plainMatch[3],
            openParenIdx: source.indexOf('(', plainMatch.index + plainMatch[0].length - 1)
        });
    }

    return results;
}

function hasApiSignature(content, apiName, callingConvention) {
    return parseAscendcSignaturesFromContent(content).some(signature =>
        signature.funcName === apiName &&
        (!callingConvention || signature.callingConvention === callingConvention)
    );
}

module.exports = {
    CALLING_CONVENTIONS,
    extractParameterName,
    getParameterNames,
    getCallingConvention,
    hasApiSignature,
    normalizeSpaces,
    parseAscendcSignaturesFromContent,
    removeComments,
    signatureShapeKey,
    splitTopLevel,
    stripTopLevelDefaultValue
};