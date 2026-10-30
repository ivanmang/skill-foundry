'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
    buildDocumentFamilies,
    discoverSourceDocumentGroup,
    resolveDocumentFamily
} = require('../lib/ascendc-api-family');
const { buildPrototypeSection } = require('../extract-prototype');
const {
    getParameterNames,
    parseAscendcSignaturesFromContent,
    splitTopLevel
} = require('../lib/ascendc-signatures');

const sourceFile = 'include/c_api/demo.h';
const source = `
__aicore__ inline void Demo(float* dst, const Pair<int, float>& value = {});
__aicore__ inline void Demo_sync(float* dst, const Pair<int, float>& value = {});
__aicore__ inline void Demo_s4(float* dst, int mode);
`;
const signatures = parseAscendcSignaturesFromContent(source)
    .map(signature => ({ ...signature, sourceFile }));

const family = resolveDocumentFamily({
    requestedApiName: 'Demo',
    signatures,
    callingConvention: '__aicore__'
});
assert.equal(family.documentApiName, 'Demo');
assert.deepEqual(family.members.map(member => member.name), ['Demo', 'Demo_sync']);

const syncFamily = resolveDocumentFamily({
    requestedApiName: 'Demo_sync',
    signatures,
    callingConvention: '__aicore__'
});
assert.equal(syncFamily.documentApiName, 'Demo');
assert.deepEqual(syncFamily.members.map(member => member.name), ['Demo', 'Demo_sync']);

const exact = resolveDocumentFamily({
    requestedApiName: 'Demo',
    signatures,
    callingConvention: '__aicore__',
    exactInterface: true
});
assert.deepEqual(exact.members.map(member => member.name), ['Demo']);

const families = buildDocumentFamilies(signatures);
assert.deepEqual(
    families.map(item => [item.name, item.members.map(member => member.name)]),
    [
        ['Demo', ['Demo', 'Demo_sync']],
        ['Demo_s4', ['Demo_s4']]
    ]
);

assert.deepEqual(
    splitTopLevel('float* dst, const Pair<int, float>& value = {}, Fn<void(int, int)> callback'),
    ['float* dst', 'const Pair<int, float>& value = {}', 'Fn<void(int, int)> callback']
);
assert.deepEqual(
    getParameterNames('float* dst, const Pair<int, float>& value = {}, Fn<void(int, int)> callback'),
    ['dst', 'value', 'callback']
);

const mismatchedSource = `
__aicore__ inline void Other(float* dst);
__aicore__ inline void Other_sync(float* dst, int mode);
`;
const mismatched = parseAscendcSignaturesFromContent(mismatchedSource)
    .map(signature => ({ ...signature, sourceFile }));
const mismatchedFamily = resolveDocumentFamily({
    requestedApiName: 'Other',
    signatures: mismatched,
    callingConvention: '__aicore__'
});
assert.deepEqual(mismatchedFamily.members.map(member => member.name), ['Other']);
assert.equal(mismatchedFamily.diagnostics.length, 1);
const subsetSource = `
// ==========Copy==========
__aicore__ inline void Copy(void* dst, void* src, uint32_t size);
__aicore__ inline void Copy(void* dst, void* src, uint16_t count, uint16_t gap);
__aicore__ inline void Copy_sync(void* dst, void* src, uint32_t size);
__aicore__ inline void Copy_pad1(void* dst, void* src, uint32_t size);
__aicore__ inline void Copy_pad1_sync(void* dst, void* src, uint32_t size);
// ==========Copy_nd2nz==========
__aicore__ inline void Copy_nd2nz(void* dst, void* src, uint32_t rows);
`;
const sourceDocumentGroup = discoverSourceDocumentGroup(subsetSource, 'Copy');
assert.deepEqual(sourceDocumentGroup, {
    rootName: 'Copy',
    memberNames: ['Copy', 'Copy_sync', 'Copy_pad1', 'Copy_pad1_sync']
});
const subsetSignatures = parseAscendcSignaturesFromContent(subsetSource)
    .map(signature => ({ ...signature, sourceFile }));
const subsetFamily = resolveDocumentFamily({
    requestedApiName: 'Copy',
    signatures: subsetSignatures,
    callingConvention: '__aicore__',
    sourceDocumentGroup
});
assert.deepEqual(
    subsetFamily.members.map(member => [member.name, member.relation]),
    [
        ['Copy', 'document-root'],
        ['Copy_sync', 'sync-counterpart'],
        ['Copy_pad1', 'source-document-group'],
        ['Copy_pad1_sync', 'source-document-group']
    ]
);
assert.doesNotMatch(subsetFamily.members.map(member => member.name).join(','), /Copy_nd2nz/);
const implicitPadFamily = resolveDocumentFamily({
    requestedApiName: 'Copy_pad1',
    signatures: subsetSignatures,
    callingConvention: '__aicore__'
});
assert.equal(implicitPadFamily.documentApiName, 'Copy');
assert.deepEqual(
    implicitPadFamily.members.map(member => member.name),
    ['Copy', 'Copy_sync', 'Copy_pad1', 'Copy_pad1_sync']
);
assert.deepEqual(
    buildDocumentFamilies(subsetSignatures).map(item => item.name),
    ['Copy', 'Copy_nd2nz']
);

const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ascendc-family-'));
try {
    const header = path.join(projectRoot, 'include', 'c_api', 'demo.h');
    fs.mkdirSync(path.dirname(header), { recursive: true });
    fs.writeFileSync(header, source);
    const prototypeSection = buildPrototypeSection(
        projectRoot,
        'Demo',
        'c_api',
        header,
        '__aicore__',
        family.members
    );
    assert.match(prototypeSection, /## Demo（常规接口）/);
    assert.match(prototypeSection, /## Demo_sync（同步接口）/);
    assert.doesNotMatch(prototypeSection, /参数集合/);
    assert.doesNotMatch(prototypeSection, /^###\s+/m);
    assert.doesNotMatch(prototypeSection, /包含.*参数的重载/);
    assert.equal((prototypeSection.match(/\bDemo\s*\(/g) || []).length, 1);
    assert.equal((prototypeSection.match(/\bDemo_sync\s*\(/g) || []).length, 1);
    assert.doesNotMatch(prototypeSection, /\bDemo_s4\s*\(/);
    assert.ok(prototypeSection.split(/\r?\n/)
        .filter(line => /\bDemo(?:_sync)?\s*\(/.test(line))
        .every(line => /;\s*$/.test(line)));
} finally {
    fs.rmSync(projectRoot, { recursive: true, force: true });
}
console.log('ascendc-api-family tests passed');