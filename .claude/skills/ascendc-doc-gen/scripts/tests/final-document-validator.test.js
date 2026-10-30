'use strict';

const assert = require('node:assert/strict');
const {
    normalizeInlineCodeInHtmlTables,
    normalizeInlineCodeOutsideFences,
    normalizePrototypeSemicolons,
    validateCallExample,
    validatePrototypeCompleteness,
    validateTableSyntax,
} = require('../lib/final-document-validator');

const prototypeA = '```cpp\n__aicore__ inline void Demo(int32_t value);\n```';
const prototypeB = '```cpp\n__aicore__ inline void Demo(float value);\n```';
const prototypes = `${prototypeA}\n\n${prototypeB}`;

assert.doesNotThrow(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    prototypeDoc: prototypes,
    finalDoc: `## 函数原型\n\n${prototypes}\n\n## 参数说明\n`,
    callingConvention: '__aicore__',
}));
assert.throws(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    prototypeDoc: prototypes,
    finalDoc: `## 函数原型\n\n### 常规接口\n\n${prototypes}\n\n## 参数说明\n`,
    callingConvention: '__aicore__',
}), /禁止包含子标题/);
assert.throws(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    prototypeDoc: prototypes,
    finalDoc: '## 函数原型\n\n- 参数集合 <code>value</code>：\n\n' + prototypes + '\n\n## 参数说明\n',
    callingConvention: '__aicore__',
}), /禁止使用参数集合进行机械分组/);

assert.throws(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    prototypeDoc: prototypes,
    finalDoc: `## 函数原型\n\n${prototypeA}\n\n## 参数说明\n`,
    callingConvention: '__aicore__',
}), /函数原型不完整/);

const missingSemicolonDoc = '## 函数原型\n\n```cpp\n__aicore__ inline void Demo(int32_t value)\n```\n\n```cpp\n__aicore__ inline void Demo(float value)\n```\n\n## 参数说明\n';
const normalizedSemicolonDoc = normalizePrototypeSemicolons({
    apiName: 'Demo',
    prototypeDoc: prototypes,
    finalDoc: missingSemicolonDoc,
    callingConvention: '__aicore__',
});
assert.match(normalizedSemicolonDoc, /Demo\(int32_t value\);/);
assert.match(normalizedSemicolonDoc, /Demo\(float value\);/);
assert.doesNotThrow(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    prototypeDoc: prototypes,
    finalDoc: normalizedSemicolonDoc,
    callingConvention: '__aicore__',
}));

const changedPrototypeDoc = missingSemicolonDoc.replace('int32_t value)', 'uint32_t value)');
const normalizedChangedPrototypeDoc = normalizePrototypeSemicolons({
    apiName: 'Demo',
    prototypeDoc: prototypes,
    finalDoc: changedPrototypeDoc,
    callingConvention: '__aicore__',
});
assert.match(normalizedChangedPrototypeDoc, /Demo\(uint32_t value\)\n/);
assert.doesNotMatch(normalizedChangedPrototypeDoc, /Demo\(uint32_t value\);/);
assert.match(normalizedChangedPrototypeDoc, /Demo\(float value\);/);
assert.throws(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    prototypeDoc: prototypes,
    finalDoc: normalizedChangedPrototypeDoc,
    callingConvention: '__aicore__',
}), /函数原型不完整/);
const templatePrototype = '```cpp\ntemplate <typename T>\n__aicore__ inline void TDemo(T value);\n```';
const templateMissingSemicolonDoc = '## 函数原型\n\n```cpp\ntemplate <typename T>\n__aicore__ inline void TDemo(T value)\n```\n\n## 参数说明\n';
const normalizedTemplateDoc = normalizePrototypeSemicolons({
    apiName: 'TDemo',
    prototypeDoc: templatePrototype,
    finalDoc: templateMissingSemicolonDoc,
    callingConvention: '__aicore__',
});
assert.match(normalizedTemplateDoc, /TDemo\(T value\);/);
assert.doesNotThrow(() => validatePrototypeCompleteness({
    apiName: 'TDemo',
    prototypeDoc: templatePrototype,
    finalDoc: normalizedTemplateDoc,
    callingConvention: '__aicore__',
}));
assert.throws(() => validateCallExample(
    '## 调用示例\n\n【待开发补齐】缺少可验证调用示例。\n',
    'Demo',
), /必须根据代码生成模型示例/);

assert.doesNotThrow(() => validateCallExample(
    '## 调用示例\n\n【示例为基于函数原型构造】\n\n```cpp\nint32_t value = 1;\nDemo(value);\n```\n\n结果示例如下：\n\n```text\n输入：value = 1\n输出：接口按value执行\n```\n',
    'Demo',
));

assert.throws(() => validateCallExample(
    '## 调用示例\n\n```cpp\n__gm__ void* src;\nDemo(src);\n```\n\n结果示例如下：\n\n```text\n输出：x\n```\n',
    'Demo',
), /未初始化的地址空间指针/);

const normalizedTable = normalizeInlineCodeInHtmlTables(
    '<table><tbody><tr><td><p>`n_burst`</p></td></tr></tbody></table>',
);
assert.equal(
    normalizedTable,
    '<table><tbody><tr><td><p><code>n_burst</code></p></td></tr></tbody></table>',
);
const normalizedProse = normalizeInlineCodeOutsideFences(
    '参数 `n_burst`。\n\n```cpp\nconst char* literal = "`keep`";\n```',
);
assert.equal(
    normalizedProse,
    '参数 <code>n_burst</code>。\n\n```cpp\nconst char* literal = "`keep`";\n```',
);
assert.doesNotThrow(() => validateTableSyntax(normalizedProse));
assert.throws(() => validateTableSyntax(
    '参数 `n_burst`。',
), /Markdown行内代码/);
assert.doesNotThrow(() => validateTableSyntax(normalizedTable));
assert.throws(() => validateTableSyntax(
    '约束：参数集合为<code>dst</code>、<code>src</code>时适用。',
), /禁止使用参数集合进行机械分组/);
assert.throws(() => validateTableSyntax(
    '<table><tbody><tr><td><p>`n_burst`</p></td></tr></tbody></table>',
), /Markdown行内代码/);

const familyMembers = [
    { name: 'Demo', role: 'regular' },
    { name: 'Demo_sync', role: 'sync' },
];
const syncPrototype = '```cpp\n__aicore__ inline void Demo_sync(int32_t value);\n```';
const familyPrototypes = `${prototypeA}\n\n${prototypeB}\n\n${syncPrototype}`;
assert.doesNotThrow(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    memberApis: familyMembers,
    prototypeDoc: familyPrototypes,
    finalDoc: `## 函数原型\n\n${familyPrototypes}\n\n## 参数说明\n`,
    callingConvention: '__aicore__',
}));
assert.throws(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    memberApis: familyMembers,
    prototypeDoc: familyPrototypes,
    finalDoc: `## 函数原型\n\n${prototypes}\n\n## 参数说明\n`,
    callingConvention: '__aicore__',
}), /函数原型不完整/);
const unrelatedPrototype = '```cpp\n__aicore__ inline void Demo_s4(int32_t value);\n```';
assert.throws(() => validatePrototypeCompleteness({
    apiName: 'Demo',
    memberApis: familyMembers,
    prototypeDoc: familyPrototypes,
    finalDoc: `## 函数原型\n\n${familyPrototypes}\n\n${unrelatedPrototype}\n\n## 参数说明\n`,
    callingConvention: '__aicore__',
}), /混入非文档成员原型/);

const familyExample = '## 调用示例\n\n```cpp\nint32_t value = 1;\nDemo(value);\nDemo_sync(value);\n```\n\n结果示例如下：\n\n```text\n输入：value = 1\n输出：两个接口均执行\n```\n';
assert.doesNotThrow(() => validateCallExample(familyExample, 'Demo', familyMembers));
const sourceGroupedMembers = [
    { name: 'Demo', role: 'regular', relation: 'document-root' },
    { name: 'Demo_sync', role: 'sync', relation: 'sync-counterpart' },
    { name: 'Demo_pad1', role: 'regular', relation: 'source-document-group' },
];
assert.doesNotThrow(() => validateCallExample(familyExample, 'Demo', sourceGroupedMembers));
assert.throws(() => validateCallExample(
    familyExample.replace('Demo_sync(value);\n', ''),
    'Demo',
    familyMembers,
), /未覆盖文档成员/);
console.log('final-document-validator tests passed');
