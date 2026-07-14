---
description: Marketplace pluginlerinin tum on kosullarini kurar, projeyi indeksler ve dogrular.
---

Bu proje icin Vatan marketplace pluginlerini uctan uca calisir hale getir.

Kurallar:
- Her adimda once **kontrol et**, kurulu olani tekrar kurma.
- Bir sey kurmadan once kullaniciya ne kuracagini tek satirda soyle ve onay al.
- Bir adim basarisiz olursa dur, hatayi yaz, sonraki adima gec.
- Isletim sistemini tespit et ve dogru paket yoneticisini kullan.
- Sonunda tek bir tablo halinde rapor ver.

## Calisma modu

Once `~/.claude/settings.json` icinde RTK hook'u var mi ve `rtk --version` calisiyor mu kontrol et.

- **Ikisi de varsa** → global kurulum daha once yapilmis. Adim 1 ve 2'yi **atla**, dogrudan
  Adim 3'ten (Serena indeksleme) basla ve "global kurulum zaten mevcut, sadece proje indekslemesi
  yapiliyor" diye bildir.
- **Yoksa** → tam kurulum yap (Adim 1'den basla).

## 1. On kosul kontrolu

```
git --version
node --version
dotnet --version
uv --version
rtk --version
rg --version
```

Eksik olanlari kur:

| Arac | Windows | macOS | Ne icin |
|---|---|---|---|
| git | `winget install Git.Git` | `brew install git` | Code sekmesi oturum izolasyonu |
| node | `winget install OpenJS.NodeJS.LTS` | `brew install node` | context7, context-mode MCP |
| uv | `winget install astral-sh.uv` | `brew install uv` | serena MCP |
| rtk | `winget install rtk` | `brew install rtk` | komut ciktisi sikistirma |
| ripgrep | `winget install BurntSushi.ripgrep.MSVC` | `brew install ripgrep` | `rtk rg` icin zorunlu |

`dotnet` yoksa kurma, sadece bildir.

## 2. RTK hook — KULLANICIYA YAPTIR

`rtk init -g` **interaktif onay** ister (`Patch existing settings.json? [y/N]`). Agent olarak
calistirirsan onay soruna cevap veremezsin ve komut sessizce "N" varsayip hook'u kurmaz.

Bu yuzden **kendin calistirma**. Kullaniciya soyle:

> RTK hook'unu kurmak icin terminalde su komutu calistir ve cikan sorulara `y` cevabi ver:
> ```
> rtk init -g
> ```
> Ardindan Claude Desktop'i tepsi ikonundan tamamen kapatip yeniden ac.

Kullanici calistirdigini soyledikten sonra dogrula:

```
rtk hook check "git status"
```

Cikti `rtk git status` gosteriyorsa hook calisiyor.

## 3. Serena — TLS ve dil sorusu tuzaklari

Kurumsal ag arkasinda `uvx` TLS sertifika hatasi verir; ayrica `serena project index`
interaktif dil sorusu sorar ve non-interactive modda EOF ile patlar. Ikisini de asagidaki
tek komut cozer.

Proje kokunde `.sln` dosyasi ara. Varsa:

```
uvx --native-tls --from git+https://github.com/oraios/serena serena project create --language csharp --index .
```

React/TypeScript projesi ise `--language typescript` kullan.

`.sln` yoksa C# dil sunucusu calismaz, kullaniciya bildir ve gec.

Uretilen `.serena/` klasorunu `.gitignore`'a ekle.

## 4. Context-mode indeksleme

**Varsayilan uzanti listesi `.cs` ve `.cshtml` icermez** — bunu belirtmezsen C# projesinde
neredeyse hicbir sey indekslenmez.

`ctx_index` cagirirken uzantilari acikca ver: `.cs`, `.cshtml`, `.csproj`, `.json`, `.sql`,
`.md`, `.js`, `.ts`, `.tsx`, `.css`.

Haric tut: `bin`, `obj`, `node_modules`, `Logs`, `.git`, `.serena`.

Ardindan `ctx_search` ile bir dogrulama aramasi yap ve isabet edip etmedigini raporla.

## 5. Dogrulama

MCP tool listesini kontrol et:

- **serena**: `find_symbol`, `find_referencing_symbols`, `activate_project`
- **context7**: `resolve-library-id`, `query-docs`
- **context-mode**: `ctx_index`, `ctx_search`, `ctx_execute`, `ctx_stats`

Serena tool'lari gorunmuyorsa sebebi TLS'tir; `.mcp.json`'da `UV_NATIVE_TLS=1` var mi kontrol et.

Skill'leri de dogrula: `vatan-dotnet-core`, `vatan-sql`, `vatan-postgres`, `vatan-react-js`,
`vatan-legacy-dotnet`, `vatan-rtk`.

## 6. Rapor

```
| Bilesen | Durum | Not |
|---|---|---|
| git / node / uv / rtk / rg | | surum |
| RTK hook | | kullanici calistirdi mi, hook check sonucu |
| serena | | tool gorunuyor mu, indeks alindi mi |
| context7 | | tool gorunuyor mu |
| context-mode | | kac dosya indekslendi |
| vatan-skills | | kac skill yuklu |
```

Sonunda kullaniciya net tek cumle: neyi yapmasi gerekiyor (genelde: terminalde `rtk init -g`
calistir ve Desktop'i yeniden baslat).