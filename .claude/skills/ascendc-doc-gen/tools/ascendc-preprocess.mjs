#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

const TOOL_ROOT = path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, '$1');
const SKILL_ROOT = path.dirname(TOOL_ROOT);
const DEFAULT_SCRIPTS_DIR = path.join(SKILL_ROOT, 'scripts');
const API_TYPES = ['adv_api', 'basic_api', 'c_api', 'simt_api'];
const require = createRequire(import.meta.url);
const {
  CALLING_CONVENTIONS,
  parseAscendcSignaturesFromContent
} = require(path.join(DEFAULT_SCRIPTS_DIR, 'lib', 'ascendc-signatures.js'));
const {
  discoverSourceDocumentGroup,
  resolveDocumentFamily
} = require(path.join(DEFAULT_SCRIPTS_DIR, 'lib', 'ascendc-api-family.js'));

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.inputPath || !args.projectRoot) {
    usage();
    process.exit(1);
  }

  const inputPath = path.resolve(args.inputPath);
  const projectRoot = path.resolve(args.projectRoot);
  const scriptsDir = path.resolve(args.scriptsDir || DEFAULT_SCRIPTS_DIR);
  const isaReferenceInputs = (args.isaReferences || []).map(reference => path.resolve(reference));

  await assertExists(inputPath, 'AscendC API文件或目录');
  await assertDirectory(projectRoot, '代码库根目录');
  await assertDirectory(scriptsDir, '预处理脚本目录');

  const detectedApis = args.interfaceName ? [] : await detectAscendCApis(inputPath);
  const apiName = args.interfaceName || await chooseApi(detectedApis);
  if (!apiName) {
    throw new Error(`未检测到 AscendC API：${inputPath}`);
  }
  if (args.interfaceName && detectedApis.length > 0 && !detectedApis.includes(args.interfaceName)) {
    console.warn(`警告: 指定 API ${args.interfaceName} 不在输入路径检测结果中，将继续按指定 API 预处理。`);
  }

  const sourceDocumentGroup = args.exactInterface ? null : await discoverInputDocumentGroup(inputPath, apiName);
  const candidateNames = documentCandidateNames(
    apiName,
    Boolean(args.exactInterface),
    args.relatedInterfaces || [],
    sourceDocumentGroup
  );
  const inputSignatures = await collectInputSignatures(inputPath, candidateNames);
  const requestedSignatures = inputSignatures.filter(signature => signature.funcName === apiName);
  if (requestedSignatures.length === 0) {
    throw new Error('未在输入路径中找到目标 API 定义: ' + apiName);
  }
  const availableConventions = [...new Set(requestedSignatures.map(signature => signature.callingConvention))];
  const callingConvention = await selectCallingConvention(
    apiName,
    availableConventions,
    args.callingConvention,
    Boolean(args.interfaceName)
  );
  const family = resolveDocumentFamily({
    requestedApiName: apiName,
    signatures: inputSignatures,
    callingConvention,
    exactInterface: Boolean(args.exactInterface),
    relatedInterfaces: args.relatedInterfaces || [],
    sourceDocumentGroup
  });
  for (const diagnostic of family.diagnostics) console.warn(`Warning: ${diagnostic}`);
  const documentApiName = family.documentApiName;
  const memberApis = family.members;
  const memberNames = new Set(memberApis.map(member => member.name));
  const selectedSourceFiles = [...new Set(inputSignatures
    .filter(signature => memberNames.has(signature.funcName) && signature.callingConvention === callingConvention)
    .map(signature => signature.sourceFile))];
  const targetInputPath = resolveSourceInputPath(inputPath, selectedSourceFiles, documentApiName);
  const apiType = args.apiType || await detectApiType(projectRoot, documentApiName);
  const crossDirInputPath = targetInputPath;

  const outputsDir = path.join(projectRoot, 'outputs', documentApiName);
  await fs.mkdir(outputsDir, { recursive: true });
  const isaReferenceFiles = await writeIsaReferences(outputsDir, isaReferenceInputs);

  console.log(`输入路径: ${inputPath}`);
  console.log(`代码库根目录: ${projectRoot}`);
  console.log(`预处理脚本目录: ${scriptsDir}`);
  console.log(`请求 API: ${apiName}`);
  console.log(`文档 API: ${documentApiName}`);
  console.log(`文档成员: ${memberApis.map(member => member.name).join(', ')}`);
  console.log(`API 类型: ${apiType || '未识别'}`);
  console.log(`调用约定: ${callingConvention}`);
  console.log(`接口源范围: ${targetInputPath}`);
  console.log(`输出目录: ${outputsDir}`);
  if (isaReferenceFiles.length > 0) console.log(`ISA参考文件: ${isaReferenceFiles.length}个`);
  if (crossDirInputPath !== inputPath) {
    console.log(`cross_dir 输入路径: ${crossDirInputPath}`);
  }

  const memberArgs = memberApis.flatMap(member => ['--member', member.name]);
  const results = [];
  results.push(await runCapture({
    name: 'prototype',
    scriptPath: path.join(scriptsDir, 'extract-prototype.js'),
    args: compact([projectRoot, documentApiName, apiType, '--input', targetInputPath, '--calling-convention', callingConvention]).concat(memberArgs),
    outputsDir,
    outputFile: path.join(outputsDir, '0_prototype.md')
  }));
  results.push(await runInherited({
    name: 'cross_dir',
    scriptPath: path.join(scriptsDir, 'extract-cross-dir.js'),
    args: [crossDirInputPath, projectRoot, '--output', path.join(outputsDir, '0_cross_dir.md')],
    outputsDir
  }));
  results.push(await runCapture({
    name: 'semantic_links',
    scriptPath: path.join(scriptsDir, 'extract-semantic-links.js'),
    args: compact([projectRoot, documentApiName, apiType, '--input', targetInputPath,
      '--calling-convention', callingConvention]).concat(memberArgs),
    outputsDir,
    outputFile: path.join(outputsDir, '0_semantic_links.json')
  }));
  results.push(await runCapture({
    name: 'call_example',
    scriptPath: path.join(scriptsDir, 'extract-call-example.js'),
    args: compact([projectRoot, documentApiName, apiType]).concat(memberArgs),
    outputsDir,
    outputFile: path.join(outputsDir, '0_call_example.md')
  }));

  await writeManifest(outputsDir, {
    apiName: documentApiName,
    requestedApiName: apiName,
    documentApiName,
    memberApis,
    exactInterface: Boolean(args.exactInterface),
    apiType,
    callingConvention,
    sourceFiles: selectedSourceFiles,
    inputPath,
    projectRoot,
    scriptsDir,
    isaReferences: isaReferenceFiles,
    generatedFiles: [
      '0_prototype.md',
      '0_cross_dir.md',
      '0_semantic_links.json',
      '0_call_example.md',
      ...(isaReferenceFiles.length > 0 ? ['0_isa_reference.md'] : []),
      '0_preprocess_manifest.json'
    ],
    results
  });

  for (const result of results) {
    console.log(`[${result.ok ? 'OK' : 'FAILED'}] ${result.name}`);
  }
  console.log(`预处理完成: ${outputsDir}`);

  if (results.some(result => !result.ok)) {
    process.exit(1);
  }
}

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    if (arg === '--interface') {
      result.interfaceName = argv[++index];
    } else if (arg === '--related-interface') {
      result.relatedInterfaces ||= [];
      result.relatedInterfaces.push(argv[++index]);
    } else if (arg === '--exact-interface') {
      result.exactInterface = true;
    } else if (arg === '--api-type') {
      result.apiType = argv[++index];
    } else if (arg === '--calling-convention') {
      result.callingConvention = argv[++index];
    } else if (arg === '--scripts-dir') {
      result.scriptsDir = argv[++index];
    } else if (arg === '--isa-reference') {
      result.isaReferences ||= [];
      result.isaReferences.push(argv[++index]);
    } else if (!result.inputPath) {
      result.inputPath = arg;
    } else if (!result.projectRoot) {
      result.projectRoot = arg;
    } else {
      throw new Error(`未知参数: ${arg}`);
    }
  }
  return result;
}

function usage() {
  console.log('用法: node tools/ascendc-preprocess.mjs <AscendC API文件或目录> <代码库根目录> [--interface API名] [--related-interface API名] [--exact-interface] [--api-type adv_api|basic_api|c_api|simt_api] [--calling-convention __aicore__|__simd_callee__|__SIMT_DEVICE_FUNCTIONS_DECL__|unqualified] [--isa-reference <ISA.md或目录>] [--scripts-dir <dir>]');
}

async function assertExists(targetPath, label) {
  const stat = await fs.stat(targetPath).catch(() => null);
  if (!stat) {
    throw new Error(`${label}不存在: ${targetPath}`);
  }
}

async function assertDirectory(dir, label) {
  const stat = await fs.stat(dir).catch(() => null);
  if (!stat?.isDirectory()) {
    throw new Error(`${label}不存在或不是目录: ${dir}`);
  }
}

async function writeIsaReferences(outputsDir, inputs) {
  if (inputs.length === 0) return [];
  const files = [];
  for (const inputPath of inputs) {
    await assertExists(inputPath, 'ISA参考文件或目录');
    const stat = await fs.stat(inputPath);
    if (stat.isFile()) {
      if (!isTextReference(inputPath)) throw new Error(`ISA参考仅支持.md/.markdown/.txt文件: ${inputPath}`);
      files.push(inputPath);
    } else if (stat.isDirectory()) {
      await collectTextReferences(inputPath, files);
    }
  }
  const uniqueFiles = [...new Set(files)].sort((a, b) => a.localeCompare(b));
  if (uniqueFiles.length === 0) throw new Error('ISA参考目录中未找到.md/.markdown/.txt文件');
  const sections = ['# ISA参考证据', '', '> 仅可使用与目标API调用链明确映射的条目；名称相似不能作为证据。'];
  for (const file of uniqueFiles) {
    sections.push('', `## ${file}`, '', (await fs.readFile(file, 'utf8')).trim());
  }
  await fs.writeFile(path.join(outputsDir, '0_isa_reference.md'), `${sections.join('\n').trim()}\n`, 'utf8');
  return uniqueFiles;
}

async function collectTextReferences(dir, output) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) await collectTextReferences(fullPath, output);
    else if (entry.isFile() && isTextReference(fullPath)) output.push(fullPath);
  }
}

function isTextReference(filePath) {
  return ['.md', '.markdown', '.txt'].includes(path.extname(filePath).toLowerCase());
}
function compact(items) {
  return items.filter(Boolean);
}

async function chooseApi(apis) {
  if (apis.length === 0) return '';
  if (apis.length === 1) {
    console.log(`检测到 1 个 API: ${apis[0]}`);
    return apis[0];
  }

  console.log(`检测到 ${apis.length} 个 API，请选择要预处理的 API:`);
  apis.forEach((name, index) => console.log(`  ${index + 1}. ${name}`));
  const rl = readline.createInterface({ input, output });
  try {
    while (true) {
      const answer = await rl.question('请输入序号或 API 名: ');
      const trimmed = answer.trim();
      const numeric = Number(trimmed);
      if (Number.isInteger(numeric) && numeric >= 1 && numeric <= apis.length) {
        return apis[numeric - 1];
      }
      if (apis.includes(trimmed)) {
        return trimmed;
      }
      console.log('输入无效，请重新选择。');
    }
  } finally {
    rl.close();
  }
}

function documentCandidateNames(apiName, exactInterface, relatedInterfaces, sourceDocumentGroup = null) {
  const names = new Set([apiName, ...relatedInterfaces, ...(sourceDocumentGroup?.memberNames || [])]);
  if (!exactInterface) {
    if (apiName.endsWith('_sync')) names.add(apiName.slice(0, -'_sync'.length));
    else names.add(apiName + '_sync');
  }
  return names;
}

async function discoverInputDocumentGroup(inputPath, apiName) {
  const groups = [];
  for (const file of await collectSourceFiles(inputPath)) {
    const content = await fs.readFile(file, 'utf8').catch(() => '');
    if (!content.includes(apiName)) continue;
    const group = discoverSourceDocumentGroup(content, apiName);
    if (group) groups.push(group);
  }
  if (groups.length === 0) return null;
  const roots = [...new Set(groups.map(group => group.rootName))];
  if (roots.length !== 1) return null;
  return {
    rootName: roots[0],
    memberNames: [...new Set(groups.flatMap(group => group.memberNames))]
  };
}

async function collectInputSignatures(inputPath, candidateNames) {
  const signatures = [];
  for (const file of await collectSourceFiles(inputPath)) {
    const content = await fs.readFile(file, 'utf8').catch(() => '');
    if (![...candidateNames].some(name => hasApiSignature(content, name))) continue;
    for (const signature of parseAscendcSignaturesFromContent(content)) {
      if (candidateNames.has(signature.funcName)) {
        signatures.push({ ...signature, sourceFile: file });
      }
    }
  }
  return signatures;
}


async function findApiSourceMatches(inputPath, apiName) {
  const files = await collectSourceFiles(inputPath);
  const matches = [];
  for (const file of files) {
    const content = await fs.readFile(file, 'utf8').catch(() => '');
    const signatures = parseAscendcSignaturesFromContent(content)
      .filter(signature => signature.funcName === apiName);
    if (signatures.length === 0) continue;
    matches.push({
      file,
      callingConventions: [...new Set(signatures.map(signature => signature.callingConvention))]
    });
  }
  return matches;
}

async function selectCallingConvention(apiName, available, requested, nonInteractive) {
  if (requested && !CALLING_CONVENTIONS.includes(requested)) {
    throw new Error('不支持的调用约定: ' + requested);
  }
  if (requested) {
    if (!available.includes(requested)) {
      throw new Error(
        'API ' + apiName + ' 在输入路径中不存在调用约定 ' + requested +
        '，可选值: ' + available.join(', ')
      );
    }
    return requested;
  }
  if (available.length === 1) return available[0];
  if (available.length === 0) return 'unqualified';
  if (nonInteractive) {
    throw new Error(
      'API ' + apiName + ' 匹配到多个调用约定: ' + available.join(', ') +
      '。请传入具体头文件，或使用 --calling-convention 显式选择。'
    );
  }

  console.log('API ' + apiName + ' 匹配到多个调用约定，请选择:');
  available.forEach((value, index) => console.log('  ' + (index + 1) + '. ' + value));
  const rl = readline.createInterface({ input, output });
  try {
    while (true) {
      const answer = (await rl.question('请输入序号或调用约定: ')).trim();
      const numeric = Number(answer);
      if (Number.isInteger(numeric) && numeric >= 1 && numeric <= available.length) {
        return available[numeric - 1];
      }
      if (available.includes(answer)) return answer;
      console.log('输入无效，请重新选择。');
    }
  } finally {
    rl.close();
  }
}

function resolveSourceInputPath(inputPath, sourceFiles, apiName) {
  if (sourceFiles.length === 0) {
    throw new Error('未找到符合所选调用约定的 API 定义: ' + apiName);
  }
  if (sourceFiles.length === 1) return sourceFiles[0];
  const commonDir = commonAncestorDir(sourceFiles.map(file => path.dirname(file)));
  console.warn(
    '警告: API ' + apiName + ' 在同一调用约定下匹配到 ' + sourceFiles.length +
    ' 个源文件，使用公共目录: ' + commonDir
  );
  return commonDir || inputPath;
}
async function resolveCrossDirInputPath(inputPath, apiName) {
  const files = await findApiSourceFiles(inputPath, apiName);
  if (files.length === 0) {
    console.warn(`警告: 未在输入路径下定位到 API ${apiName} 的源文件，cross_dir 仍使用原输入路径: ${inputPath}`);
    return inputPath;
  }
  if (files.length === 1) return files[0];

  const commonDir = commonAncestorDir(files.map(file => path.dirname(file)));
  console.warn(`警告: API ${apiName} 在输入路径下匹配到 ${files.length} 个源文件，cross_dir 使用公共目录: ${commonDir}`);
  return commonDir || inputPath;
}

async function findApiSourceFiles(inputPath, apiName) {
  const files = await collectSourceFiles(inputPath);
  const matches = [];
  for (const file of files) {
    const content = await fs.readFile(file, 'utf8').catch(() => '');
    const names = new Set([
      ...parseKernelApiNames(content),
      ...parseTilingApiNames(content, file)
    ]);
    if (names.has(apiName) || hasApiSignature(content, apiName)) {
      matches.push(file);
    }
  }
  return matches;
}

function hasApiSignature(content, apiName) {
  const source = removeComments(content);
  const name = escapeRegExp(apiName);
  const re = new RegExp(
    `(?:template\\s*<[^;{}]*?>\\s*)?(?:(?:__aicore__|__simd_callee__|__SIMT_DEVICE_FUNCTIONS_DECL__|static|inline|__in_pipe__\\([^)]*\\)|__out_pipe__\\([^)]*\\)|__inout_pipe__\\([^)]*\\))\\s+)*(?:void|bool|auto|int\\d+_t|uint\\d+_t|float|double|[A-Za-z_][A-Za-z0-9_:<>*&\\s]*?)\\s+${name}\\s*\\(`,
    'm'
  );
  return re.test(source);
}

function commonAncestorDir(dirs) {
  if (dirs.length === 0) return '';
  const splitDirs = dirs.map(dir => path.resolve(dir).split(/[\\/]+/));
  const first = splitDirs[0];
  let end = first.length;
  for (const parts of splitDirs.slice(1)) {
    end = Math.min(end, parts.length);
    for (let index = 0; index < end; index++) {
      if (parts[index].toLowerCase() !== first[index].toLowerCase()) {
        end = index;
        break;
      }
    }
  }
  return first.slice(0, end).join(path.sep);
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
async function detectAscendCApis(inputPath) {
  const files = await collectSourceFiles(inputPath);
  const names = new Set();
  for (const file of files) {
    const content = await fs.readFile(file, 'utf8').catch(() => '');
    for (const name of parseKernelApiNames(content)) names.add(name);
    for (const name of parseTilingApiNames(content, file)) names.add(name);
  }
  return Array.from(names).sort((a, b) => a.localeCompare(b));
}

async function collectSourceFiles(inputPath) {
  const stat = await fs.stat(inputPath);
  if (stat.isFile()) {
    return isSourceFile(inputPath) ? [inputPath] : [];
  }
  const result = [];
  await walk(inputPath, result);
  return result;
}

async function walk(dir, result) {
  const entries = await fs.readdir(dir, { withFileTypes: true }).catch(() => []);
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!['tests', 'test', 'build', 'output', 'outputs'].includes(entry.name.toLowerCase())) {
        await walk(fullPath, result);
      }
      continue;
    }
    if (isSourceFile(fullPath)) result.push(fullPath);
  }
}

function isSourceFile(filePath) {
  return /\.(h|hpp|hh|cpp|cc|cxx)$/i.test(filePath);
}

function removeComments(source) {
  return source
    .replace(/\/\/.*$/gm, '')
    .replace(/\/\*[\s\S]*?\*\//g, '');
}

function parseKernelApiNames(content) {
  const source = removeComments(content);
  const names = new Set();
  const documentedRe = /\/\*(?:\s*!|\*)[\s\S]*?(?:\\brief|@brief)[\s\S]*?\*\/\s*(?:template\s*<[^;{}]*?>\s*)?(?:(?:__aicore__|__simd_callee__|__SIMT_DEVICE_FUNCTIONS_DECL__|static|inline|__in_pipe__\([^)]*\)|__out_pipe__\([^)]*\)|__inout_pipe__\([^)]*\))\s+)*(?:void|bool|auto|int\d+_t|uint\d+_t|float|double|[A-Za-z_][A-Za-z0-9_:<>*&\s]*?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/g;
  const qualifiedRe = /(?:template\s*<[^;{}]*?>\s*)?(?:(?:__aicore__|__simd_callee__|__SIMT_DEVICE_FUNCTIONS_DECL__|static|inline|__in_pipe__\([^)]*\)|__out_pipe__\([^)]*\)|__inout_pipe__\([^)]*\))\s+)*(?:__aicore__|__simd_callee__|__SIMT_DEVICE_FUNCTIONS_DECL__)\s+(?:(?:static|inline|__in_pipe__\([^)]*\)|__out_pipe__\([^)]*\)|__inout_pipe__\([^)]*\))\s+)*(?:void|bool|auto|int\d+_t|uint\d+_t|float|double|[A-Za-z_][A-Za-z0-9_:<>*&\s]*?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/g;
  let match;
  while ((match = documentedRe.exec(content)) !== null) addApiName(names, match[1]);
  while ((match = qualifiedRe.exec(source)) !== null) addApiName(names, match[1]);
  return names;
}

function addApiName(names, name) {
  if (isIgnoredApiCandidateName(name)) return;
  names.add(name);
}

function isIgnoredApiCandidateName(name) {
  return [
    '_',
    '__in_pipe__',
    '__out_pipe__',
    '__inout_pipe__',
    'operator',
    'ASSERT',
    'DEBUG_CODE',
    'EXTERN_IMPL_BUFPOOL'
  ].includes(name);
}
function parseTilingApiNames(content, filePath) {
  return [];
}

async function detectApiType(projectRoot, apiName) {
  const matches = [];
  for (const apiType of API_TYPES) {
    const includeDir = path.join(projectRoot, 'include', apiType);
    const stat = await fs.stat(includeDir).catch(() => null);
    if (!stat?.isDirectory()) continue;
    const files = await collectSourceFiles(includeDir);
    for (const file of files) {
      const content = await fs.readFile(file, 'utf8').catch(() => '');
      const names = new Set([
        ...parseKernelApiNames(content),
        ...parseTilingApiNames(content, file)
      ]);
      if (names.has(apiName)) {
        matches.push(apiType);
        break;
      }
    }
  }
  if (matches.length > 1) {
    console.warn(`警告: API ${apiName} 同时出现在多个 API 类型中: ${matches.join(', ')}，请显式传入 --api-type。`);
    return '';
  }
  if (matches.length === 1) return matches[0];
  return '';
}

async function runCapture({ name, scriptPath, args, outputsDir, outputFile }) {
  const exists = await fileExists(scriptPath);
  if (!exists) {
    await writeFailedFile(outputsDir, name, scriptPath, 1, '脚本不存在');
    return { name, ok: false, outputFile };
  }
  const result = await runNode(scriptPath, args, { capture: true, cwd: path.dirname(scriptPath) });
  if (result.code === 0) {
    await fs.writeFile(outputFile, ensureTrailingNewline(result.stdout.trim()), 'utf8');
    return { name, ok: true, outputFile };
  }
  await writeFailedFile(outputsDir, name, scriptPath, result.code, result.stderr || result.stdout);
  return { name, ok: false, outputFile };
}

async function runInherited({ name, scriptPath, args, outputsDir }) {
  const exists = await fileExists(scriptPath);
  if (!exists) {
    await writeFailedFile(outputsDir, name, scriptPath, 1, '脚本不存在');
    return { name, ok: false };
  }
  const result = await runNode(scriptPath, args, { capture: false, cwd: path.dirname(scriptPath) });
  if (result.code === 0) return { name, ok: true };
  await writeFailedFile(outputsDir, name, scriptPath, result.code, result.stderr || result.stdout);
  return { name, ok: false };
}

function runNode(scriptPath, args, options) {
  return new Promise(resolve => {
    const child = spawn(process.execPath, [scriptPath, ...args], {
      cwd: options.cwd,
      stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit'
    });
    let stdout = '';
    let stderr = '';
    if (options.capture) {
      child.stdout.on('data', chunk => { stdout += chunk.toString(); });
      child.stderr.on('data', chunk => { stderr += chunk.toString(); });
    }
    child.on('close', code => resolve({ code: code ?? 1, stdout, stderr }));
    child.on('error', error => resolve({ code: 1, stdout, stderr: error.message }));
  });
}

async function fileExists(filePath) {
  const stat = await fs.stat(filePath).catch(() => null);
  return Boolean(stat?.isFile());
}

function ensureTrailingNewline(content) {
  return `${content.replace(/\r\n/g, '\n')}\n`;
}

async function writeFailedFile(outputsDir, name, scriptPath, code, detail) {
  const content = [
    `# 预处理 ${name} 失败`,
    '',
    `**失败阶段**：预处理 - ${name}`,
    `**执行脚本**：${scriptPath}`,
    `**退出码**：${code}`,
    '',
    '## 错误输出摘要',
    '',
    (detail || '无').trim(),
    ''
  ].join('\n');
  await fs.writeFile(path.join(outputsDir, `0_${name}_FAILED.md`), content, 'utf8');
}

async function writeManifest(outputsDir, manifest) {
  const content = {
    schemaVersion: 2,
    kind: 'ascendc_preprocess_manifest',
    generatedAt: new Date().toISOString(),
    ...manifest
  };
  await fs.writeFile(path.join(outputsDir, '0_preprocess_manifest.json'), `${JSON.stringify(content, null, 2)}\n`, 'utf8');
}

main().catch(error => {
  console.error(`错误: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
