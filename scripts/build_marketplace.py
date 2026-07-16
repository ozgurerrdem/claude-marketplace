import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / ".claude-plugin" / "marketplace.json"
TEAM_SETTINGS_OUT = ROOT / "plugins" / "marketplace-setup" / "team-settings.json"

MARKETPLACE_NAME = "vatan-marketplace"
MARKETPLACE_OWNER = "Ozgur Dagdeviren"
MARKETPLACE_REPO = "ozgurerrdem/claude-marketplace"


def gh(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def resolve_sha(repo, ref):
    return gh(f"https://api.github.com/repos/{repo}/commits/{ref}")["sha"]


def tree(repo, sha):
    data = gh(f"https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1")
    if data.get("truncated"):
        print(f"UYARI: {repo} agac cikti truncated", file=sys.stderr)
    return [t["path"] for t in data.get("tree", []) if t["type"] == "blob"]


def discover_skills(repo, sha, base):
    prefix = base.rstrip("/") + "/"
    names = set()
    for p in tree(repo, sha):
        if p.startswith(prefix) and p.endswith("/SKILL.md"):
            rel = p[len(prefix):]
            parts = rel.split("/")
            if len(parts) == 2:
                names.add(parts[0])
    return sorted(names)


def base_entry(s):
    return {
        "name": s["name"],
        "displayName": s.get("displayName", s["name"]),
        "description": s["description"],
        "author": {"name": s["author"]},
        "category": s.get("category", "development"),
        "homepage": s.get("homepage") or f"https://github.com/{s.get('repo', '')}",
    }


def build_plugin(s):
    entry = base_entry(s)
    entry["source"] = {"source": "github", "repo": s["repo"], "ref": s.get("ref", "main")}
    return entry


def build_skills_subdir(s):
    sha = resolve_sha(s["repo"], s.get("ref", "main"))
    skills = discover_skills(s["repo"], sha, s["path"])
    if not skills:
        print(f"UYARI: {s['name']} icin skill bulunamadi, atlaniyor", file=sys.stderr)
        return None
    entry = base_entry(s)
    entry["source"] = {
        "source": "git-subdir",
        "url": f"https://github.com/{s['repo']}.git",
        "path": s["path"],
        "ref": s.get("ref", "main"),
    }
    entry["strict"] = False
    entry["skills"] = [f"./{n}" for n in skills]
    return entry


def build_local(s):
    src = ROOT / s["source"].lstrip("./")
    if not (src / ".claude-plugin" / "plugin.json").exists():
        print(f"UYARI: {s['name']} icin plugin.json yok, atlaniyor", file=sys.stderr)
        return None
    entry = base_entry(s)
    entry["source"] = s["source"]
    return entry


BUILDERS = {
    "plugin": build_plugin,
    "skills-subdir": build_skills_subdir,
    "local": build_local,
}


def main():
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    plugins = []
    failed = False

    for s in sources:
        builder = BUILDERS.get(s["kind"])
        if builder is None:
            print(f"HATA: bilinmeyen kind '{s['kind']}' ({s['name']})", file=sys.stderr)
            failed = True
            continue
        try:
            entry = builder(s)
        except urllib.error.HTTPError as e:
            print(f"HATA: {s['name']} -> {e.code} {e.reason}", file=sys.stderr)
            failed = True
            continue
        if entry:
            plugins.append(entry)

    if not plugins:
        print("HATA: hic plugin uretilemedi", file=sys.stderr)
        sys.exit(1)

    doc = {
        "name": MARKETPLACE_NAME,
        "owner": {"name": MARKETPLACE_OWNER},
        "plugins": plugins,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(plugins)} plugin yazildi -> {OUT.relative_to(ROOT)}")

    # Ekip icin proje `.claude/settings.json`'a birlestirilecek hazir sablon.
    # marketplace-setup plugin'inin kendi klasorunde tutulur ki plugin kurulunca
    # bu dosya da ekip uyeleriyle birlikte dagilsin (repo kokundeki dosyalar
    # yerel kind="plugin" pluginlerle birlikte kopyalanmaz).
    team_settings = {
        "extraKnownMarketplaces": {
            MARKETPLACE_NAME: {
                "source": {"source": "github", "repo": MARKETPLACE_REPO}
            }
        },
        "enabledPlugins": {
            f"{p['name']}@{MARKETPLACE_NAME}": True for p in plugins
        },
    }
    TEAM_SETTINGS_OUT.parent.mkdir(parents=True, exist_ok=True)
    TEAM_SETTINGS_OUT.write_text(
        json.dumps(team_settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"ekip sablonu yazildi -> {TEAM_SETTINGS_OUT.relative_to(ROOT)}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
