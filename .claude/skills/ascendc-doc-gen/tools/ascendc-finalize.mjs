#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.projectRoot) {
    usage();
    process.exit(1);
  }

  const projectRoot = path.resolve(args.projectRoot);
  await assertDirectory(projectRoot, '代码库根目录');

  const apiName = args.interfaceName || await chooseOutputApi(projectRoot);
  const outputsDir = path.join(projectRoot, 'outputs', apiName);
  await assertDirectory(outputsDir, '阶段产物目录');

  const reviewPath = path.join(outputsDir, '4_review.md');
  const callExamplePath = path.join(outputsDir, '0_call_example.md');
  const manifestPath = path.join(outputsDir, '0_preprocess_manifest.json');
  const reviewDoc = await readRequired(reviewPath);
  const callExample = await readOptional(callExamplePath);
  const manifest = JSON.parse(await readRequired(manifestPath));

  const documentApiName = manifest.documentApiName || manifest.apiName || apiName;
  const assembledDoc = normalizeInlineCodeOutsideFences(appendCallExample(reviewDoc, callExample));
  const finalDoc = normalizeDoc(assembledDoc);
  const finalPath = path.join(outputsDir, `${documentApiName}_${formatTimestamp()}.md`);
  await fs.writeFile(finalPath, `${finalDoc.trimEnd()}\n`, 'utf8');

  console.log(`已生成最终文档: ${finalPath}`);
}

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    if (arg === '--interface') {
      result.interfaceName = argv[++index];
    } else if (!result.projectRoot) {
      result.projectRoot = arg;
    } else {
      throw new Error(`未知参数: ${arg}`);
    }
  }
  return result;
}

function usage() {
  console.log('用法: node tools/ascendc-finalize.mjs <代码库根目录> --interface API名');
}

async function assertDirectory(dir, label) {
  const stat = await fs.stat(dir).catch(() => null);
  if (!stat?.isDirectory()) {
    throw new Error(`${label}不存在或不是目录: ${dir}`);
  }
}

async function readRequired(filePath) {
  try {
    return await fs.readFile(filePath, 'utf8');
  } catch {
    throw new Error(`缺少必需文件: ${filePath}`);
  }
}

async function readOptional(filePath) {
  return fs.readFile(filePath, 'utf8').catch(() => '');
}

async function chooseOutputApi(projectRoot) {
  const outputsRoot = path.join(projectRoot, 'outputs');
  const entries = await fs.readdir(outputsRoot, { withFileTypes: true }).catch(() => []);
  const candidates = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const dir = path.join(outputsRoot, entry.name);
    if (await fileExists(path.join(dir, '4_review.md'))) {
      candidates.push(entry.name);
    }
  }

  if (candidates.length === 0) {
    throw new Error(`未在 outputs 目录下找到可合成的 4_review.md: ${outputsRoot}`);
  }
  if (candidates.length === 1) {
    console.log(`检测到 1 个可合成 API: ${candidates[0]}`);
    return candidates[0];
  }

  console.log(`检测到 ${candidates.length} 个可合成 API，请选择:`);
  candidates.forEach((name, index) => console.log(`  ${index + 1}. ${name}`));
  const rl = readline.createInterface({ input, output });
  try {
    while (true) {
      const answer = await rl.question('请输入序号或 API 名: ');
      const trimmed = answer.trim();
      const numeric = Number(trimmed);
      if (Number.isInteger(numeric) && numeric >= 1 && numeric <= candidates.length) {
        return candidates[numeric - 1];
      }
      if (candidates.includes(trimmed)) {
        return trimmed;
      }
      console.log('输入无效，请重新选择。');
    }
  } finally {
    rl.close();
  }
}

async function fileExists(filePath) {
  const stat = await fs.stat(filePath).catch(() => null);
  return Boolean(stat?.isFile());
}

function appendCallExample(reviewDoc, rawCallExample) {
  reviewDoc = reviewDoc.replace(/\r\n/g, '\n');
  rawCallExample = rawCallExample.replace(/\r\n/g, '\n');
  const scriptExample = normalizeScriptCallExample(rawCallExample);
  if (!scriptExample) {
    return reviewDoc;
  }

  const base = removeCallExampleSection(reviewDoc).trimEnd();
  return `${base}\n\n## 调用示例\n\n${scriptExample}\n`;
}

function removeCallExampleSection(content) {
  return content.replace(/\n## 调用示例[\s\S]*$/u, '');
}


function normalizeScriptCallExample(raw) {
  const content = raw.trim();
  if (!content) {
    return '';
  }

  if (/【待开发补齐】|未找到对应的 \.asc 示例文件|未找到 Compute\(\) 函数/.test(content)) {
    return '';
  }

  const codeBlock = /```(?:cpp|c\+\+|c)?\s*\n[\s\S]*?```/i.test(content)
    ? content
    : ['```cpp', content, '```'].join('\n');
  return `${codeBlock}\n\n${buildResultExamplePlaceholder()}`;
}

function buildResultExamplePlaceholder() {
  return [
    '结果示例如下：',
    '',
    '```text',
    '输入数据：【待开发补齐】',
    '输出数据：【待开发补齐】',
    '```'
  ].join('\n');
}

function normalizeInlineCodeOutsideFences(content) {
  const fencePattern = /```[\s\S]*?```/g;
  let cursor = 0;
  let result = '';

  for (const match of content.matchAll(fencePattern)) {
    result += content.slice(cursor, match.index).replace(/`([^`\n]+)`/g, '<code>$1</code>');
    result += match[0];
    cursor = match.index + match[0].length;
  }

  return result + content.slice(cursor).replace(/`([^`\n]+)`/g, '<code>$1</code>');
}

function normalizeDoc(content) {
  return content
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+$/gm, '')
    .replace(/\n{3,}/g, '\n\n');
}

function formatTimestamp(date = new Date()) {
  const pad = value => String(value).padStart(2, '0');
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    pad(date.getHours()),
    pad(date.getMinutes())
  ].join('');
}

main().catch(error => {
  console.error(`错误: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
