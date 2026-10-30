#!/usr/bin/env node

/**
 * AscendC 调用示例提取脚本
 *
 * 从 examples 目录中提取 .asc 文件中 Compute() 函数的内容作为调用示例
 *
 * 用法: node extract-call-example.js <代码库根目录> <API名> [API类型]
 * 示例: node extract-call-example.js ./asc-devkit ReduceSum adv_api
 *
 * API类型与示例目录的映射：
 *   adv_api/basic_api → examples/01_simd_cpp_api/
 *   c_api             → examples/02_simd_c_api/
 *   simt_api          → examples/03_simt_api/
 */

const fs = require('fs');
const path = require('path');
const { hasApiSignature } = require('./lib/ascendc-signatures');

const API_TYPE_TO_EXAMPLE_DIR = {
    'adv_api': '01_simd_cpp_api',
    'basic_api': '01_simd_cpp_api',
    'c_api': '02_simd_c_api',
    'simt_api': '03_simt_api'
};

function ensureTrailingNewline(content) {
    return content.endsWith('\n') ? content : content + '\n';
}

function cleanExampleCode(content) {
    content = content.replace(
        /\/\*[\s\S]*?[Cc]opyright[\s\S]*?\*\//g,
        ''
    );
    content = content.replace(/\n{3,}/g, '\n\n');
    return content.trim();
}

function extractComputeFunction(content) {
    const patterns = [
        /\bCompute\s*\(\s*\)\s*\{/,
        /\b__aicore__\s+inline\s+void\s+Compute\s*\(\s*\)\s*\{/
    ];

    let match = null;
    for (const pattern of patterns) {
        match = content.match(pattern);
        if (match) break;
    }

    if (!match) return null;

    const startIdx = match.index + match[0].length;
    let depth = 1;
    let i = startIdx;

    while (i < content.length && depth > 0) {
        if (content[i] === '{') depth++;
        if (content[i] === '}') depth--;
        i++;
    }

    if (depth !== 0) return null;

    const body = content.slice(startIdx, i - 1);
    return body.trim();
}

function getSearchDirs(rootDir, apiType) {
    const exampleSubDir = apiType ? (API_TYPE_TO_EXAMPLE_DIR[apiType] || null) : null;

    const searchDirs = [];
    if (exampleSubDir) {
        searchDirs.push(path.join(rootDir, 'examples', exampleSubDir));
    } else {
        for (const subDir of Object.values(API_TYPE_TO_EXAMPLE_DIR)) {
            searchDirs.push(path.join(rootDir, 'examples', subDir));
        }
    }
    return searchDirs;
}

function collectDirs(rootDir) {
    const result = [];
    if (!fs.existsSync(rootDir)) return result;

    function walk(dir) {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            if (!entry.isDirectory()) continue;
            const fullPath = path.join(dir, entry.name);
            result.push(fullPath);
            walk(fullPath);
        }
    }

    walk(rootDir);
    return result;
}

function collectAscFiles(rootDir) {
    const result = [];
    if (!fs.existsSync(rootDir)) return result;

    function walk(dir) {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                walk(fullPath);
            } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.asc')) {
                result.push(fullPath);
            }
        }
    }

    walk(rootDir);
    return result;
}

function findExampleDir(rootDir, apiName, apiType) {
    const lowerName = apiName.toLowerCase();
    const searchDirs = getSearchDirs(rootDir, apiType);

    for (const searchDir of searchDirs) {
        if (!fs.existsSync(searchDir)) continue;
        const dirs = collectDirs(searchDir);
        const exactMatch = dirs.find(dir => path.basename(dir).toLowerCase() === lowerName);
        if (exactMatch) return exactMatch;
    }

    for (const searchDir of searchDirs) {
        if (!fs.existsSync(searchDir)) continue;
        const dirs = collectDirs(searchDir);
        const partialMatch = dirs.find(dir => path.basename(dir).toLowerCase().includes(lowerName));
        if (partialMatch) return partialMatch;
    }

    return null;
}

function findAscFile(exampleDir, apiName) {
    const lowerName = apiName.toLowerCase();
    const entries = collectAscFiles(exampleDir);

    const exactMatch = entries.find(e =>
        path.basename(e).toLowerCase() === `${lowerName}.asc`
    );
    if (exactMatch) return exactMatch;

    const partialMatch = entries.find(e =>
        path.basename(e).toLowerCase().includes(lowerName)
    );
    if (partialMatch) return partialMatch;

    const anyAsc = entries[0];
    if (anyAsc) return anyAsc;

    return null;
}

function containsApiCall(filePath, apiName) {
    const content = fs.readFileSync(filePath, 'utf8');
    const escaped = apiName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const patterns = [
        new RegExp(`\\bAscendC::${escaped}\\b`),
        new RegExp(`\\b${escaped}\\s*<`),
        new RegExp(`\\b${escaped}\\s*\\(`)
    ];
    return patterns.some(pattern => pattern.test(content));
}

function findAscFileByContent(rootDir, apiName, apiType) {
    const searchDirs = getSearchDirs(rootDir, apiType);

    for (const searchDir of searchDirs) {
        const files = collectAscFiles(searchDir);
        const matched = files.find(file => containsApiCall(file, apiName));
        if (matched) return matched;
    }

    return null;
}

function buildSingleCallExampleSection(rootDir, apiName, apiType) {
    const exampleDir = findExampleDir(rootDir, apiName, apiType);

    const ascFile = exampleDir ? findAscFile(exampleDir, apiName) : findAscFileByContent(rootDir, apiName, apiType);

    if (!ascFile) {
        return '- <span style="color:#dc2626;">【待开发补齐】未找到对应的 .asc 示例文件。</span>';
    }

    const content = fs.readFileSync(ascFile, 'utf8');
    const computeBody = extractComputeFunction(content);

    if (!computeBody) {
        return '- <span style="color:#dc2626;">【待开发补齐】在示例文件中未找到 Compute() 函数。</span>';
    }

    return [
        '```cpp',
        ensureTrailingNewline(cleanExampleCode(computeBody)),
        '```'
    ].join('\n');
}

function buildCallExampleSection(rootDir, documentApiName, apiType, memberApis) {
    const members = memberApis.length > 0 ? [...new Set(memberApis)] : [documentApiName];
    if (members.length === 1) return buildSingleCallExampleSection(rootDir, members[0], apiType);

    const sections = [];
    for (const member of members) {
        sections.push(`### ${member}`, '', buildSingleCallExampleSection(rootDir, member, apiType), '');
    }
    return sections.join('\n').trim();
}

function detectApiType(rootDir, apiName) {
    const lowerName = apiName.toLowerCase();
    const apiTypes = ['adv_api', 'basic_api', 'c_api', 'simt_api'];

    for (const apiType of apiTypes) {
        const includeDir = path.join(rootDir, 'include', apiType);
        if (!fs.existsSync(includeDir)) continue;

        function scanDir(dir) {
            const entries = fs.readdirSync(dir, { withFileTypes: true });
            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);
                if (entry.isDirectory()) {
                    const result = scanDir(fullPath);
                    if (result) return result;
                } else if (/\.(h|hpp|hh)$/i.test(entry.name)) {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (hasApiSignature(content, apiName)) return apiType;
                }
            }
            return null;
        }

        const result = scanDir(includeDir);
        if (result) return result;
    }

    return null;
}

function main() {
    const args = process.argv.slice(2);

    if (args.length < 2) {
        console.error('用法: node extract-call-example.js <代码库根目录> <文档API名> [API类型] [--member <API名>]...');
        console.error('示例: node extract-call-example.js ./asc-devkit ReduceSum adv_api');
        console.error('API类型: adv_api, basic_api, c_api, simt_api（可选，自动检测）');
        process.exit(1);
    }

    const rootDir = args[0];
    const apiName = args[1];
    let apiType = null;
    const memberApis = [];
    for (let index = 2; index < args.length; index++) {
        if (args[index] === '--member') memberApis.push(args[++index]);
        else if (!apiType) apiType = args[index];
        else throw new Error(`Unknown argument: ${args[index]}`);
    }

    if (!apiType) {
        apiType = detectApiType(rootDir, apiName);
        if (apiType) console.error(`自动检测到 API 类型: ${apiType}`);
    }

    const result = buildCallExampleSection(rootDir, apiName, apiType, memberApis);
    console.log(result);
}

main();
