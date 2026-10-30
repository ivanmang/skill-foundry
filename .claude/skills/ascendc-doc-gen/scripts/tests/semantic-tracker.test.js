'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { buildSemanticLinks } = require('../lib/ascendc-semantic-tracker');
const { parseAscendcSignaturesFromContent } = require('../lib/ascendc-signatures');

const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ascendc-semantic-'));
try {
    const targetHeader = path.join(projectRoot, 'include', 'c_api', 'target.h');
    const basicHeader = path.join(projectRoot, 'include', 'basic_api', 'mmad.h');
    const implDir = path.join(projectRoot, 'impl');
    fs.mkdirSync(path.dirname(targetHeader), { recursive: true });
    fs.mkdirSync(path.dirname(basicHeader), { recursive: true });
    fs.mkdirSync(implDir, { recursive: true });

    const targetDeclarations = `
__aicore__ inline void Target(float* dst, uint8_t c_matrix_source);
__aicore__ inline void Target_sync(float* dst, uint8_t c_matrix_source);
`;
    fs.writeFileSync(targetHeader, targetDeclarations);
    fs.writeFileSync(basicHeader, `
__aicore__ inline void Mmad(float* dst, float* bias);
`);
    fs.writeFileSync(path.join(implDir, 'target_impl.h'), `
__aicore__ inline void Target(float* dst, uint8_t source) {
    target_impl(dst, source);
}
__aicore__ inline void Target_sync(float* dst, uint8_t source) {
    target_impl(dst, source);
    sync_post_process();
}
inline void target_impl(float* dst, uint8_t source) {
    low_level(dst, source);
}
`);
    fs.writeFileSync(path.join(implDir, 'mmad_impl.h'), `
__aicore__ inline void Mmad(float* dst, float* bias) {
    uint8_t source = 0;
    if (bias != nullptr) {
        source = 1;
    }
    basic_impl(dst, source);
}
inline void basic_impl(float* dst, uint8_t source) {
    low_level(dst, source);
}
`);

    const publicSignatures = parseAscendcSignaturesFromContent(targetDeclarations)
        .map(signature => ({ ...signature, sourceFile: targetHeader }));
    const result = buildSemanticLinks({
        projectRoot,
        memberApis: [
            { name: 'Target', role: 'regular' },
            { name: 'Target_sync', role: 'sync' }
        ],
        publicSignatures
    });

    const biasLinks = result.links.filter(link =>
        link.targetParameter === 'c_matrix_source' &&
        link.relatedPublicApi === 'Mmad' &&
        link.relatedParameters.includes('bias') &&
        link.sink.symbol === 'low_level' &&
        link.sink.argumentIndex === 1);
    assert.ok(biasLinks.length >= 1, JSON.stringify(result.links, null, 2));
    assert.ok(result.links.every(link => !['Target', 'Target_sync'].includes(link.relatedPublicApi)));
    assert.ok(result.targetEdges.some(edge => edge.targetParameter === 'c_matrix_source'));
} finally {
    fs.rmSync(projectRoot, { recursive: true, force: true });
}

console.log('semantic-tracker tests passed');