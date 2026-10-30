#!/usr/bin/env node

/**
 * ACLNN 接口检测脚本
 *
 * 自动完成步骤 2-4：
 *   1. 判断给定路径是算子目录还是算子父目录
 *   2. 如为父目录，递归列出所有算子子目录
 *   3. 扫描头文件和实现文件，提取并分组所有 ACLNN 接口名
 *
 * 用法: node scripts/detect-interfaces.js <路径>
 * 示例: node scripts/detect-interfaces.js D:/work/ops-nn/matmul/batch_mat_mul_v3
 *        node scripts/detect-interfaces.js D:/work/ops-nn/matmul
 */

'use strict';

const fs   = require('fs');
const path = require('path');

// ========== 签名解析（复用自 extract-prototype.js）==========

function removeComments(source) {
    source = source.replace(/\/\/.*$/gm, '');
    source = source.replace(/\/\*[\s\S]*?\*\//g, '');
    return source;
}

function findMatchingParen(source, openParenIndex) {
    let depth = 0;
    for (let i = openParenIndex; i < source.length; i++) {
        const ch = source[i];
        if (ch === '(') depth++;
        if (ch === ')') { depth--; if (depth === 0) return i; }
    }
    return -1;
}

function parseAclnnSignatureNames(content) {
    const source = removeComments(content);
    const names  = new Set();
    const re     = /\baclnnStatus\s+(aclnn[A-Za-z0-9_]*)\s*\(/g;
    let m;
    while ((m = re.exec(source)) !== null) {
        const openIdx  = re.lastIndex - 1;
        const closeIdx = findMatchingParen(source, openIdx);
        if (closeIdx === -1) continue;
        const afterParen = source.slice(closeIdx + 1);
        if (!/^\s*[;{]/.test(afterParen)) continue;
        names.add(m[1]);
        re.lastIndex = closeIdx + 1;
    }
    return names;
}

// ========== 目录检测 ==========

const OP_SUBDIRS = ['op_host', 'op_api', 'op_kernel'];
const SKIP_DIRS = new Set([
    '.git', '.svn', '.hg',
    'build', 'cmake-build-debug', 'cmake-build-release',
    'output', 'outputs', 'out', 'install',
    'third_party', 'node_modules'
]);

function isOperatorDir(dirPath) {
    return OP_SUBDIRS.some(sub => fs.existsSync(path.join(dirPath, sub)));
}

/**
 * 在给定目录下递归查找算子目录。
 * 命中算子目录后不再向下递归，避免把 op_host/op_api 内部目录误报为算子。
 */
function findOperatorSubdirs(parentPath) {
    const results = [];

    const walk = (dirPath) => {
        let entries;
        try { entries = fs.readdirSync(dirPath, { withFileTypes: true }); }
        catch { return; }
        for (const entry of entries) {
            if (!entry.isDirectory()) continue;
            if (SKIP_DIRS.has(entry.name.toLowerCase())) continue;

            const fullPath = path.join(dirPath, entry.name);
            if (isOperatorDir(fullPath)) {
                results.push(fullPath);
                continue;
            }
            walk(fullPath);
        }
    }

    walk(parentPath);
    return [...new Set(results)].sort();
}

// ========== 接口分组 ==========

/**
 * 从接口名推导"接口基础名"（去掉 GetWorkspaceSize 后缀）。
 * aclnnXxxGetWorkspaceSize  → aclnnXxx
 * aclnnInplaceXxx           → aclnnInplaceXxx（不变）
 */
function baseName(sigName) {
    return sigName.replace(/GetWorkspaceSize$/, '');
}

/**
 * 扫描算子目录下 op_api/ 和 op_host/ 的头文件，返回去重的接口基础名列表。
 */
function detectInterfacesInDir(opDir) {
    const allNames = new Set();

    const scanDir = (dir) => {
        if (!fs.existsSync(dir)) return;
        let entries;
        try { entries = fs.readdirSync(dir, { withFileTypes: true }); }
        catch { return; }
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                scanDir(fullPath);
            } else if (entry.isFile()) {
                const lname = entry.name.toLowerCase();
                const isHeader = lname.endsWith('.h') || lname.endsWith('.hpp');
                const isCpp    = lname.endsWith('.cpp') || lname.endsWith('.cc') || lname.endsWith('.cxx');
                if (!isHeader && !isCpp) continue;
                // 只处理含 aclnn 前缀的文件，避免扫大量无关文件
                if (!lname.startsWith('aclnn')) continue;
                let content;
                try { content = fs.readFileSync(fullPath, 'utf8'); }
                catch { continue; }
                for (const name of parseAclnnSignatureNames(content)) {
                    allNames.add(name);
                }
            }
        }
    };

    scanDir(path.join(opDir, 'op_api'));
    scanDir(path.join(opDir, 'op_host'));

    // 按基础名去重：若 aclnnXxx 和 aclnnXxxGetWorkspaceSize 都出现，只保留基础名
    const bases = new Set([...allNames].map(baseName));
    // 排序：GetWorkspace 优先（方便阅读），其余字母序
    return [...bases].sort((a, b) => {
        const aw = a.includes('GetWorkspaceSize') ? 0 : 1;
        const bw = b.includes('GetWorkspaceSize') ? 0 : 1;
        if (aw !== bw) return aw - bw;
        return a.localeCompare(b);
    });
}

// ========== 报告生成 ==========

function generateReport(inputPath) {
    const lines = [];

    lines.push('# 接口检测结果');
    lines.push('');

    // 判断输入路径类型
    if (!fs.existsSync(inputPath)) {
        lines.push(`错误：路径不存在: ${inputPath}`);
        return lines.join('\n');
    }

    let opDirs;
    if (isOperatorDir(inputPath)) {
        opDirs = [inputPath];
    } else {
        opDirs = findOperatorSubdirs(inputPath);
        if (opDirs.length === 0) {
            lines.push(`未在以下路径找到算子目录（递归子目录中无含 op_host/op_api/op_kernel 的目录）：`);
            lines.push(`  ${inputPath}`);
            return lines.join('\n');
        }
    }

    lines.push(`输入路径: \`${inputPath}\``);
    lines.push(`算子目录数: ${opDirs.length}`);
    lines.push('');
    lines.push('---');
    lines.push('');

    for (const opDir of opDirs) {
        const dirName    = path.basename(opDir);
        const interfaces = detectInterfacesInDir(opDir);

        lines.push(`## ${dirName}`);
        lines.push('');
        lines.push(`- 路径: \`${opDir}\``);

        if (interfaces.length === 0) {
            lines.push('- 接口: （未找到 aclnnStatus 函数声明）');
        } else {
            lines.push(`- 接口数: ${interfaces.length}`);
            lines.push('- 接口列表:');
            for (const iface of interfaces) {
                lines.push(`  - \`${iface}\``);
            }
        }
        lines.push('');
    }

    // 汇总
    if (opDirs.length > 1) {
        lines.push('---');
        lines.push('');
        lines.push('## 汇总');
        lines.push('');
        lines.push('| 算子目录 | 接口 |');
        lines.push('|---------|------|');
        for (const opDir of opDirs) {
            const dirName    = path.basename(opDir);
            const interfaces = detectInterfacesInDir(opDir);
            lines.push(`| \`${dirName}\` | ${interfaces.length > 0 ? interfaces.map(i => `\`${i}\``).join('、') : '无'} |`);
        }
        lines.push('');
    }

    return lines.join('\n');
}

// ========== 主函数 ==========

function main() {
    const argv = process.argv.slice(2);
    if (argv.length < 1) {
        console.error('用法: node scripts/detect-interfaces.js <路径>');
        console.error('示例: node scripts/detect-interfaces.js D:/work/ops-nn/matmul/batch_mat_mul_v3');
        process.exit(1);
    }

    const inputPath = path.resolve(argv[0]);
    const report    = generateReport(inputPath);
    process.stdout.write(report + '\n', 'utf8');
}

main();
