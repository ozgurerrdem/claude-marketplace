# claude-marketplace

Claude Desktop, Cowork ve Claude Code icin kisisel plugin marketplace.

> Bu GitHub reposunun adi `claude-marketplace`, ama marketplace **`workbench`** adiyla
> kayit olur (adin kaynagi `scripts/build_marketplace.py` icindeki `MARKETPLACE_NAME`).
> Plugin ID'leri bu yuzden `<plugin>@workbench` seklinde. Repo adi ile marketplace adinin
> ayni olmasi gerekmez.

Pluginler iki sekilde tutulur:

- `kind: "plugin"` olanlar (context-mode, andrej-karpathy-skills) burada **kopyalanmaz**,
  referans edilir; Claude kurulum aninda icerigi upstream repodan ceker ve kendiliginden
  guncel kalir.
- `kind: "local"` olanlar (serena, context7, engineering-standards, vatan-skills,
  marketplace-setup) bu repoda **tutulur**; guncellemesi elle yapilir.

## Icerik

| Plugin | Kaynak | Tur | Ne ise yarar |
|---|---|---|---|
| **engineering-standards** | `plugins/engineering-standards` (bu repo) | 5 skill | Vendor-neutral Clean Architecture standartlari: .NET, MSSQL, PostgreSQL, React, legacy .NET |
| **vatan-skills** | `plugins/vatan-skills` (bu repo) | 6 skill | Ayni kapsam, Vatan'a ozgu kurumsal konvansiyonlarla |
| **context-mode** | `mksglu/context-mode` | skill + yerel MCP | Buyuk tool ciktilarini yerel FTS5 veritabanina alip ajana ozet doner; context penceresini korur |
| **serena** | `plugins/serena` -> `oraios/serena` | yerel MCP | LSP tabanli sembol duzeyi kod navigasyonu ve duzenleme |
| **context7** | `plugins/context7` -> `upstash/context7` | yerel MCP | Kutuphanelerin surume ozel guncel dokumanlarini context'e ceker |
| **andrej-karpathy-skills** | `multica-ai/andrej-karpathy-skills` | skill | LLM kodlama hatalarini azaltan davranissal kurallar |
| **marketplace-setup** | `plugins/marketplace-setup` (bu repo) | 3 komut | `/marketplace-setup`, `/marketplace-doctor`, `/marketplace-refresh` |

### Standart seti secimi

`engineering-standards` ve `vatan-skills` **birbirinin alternatifidir** — ayni konularda
cakisan skill'ler uretirler, ikisini birden acmayin. Her ikisi de `sources.json`'da
`"optional": true` isaretlidir, yani ekip sablonunda varsayilan olarak **acilmaz**;
ortama gore elle secilir:

| Ortam | Secim |
|---|---|
| Kurumsal Vatan | `vatan-skills@workbench` |
| Kisisel / vendor-neutral | `engineering-standards@workbench` |

Iki setin SP hata konvansiyonu farklidir: `vatan-skills` `@Sorun`/`@Mesaj` bayrak tabanli
sonuc kumesi kullanir, `engineering-standards` ise exception-based (`THROW`) yaklasimi
varsayilan alir. Birinin ciktisini digerinin kuraliyla denetlemeyin.

### vatan-skills icerigi

| Skill | Kapsam |
|---|---|
| `vatan-dotnet-core` | Katmanli mimari, DI kaydi, servis tasarimi, hata yonetimi, Turkce structured log, async/CancellationToken, cache (in-memory vs Redis), kod kalite kurallari |
| `vatan-sql` | MSSQL: stored procedure/fonksiyon, `@Sorun`/`@Mesaj` bayrak tabanli hata sozlesmesi, Dapper cagrisi, connection omru, indeks, deadlock |
| `vatan-postgres` | PostgreSQL: PL/pgSQL fonksiyon/prosedur, Npgsql tuzaklari, `ON CONFLICT` upsert, advisory lock, tip ve indeks kurallari |
| `vatan-react-js` | React: TypeScript zorunlu, feature bazli klasor yapisi, TanStack Query, react-hook-form + zod, API katmani, Turkce arayuz |
| `vatan-legacy-dotnet` | .NET Framework / WCF: `ConfigureAwait(false)`, sozlesme kirmama, kademeli modernizasyon |
| `vatan-rtk` | RTK (Rust Token Killer) komut referansi ve hook kullanimi |

### engineering-standards icerigi

| Skill | Kapsam |
|---|---|
| `dotnet-core` | Clean Architecture katmanlama, DI, servis tasarimi, hata yonetimi, log, cache, async/CancellationToken |
| `mssql` | MSSQL: stored procedure, exception-based hata sozlesmesi, Dapper cagrisi, indeks, kilitlenme |
| `postgresql` | PostgreSQL: PL/pgSQL, Npgsql + Dapper, upsert, JSONB, sayfalama |
| `react` | React: TypeScript, Vite, TanStack Query, react-hook-form + zod |
| `legacy-dotnet` | .NET Framework / WCF: guvenli degisiklik, deadlock kacinma, kademeli modernizasyon |

## Kurulum

### Tek kisilik kullanim (Claude Desktop UI)

Claude Desktop: **Customize > Plugins > Personal plugins > `+` > Add marketplace**
-> `ozgurerrdem/claude-marketplace` -> katalogdan istedigin plugini **Install**.

Guncelleme: marketplace kartindaki menuden **Update**. Upstream repolardaki son commit cekilir.

**Onemli:** Sadece marketplace'i eklemek (`Add marketplace` / `claude plugin marketplace add`)
hicbir plugin'i kurmaz — bu adim yalnizca katalogu kaydeder. Her plugin ayrica tek tek
**Install** edilmeli / `claude plugin install <ad>@workbench` calistirilmalidir. Bu,
sadece o an kurulumu yapan kisinin makinesini etkiler.

**Ayni repoyu hem Desktop UI'dan hem Claude Code'dan eklemeyin.** Iki yuzey farkli
adlandirma kullanir (Desktop repo adini, Claude Code `marketplace.json` icindeki `name`
alanini) ve ayni katalog iki ayri marketplace gibi gorunur; pluginler listede cift cikar.
Tek bir yuzey secin.

### Ekip icin otomatik dagitim (`.claude/settings.json`)

Sirket ici bir ekipte herkesin ayni plugin setini otomatik almasi icin dogru yontem, hedef
projenin `.claude/settings.json` dosyasina marketplace kaydini ve istenen plugin listesini
yazip **git'e commitlemek**tir. Bir gelistirici projeyi ilk kez trust ettiginde Claude Code bu
dosyaya bakar ve marketplace + plugin kurulumunu **onerir** (tek seferlik onay ister, sessiz
kurulum yapmaz).

Hazir sablon: [`plugins/marketplace-setup/team-settings.json`](plugins/marketplace-setup/team-settings.json)
— icerigini hedef projenin `.claude/settings.json`'una birlestirin (mevcut anahtarlari koruyarak).
Bu sablon `sources.json`'dan otomatik uretilir, elle guncellenmez.

`/marketplace-setup` komutu (bkz. asagida) bu birlestirmeyi bir proje icin otomatik yapar.

### On kosullar

| Plugin | Gereksinim |
|---|---|
| serena | `uv` (`winget install astral-sh.uv`). Buyuk repolarda ilk kullanimdan once `serena project index` |
| context7 | Node.js (`npx` ile calisir) |
| context-mode | Node.js |
| engineering-standards, vatan-skills, karpathy, marketplace-setup | yok (saf skill/komut) |

## Yeni kaynak ekleme

`sources.json` dosyasina bir kayit ekle ve push et. GitHub Actions `.claude-plugin/marketplace.json`
dosyasini yeniden uretir.

| `kind` | Ne zaman |
|---|---|
| `plugin` | Hedef reponun kokunde `.claude-plugin/plugin.json` var |
| `skills-subdir` | Hedef repoda manifest yok; `path` altindaki `SKILL.md` klasorleri otomatik taranir |
| `local` | `plugins/<ad>/` altinda bu repoda tutulan plugin (MCP sarmalayicilari ve kendi skillerimiz) |

## Otomatik senkronizasyon

`.github/workflows/sync-marketplace.yml`:

- Her gun 03:00 UTC (cron)
- `sources.json`, `scripts/` veya `plugins/` degistiginde push'ta
- Actions sekmesinden manuel (**Run workflow**)

Job upstream repolari tarar, `marketplace.json`'i yeniden uretir ve degisiklik varsa commit atar.
Degisiklik yoksa commit atmaz.

## Yapi

```
.claude-plugin/marketplace.json           # uretilen katalog, elle duzenlenmez
sources.json                              # elle duzenlenen tek dosya
scripts/build_marketplace.py              # katalog + ekip sablonu ureteci
.github/workflows/                        # gunluk senkronizasyon
plugins/
  serena/                     # MCP sarmalayici (.mcp.json)
  context7/                   # MCP sarmalayici (.mcp.json)
  engineering-standards/      # vendor-neutral skill seti (opsiyonel)
  vatan-skills/               # kurumsal skill seti (opsiyonel)
  marketplace-setup/
    commands/                 # /marketplace-setup, -doctor, -refresh
    team-settings.json        # uretilen ekip sablonu, elle duzenlenmez
```