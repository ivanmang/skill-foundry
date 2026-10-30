'use strict';

const fs = require('fs');
const path = require('path');
const {
    getParameterNames,
    parseAscendcSignaturesFromContent,
    splitTopLevel
} = require('./ascendc-signatures');

const CODE_EXTENSIONS = new Set(['.h', '.hpp', '.hh', '.cpp', '.cc', '.cxx']);
const SKIP_DIRS = new Set(['.git', 'build', 'out', 'output', 'outputs', 'test', 'tests', 'docs']);
const CALL_KEYWORDS = new Set(['if', 'for', 'while', 'switch', 'sizeof', 'alignof', 'decltype', 'return', 'static_cast',
    'reinterpret_cast', 'const_cast', 'dynamic_cast']);
const MAX_TRACE_DEPTH = 7;
const MAX_LINKS_PER_PARAMETER = 30;

function normPath(filePath) {
    return path.resolve(filePath).replace(/\\/g, '/');
}

function collectCodeFiles(root) {
    const files = [];
    if (!fs.existsSync(root)) return files;
    const stat = fs.statSync(root);
    if (stat.isFile()) return CODE_EXTENSIONS.has(path.extname(root).toLowerCase()) ? [path.resolve(root)] : [];
    const walk = (dir) => {
        let entries = [];
        try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                if (!SKIP_DIRS.has(entry.name.toLowerCase())) walk(fullPath);
            } else if (CODE_EXTENSIONS.has(path.extname(fullPath).toLowerCase())) {
                files.push(path.resolve(fullPath));
            }
        }
    };
    walk(root);
    return files;
}

function removeCommentsKeepLines(source) {
    return source
        .replace(/\/\*[\s\S]*?\*\//g, match => match.replace(/[^\n]/g, ' '))
        .replace(/\/\/[^\n]*/g, match => ' '.repeat(match.length));
}

function findClosing(source, openIndex, openChar, closeChar) {
    let depth = 1;
    let quote = '';
    let escaped = false;
    for (let index = openIndex + 1; index < source.length; index++) {
        const char = source[index];
        if (quote) {
            if (escaped) escaped = false;
            else if (char === '\\') escaped = true;
            else if (char === quote) quote = '';
            continue;
        }
        if (char === '"' || char === "'") {
            quote = char;
            continue;
        }
        if (char === openChar) depth++;
        else if (char === closeChar && --depth === 0) return index;
    }
    return -1;
}

function lineNumberAt(source, index) {
    return source.slice(0, index).split('\n').length;
}

function extractDefinitions(content, filePath) {
    const source = removeCommentsKeepLines(content);
    const definitions = [];
    const regex = /\b([A-Za-z_]\w*)\s*\(/g;
    let match;
    while ((match = regex.exec(source)) !== null) {
        const name = match[1];
        if (CALL_KEYWORDS.has(name)) continue;
        const openParen = source.indexOf('(', match.index + name.length);
        const closeParen = findClosing(source, openParen, '(', ')');
        if (closeParen === -1) continue;
        let cursor = closeParen + 1;
        while (/\s/.test(source[cursor] || '')) cursor++;
        if (source[cursor] !== '{') continue;
        const closeBrace = findClosing(source, cursor, '{', '}');
        if (closeBrace === -1) continue;
        const prefix = source.slice(Math.max(0, match.index - 160), match.index);
        if (!/(?:\b(?:void|bool|auto|int\d+_t|uint\d+_t|float|double)\b|[>*&])\s*$/.test(prefix)) continue;
        const rawParams = source.slice(openParen + 1, closeParen).trim();
        definitions.push({
            id: `${normPath(filePath)}:${match.index}`,
            name,
            params: getParameterNames(rawParams),
            rawParams,
            body: source.slice(cursor + 1, closeBrace),
            bodyOffset: cursor + 1,
            source,
            file: normPath(filePath),
            line: lineNumberAt(source, match.index)
        });
        regex.lastIndex = closeBrace + 1;
    }
    return definitions;
}

function extractCalls(definition) {
    if (definition.calls) return definition.calls;
    const calls = [];
    const regex = /\b([A-Za-z_]\w*)\s*\(/g;
    let match;
    while ((match = regex.exec(definition.body)) !== null) {
        const name = match[1];
        if (CALL_KEYWORDS.has(name)) continue;
        const openParen = definition.body.indexOf('(', match.index + name.length);
        const closeParen = findClosing(definition.body, openParen, '(', ')');
        if (closeParen === -1) continue;
        const rawArgs = definition.body.slice(openParen + 1, closeParen);
        calls.push({
            name,
            args: rawArgs.trim() ? splitTopLevel(rawArgs) : [],
            rawArgs,
            line: lineNumberAt(definition.source, definition.bodyOffset + match.index),
            file: definition.file
        });
        regex.lastIndex = closeParen + 1;
    }
    definition.calls = calls;
    return calls;
}

function identifiers(expression) {
    return [...new Set((expression.match(/\b[A-Za-z_]\w*\b/g) || [])
        .filter(identifier => !CALL_KEYWORDS.has(identifier) && !/^(?:true|false|nullptr)$/.test(identifier)))];
}

function assignmentDependencies(definition, variable) {
    const escaped = variable.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const dependencies = new Set();
    const assignment = new RegExp(`\\b${escaped}\\s*=\\s*([^;]+)`, 'g');
    let match;
    while ((match = assignment.exec(definition.body)) !== null) {
        for (const identifier of identifiers(match[1])) dependencies.add(identifier);
        const before = definition.body.slice(Math.max(0, match.index - 500), match.index);
        const conditions = [...before.matchAll(/\bif\s*\(([^()]*)\)\s*\{?/g)];
        const nearest = conditions[conditions.length - 1];
        if (nearest) for (const identifier of identifiers(nearest[1])) dependencies.add(identifier);
    }
    return dependencies;
}

function dependencyClosure(definition, initialIdentifiers) {
    const result = new Set(initialIdentifiers);
    const queue = [...initialIdentifiers];
    while (queue.length > 0 && result.size < 80) {
        const variable = queue.shift();
        for (const dependency of assignmentDependencies(definition, variable)) {
            if (result.has(dependency)) continue;
            result.add(dependency);
            queue.push(dependency);
        }
    }
    return result;
}

function originsForExpression(definition, expression, provenance) {
    const closure = dependencyClosure(definition, identifiers(expression));
    const origins = new Set();
    for (const identifier of closure) {
        for (const origin of provenance.get(identifier) || []) origins.add(origin);
    }
    return origins;
}

function indexDefinitions(codeFiles) {
    const definitions = [];
    const fileContents = new Map();
    for (const file of codeFiles) {
        let content;
        try { content = fs.readFileSync(file, 'utf8'); } catch { continue; }
        fileContents.set(normPath(file), content);
        definitions.push(...extractDefinitions(content, file));
    }
    const byName = new Map();
    for (const definition of definitions) {
        if (!byName.has(definition.name)) byName.set(definition.name, []);
        byName.get(definition.name).push(definition);
    }
    return { definitions, byName, fileContents };
}

function traceTargetMembers(memberApis, publicSignatures, index) {
    const terminalEdges = [];
    const allEdges = [];
    for (const member of memberApis) {
        const signatures = publicSignatures.filter(signature => signature.funcName === member.name);
        const signatureParamsByArity = signatures.map(signature => getParameterNames(signature.rawParams));
        const starts = index.byName.get(member.name) || [];
        const queue = starts.map(definition => {
            const matchingParameters = signatureParamsByArity
                .filter(parameters => parameters.length === definition.params.length);
            const provenance = new Map(definition.params.map((parameter, parameterIndex) => [
                parameter,
                new Set(matchingParameters.map(parameters => parameters[parameterIndex]).filter(Boolean))
            ]));
            return { definition, depth: 0, provenance, path: [] };
        });
        const visited = new Set();
        while (queue.length > 0) {
            const state = queue.shift();
            const provenanceKey = [...state.provenance.entries()]
                .map(([key, value]) => `${key}:${[...value].sort().join(',')}`).sort().join('|');
            const visitKey = `${member.name}|${state.definition.id}|${provenanceKey}`;
            if (visited.has(visitKey) || state.depth > MAX_TRACE_DEPTH) continue;
            visited.add(visitKey);

            for (const call of extractCalls(state.definition)) {
                const argumentOrigins = call.args.map(argument => originsForExpression(state.definition, argument, state.provenance));
                const calleeDefinitions = (index.byName.get(call.name) || [])
                    .filter(definition => definition.params.length === call.args.length);
                for (let argumentIndex = 0; argumentIndex < argumentOrigins.length; argumentIndex++) {
                    for (const targetParameter of argumentOrigins[argumentIndex]) {
                        const edge = {
                            memberApi: member.name,
                            targetParameter,
                            caller: state.definition.name,
                            callee: call.name,
                            argumentIndex,
                            argumentCount: call.args.length,
                            expression: call.args[argumentIndex],
                            file: call.file,
                            line: call.line
                        };
                        allEdges.push(edge);
                        if (calleeDefinitions.length === 0) terminalEdges.push(edge);
                    }
                }
                for (const calleeDefinition of calleeDefinitions) {
                    const nextProvenance = new Map();
                    for (let indexArg = 0; indexArg < calleeDefinition.params.length; indexArg++) {
                        nextProvenance.set(calleeDefinition.params[indexArg], argumentOrigins[indexArg] || new Set());
                    }
                    queue.push({
                        definition: calleeDefinition,
                        depth: state.depth + 1,
                        provenance: nextProvenance,
                        path: [...state.path, call.name]
                    });
                }
            }
        }
    }
    return { terminalEdges, allEdges };
}

function buildCallers(index) {
    const callers = new Map();
    for (const definition of index.definitions) {
        for (const call of extractCalls(definition)) {
            if (!callers.has(call.name)) callers.set(call.name, []);
            callers.get(call.name).push({ definition, call });
        }
    }
    return callers;
}

function reverseTraceSink(edge, index, publicNames, callers = buildCallers(index)) {
    const links = [];
    const sinkCallers = (callers.get(edge.callee) || [])
        .filter(item => item.call.args.length === edge.argumentCount);
    const queue = [];
    for (const item of sinkCallers) {
        const provenance = new Map(item.definition.params.map(param => [param, new Set([param])]));
        const origins = originsForExpression(item.definition, item.call.args[edge.argumentIndex] || '', provenance);
        if (origins.size === 0) continue;
        queue.push({ definition: item.definition, trackedParams: origins, path: [{
            function: item.definition.name,
            callee: edge.callee,
            argumentIndex: edge.argumentIndex,
            file: item.call.file,
            line: item.call.line
        }], depth: 0 });
    }

    const visited = new Set();
    while (queue.length > 0 && links.length < MAX_LINKS_PER_PARAMETER) {
        const state = queue.shift();
        const key = `${state.definition.id}|${[...state.trackedParams].sort().join(',')}`;
        if (visited.has(key) || state.depth > MAX_TRACE_DEPTH) continue;
        visited.add(key);
        if (publicNames.has(state.definition.name)) {
            links.push({
                relatedPublicApi: state.definition.name,
                relatedParameters: [...state.trackedParams].filter(param => state.definition.params.includes(param)),
                evidenceLevel: 'mapping_only',
                path: state.path
            });
        }

        for (const caller of callers.get(state.definition.name) || []) {
            if (caller.call.args.length !== state.definition.params.length) continue;
            const provenance = new Map(caller.definition.params.map(param => [param, new Set([param])]));
            const nextTracked = new Set();
            for (const trackedParam of state.trackedParams) {
                const parameterIndex = state.definition.params.indexOf(trackedParam);
                if (parameterIndex === -1) continue;
                const expression = caller.call.args[parameterIndex] || '';
                for (const origin of originsForExpression(caller.definition, expression, provenance)) nextTracked.add(origin);
            }
            if (nextTracked.size === 0) continue;
            queue.push({
                definition: caller.definition,
                trackedParams: nextTracked,
                path: [{
                    function: caller.definition.name,
                    callee: state.definition.name,
                    argumentIndex: [...state.trackedParams]
                        .map(param => state.definition.params.indexOf(param)).filter(value => value >= 0),
                    file: caller.call.file,
                    line: caller.call.line
                }, ...state.path],
                depth: state.depth + 1
            });
        }
    }
    return links;
}

function normalizedIdentifier(identifier) {
    return identifier.replace(/_/g, '').toLowerCase();
}

function collectNameHints(targetParameters, fileContents) {
    const hints = Object.fromEntries(targetParameters.map(parameter => [parameter, []]));
    const parametersByNormalizedName = new Map();
    for (const parameter of targetParameters) {
        const normalized = normalizedIdentifier(parameter);
        if (!parametersByNormalizedName.has(normalized)) parametersByNormalizedName.set(normalized, []);
        parametersByNormalizedName.get(normalized).push(parameter);
    }

    for (const [file, content] of fileContents) {
        const lines = content.split(/\r?\n/);
        for (let index = 0; index < lines.length; index++) {
            const matchedParameters = new Set();
            for (const identifier of identifiers(lines[index])) {
                for (const parameter of parametersByNormalizedName.get(normalizedIdentifier(identifier)) || []) {
                    matchedParameters.add(parameter);
                }
            }
            for (const parameter of matchedParameters) {
                if (hints[parameter].length >= 20) continue;
                hints[parameter].push({
                    file,
                    line: index + 1,
                    text: lines[index].trim(),
                    evidenceLevel: 'name_hint_only'
                });
            }
        }
    }
    return hints;
}


function buildSemanticLinks({ projectRoot, memberApis, publicSignatures }) {
    const roots = [path.join(projectRoot, 'include'), path.join(projectRoot, 'impl')];
    const codeFiles = [...new Set(roots.flatMap(collectCodeFiles))];
    const index = indexDefinitions(codeFiles);
    const publicNames = new Set();
    for (const file of codeFiles.filter(file => normPath(file).includes('/include/'))) {
        const content = index.fileContents.get(normPath(file)) || '';
        for (const signature of parseAscendcSignaturesFromContent(content)) publicNames.add(signature.funcName);
    }

    const trace = traceTargetMembers(memberApis, publicSignatures, index);
    const callers = buildCallers(index);
    const memberNames = new Set(memberApis.map(member => member.name));
    const links = [];
    const seen = new Set();
    for (const edge of trace.terminalEdges) {
        for (const related of reverseTraceSink(edge, index, publicNames, callers)) {
            if (memberNames.has(related.relatedPublicApi)) continue;
            const key = `${edge.memberApi}|${edge.targetParameter}|${edge.callee}|${edge.argumentIndex}|` +
                `${related.relatedPublicApi}|${related.relatedParameters.join(',')}`;
            if (seen.has(key)) continue;
            seen.add(key);
            links.push({
                targetMember: edge.memberApi,
                targetParameter: edge.targetParameter,
                sink: {
                    symbol: edge.callee,
                    argumentIndex: edge.argumentIndex,
                    argumentCount: edge.argumentCount,
                    file: edge.file,
                    line: edge.line
                },
                ...related
            });
        }
    }

    const targetParameters = [...new Set(publicSignatures
        .filter(signature => memberApis.some(member => member.name === signature.funcName))
        .flatMap(signature => getParameterNames(signature.rawParams)))];
    return {
        scannedFileCount: codeFiles.length,
        definitionCount: index.definitions.length,
        targetEdges: trace.allEdges,
        links,
        nameHints: collectNameHints(targetParameters, index.fileContents),
        diagnostics: links.length === 0
            ? ['No exact same-sink public-wrapper link was resolved; name hints remain weak evidence only.']
            : []
    };
}

module.exports = {
    buildSemanticLinks,
    collectCodeFiles,
    dependencyClosure,
    extractCalls,
    extractDefinitions,
    normalizedIdentifier,
    reverseTraceSink
};
