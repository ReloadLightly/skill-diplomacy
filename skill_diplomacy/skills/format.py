"""Agent-Skills-compatible skill libraries.

Per the handoff brief (§2, §5): libraries MUST stay in Agent-Skills-compatible
folders so artifacts transfer to ACTIR unchanged. One folder per skill:

    library_root/
      <skill-name>/
        SKILL.md          # frontmatter (name, description, version, provenance) + playbook body
        scripts/*.py      # optional bundled tools

Mutation = text editing; provenance records authorship and import lineage so
the adoption graph is reconstructible from libraries alone (and from the event
log — both should agree)."""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkillMeta:
    name: str
    description: str
    version: int
    provenance: dict


def _frontmatter(meta: SkillMeta) -> str:
    return ("---\n"
            f"name: {meta.name}\n"
            f"description: {meta.description}\n"
            f"version: {meta.version}\n"
            f"provenance: {json.dumps(meta.provenance, ensure_ascii=False)}\n"
            "---\n")


def _parse_skill_md(text: str) -> tuple[SkillMeta, str]:
    parts = text.split("---\n")
    if len(parts) < 3:
        raise ValueError("SKILL.md missing frontmatter")
    fm, body = parts[1], "---\n".join(parts[2:]).lstrip("\n")
    fields: dict[str, str] = {}
    for line in fm.strip().splitlines():
        k, _, v = line.partition(":")
        fields[k.strip()] = v.strip()
    meta = SkillMeta(fields["name"], fields.get("description", ""),
                     int(fields.get("version", "1")),
                     json.loads(fields.get("provenance", "{}")))
    return meta, body


class SkillLibrary:
    def __init__(self, root: str | Path, owner: str):
        self.root = Path(root)
        self.owner = owner
        self.root.mkdir(parents=True, exist_ok=True)

    # -- authoring ---------------------------------------------------------
    def add_skill(self, name: str, description: str, body: str,
                  scripts: dict[str, str] | None = None,
                  provenance: dict | None = None) -> Path:
        prov = {"author": self.owner, "imported_from": None, **(provenance or {})}
        d = self.root / name
        version = self.meta(name).version + 1 if d.exists() else 1
        d.mkdir(parents=True, exist_ok=True)
        meta = SkillMeta(name, description, version, prov)
        (d / "SKILL.md").write_text(_frontmatter(meta) + body.strip() + "\n")
        if scripts:
            sdir = d / "scripts"
            sdir.mkdir(exist_ok=True)
            for fname, code in scripts.items():
                (sdir / fname).write_text(code)
        return d

    # -- reading -----------------------------------------------------------
    def skill_names(self) -> list[str]:
        return sorted(p.parent.name for p in self.root.glob("*/SKILL.md"))

    def meta(self, name: str) -> SkillMeta:
        meta, _ = _parse_skill_md((self.root / name / "SKILL.md").read_text())
        return meta

    def body(self, name: str) -> str:
        _, body = _parse_skill_md((self.root / name / "SKILL.md").read_text())
        return body

    def scripts(self, name: str) -> dict[str, str]:
        sdir = self.root / name / "scripts"
        return {p.name: p.read_text() for p in sorted(sdir.glob("*.py"))} if sdir.exists() else {}

    def content_hash(self, name: str) -> str:
        h = hashlib.sha256((self.root / name / "SKILL.md").read_text().encode())
        for fname, code in sorted(self.scripts(name).items()):
            h.update(fname.encode()); h.update(code.encode())
        return h.hexdigest()[:16]

    def render_index(self) -> str:
        """Progressive-disclosure-lite: names + descriptions only (full bodies
        are injected per-task only for the home-shard family in v0)."""
        lines = []
        for n in self.skill_names():
            m = self.meta(n)
            lines.append(f"- {m.name} (v{m.version}): {m.description}")
        return "Available skills:\n" + "\n".join(lines) if lines else "No skills yet."

    def render_full(self, name: str) -> str:
        parts = [f"## Skill: {name}\n{self.body(name)}"]
        for fname, code in self.scripts(name).items():
            parts.append(f"### scripts/{fname}\n```python\n{code}\n```")
        return "\n\n".join(parts)

    # -- exchange ----------------------------------------------------------
    def export_skill(self, name: str) -> dict:
        m = self.meta(name)
        return {"name": name, "description": m.description, "body": self.body(name),
                "scripts": self.scripts(name), "content_hash": self.content_hash(name),
                "provenance": m.provenance}

    def import_skill(self, artifact: dict, exporter: str) -> Path:
        prov = {"author": artifact["provenance"].get("author", exporter),
                "imported_from": exporter,
                "origin_hash": artifact["content_hash"]}
        return self.add_skill(artifact["name"], artifact["description"],
                              artifact["body"], artifact["scripts"], prov)

    def remove_skill(self, name: str) -> None:
        shutil.rmtree(self.root / name, ignore_errors=True)

    # -- diversity ---------------------------------------------------------
    def shingles(self, k: int = 5) -> set[str]:
        toks: list[str] = []
        for n in self.skill_names():
            toks.extend(self.body(n).split())
        return {" ".join(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}


def jaccard(a: SkillLibrary, b: SkillLibrary, k: int = 5) -> float:
    sa, sb = a.shingles(k), b.shingles(k)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)
