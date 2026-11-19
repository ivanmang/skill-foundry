#!/usr/bin/env python3
"""Import external skills/libraries — core engine.

The `./harness import` verb integrates external skill sources into the harness.
This module is the deterministic machinery: the source registry, the adapter
protocol, discovery, and the relevance check (completeness / self-containment /
dedupe, plus an optional LLM semantic judge). It never mutates the published
corpus — it discovers, scores, and records a manifest. Publishing reuses the
existing validate -> gates -> review -> promote loop unchanged.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from skill_foundry.paths import IMPORTS_HUB, INBOX, ROOT, SKILLS
from skill_foundry.lib import validate_skills

# ── verdicts ────────────────────────────────────────────────────────────────
RELEVANT = "relevant"
IRRELEVANT = "irrelevant"
DUPLICATE = "duplicate"
EXTEND = "extend"
HOLD = "hold"
VERDICTS = (RELEVANT, IRRELEVANT, DUPLICATE, EXTEND, HOLD)

# Highest priority wins when combining the deterministic verdict with the LLM
# judge's verdict (most restrictive first).
_VERDICT_PRIORITY = {IRRELEVANT: 5, DUPLICATE: 4, HOLD: 3, EXTEND: 2, RELEVANT: 1}

# Dedupe thresholds (name-token / description similarity vs existing skills).
DUP_THRESHOLD = 0.85
EXTEND_THRESHOLD = 0.60
CLOSEST_HINT_THRESHOLD = 0.40

# Adapter types and import modes (mirrors the CLI surface).
KNOWN_TYPES = ("knowledge-library", "agent-skills", "local-dir")
KNOWN_MODES = ("vendor", "reference", "passthrough")

# Files always skipped when resolving an include (build artifacts / VCS noise).
SKIP_NAMES = {".git", ".gitignore", "__pycache__", "node_modules"}
SKIP_SUFFIXES = (".pyc",)

# Machine-specific home paths — a self-containment violation (the source
# should be portable; a sentence sending the reader to a machine path is a bug).
_ABS_PATH_RE = re.compile(r"(?:/home/|/root/|/Users/)")


# ── source + candidate model ────────────────────────────────────────────────
@dataclass
class SourceConfig:
    name: str
    type: str
    location: str
    origin: str = "library"
    owner: str = "skills-library"
    mode: str = "vendor"
    scope_hint: str = ""
    mapping: str = ""

    @property
    def root(self) -> Path:
        """Resolved local path for this source (tilde / env var expanded)."""
        if self.location.startswith(("http://", "https://", "git@", "ssh://")):
            raise ValueError(f"source '{self.name}' is a remote URL — clone it first")
        return Path(os.path.expanduser(os.path.expandvars(self.location))).resolve()


@dataclass
class Candidate:
    name: str
    description: str
    category: str
    entry: bool = False
    include: list[str] = field(default_factory=list)  # declared include entries
    entry_file: str = ""  # primary source-relative file
    files: list[str] = field(default_factory=list)  # resolved source-relative files
    fingerprint: str = ""  # stable hash over (relpath, content)


class Adapter(Protocol):
    """A source type. New kinds of external sources add one adapter; the shared
    relevance / validate / promote pipeline is unchanged."""

    type_name: str

    def discover(self, src: SourceConfig) -> list[Candidate]: ...

    def build_skill(self, c: Candidate, src: SourceConfig) -> None: ...

    def provenance(self, c: Candidate, src: SourceConfig) -> dict: ...

    def sync_refs(self, c: Candidate, src: SourceConfig) -> bool: ...


# ── registry ────────────────────────────────────────────────────────────────
def load_registry() -> dict:
    from skill_foundry.paths import IMPORTS_CONFIG

    try:
        data = json.loads(IMPORTS_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "sources": {}}
    if not isinstance(data, dict):
        return {"version": 1, "sources": {}}
    data.setdefault("version", 1)
    data.setdefault("sources", {})
    return data


def save_registry(registry: dict) -> None:
    from skill_foundry.paths import IMPORTS_CONFIG

    IMPORTS_CONFIG.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def source_from_registry(name: str) -> SourceConfig | None:
    entry = load_registry().get("sources", {}).get(name)
    if not isinstance(entry, dict):
        return None
    return SourceConfig(
        name=name,
        type=entry.get("type", ""),
        location=entry.get("location") or entry.get("git", ""),
        origin=entry.get("origin", "library"),
        owner=entry.get("owner", name),
        mode=entry.get("mode", "vendor"),
        scope_hint=entry.get("scope_hint", ""),
        mapping=entry.get("mapping", ""),
    )


def add_source(
    name: str,
    type_: str,
    location: str,
    origin: str | None = None,
    owner: str | None = None,
    mode: str = "vendor",
    scope_hint: str = "",
    mapping: str = "",
) -> SourceConfig:
    """Register a source in config/imports.json. Raises ValueError on bad input."""
    if (
        not re.fullmatch(r"[a-z0-9-]+", name)
        or len(name) > 64
        or name.startswith("-")
        or name.endswith("-")
        or "--" in name
    ):
        raise ValueError(
            f"invalid source name '{name}' — [a-z0-9-], no "
            "leading/trailing/consecutive hyphens"
        )
    if type_ not in KNOWN_TYPES:
        raise ValueError(f"unknown type '{type_}' — one of {sorted(KNOWN_TYPES)}")
    mode = mode or "vendor"
    if mode not in KNOWN_MODES:
        raise ValueError(f"unknown mode '{mode}' — one of {sorted(KNOWN_MODES)}")
    if not location:
        raise ValueError("need --path <loc>")
    if location.startswith(("http://", "https://", "git@", "ssh://")):
        raise ValueError(
            "remote git URLs are not supported yet — clone the repo and pass "
            "--path <local checkout>"
        )
    if origin and origin not in validate_skills.KNOWN_ORIGINS:
        raise ValueError(
            f"unknown origin '{origin}' — one of {sorted(validate_skills.KNOWN_ORIGINS)}"
        )
    registry = load_registry()
    sources = registry.setdefault("sources", {})
    if name in sources:
        raise ValueError(
            f"source '{name}' already registered (./harness import --remove {name} first)"
        )
    entry: dict = {
        "type": type_,
        "location": location,
        "origin": origin or "library",
        "owner": owner or name,
        "mode": mode or "vendor",
    }
    if scope_hint:
        entry["scope_hint"] = scope_hint
    if mapping:
        entry["mapping"] = mapping
    sources[name] = entry
    save_registry(registry)
    return source_from_registry(name)


def remove_source(name: str) -> None:
    """Deregister a source (registry entry only — never removes skills/drafts)."""
    registry = load_registry()
    sources = registry.setdefault("sources", {})
    if name not in sources:
        raise ValueError(f"source '{name}' not registered")
    del sources[name]
    save_registry(registry)


def ensure_mapping(name: str, mapping_path: str) -> Path:
    """Create an empty mapping manifest stub if it does not exist."""
    p = ROOT / mapping_path
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"version": 1, "source": name, "skills": []}, indent=2) + "\n",
            encoding="utf-8",
        )
    return p


# ── mapping manifest ────────────────────────────────────────────────────────
def load_mapping(src: SourceConfig) -> dict:
    if not src.mapping:
        return {"skills": []}
    p = ROOT / src.mapping
    if not p.is_file():
        raise FileNotFoundError(f"mapping manifest not found: {src.mapping}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"mapping manifest is not valid JSON: {src.mapping}") from exc
    if not isinstance(data, dict):
        return {"skills": []}
    return data


# ── file resolution + fingerprint ───────────────────────────────────────────
def _keep(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name in SKIP_NAMES or "__pycache__" in path.parts:
        return False
    return not path.name.endswith(SKIP_SUFFIXES)


def resolve_include(root: Path, entry: str) -> list[Path]:
    """Expand one include entry (directory, file, or glob) to files, in order."""
    if entry.endswith("/") or (root / entry).is_dir():
        base = root / entry.rstrip("/")
        return [f for f in sorted(base.rglob("*")) if _keep(f)]
    if any(ch in entry for ch in "*?["):
        return [f for f in sorted(root.glob(entry)) if _keep(f)]
    p = root / entry
    return [p] if _keep(p) else []


def resolve_includes(root: Path, include: list[str]) -> list[str]:
    """Resolve a list of include entries to deduped source-relative file paths."""
    rels: list[str] = []
    seen: set[str] = set()
    for entry in include:
        for f in resolve_include(root, entry):
            rel = f.relative_to(root).as_posix()
            if rel not in seen:
                seen.add(rel)
                rels.append(rel)
    return rels


def fingerprint_files(root: Path, rel_paths: list[str]) -> str:
    """Stable hash over (relative path, content) — the --sync drift signal."""
    h = hashlib.sha256()
    for rel in sorted(rel_paths):
        h.update(rel.encode())
        h.update(b"\0")
        h.update(hashlib.sha256((root / rel).read_bytes()).digest())
    return h.hexdigest()


# ── adapters ────────────────────────────────────────────────────────────────
def _first_heading(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return ""


def _detect_license(src: SourceConfig) -> str:
    p = src.root / "LICENSE"
    if not p.is_file():
        return "See references/LICENSE"
    head = p.read_text(encoding="utf-8", errors="replace")[:400].lower()
    if "apache license" in head and "version 2.0" in head:
        return "Apache-2.0"
    if "mit license" in head:
        return "MIT"
    return "See references/LICENSE"


_FRONT_SPLIT_RE = re.compile(r"^---\s*\n(.*?)^---\s*\n?(.*)$", re.MULTILINE | re.DOTALL)


def _split_skill_md(text: str) -> tuple[str, str]:
    """Return (frontmatter_content, body); fm_content is '' when absent."""
    m = _FRONT_SPLIT_RE.match(text)
    if not m:
        return "", text
    return m.group(1), m.group(2)


def _inject_frontmatter(text: str, fields: dict[str, str]) -> str:
    """Add missing top-level scalar fields to a SKILL.md, preserving the rest."""
    fm, body = _split_skill_md(text)
    existing, _ = validate_skills.parse_frontmatter(text)
    additions = [
        f"{k}: {v}" for k, v in fields.items() if not (existing.get(k) or "").strip()
    ]
    if not additions:
        return text
    if fm:
        return (
            "---\n" + fm.rstrip("\n") + "\n" + "\n".join(additions) + "\n---\n" + body
        )
    return "---\n" + "\n".join(additions) + "\n---\n\n" + text


class KnowledgeLibraryAdapter:
    """A self-contained knowledge library with no SKILL.md files: a mapping
    manifest groups its leaves into skill candidates."""

    type_name = "knowledge-library"

    def discover(self, src: SourceConfig) -> list[Candidate]:
        root = src.root
        if not root.is_dir():
            raise FileNotFoundError(f"source root not found: {root}")
        manifest = load_mapping(src)
        out: list[Candidate] = []
        for entry in manifest.get("skills", []):
            if not isinstance(entry, dict):
                continue
            include = [i for i in entry.get("include", []) if isinstance(i, str)]
            files = resolve_includes(root, include)
            cand = Candidate(
                name=entry.get("name", ""),
                description=entry.get("description", ""),
                category=entry.get("category", ""),
                entry=bool(entry.get("entry")),
                include=include,
                entry_file=entry.get("entry_file", ""),
                files=files,
            )
            cand.fingerprint = fingerprint_files(root, cand.files)
            out.append(cand)
        return out

    def build_skill(self, c: Candidate, src: SourceConfig) -> None:
        """Snapshot the candidate's source files into hub/inbox/<name>/ and
        synthesize a thin router SKILL.md (frontmatter + file table)."""
        root = src.root
        dest = INBOX / c.name
        if dest.exists():
            raise FileExistsError(f"draft already exists: hub/inbox/{c.name}")
        refs = dest / "references"
        for rel in c.files:
            dst = refs / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dst)
        lic = root / "LICENSE"
        if lic.is_file():
            shutil.copy2(lic, refs / "LICENSE")
        (dest / "SKILL.md").write_text(
            self._frontmatter(c, src) + "\n" + self._body(c, src), encoding="utf-8"
        )

    def _title(self, c: Candidate, src: SourceConfig) -> str:
        if c.entry_file:
            heading = _first_heading(src.root / c.entry_file)
            if heading:
                return heading
        return c.name.replace("-", " ").title()

    def _frontmatter(self, c: Candidate, src: SourceConfig) -> str:
        prov = self.provenance(c, src)
        md = prov.get("metadata", {})
        lines = [
            "---",
            f"name: {c.name}",
            "description: >",
            f"  {c.description}",
            f"license: {_detect_license(src)}",
            f"category: {c.category}",
            f"origin: {prov.get('origin', src.origin)}",
            f"owner: {prov.get('owner', src.owner)}",
            f"maturity: {prov.get('maturity', 'ready')}",
            "metadata:",
            "  status: draft",
            f"  source: {md.get('source', src.name)}",
            f"  location: {md.get('location', src.location)}",
            f"  fingerprint: {md.get('fingerprint', c.fingerprint)}",
            "---",
        ]
        return "\n".join(lines) + "\n"

    def _body(self, c: Candidate, src: SourceConfig) -> str:
        lines = [
            f"# {self._title(c, src)}",
            "",
            c.description,
            "",
            f"Imported from `{src.name}` (`{src.location}`) — reference snapshot. "
            f"Run `./harness import {src.name} --sync` to refresh from source.",
            "",
            "## Files",
            "",
            "Match your job, then open the one file it names.",
            "",
            "| File | Purpose |",
            "|---|---|",
        ]
        for rel in c.files:
            purpose = _first_heading(src.root / rel)
            lines.append(f"| `references/{rel}` | {purpose or '—'} |")
        lines += [
            "",
            "## Start here",
            "",
        ]
        if c.entry_file:
            lines.append(f"Open `references/{c.entry_file}` first.")
        else:
            lines.append("Open the file above that matches your job.")
        lines += [
            "",
            "## Gotchas",
            "",
            "- The reference files are snapshots; the source library is the single "
            "source of truth. Refresh with `./harness import <source> --sync`.",
            "- Open one file per job (the library's `job → one open` rule).",
        ]
        return "\n".join(lines) + "\n"

    def provenance(self, c: Candidate, src: SourceConfig) -> dict:
        return {
            "origin": src.origin,
            "owner": src.owner,
            "maturity": "ready",
            "metadata": {
                "source": src.name,
                "location": src.location,
                "fingerprint": c.fingerprint,
            },
        }

    def sync_refs(self, c: Candidate, src: SourceConfig) -> bool:
        """Refresh the references/ snapshot for a drifted draft."""
        root = src.root
        dest = INBOX / c.name
        if not (dest / "SKILL.md").exists():
            return False
        refs = dest / "references"
        wanted = set(c.files)
        if refs.exists():
            for p in sorted(refs.rglob("*")):
                if (
                    not p.is_file()
                    or p.name in SKIP_NAMES
                    or p.name.endswith(SKIP_SUFFIXES)
                ):
                    continue
                rel = p.relative_to(refs).as_posix()
                if rel == "LICENSE":
                    continue
                if rel not in wanted:
                    p.unlink()
        for rel in c.files:
            dst = refs / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dst)
        lic = root / "LICENSE"
        if lic.is_file():
            shutil.copy2(lic, refs / "LICENSE")
        sm = dest / "SKILL.md"
        text = sm.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"(fingerprint:\s*)[0-9a-f]+", r"\g<1>" + c.fingerprint, text)
        sm.write_text(text, encoding="utf-8")
        return True


class AgentSkillsAdapter:
    """An Agent Skills source: a directory of <name>/SKILL.md folders.

    vendor      copy the folder and inject missing provenance frontmatter.
    passthrough copy as-is (trust the source's frontmatter).
    reference   write a pointer stub (content stays at the source location).
    """

    type_name = "agent-skills"

    def discover(self, src: SourceConfig) -> list[Candidate]:
        root = src.root
        if not root.is_dir():
            raise FileNotFoundError(f"source root not found: {root}")
        out: list[Candidate] = []
        for d in sorted(root.iterdir()):
            sm = d / "SKILL.md"
            if not d.is_dir() or not sm.exists():
                continue
            fm, _ = validate_skills.parse_frontmatter(
                sm.read_text(encoding="utf-8", errors="replace")
            )
            files = [str(p.relative_to(root)) for p in sorted(d.rglob("*")) if _keep(p)]
            cand = Candidate(
                name=d.name,
                description=(fm.get("description") or "").strip(),
                category=(fm.get("category") or "imported").strip(),
                entry=(fm.get("entry") or "").strip().lower()
                in {"true", "yes", "1", "on"},
                include=[],
                entry_file=f"{d.name}/SKILL.md",
                files=files,
            )
            cand.fingerprint = fingerprint_files(root, cand.files)
            out.append(cand)
        return out

    def build_skill(self, c: Candidate, src: SourceConfig) -> None:
        root = src.root
        dest = INBOX / c.name
        if dest.exists():
            raise FileExistsError(f"draft already exists: hub/inbox/{c.name}")
        if src.mode == "reference":
            self._build_reference(c, src, dest)
            return
        prefix = f"{c.name}/"
        for rel in c.files:
            rel_dest = rel[len(prefix) :] if rel.startswith(prefix) else rel
            dst = dest / rel_dest
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dst)
        if src.mode == "passthrough":
            return
        self._inject_provenance(c, src, dest)

    def _inject_provenance(self, c: Candidate, src: SourceConfig, dest: Path) -> None:
        """Add missing skill-foundry metadata to a copied SKILL.md."""
        sm = dest / "SKILL.md"
        text = sm.read_text(encoding="utf-8", errors="replace")
        fm, _ = validate_skills.parse_frontmatter(text)
        fields: dict[str, str] = {}
        if not (fm.get("name") or "").strip():
            fields["name"] = c.name
        if not (fm.get("category") or "").strip():
            fields["category"] = "imported"
        if not (fm.get("origin") or "").strip():
            fields["origin"] = src.origin
        if not (fm.get("owner") or "").strip():
            fields["owner"] = src.owner
        if not (fm.get("maturity") or "").strip():
            fields["maturity"] = "ready"
        if fields:
            sm.write_text(_inject_frontmatter(text, fields), encoding="utf-8")

    def _build_reference(self, c: Candidate, src: SourceConfig, dest: Path) -> None:
        dest.mkdir(parents=True)
        body = (
            f"# {c.name.replace('-', ' ').title()}\n\n"
            f"{c.description}\n\n"
            "This is a **reference** import — the skill's content lives outside "
            "this repo:\n\n"
            f"`{src.location}/{c.name}`\n\n"
            "Open the original `SKILL.md` there. This stub only registers the "
            "name for discovery and cross-reference resolution.\n"
        )
        fm = (
            "---\n"
            f"name: {c.name}\n"
            "description: >\n"
            f"  {c.description}\n"
            f"category: {c.category}\n"
            f"origin: {src.origin}\n"
            f"owner: {src.owner}\n"
            "maturity: draft\n"
            "metadata:\n"
            "  status: draft\n"
            f"  source: {src.name}\n"
            f"  location: {src.location}\n"
            "---\n"
        )
        (dest / "SKILL.md").write_text(fm + "\n" + body, encoding="utf-8")

    def provenance(self, c: Candidate, src: SourceConfig) -> dict:
        return {
            "origin": src.origin,
            "owner": src.owner,
            "maturity": "ready",
            "metadata": {
                "source": src.name,
                "location": src.location,
                "fingerprint": c.fingerprint,
            },
        }

    def sync_refs(self, c: Candidate, src: SourceConfig) -> bool:
        """Refresh a vendored draft from the source (remove stale, re-copy)."""
        root = src.root
        dest = INBOX / c.name
        if not (dest / "SKILL.md").exists():
            return False
        if src.mode == "reference":
            return True  # content lives outside this repo
        prefix = f"{c.name}/"
        wanted = {
            rel[len(prefix) :] if rel.startswith(prefix) else rel for rel in c.files
        }
        for p in sorted(dest.rglob("*")):
            if (
                not p.is_file()
                or p.name in SKIP_NAMES
                or p.name.endswith(SKIP_SUFFIXES)
            ):
                continue
            if p.relative_to(dest).as_posix() not in wanted:
                p.unlink()
        for rel in c.files:
            rel_dest = rel[len(prefix) :] if rel.startswith(prefix) else rel
            dst = dest / rel_dest
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dst)
        if src.mode == "passthrough":
            return True
        self._inject_provenance(c, src, dest)
        return True


ADAPTERS: dict[str, Adapter] = {
    "knowledge-library": KnowledgeLibraryAdapter(),
    "agent-skills": AgentSkillsAdapter(),
    "local-dir": AgentSkillsAdapter(),
}


def get_adapter(type_name: str) -> Adapter | None:
    return ADAPTERS.get(type_name)


# ── relevance (deterministic) ───────────────────────────────────────────────
def existing_skills() -> list[dict]:
    """Published skill names + descriptions (the dedupe corpus)."""
    out: list[dict] = []
    for d in sorted(SKILLS.iterdir()):
        sm = d / "SKILL.md"
        if not d.is_dir() or not sm.exists():
            continue
        fm, err = validate_skills.parse_frontmatter(
            sm.read_text(encoding="utf-8", errors="replace")
        )
        if err:
            continue
        out.append(
            {
                "name": fm.get("name") or d.name,
                "description": (fm.get("description") or "").strip(),
            }
        )
    return out


def _tokens(name: str) -> set[str]:
    return {t for t in name.split("-") if t}


def closest_existing(c: Candidate, existing: list[dict]) -> tuple[str, float]:
    cand_tokens = _tokens(c.name)
    cand_desc = c.description.lower()
    best_name, best_score = "", 0.0
    for ex in existing:
        ex_name = ex["name"]
        ex_tokens = _tokens(ex_name)
        if cand_tokens and ex_tokens:
            inter = cand_tokens & ex_tokens
            token_score = len(inter) / len(cand_tokens | ex_tokens)  # Jaccard
        else:
            token_score = 0.0
        desc_score = difflib.SequenceMatcher(
            None, cand_desc, (ex.get("description") or "").lower()
        ).ratio()
        score = max(desc_score, token_score)
        if score > best_score:
            best_name, best_score = ex_name, score
    return best_name, best_score


def _self_containment_issues(c: Candidate, src: SourceConfig) -> list[str]:
    root = src.root
    issues: list[str] = []
    for rel in c.files:
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for m in _ABS_PATH_RE.finditer(text):
            issues.append(f"{rel}: machine-specific path '{m.group(0)}'")
            if len(issues) >= 5:
                return issues
    return issues


def relevance(
    c: Candidate, src: SourceConfig, existing: list[dict]
) -> tuple[str, list[str]]:
    """Deterministic relevance. Returns (verdict, reasons)."""
    reasons: list[str] = []

    # completeness
    if not c.name or not c.description or not c.category:
        return IRRELEVANT, ["mapping entry is missing name/description/category"]
    if not c.files:
        return IRRELEVANT, ["resolves to 0 files — fix the include list"]
    if c.entry_file and c.entry_file not in c.files:
        return IRRELEVANT, [f"entry_file '{c.entry_file}' not among resolved files"]

    # self-containment
    sc_issues = _self_containment_issues(c, src)
    reasons.extend(sc_issues)

    # dedupe
    best, score = closest_existing(c, existing)
    verdict = RELEVANT
    if score >= DUP_THRESHOLD:
        verdict = DUPLICATE
        reasons.append(f"duplicate of existing skill '{best}' (score {score:.2f})")
    elif score >= EXTEND_THRESHOLD:
        verdict = EXTEND
        reasons.append(
            f"overlaps existing skill '{best}' (score {score:.2f}) — extend, don't fork"
        )
    elif best and score >= CLOSEST_HINT_THRESHOLD:
        reasons.append(f"closest existing: '{best}' (score {score:.2f})")

    if sc_issues:
        verdict = combine_verdicts(verdict, HOLD)
    return verdict, reasons


def combine_verdicts(a: str, b: str) -> str:
    """Return the more restrictive of two verdicts."""
    return a if _VERDICT_PRIORITY.get(a, 0) >= _VERDICT_PRIORITY.get(b, 0) else b


# ── LLM semantic judge (optional; mirrors reviewer.SKILL_REVIEWER contract) ──
def llm_payload(c: Candidate, src: SourceConfig, existing: list[dict]) -> str:
    best, score = closest_existing(c, existing)
    lines = [
        "Review this candidate for import into skill-foundry.",
        "",
        f"Candidate: {c.name}",
        f"  category: {c.category}",
        f"  source: {src.name} ({src.type})",
        f"  description: {c.description}",
        f"  files: {len(c.files)}",
    ]
    if best:
        lines.append(f"  closest existing skill: {best} (score {score:.2f})")
    lines += [
        "",
        "Reply exactly one word: RELEVANT, IRRELEVANT, DUPLICATE, EXTEND, or HOLD.",
    ]
    return "\n".join(lines)


def llm_relevance(payload: str) -> str | None:
    """Run IMPORT_REVIEWER on a candidate payload. None when not configured."""
    cmd = os.environ.get("IMPORT_REVIEWER")
    if not cmd:
        return None
    try:
        argv = shlex.split(cmd)
    except ValueError:
        argv = [cmd]
    if not argv:
        return None
    try:
        r = subprocess.run(
            argv, input=payload, capture_output=True, text=True, timeout=180
        )
    except Exception as exc:  # pragma: no cover - environmental
        print(f"import reviewer error: {exc}", file=sys.stderr)
        return None
    out = ((r.stdout or "") + " " + (r.stderr or "")).upper()
    m = re.search(r"\b(RELEVANT|IRRELEVANT|DUPLICATE|EXTEND|HOLD)\b", out)
    return m.group(1).lower() if m else None


# ── manifest ────────────────────────────────────────────────────────────────
def manifest_path(source_name: str) -> Path:
    return IMPORTS_HUB / source_name / "manifest.json"


def read_manifest(source_name: str) -> dict | None:
    p = manifest_path(source_name)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_manifest(source_name: str, results: list[dict]) -> Path:
    import datetime as _dt

    p = manifest_path(source_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source": source_name,
        "scanned_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "candidates": results,
    }
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return p
