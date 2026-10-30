'use strict';

const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const {
  detectInterfaces,
  parseArgs
} = require('../detect-interfaces');

const parsedArgs = parseArgs([
  'input/path',
  'project/root',
  '--output',
  'interfaces.json',
  '--compact'
]);
assert.deepEqual(parsedArgs, {
  pretty: false,
  inputPath: 'input/path',
  projectRoot: 'project/root',
  output: 'interfaces.json'
});

const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ascendc-detect-'));
try {
  const projectRoot = path.join(tempRoot, 'project');
  const headerDir = path.join(projectRoot, 'include', 'c_api', 'demo');
  const headerPath = path.join(headerDir, 'demo.h');
  fs.mkdirSync(headerDir, { recursive: true });
  fs.writeFileSync(headerPath, [
    '__aicore__ inline void Demo(int value);',
    '__aicore__ inline void Demo_sync(int value);',
    '__aicore__ inline void Demo_pad1(int value);',
    '__aicore__ inline void Demo_pad1_sync(int value);',
    '__aicore__ inline void Demo_nd2nz(int value);',
    '__aicore__ inline void Convert(int value);',
    '__simd_callee__ inline void Convert(int value);',
    ''
  ].join('\n'), 'utf8');

  const report = detectInterfaces(headerPath, projectRoot);
  assert.equal(report.summary.symbolCount, 7);
  assert.equal(report.summary.interfaceCount, 4);
  assert.equal(report.documentFamilies, undefined);
  assert.equal(report.symbols.length, 7);
  assert.equal(report.interfaces.length, 4);

  const demo = report.interfaces.find(item => item.name === 'Demo');
  assert.equal(demo.id, 'c_api|__aicore__|Demo');
  assert.equal(demo.apiType, 'c_api');
  assert.equal(demo.callingConvention, '__aicore__');
  assert.deepEqual(
    demo.members.map(member => member.name),
    ['Demo', 'Demo_sync', 'Demo_pad1', 'Demo_pad1_sync']
  );
  assert.equal(report.interfaces.some(item => item.name === 'Demo_pad1'), false);
  assert.deepEqual(
    report.interfaces.find(item => item.name === 'Demo_nd2nz').members.map(member => member.name),
    ['Demo_nd2nz']
  );

  const convert = report.interfaces.filter(item => item.name === 'Convert');
  assert.deepEqual(
    convert.map(item => item.callingConvention).sort(),
    ['__aicore__', '__simd_callee__']
  );
  assert.ok(report.interfaces.every(item => typeof item.apiType === 'string'));
  assert.ok(report.files[0].symbolIds.length === 7);
  assert.ok(report.files[0].interfaceIds.length === 4);
} finally {
  fs.rmSync(tempRoot, { recursive: true, force: true });
}

console.log('detect-interfaces tests passed');