'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const skillRoot = path.join(__dirname, '..', '..');
const read = relativePath => fs.readFileSync(path.join(skillRoot, relativePath), 'utf8');
const generate = read('tasks/generate.md');
const review = read('tasks/review.md');
const skill = read('SKILL.md');
const chipMapping = read('references/chip_mapping.md');
const validator = read('scripts/lib/final-document-validator.js');

const products = [
    ['950', 'id1', 'Ascend 950PR/Ascend 950DT'],
    ['A3', 'id2', 'Atlas A3训练系列产品/Atlas A3推理系列产品'],
    ['910b', 'id3', 'Atlas A2训练系列产品/Atlas A2推理系列产品'],
    ['310b', 'id4', 'Atlas 200I/500 A2推理产品'],
    ['310p', 'id5', 'Atlas推理系列产品AI Core'],
    ['310p', 'id6', 'Atlas推理系列产品Vector Core'],
    ['910', 'id7', 'Atlas训练系列产品'],
];

for (const document of [generate, review]) {
    let previousIndex = -1;
    for (const [npu, id, product] of products) {
        const block = [
            '<' + '!-- npu="' + npu + '" ' + id + ' -->',
            '- ' + product + '：支持/不支持',
            '<' + '!-- end ' + id + ' -->',
        ].join('\n');
        const index = document.indexOf(block);
        assert.ok(index > previousIndex, id + ' fixed product block is missing or out of order');
        previousIndex = index;
    }
    assert.doesNotMatch(document, /^\s*<(?:table|thead|tbody|tr|th|td)\b/im);
}

assert.match(generate, /\| 参数名 \| 输入\/输出 \| 描述 \|/);
assert.match(generate, /\| 源操作数src0 type \| 源操作数src1 type \| 目的操作数dst type \|/);
assert.match(skill, /固定 7 个产品项/);
assert.match(chipMapping, /Atlas推理系列产品AI Core/);
assert.match(chipMapping, /Atlas推理系列产品Vector Core/);
assert.match(skill, /详细分析方法、输出结构和格式规则以对应 `tasks\/\*\.md` 为唯一准则/);
assert.match(skill, /固定 7 个产品项、Markdown 表格、空章节格式/);
assert.match(skill, /单个 API[\s\S]*当前 agent[\s\S]*不得启动 subagent 或 worker/);
assert.match(skill, /多个 API[\s\S]*两个或以上 API 文档族[\s\S]*独立 worker/);
assert.ok(skill.split(/\r?\n/).length <= 120, 'SKILL.md should stay concise; move stage details into tasks/*.md');

for (const document of [generate, review, chipMapping]) {
    assert.doesNotMatch(document, /固定\s*6|6\s*个产品|√或×|支持打√|不支持打×/);
}
assert.doesNotMatch(validator, /PRODUCT_SUPPORT_ITEMS|validateProductSupportSection/);

for (const document of [generate, review]) {
    assert.match(document, /空章节格式/);
    assert.match(document, /## 参数说明/);
    assert.match(document, /## 返回值说明/);
    assert.match(document, /## 约束说明/);
    assert.match(document, /“无。”/);
}
assert.match(generate, /无返回值（void）时，`## 返回值说明`章节正文只输出单独一行“无”/);
assert.match(generate, /除空章节正文“无”外，完整描述必须加标点符号/);
assert.match(generate, /没有可输出的用户可见约束时[\s\S]*`## 约束说明`章节正文只输出单独一行“无”/);
assert.match(review, /内容为空时，章节正文必须精确为单独一行“无”/);

console.log('document-format-rules tests passed');