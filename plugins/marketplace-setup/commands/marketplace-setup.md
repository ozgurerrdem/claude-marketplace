---
description: Marketplace pluginlerinin tum on kosullarini kurar, projeyi indeksler ve dogrular.
---

Bu proje icin marketplace pluginlerini uctan uca calisir hale getir.

Kurallar:
- Her adimda once **kontrol et**, kurulu olani tekrar kurma.
- Bir sey kurmadan once kullaniciya ne kuracagini tek satirda soyle ve onay al.
- Bir adim basarisiz olursa dur, hatayi yaz, sonraki adima gec.
- Isletim sistemini tespit et ve dogru paket yoneticisini kullan.
- Sonunda tek bir tablo halinde rapor ver.
- Kullaniciya bir dosya yolu soyleyecegin zaman **daima tam, mutlak yolu** yaz; `~` gibi
  kisaltma kullanma. Once kullanici ana klasorunu tespit et:
  - Windows: PowerShell'de `$env:USERPROFILE` (ornek: `C:\Users\ozgurdagdeviren`)
  - macOS/Linux: `$HOME` (ornek: `/Users/ozgurdagdeviren`)
  Sonra yollari bu gercek deger ile birlestirerek goster
  (ornek: `C:\Users\ozgurdagdeviren\.claude\settings.json`).

## 0. Calisma modu tespiti

Once global kurulumun daha once yapilip yapilmadigini anla:

- `rtk --version` calisiyor mu?
- Kullanici ana klasorundeki `.claude\settings.json` dosyasinda RTK hook'u (`PreToolUse` altinda
  `rtk hook claude`) var mi?

Karar:
- **Ikisi de varsa** → global kurulum mevcut. Adim 1 ve 2'yi **atla**, dogrudan Adim 3'ten
  (Serena indeksleme) basla. Kullaniciya "Global kurulum zaten yapilmis, sadece bu projenin
  indekslemesini yapiyorum" de.
- **Eksik varsa** → Adim 1'den tam kurulum yap.

Not: Adim 1-2 makine geneli, bir kez yapilir. Adim 3-4 (indeksleme) **her yeni proje icin**
tekrar gereklidir; indeksler proje klasorune yazilir.

## 1. On kosul kontrolu (global, bir kez)

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

Kurulum sonrasi `winget` PATH'i mevcut terminale yansitmaz; kullaniciya "yeni araclar icin
terminali (ve gerekirse Claude Desktop'i) yeniden baslatman gerekebilir" diye hatirlat.

## 2. RTK hook — KULLANICIYA YAPTIR (global, bir kez)

`rtk init -g` **interaktif onay** ister (`Patch existing settings.json? [y/N]`). Agent olarak
calistirirsan onaya cevap veremezsin ve komut sessizce "N" varsayarak hook'u kurmaz.

Bu yuzden **kendin calistirma**. Kullaniciya aynen soyle (ana klasoru gercek deger ile yaz):

> RTK hook'unu kurmak icin **terminalde** su komutu calistir ve cikan tum sorulara `y` yaz:
> ```
> rtk init -g
> ```
> Bu komut hook'u su dosyaya ekler ve yedegini alir:
> `C:\Users\<SENIN-KULLANICI-ADIN>\.claude\settings.json`
> Bittiginde Claude Desktop'i **tepsi (saat yani) ikonundan tamamen kapat** ve yeniden ac —
> pencereyi kapatmak yetmez.

Kullanici "yaptim" dedikten sonra dogrula:

```
rtk hook check "git status"
```

Cikti `rtk git status` gosteriyorsa hook calisiyor. `No rewrite for:` gibi bos cikti gelirse
hook henuz aktif degildir; Desktop'in yeniden baslatilmasi gerektigini hatirlat.

## 3. Serena indeksleme (her proje icin)

Kurumsal ag arkasinda `uvx` TLS sertifika hatasi verir; ayrica `serena project index` interaktif
dil sorusu sorar ve non-interactive modda EOF ile patlar. Ikisini de tek komut cozer.

Proje kokunde `.sln` dosyasi ara. Varsa:

```
uvx --native-tls --from git+https://github.com/oraios/serena serena project create --language csharp --index .
```

React/TypeScript projesi ise `--language typescript` kullan.

`.sln` yoksa C# dil sunucusu calismaz; kullaniciya bildir ve gec.

Uretilen `.serena/` klasorunu proje kokundeki `.gitignore` dosyasina ekle (yoksa olustur).

## 4. Context-mode indeksleme (her proje icin)

**Varsayilan uzanti listesi `.cs` ve `.cshtml` icermez** — belirtmezsen C# projesinde neredeyse
hicbir sey indekslenmez.

`ctx_index` cagirirken uzantilari acikca ver: `.cs`, `.cshtml`, `.csproj`, `.json`, `.sql`, `.md`,
`.js`, `.ts`, `.tsx`, `.css`.

Haric tut: `bin`, `obj`, `node_modules`, `Logs`, `.git`, `.serena`.

Ardindan `ctx_search` ile bir dogrulama aramasi yap ve isabet edip etmedigini raporla.

## 5. Dogrulama

MCP tool listesini kontrol et:

- **serena**: `find_symbol`, `find_referencing_symbols`, `activate_project`
- **context7**: `resolve-library-id`, `query-docs`
- **context-mode**: `ctx_index`, `ctx_search`, `ctx_execute`, `ctx_stats`

Serena tool'lari gorunmuyorsa sebebi genellikle TLS'tir; serena pluginin `.mcp.json` dosyasinda
`UV_NATIVE_TLS=1` ortam degiskeni var mi kontrol et.

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

Sonunda kullaniciya net, tek cumlelik bir sonraki adim ver. Kalan manuel is genellikle sudur:
terminalde `rtk init -g` calistirip `y` demek ve Claude Desktop'i tepsi ikonundan yeniden baslatmak.
