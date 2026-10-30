#!/usr/bin/env node

/**
 * ACLNN 函数原型提取与格式化脚本
 * 
 * 从算子目录中提取函数签名并格式化为文档章节
 * 
 * 用法: node extract-prototype.js <算子目录路径> [目标接口名]
 * 示例: node extract-prototype.js ./op_host aclnnMatmul
 */

const fs = require('fs');
const path = require('path');

/**
 * 移除 C++ 注释
 */
function removeComments(source) {
    // 移除单行注释 //
    source = source.replace(/\/\/.*$/gm, '');
    // 移除多行注释 /* */
    source = source.replace(/\/\*[\s\S]*?\*\//g, '');
    return source;
}

/**
 * 查找匹配的括号位置
 */
function findMatchingParen(source, openParenIndex) {
    let depth = 0;
    for (let i = openParenIndex; i < source.length; i++) {
        const ch = source[i];
        if (ch === '(') depth++;
        if (ch === ')') {
            depth--;
            if (depth === 0) return i;
        }
    }
    return -1;
}

/**
 * 分割函数参数
 */
function splitFunctionParameters(paramsStr) {
    const result = [];
    let current = '';
    let depth = 0;
    
    for (let i = 0; i < paramsStr.length; i++) {
        const ch = paramsStr[i];
        if (ch === '(' || ch === '<') depth++;
        if (ch === ')' || ch === '>') depth--;
        if (ch === ',' && depth === 0) {
            result.push(current.trim());
            current = '';
        } else {
            current += ch;
        }
    }
    if (current.trim()) {
        result.push(current.trim());
    }
    return result;
}

/**
 * 规范化空格
 */
function normalizeSpaces(str) {
    return str.replace(/\s+/g, ' ').trim();
}

/**
 * 解析参数
 */
function parseParameter(param) {
    const cleaned = normalizeSpaces(param);
    if (!cleaned) {
        return { type: '', pointer: '', name: '' };
    }
    
    if (cleaned === '...') {
        return { type: '...', pointer: '', name: '' };
    }
    
    // 匹配参数名（最后一个标识符）
    const nameMatch = cleaned.match(/([A-Za-z_]\w*(?:\[[^\]]*\])?)$/);
    if (!nameMatch || nameMatch.index === undefined) {
        return { type: cleaned, pointer: '', name: '' };
    }
    
    const name = nameMatch[1];
    const beforeName = cleaned.slice(0, nameMatch.index).trim();
    
    // 匹配指针符号
    const pointerMatch = beforeName.match(/(\*+)\s*$/);
    const pointer = pointerMatch ? pointerMatch[1] : '';
    const type = pointer
        ? beforeName.slice(0, beforeName.length - pointer.length).trim()
        : beforeName;
    
    return { type, pointer, name };
}

/**
 * 格式化签名（对齐）
 */
function formatAclnnSignature(name, parameters) {
    if (parameters.length === 0) {
        return `aclnnStatus ${name}()`;
    }
    
    const parsed = parameters.map(p => parseParameter(p));
    const maxTypeLen = parsed.reduce((max, item) => Math.max(max, item.type.length), 0);
    
    const lines = parsed.map((item, index) => {
        const typePart = item.type.padEnd(maxTypeLen, ' ');
        const pointerPart = item.pointer || ' ';
        const namePart = item.name;
        const suffix = index === parsed.length - 1 ? '' : ',';
        return `  ${typePart} ${pointerPart}${namePart}${suffix}`.trimEnd();
    });
    
    return [`aclnnStatus ${name}(`, ...lines, ')'].join('\n');
}

/**
 * 生成用于跨文件去重的规范化签名 key。
 * 头文件和 cpp 中常见 `void* p` / `void *p` 这类写法差异，不能导致重复原型。
 */
function buildCanonicalSignatureKey(name, parameters) {
    const canonicalParams = parameters.map(param => {
        const parsed = parseParameter(param);
        return [
            normalizeSpaces(parsed.type),
            parsed.pointer,
            parsed.name
        ].filter(Boolean).join(' ');
    });
    return `${name}(${canonicalParams.join(',')})`;
}

/**
 * 从内容中解析签名
 */
function parseAclnnSignaturesFromContent(content) {
    const source = removeComments(content);
    const results = [];
    const headRegex = /\baclnnStatus\s+(aclnn[A-Za-z0-9_]*)\s*\(/g;
    let match;
    
    while ((match = headRegex.exec(source)) !== null) {
        const name = match[1];
        const openParenIndex = headRegex.lastIndex - 1;
        const closeParenIndex = findMatchingParen(source, openParenIndex);
        if (closeParenIndex === -1) continue;
        
        const afterParen = source.slice(closeParenIndex + 1);
        const endMatch = afterParen.match(/^\s*([;{])/);
        if (!endMatch) continue;
        
        const rawParams = source.slice(openParenIndex + 1, closeParenIndex).trim();
        const parameters = splitFunctionParameters(rawParams)
            .map(p => normalizeSpaces(p))
            .filter(Boolean);
        
        if (parameters.length === 1 && parameters[0] === 'void') {
            results.push({ name, parameters: [] });
        } else {
            results.push({ name, parameters });
        }
        
        headRegex.lastIndex = closeParenIndex + 1;
    }
    
    return results;
}

/**
 * 检查是否为 ACLNN 头文件
 */
function isAclnnHeaderFile(filePath) {
    const name = path.basename(filePath).toLowerCase();
    return name.startsWith('aclnn') && (name.endsWith('.h') || name.endsWith('.hpp'));
}

/**
 * 检查是否包含 ACLNN 签名
 */
function containsAclnnSignature(content) {
    return /\baclnnStatus\s+aclnn[A-Za-z0-9_]*\s*\(/.test(content);
}

/**
 * 检查签名是否与目标接口相关
 *
 * 规则：
 * 1. Inplace 属性必须严格一致——目标是 Inplace 接口只匹配 Inplace 签名，反之排除
 * 2. 去掉 aclnn 前缀、Inplace 标记、GetWorkspaceSize 后缀后，算子基础名必须完全相同
 *
 * 示例：targetApiName = 'aclnnAddbmm'
 *   ✓ aclnnAddbmmGetWorkspaceSize  ✓ aclnnAddbmm
 *   ✗ aclnnInplaceAddbmm          ✗ aclnnInplaceAddbmmGetWorkspaceSize
 */
function isRelatedAclnnSignature(sigName, targetApiName) {
    if (!targetApiName) return true;

    // Inplace 类型必须严格一致
    const targetIsInplace = /Inplace/.test(targetApiName);
    const sigIsInplace    = /Inplace/.test(sigName);
    if (targetIsInplace !== sigIsInplace) return false;

    // 去掉 aclnn 前缀、Inplace 标记、GetWorkspaceSize 后缀，比较算子基础名
    const stripVariants = (s) => s
        .replace(/^aclnn/, '')
        .replace(/Inplace/, '')
        .replace(/GetWorkspaceSize$/, '');

    return stripVariants(sigName) === stripVariants(targetApiName);
}

/**
 * 比较签名顺序
 * GetWorkspaceSize 接口始终排在主接口之前（无论是否为 Inplace 变体）
 */
function compareAclnnSignatureOrder(aName, bName, targetApiName) {
    const getPriority = (name) => name.includes('GetWorkspaceSize') ? 0 : 1;
    const pa = getPriority(aName);
    const pb = getPriority(bName);
    if (pa !== pb) return pa - pb;
    return aName.localeCompare(bName);
}

/**
 * 从目录提取签名
 */
function extractSignatures(opApiDir, opHostDir, targetApiName) {
    const results = [];
    
    const scanDir = (dir) => {
        if (!fs.existsSync(dir)) return [];
        const files = fs.readdirSync(dir, { withFileTypes: true });
        const candidateFiles = [];
        
        for (const entry of files) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                candidateFiles.push(...scanDir(fullPath));
            } else if (entry.isFile()) {
                const lowerName = entry.name.toLowerCase();
                if (isAclnnHeaderFile(entry.name) || lowerName.endsWith('.cpp') || lowerName.endsWith('.cc') || lowerName.endsWith('.cxx')) {
                    candidateFiles.push(fullPath);
                }
            }
        }
        return candidateFiles;
    };
    
    const candidates = [];
    if (opApiDir) candidates.push(...scanDir(opApiDir));
    if (opHostDir) candidates.push(...scanDir(opHostDir));
    
    // 去重并解析签名
    const seen = new Set();
    for (const filePath of candidates) {
        const content = fs.readFileSync(filePath, 'utf8');
        const sigs = parseAclnnSignaturesFromContent(content);
        for (const sig of sigs) {
            const key = buildCanonicalSignatureKey(sig.name, sig.parameters);
            if (!seen.has(key) && isRelatedAclnnSignature(sig.name, targetApiName)) {
                seen.add(key);
                results.push(sig);
            }
        }
    }
    
    // 排序
    results.sort((a, b) => compareAclnnSignatureOrder(a.name, b.name, targetApiName));
    
    return results;
}

/**
 * 生成函数原型章节
 */
function buildStaticAclnnPrototypeSection(opApiDir, opHostDir, apiName) {
    const signatures = extractSignatures(opApiDir, opHostDir, apiName);
    if (signatures.length === 0) {
        return null;
    }
    
    // 推断 opener 用的算子基础名（不含 aclnn 前缀，不含 GetWorkspaceSize 后缀）
    let opName;
    if (apiName) {
        opName = apiName.replace(/^aclnn/, '').replace(/GetWorkspaceSize$/, '');
    } else {
        // 未提供目标名时，优先取非 Inner 变体
        const preferredSig = signatures.find(s => !s.name.includes('Inner')) || signatures[0];
        const match = preferredSig.name.match(/^aclnn(.+?)(?:GetWorkspaceSize)?$/);
        opName = match ? match[1] : preferredSig.name.replace(/^aclnn/, '');
    }

    const executeInterfaceName = `aclnn${opName}`;
    const workspaceInterfaceName = `${executeInterfaceName}GetWorkspaceSize`;
    const hasWorkspaceInterface = signatures.some(sig => sig.name === workspaceInterfaceName);
    const hasExecuteInterface = signatures.some(sig => sig.name === executeInterfaceName);
    const opener = hasWorkspaceInterface && hasExecuteInterface
        ? `每个算子分为[两段式接口](../../../docs/zh/context/两段式接口.md)，必须先调用"${workspaceInterfaceName}"接口获取计算所需workspace大小以及包含了算子计算流程的执行器，再调用"${executeInterfaceName}"接口执行计算。`
        : `调用"${executeInterfaceName}"接口执行计算。`;
    
    const blocks = signatures
        .map(sig => {
            const formatted = formatAclnnSignature(sig.name, sig.parameters);
            return ['```cpp', formatted, '```'].join('\n');
        })
        .join('\n\n');
    
    return [opener, '', blocks].join('\n');
}

/**
 * 主函数
 */
function main() {
    const args = process.argv.slice(2);

    if (args.length < 1) {
        console.error('用法: node extract-prototype.js <算子目录路径> [目标接口名] [--output <文件路径>]');
        console.error('示例: node extract-prototype.js ./op_host aclnnMatmul --output ./outputs/aclnnMatmul/0_prototype.md');
        process.exit(1);
    }

    const outputFlagIdx = args.indexOf('--output');
    let outputFile = null;
    let positional = args;
    if (outputFlagIdx !== -1) {
        outputFile = args[outputFlagIdx + 1];
        positional = args.filter((_, i) => i !== outputFlagIdx && i !== outputFlagIdx + 1);
    }

    const operatorDir = positional[0];
    const targetApiName = positional[1] || '';

    // 扫描 op_api 和 op_host 目录
    const opApiDir = path.join(operatorDir, 'op_api');
    const opHostDir = path.join(operatorDir, 'op_host');

    if (!fs.existsSync(opApiDir) && !fs.existsSync(opHostDir)) {
        console.error(`错误: 找不到 op_api 或 op_host 目录: ${operatorDir}`);
        process.exit(1);
    }

    const result = buildStaticAclnnPrototypeSection(opApiDir, opHostDir, targetApiName);

    if (!result) {
        console.error('未找到函数签名');
        process.exit(1);
    }

    const output = result + '\n';
    if (outputFile) {
        fs.mkdirSync(path.dirname(outputFile), { recursive: true });
        fs.writeFileSync(outputFile, output, 'utf8');
    } else {
        process.stdout.write(output, 'utf8');
    }
}

main();
