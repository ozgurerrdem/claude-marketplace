# ozgur-marketplace

Claude (Desktop / Cowork / Claude Code) icin kisisel plugin marketplace.

## Icerik

| Plugin | Kaynak | Tur |
|---|---|---|
| andrej-karpathy-skills | multica-ai/andrej-karpathy-skills | skill |
| context-mode | mksglu/context-mode | skill + yerel MCP |
| rtk-skills | rtk-ai/rtk (`.claude/skills`) | skill |
| codegraph | npm `@colbymchenry/codegraph` | yerel MCP |
| codebase-memory | npm `codebase-memory-mcp` | yerel MCP |

## Kullanim

Claude Desktop: **Customize > Plugins > Personal plugins > + > Add marketplace** -> `KULLANICI/claude-marketplace`

## Yeni kaynak ekleme

`sources.json` dosyasina bir kayit ekle, push et. GitHub Actions `.claude-plugin/marketplace.json` dosyasini yeniden uretir.

- `kind: plugin` -> hedef repoda `.claude-plugin/plugin.json` var
- `kind: skills-subdir` -> hedef repoda manifest yok, `path` altindaki SKILL.md klasorleri otomatik taranir
- `kind: local` -> `plugins/<ad>/` altinda kendi sardigin plugin (MCP sunuculari icin)

Sync gunluk 03:00 UTC cron ile veya Actions sekmesinden **Run workflow** ile calisir.
