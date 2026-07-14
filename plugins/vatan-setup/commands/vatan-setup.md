---
description: Marketplace pluginlerinin tum on kosullarini kurar, RTK hook'unu etkinlestirir, projeyi indeksler ve dogrular.
---

Bu proje icin Vatan marketplace pluginlerini uctan uca calisir hale getir.

Kurallar:
- Her adimda once **kontrol et**, kurulu olani tekrar kurma.
- Bir sey kurmadan once kullaniciya ne kuracagini tek satirda soyle ve onay al.
- Bir adim basarisiz olursa dur, hatayi yaz, sonraki adima gec. Sessizce atlamayin.
- Isletim sistemini tespit et (Windows / macOS / Linux) ve dogru paket yoneticisini kullan.
- Sonunda tek bir tablo halinde rapor ver.

## 1. On kosul kontrolu

Su komutlari calistir ve varlik/surum bilgisini topla:

```
git --version
node --version
dotnet --version
uv --version
rtk --version
```

Eksik olanlar icin kurulum:

| Arac | Windows | macOS | Ne icin |
|---|---|---|---|
| git | `winget install Git.Git` | `brew install git` | Code sekmesi oturum izolasyonu icin zorunlu |
| node | `winget install OpenJS.NodeJS.LTS` | `brew install node` | context7 ve context-mode MCP sunuculari |
| uv | `winget install astral-sh.uv` | `brew install uv` | serena MCP sunucusu |
| rtk | `winget install rtk` (olmazsa `cargo install rtk`) | `brew install rtk` | kabuk ciktisi sikistirma |

`dotnet` yoksa kurma; kullaniciya bildir (proje bagimliligi, ortam bagimliligi degil).

## 2. RTK auto-rewrite hook

`rtk` kuruluysa hook'u global olarak etkinlestir:

```
rtk init -g
```

Sonra hook'un yerine oturdugunu dogrula:

```
rtk hook check
```

Hook `PreToolUse` / matcher `Bash` altina `rtk hook claude` komutunu yaziyor. Etkinlestikten
sonra `git status`, `git log`, `dotnet build`, `dotnet test` gibi komutlarin ciktisi otomatik
olarak sikistirilir.

Hook yalnizca **Bash** cagrilarinda calisir. Dahili `Read`, `Grep`, `Glob` araclari hook'tan
gecmez. Bu yuzden proje kokunde `CLAUDE.md` varsa (yoksa olustur) su bolumun bulundugundan
emin ol:

```markdown
## Komut kullanimi
Dosya okuma ve arama icin dahili Read/Grep/Glob yerine kabuk komutlarini kullan
(`cat`, `head`, `rg`, `find`). Boylece cikti RTK filtresinden gecer ve context sismez.
```

Kurulum sonrasi Claude Desktop'in **yeniden baslatilmasi gerektigini** kullaniciya hatirlat;
hook yeni oturumda devreye girer.

## 3. Serena indeksleme

`uv` kuruluysa ve proje kokunde bir `.sln` dosyasi varsa (C# icin zorunlu), projeyi indeksle:

```
uvx --from git+https://github.com/oraios/serena serena project index
```

`.sln` yoksa C# dil sunucusu calismaz; kullaniciya bildir.

Uretilen `.serena/` klasorunu `.gitignore`'a ekle (yoksa olustur).

## 4. Context-mode indeksleme

`ctx_index` ile projenin kaynak klasorunu indeksle. `bin`, `obj`, `node_modules`, `Logs`,
`.git` klasorlerini **haric tut** — aksi halde bilgi tabani log ve derleme ciktisiyla dolar
ve aramalar isabetsizlesir.

Ardindan `ctx_search` ile bir dogrulama aramasi yap ve isabet edip etmedigini raporla.

## 5. Dogrulama

Elindeki MCP tool listesini kontrol et ve su sunucularin araclarinin gorunur oldugunu teyit et:

- **serena**: `find_symbol`, `find_referencing_symbols`, `activate_project`
- **context7**: `resolve-library-id`, `query-docs`
- **context-mode**: `ctx_index`, `ctx_search`, `ctx_execute`, `ctx_stats`

Gorunmeyen varsa sebebini arastir (bagimlilik eksik mi, sunucu ayaga kalkmiyor mu) ve raporla.

Skill tarafini da dogrula: `vatan-dotnet-core`, `vatan-sql`, `vatan-postgres`,
`vatan-react-js`, `vatan-legacy-dotnet` ve `karpathy-guidelines` yuklu mu?

## 6. Rapor

```
| Bilesen | Durum | Not |
|---|---|---|
| git / node / uv / rtk | | surum |
| RTK hook | | etkin mi |
| serena | | tool gorunuyor mu, indeks alindi mi |
| context7 | | tool gorunuyor mu |
| context-mode | | indeks alindi mi |
| vatan-skills | | kac skill yuklu |
```

Sonunda kullaniciya tek cumleyle ne yapmasi gerektigini soyle (orn. "Claude Desktop'i yeniden
baslat, hook yeni oturumda devreye girecek").
