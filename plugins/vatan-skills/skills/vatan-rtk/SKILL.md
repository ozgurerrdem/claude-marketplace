---
name: vatan-rtk
description: >
  Kabuk (shell/Bash) komutu calistirilacak her durumda kullanilir. git komutlari (status, log,
  diff, add, commit, push), dotnet komutlari (build, test, format, restore), dosya okuma (cat,
  head, tail), arama (grep, rg, find), dizin listeleme (ls, tree), paket yoneticileri (npm,
  cargo, pip) ve test kosumu icin gecerlidir. Bu komutlarin ciktisi context penceresini gereksiz
  sisirir; rtk araci ciktilari %60-90 oraninda sikistirir. Kabuk komutu calistirmadan once bu
  skill'e bak.
---

# RTK ile Komut Calistirma

`rtk` kurulu bir ortamda kabuk komutlari **daima rtk uzerinden** calistirilir. Ham komut ciktisi
(ozellikle derleme, test, git log, arama sonuclari) context penceresini gereksiz doldurur.

## Kullanim tablosu

Olculmus kazanc oldugu icin **daima** rtk uzerinden calistir:

| Ham komut | rtk karsiligi | Olculen tasarruf |
|---|---|---|
| `dotnet build` | `rtk dotnet build` | ~%90 |
| `dotnet test` | `rtk dotnet test` | ~%90 (test varsa) |
| `dotnet format` | `rtk dotnet format` | yuksek |
| `npm test`, `npm run build` | `rtk npm ...` | yuksek |
| `git status` / `git log` / `git diff` | `rtk git ...` | ~%25 |
| `cat`, `head`, `tail` | `rtk read <dosya>` | ~%70 |
| `ls`, `tree` | `rtk ls` | ~%80 |

Kazanc saglamayan, **ham kullan**:

| Komut | Sebep |
|---|---|
| `rg` / arama | Cikti zaten kompakt, rtk katkisi ~%0 |
| `git add`, `git commit`, `git push` | Cikti zaten kisa |
| Interaktif komutlar (`dotnet watch`, `npm start`) | rtk ile sarilmaz |

Windows notu: `rtk grep` calismaz (`grep` binary'si yoktur). Arama gerekiyorsa ham `rg` kullan.

## Dahili araclar

Dosya okuma ve arama icin dahili `Read` / `Grep` / `Glob` araclari yerine `rtk read`, `rtk grep`,
`rtk find` tercih edilir. Dahili araclar filtreden gecmez ve ham icerik context'e dolar.

Istisna: tek bir kucuk dosyayi (50 satirin altinda) tam olarak okumak gerekiyorsa dahili `Read`
kullanmak sorun degil.

## rtk kurulu degilse

`rtk --version` hata veriyorsa ham komutlara devam et, kurulum icin kullaniciyi zorlama; sadece
bir kez "rtk kurulu degil, ham komut kullaniliyor" diye bildir.

## Olcum

Oturum sonunda tasarrufu gormek icin:

```
rtk gain
```

## Kural

- Buyuk cikti uretmesi beklenen hicbir komut ham calistirilmaz.
- rtk desteklemeyen bir komut varsa (`rtk <komut>` hata verirse) ham komuta don, israr etme.
- Interaktif komutlar (`dotnet watch`, `npm start`) rtk ile sarilmaz.
