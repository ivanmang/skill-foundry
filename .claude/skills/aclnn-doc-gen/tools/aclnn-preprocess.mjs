#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

const TOOL_ROOT = path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, '$1');
const DEFAULT_SCRIPTS_DIR = path.join(TOOL_ROOT, 'scripts');
const DEFAULT_SKILL_ROOT = path.join(process.env.USERPROFILE || process.env.HOME || '', '.config', 'opencode', 'skills', 'aclnn-doc-gen');

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.operatorDir) {
    usage();
    process.exit(1);
  }

  const operatorDir = path.resolve(args.operatorDir);
  const scriptsDir = path.resolve(args.scriptsDir || args.skillDir || process.env.ACLNN_PREPROCESS_SCRIPTS_DIR || DEFAULT_SCRIPTS_DIR);
  const skillRoot = path.resolve(args.skillRoot || process.env.ACLNN_SKILL_ROOT || DEFAULT_SKILL_ROOT);
  const errorCodesFile = path.resolve(args.errorCodesFile || await resolveSkillConfigFile(skillRoot, 'error_codes.yml'));
  const productMappingFile = path.resolve(args.productMappingFile || await resolveSkillConfigFile(skillRoot, 'product_mapping.yml'));
  const projectRoot = path.resolve(args.projectRoot || detectProjectRoot(operatorDir));

  await assertDirectory(operatorDir, '算子目录');
  await assertDirectory(scriptsDir, '预处理脚本目录');

  const interfaces = await detectAclnnInterfaces(operatorDir);
  if (interfaces.length === 0) {
    throw new Error(`未在算子目录中检测到 aclnn 接口：${operatorDir}`);
  }

  const interfaceName = args.interfaceName || await chooseInterface(interfaces);
  if (!interfaces.includes(interfaceName)) {
    throw new Error(`指定接口 ${interfaceName} 不在检测结果中：${interfaces.join(', ')}`);
  }

  const outputsDir = path.join(operatorDir, 'outputs', interfaceName);
  await fs.mkdir(outputsDir, { recursive: true });

  console.log(`算子目录: ${operatorDir}`);
  console.log(`项目根目录: ${projectRoot}`);
  console.log(`预处理脚本目录: ${scriptsDir}`);
  console.log(`Skill 根目录: ${skillRoot}`);
  console.log(`错误码配置: ${errorCodesFile}`);
  console.log(`产品映射配置: ${productMappingFile}`);
  console.log(`目标接口: ${interfaceName}`);
  console.log(`输出目录: ${outputsDir}`);

  const tasks = [
    {
      name: 'prototype',
      script: 'extract-prototype.js',
      args: [operatorDir, interfaceName, '--output', path.join(outputsDir, '0_prototype.md')]
    },
    {
      name: 'cross_dir',
      script: 'extract-cross-dir.js',
      args: [operatorDir, projectRoot, '--output', path.join(outputsDir, '0_cross_dir.md')]
    },
    {
      name: 'chip_evidence',
      script: 'extract-chip-evidence.js',
      args: [operatorDir, projectRoot, '--product-mapping-file', productMappingFile, '--output', path.join(outputsDir, '0_chip_evidence.md')]
    },
    {
      name: 'error_codes',
      script: 'extract-error-codes.js',
      args: [operatorDir, projectRoot, '--error-codes-file', errorCodesFile, '--output', path.join(outputsDir, '0_error_codes.md')]
    },
    {
      name: 'call_example',
      script: 'extract-call-example.js',
      args: [operatorDir, interfaceName, '--product-mapping-file', productMappingFile, '--output', path.join(outputsDir, '0_call_example.md')]
    }
  ];

  const results = await Promise.all(tasks.map(task => runPreprocessTask(scriptsDir, outputsDir, task)));
  for (const result of results) {
    const label = result.ok ? 'OK' : 'FAILED';
    console.log(`[${label}] ${result.name}`);
  }

  await writeExtractPlan(outputsDir, operatorDir, interfaceName);
  console.log(`[OK] extract_plan`);
  console.log(`预处理完成: ${outputsDir}`);
}

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    if (arg === '--interface') {
      result.interfaceName = normalizeInterfaceName(argv[++index] || '');
    } else if (arg === '--skill-dir') {
      result.skillDir = argv[++index];
    } else if (arg === '--skill-root') {
      result.skillRoot = argv[++index];
    } else if (arg === '--error-codes-file') {
      result.errorCodesFile = argv[++index];
    } else if (arg === '--product-mapping-file') {
      result.productMappingFile = argv[++index];
    } else if (arg === '--scripts-dir') {
      result.scriptsDir = argv[++index];
    } else if (arg === '--project-root') {
      result.projectRoot = argv[++index];
    } else if (!result.operatorDir) {
      result.operatorDir = arg;
    } else {
      throw new Error(`未知参数: ${arg}`);
    }
  }
  return result;
}

function usage() {
  console.log('用法: node external-aclnn-skill-tools/aclnn-preprocess.mjs <operatorDir> [--interface aclnnXxx] [--project-root <dir>] [--scripts-dir <dir>] [--skill-root <dir>] [--error-codes-file <file>] [--product-mapping-file <file>]');
}

async function assertDirectory(dir, label) {
  const stat = await fs.stat(dir).catch(() => null);
  if (!stat?.isDirectory()) {
    throw new Error(`${label}不存在或不是目录: ${dir}`);
  }
}

async function resolveSkillConfigFile(skillRoot, filename) {
  const preferred = path.join(skillRoot, 'config', filename);
  if (await fileExists(preferred)) {
    return preferred;
  }
  return path.join(skillRoot, 'references', filename);
}

async function fileExists(filePath) {
  const stat = await fs.stat(filePath).catch(() => null);
  return Boolean(stat?.isFile());
}

function detectProjectRoot(operatorDir) {
  return path.dirname(operatorDir);
}

async function detectAclnnInterfaces(operatorDir) {
  const files = await collectSourceFiles(operatorDir, ['op_api', 'op_host']);
  const names = new Set();
  for (const file of files) {
    const content = await fs.readFile(file, 'utf8').catch(() => '');
    for (const name of parseAclnnSignatureNames(content)) {
      names.add(normalizeInterfaceName(name));
    }
  }
  return Array.from(names)
    .filter(name => /^aclnn[A-Z][A-Za-z0-9]+$/.test(name))
    .sort((a, b) => a.localeCompare(b));
}

function removeComments(source) {
  return source
    .replace(/\/\/.*$/gm, '')
    .replace(/\/\*[\s\S]*?\*\//g, '');
}

function findMatchingParen(source, openParenIndex) {
  let depth = 0;
  for (let index = openParenIndex; index < source.length; index++) {
    const ch = source[index];
    if (ch === '(') depth++;
    if (ch === ')') {
      depth--;
      if (depth === 0) return index;
    }
  }
  return -1;
}

function parseAclnnSignatureNames(content) {
  const source = removeComments(content);
  const names = new Set();
  const re = /\baclnnStatus\s+(?:[A-Za-z_][A-Za-z0-9_]*\s+)*?(aclnn[A-Za-z0-9_]*)\s*\(/g;
  let match;
  while ((match = re.exec(source)) !== null) {
    const openIndex = re.lastIndex - 1;
    const closeIndex = findMatchingParen(source, openIndex);
    if (closeIndex === -1) continue;
    const afterParen = source.slice(closeIndex + 1);
    if (!/^\s*[;{]/.test(afterParen)) continue;
    names.add(match[1]);
    re.lastIndex = closeIndex + 1;
  }
  return names;
}

function normalizeInterfaceName(name) {
  return name.replace(/GetWorkspaceSize$/, '').trim();
}

async function collectSourceFiles(root, subdirs) {
  const result = [];
  for (const subdir of subdirs) {
    await walk(path.join(root, subdir), result);
  }
  return result;
}

async function walk(dir, result) {
  const entries = await fs.readdir(dir, { withFileTypes: true }).catch(() => []);
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!['tests', 'utest', 'ut', 'build', 'output'].includes(entry.name.toLowerCase())) {
        await walk(fullPath, result);
      }
      continue;
    }
    if (/\.(h|hpp|hh|cpp|cc|cxx|c)$/i.test(entry.name)) {
      result.push(fullPath);
    }
  }
}

async function chooseInterface(interfaces) {
  if (interfaces.length === 1) {
    console.log(`检测到 1 个接口: ${interfaces[0]}`);
    return interfaces[0];
  }

  console.log(`检测到 ${interfaces.length} 个接口，请选择要生成的接口:`);
  interfaces.forEach((name, index) => console.log(`  ${index + 1}. ${name}`));

  const rl = readline.createInterface({ input, output });
  try {
    while (true) {
      const answer = await rl.question('请输入序号或接口名: ');
      const trimmed = answer.trim();
      const numeric = Number(trimmed);
      if (Number.isInteger(numeric) && numeric >= 1 && numeric <= interfaces.length) {
        return interfaces[numeric - 1];
      }
      const normalized = normalizeInterfaceName(trimmed);
      if (interfaces.includes(normalized)) {
        return normalized;
      }
      console.log('输入无效，请重新选择。');
    }
  } finally {
    rl.close();
  }
}

function runPreprocessTask(scriptsDir, outputsDir, task) {
  return new Promise(resolve => {
    const scriptPath = path.join(scriptsDir, task.script);
    const child = spawn(process.execPath, [scriptPath, ...task.args], {
      cwd: scriptsDir,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let stdoutText = '';
    let stderrText = '';
    child.stdout.on('data', chunk => { stdoutText += chunk.toString(); });
    child.stderr.on('data', chunk => { stderrText += chunk.toString(); });
    child.on('close', async code => {
      if (code === 0) {
        resolve({ name: task.name, ok: true });
        return;
      }
      await writeFailedFile(outputsDir, task.name, scriptPath, code, stderrText || stdoutText);
      resolve({ name: task.name, ok: false });
    });
  });
}

async function writeFailedFile(outputsDir, name, scriptPath, code, detail) {
  const content = [
    `# 预处理 ${name} 失败`,
    '',
    `**失败时间**：${formatMinuteTimestamp()}`,
    `**失败阶段**：预处理 — ${name}`,
    '',
    '## 失败原因',
    '',
    `脚本退出码：${code}`,
    '',
    '## 执行脚本',
    '',
    scriptPath,
    '',
    '## 错误输出摘要',
    '',
    detail.trim() || '无',
    ''
  ].join('\n');
  await fs.writeFile(path.join(outputsDir, `0_${name}_FAILED.md`), content, 'utf8');
}

async function writeExtractPlan(outputsDir, operatorDir, interfaceName) {
  const files = {
    prototype: await readOptional(path.join(outputsDir, '0_prototype.md')),
    cross_dir: await readOptional(path.join(outputsDir, '0_cross_dir.md')),
    chip_evidence: await readOptional(path.join(outputsDir, '0_chip_evidence.md')),
    error_codes: await readOptional(path.join(outputsDir, '0_error_codes.md')),
    call_example: await readOptional(path.join(outputsDir, '0_call_example.md'))
  };
  const hits = [];
  for (const [source, content] of Object.entries(files)) {
    hits.push(...collectPathHits(content, source, operatorDir));
  }
  const keyFiles = dedupe(hits, item => `${item.path}:${item.line || 0}`).slice(0, 100);
  const aroundItems = keyFiles
    .filter(item => item.line)
    .filter(item => ['chip_evidence', 'error_codes'].includes(item.source) || /aclnn/i.test(item.path))
    .sort(comparePlanPriority)
    .slice(0, 40)
    .map(item => ({ path: item.path, line: item.line, before: 60, after: 80, reason: item.reason }));
  const functionItems = buildFunctionItems(keyFiles, interfaceName, files.prototype);

  const plan = {
    schemaVersion: 1,
    kind: 'aclnn_extract_plan',
    target: {
      interfaceName,
      operatorDir: normalizePath(operatorDir)
    },
    usage: {
      purpose: '减少 extract 阶段首轮工具探索耗时',
      sourceOfTruth: '源码和原始 evidence 优先；本计划只提供读取路线，不替代源码核验',
      requiredEvidenceFiles: ['cross_dir', 'chip_evidence', 'error_codes']
    },
    keyFiles,
    recommendedToolCalls: {
      read_file_around_batch: { items: aroundItems },
      extract_function_batch: { items: functionItems }
    }
  };
  await fs.writeFile(path.join(outputsDir, '0_extract_plan.json'), `${JSON.stringify(plan, null, 2)}\n`, 'utf8');
}

async function readOptional(filePath) {
  return fs.readFile(filePath, 'utf8').catch(() => '');
}

function collectPathHits(content, source, operatorDir) {
  const hits = [];
  const lines = content.split(/\r?\n/);
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    for (const match of line.matchAll(/\*\*([^*`]+?\.(?:cpp|cc|cxx|c|h|hpp|hh|md))[:：](\d+)\*\*/gi)) {
      const resolvedPath = resolveEvidencePath(match[1], operatorDir);
      hits.push({
        path: normalizePath(resolvedPath),
        line: Number(match[2]),
        source,
        sourceLine: index + 1,
        reason: classifyPath(resolvedPath)
      });
    }
    for (const match of line.matchAll(/\b[A-Za-z]:[\\/][^`'"\s|)）]+/g)) {
      const parsed = parsePathWithLine(match[0], line.slice((match.index || 0) + match[0].length));
      if (!/\.(cpp|cc|cxx|c|h|hpp|hh|md)$/i.test(parsed.path)) {
        continue;
      }
      hits.push({
        path: normalizePath(parsed.path),
        line: parsed.line,
        source,
        sourceLine: index + 1,
        reason: classifyPath(parsed.path)
      });
    }
  }
  return hits;
}

function resolveEvidencePath(filePath, operatorDir) {
  const normalized = normalizePath(filePath).replace(/^`|`$/g, '');
  if (/^[A-Za-z]:\//.test(normalized)) {
    return normalized;
  }
  const operatorBase = path.basename(operatorDir);
  if (normalized === operatorBase || normalized.startsWith(`${operatorBase}/`)) {
    return normalizePath(path.join(path.dirname(operatorDir), normalized));
  }
  return normalizePath(path.join(operatorDir, normalized));
}

function comparePlanPriority(a, b) {
  return planPriority(a) - planPriority(b) || a.path.localeCompare(b.path) || (a.line || 0) - (b.line || 0);
}

function planPriority(item) {
  const p = item.path.toLowerCase();
  if (p.includes('/op_host/op_api/aclnn_')) return 1;
  if (p.endsWith('_def.cpp')) return 2;
  if (p.includes('infershape')) return 3;
  if (p.includes('/op_tiling/')) return 4;
  if (p.includes('/op_kernel/')) return 5;
  return 9;
}

function buildFunctionItems(keyFiles, interfaceName, prototypeReport = '') {
  const aclnnCpp = keyFiles
    .map(item => item.path)
    .find(filePath => /\/op_(api|host)\/.*aclnn.*\.cpp$/i.test(filePath));
  if (!aclnnCpp) return [];
  const items = [];
  if (hasAclnnSignature(prototypeReport, `${interfaceName}GetWorkspaceSize`)) {
    items.push({
      path: aclnnCpp,
      functionName: `${interfaceName}GetWorkspaceSize`,
      reason: '目标两段式 GetWorkspaceSize 接口实现'
    });
  }
  if (hasAclnnSignature(prototypeReport, interfaceName)) {
    items.push({
      path: aclnnCpp,
      functionName: interfaceName,
      reason: '目标 ACLNN 接口实现'
    });
  }
  return items;
}

function hasAclnnSignature(content, interfaceName) {
  return new RegExp(`\\baclnnStatus\\s+${escapeRegExp(interfaceName)}\\s*\\(`).test(content);
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function parsePathWithLine(rawPath, tail) {
  const stripped = rawPath.replace(/[，,；;。]+$/g, '');
  const withLine = stripped.match(/^(.+\.(?:cpp|cc|cxx|c|h|hpp|hh|md))[:：](\d+)\D*$/i);
  if (withLine) {
    return { path: withLine[1], line: Number(withLine[2]) };
  }
  const pathOnly = stripped.match(/^(.+\.(?:cpp|cc|cxx|c|h|hpp|hh|md))[:：]?$/i);
  const tailLine = tail.match(/^\s*[:：]?\s*(?:line|行号|行)?\s*(\d+)\b/i);
  return { path: pathOnly ? pathOnly[1] : stripped, line: tailLine ? Number(tailLine[1]) : undefined };
}

function classifyPath(filePath) {
  const normalized = normalizePath(filePath).toLowerCase();
  if (normalized.endsWith('_def.cpp')) return 'OP_TYPE_REGISTER/_def.cpp，优先用于 dtype/format/产品支持分析';
  if (normalized.includes('/op_tiling/')) return 'tiling 文件，优先用于 shape/attr/workspace 约束分析';
  if (normalized.includes('/op_kernel/')) return 'kernel 文件，优先用于芯片宏分支和实现约束分析';
  if (normalized.includes('/op_api/') && /aclnn.*\.(cpp|h|hpp)$/.test(normalized)) return 'aclnn 接口文件，优先用于原型/参数/运行时校验分析';
  if (normalized.includes('/op_host/')) return 'host/proto 文件，优先用于 infer shape、注册和 host 校验分析';
  return '跨目录/include 候选文件，按 evidence 说明核验';
}

function dedupe(items, keyFn) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const key = keyFn(item);
    if (!seen.has(key)) {
      seen.add(key);
      result.push(item);
    }
  }
  return result;
}

function normalizePath(filePath) {
  return filePath.replace(/\\/g, '/');
}

function formatMinuteTimestamp() {
  const now = new Date();
  const pad = value => String(value).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

main().catch(error => {
  console.error(`错误: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
