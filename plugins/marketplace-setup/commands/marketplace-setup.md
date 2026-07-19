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

Ayrica plugin kurulum durumunu kontrol et: `claude plugin list` ciktisinda asagida (Adim 3'te)
listelenen pluginlerin hepsi var mi?

Karar:
- **Ucu de varsa** (araclar + hook + tum pluginler kurulu) → global kurulum mevcut. Adim 1, 2
  ve 3'u **atla**, dogrudan Adim 4'ten (Serena indeksleme) basla. Kullaniciya "Global kurulum
  zaten yapilmis, sadece bu projenin indekslemesini yapiyorum" de.
- **Araclar/hook tamam ama plugin eksikse** → Adim 1 ve 2'yi atla, Adim 3'ten devam et.
- **Hicbiri yoksa** → Adim 1'den tam kurulum yap.

Not: Adim 1-3 makine geneli, bir kez yapilir. Adim 4-5 (indeksleme) **her yeni proje icin**
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

## 3. Marketplace kaydi ve plugin dagitimi (proje basina, git'e commitlenir)

Bu repo'yu klonlamis/gormus olmak pluginleri **calisir hale getirmez** — `context-mode` gibi
GitHub kaynakli pluginlerin (`sources.json`'da `"kind": "plugin"`) MCP sunucusu ancak Claude
Code'un kendi kayit dosyasina (`installed_plugins.json`) yazilirsa baslar. Bu dosya bossa
(`{"plugins": {}}`) MCP tool'lari (`ctx_search`, `ctx_execute`, `ctx_stats`, `ctx_index`) hic
gorunmez — bilgisayari yeniden baslatmak bunu cozmez, kurulum eksiktir.

`claude plugin marketplace add` + tek tek `claude plugin install` calistirmak **sadece o an
calistiran kisinin makinesini** kurar; ekipteki digerlerine hicbir sekilde tasinmaz. Bu proje
bir sirket ici marketplace oldugu icin dogru yontem, kurulumu **proje kokundeki
`.claude/settings.json` dosyasina yazip git'e commitlemek**tir — Claude Code, bir gelistirici
projeyi trust ettiginde bu dosyadaki marketplace ve pluginleri otomatik olarak kurmasini
**onerir** (resmi davranis budur; sessiz/onaysiz kurulum yoktur, tek seferlik bir onay
istenir).

Bu komutu calistiran plugin'in kendi klasorunde (`${CLAUDE_PLUGIN_ROOT}`, yoksa bu komut
dosyasinin bulundugu yerin bir ust klasoru olan `marketplace-setup/`) hazir bir sablon var:
`team-settings.json`. Bu dosya `scripts/build_marketplace.py` tarafindan `sources.json`'dan
otomatik uretilir; yeni bir plugin eklendiginde elle guncellemene gerek yok, marketplace
GitHub Actions ile kendini tazeledikce bu dosya da tazelenir.

Proje kokunde `.claude/settings.json` var mi kontrol et (yoksa olustur). `team-settings.json`
icindeki `extraKnownMarketplaces` ve `enabledPlugins` anahtarlarini oku ve proje
`.claude/settings.json`'daki **mevcut anahtarlari koruyarak** (kor kopyalama/ustune yazma
yapma, JSON'u birlestir) ekle:

```json
{
  "extraKnownMarketplaces": {
    "workbench": {
      "source": { "source": "github", "repo": "ozgurerrdem/claude-marketplace" }
    }
  },
  "enabledPlugins": {
    "andrej-karpathy-skills@workbench": true,
    "context-mode@workbench": true,
    "serena@workbench": true,
    "context7@workbench": true,
    "marketplace-setup@workbench": true
  }
}
```

**Standart seti secimi (zorunlu adim).** Yukaridaki sablon bilerek hicbir standart seti
acmaz — `vatan-skills` ve `engineering-standards` birbirinin alternatifidir ve ortama gore
secilir. Kullaniciya sor:

- Kurumsal Vatan ortami          -> `"vatan-skills@workbench": true` ekle
- Kisisel / vendor-neutral ortam -> `"engineering-standards@workbench": true` ekle

Ikisini birden acma; ayni konularda cakisan skill'ler uretirler. Kullanici secim yapmazsa
`engineering-standards`'i varsayilan al ve bunu tek satirla bildir.

Bu dosyayi degistirdikten sonra:
- `.gitignore`'a bak, `.claude/settings.json` (`.claude/settings.local.json` degil) yanlislikla
  disarida birakilmis mi kontrol et; birakilmissa cikar. Bu dosya **bilerek** repo'ya
  commitlenmeli ki ekipteki herkes ayni marketplace/plugin setini alsin.
- Kullaniciya bildir: "Bu dosyayi commitleyip push ettiginde, projeyi trust eden her
  gelistiriciye Claude Code bu marketplace ve pluginleri kurmasi icin bir onay istemi
  gosterecek."

Mevcut oturumda hemen test etmek istersen (opsiyonel, sadece bu makine icin anlik dogrulama):

```
claude plugin marketplace list
claude plugin list
```

`workbench` yoksa `claude plugin marketplace add ozgurerrdem/claude-marketplace`,
ardindan `claude plugin list`'te gorunmeyen her plugin icin (kuracagini tek satirla soyleyip
onay alarak) `claude plugin install <ad>@workbench` calistirabilirsin — ama bu sadece
senin makineni kurar, ekip icin gecerli kalici cozum yukaridaki `.claude/settings.json`'dur.

MCP sunuculari **sadece yeni bir oturumda** yuklenir. Bu adimda hicbir plugin kurulmadiysa
devam et; en az bir plugin kurulduysa kullaniciya bildir: "Plugin kurulumu tamamlandi,
degisikliklerin etkili olmasi icin Claude Code oturumunu (Desktop kullaniyorsan tepsi
ikonundan tamamen kapatip) yeniden baslatman gerekiyor." ve Adim 4-6'yi bir sonraki oturuma
birak.

## 4. Serena indeksleme (her proje icin)

Kurumsal ag arkasinda `uvx` TLS sertifika hatasi verir; ayrica `serena project index` interaktif
dil sorusu sorar ve non-interactive modda EOF ile patlar. Ikisini de tek komut cozer.

Proje kokunde `.sln` dosyasi ara. Varsa:

```
uvx --native-tls --from git+https://github.com/oraios/serena serena project create --language csharp --index .
```

React/TypeScript projesi ise `--language typescript` kullan.

`.sln` yoksa C# dil sunucusu calismaz; kullaniciya bildir ve gec.

Uretilen `.serena/` klasorunu proje kokundeki `.gitignore` dosyasina ekle (yoksa olustur).

## 5. Context-mode indeksleme (her proje icin)

**Varsayilan uzanti listesi `.cs` ve `.cshtml` icermez** — belirtmezsen C# projesinde neredeyse
hicbir sey indekslenmez.

`ctx_index` cagirirken uzantilari acikca ver: `.cs`, `.cshtml`, `.csproj`, `.json`, `.sql`, `.md`,
`.js`, `.ts`, `.tsx`, `.css`.

Haric tut: `bin`, `obj`, `node_modules`, `Logs`, `.git`, `.serena`.

Ardindan `ctx_search` ile bir dogrulama aramasi yap ve isabet edip etmedigini raporla.

## 6. Dogrulama

MCP tool listesini kontrol et:

- **serena**: `find_symbol`, `find_referencing_symbols`, `activate_project`
- **context7**: `resolve-library-id`, `query-docs`
- **context-mode**: `ctx_index`, `ctx_search`, `ctx_execute`, `ctx_stats`

Serena tool'lari gorunmuyorsa sebebi genellikle TLS'tir; serena pluginin `.mcp.json` dosyasinda
`UV_NATIVE_TLS=1` ortam degiskeni var mi kontrol et.

Skill'leri de dogrula — hangi standart setinin secildigine gore:

- `vatan-skills` secildiyse: `vatan-dotnet-core`, `vatan-sql`, `vatan-postgres`,
  `vatan-react-js`, `vatan-legacy-dotnet`, `vatan-rtk`
- `engineering-standards` secildiyse: `dotnet-core`, `mssql`, `postgresql`, `react`,
  `legacy-dotnet`

Secilmeyen setin skill'lerini arama; yoklugu hata degildir.

## 7. Rapor

```
| Bilesen | Durum | Not |
|---|---|---|
| git / node / uv / rtk / rg | | surum |
| RTK hook | | kullanici calistirdi mi, hook check sonucu |
| marketplace + pluginler | | workbench kayitli mi, hangi pluginler kuruldu |
| serena | | tool gorunuyor mu, indeks alindi mi |
| context7 | | tool gorunuyor mu |
| context-mode | | kac dosya indekslendi |
| standart seti | | hangisi secildi (vatan-skills / engineering-standards), kac skill yuklu |
```

Sonunda kullaniciya net, tek cumlelik bir sonraki adim ver. Kalan manuel is genellikle sudur:
terminalde `rtk init -g` calistirip `y` demek ve Claude Desktop'i tepsi ikonundan yeniden baslatmak.
