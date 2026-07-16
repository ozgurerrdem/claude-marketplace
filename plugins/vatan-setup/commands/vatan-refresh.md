---
description: Proje buyudukce Serena ve context-mode indekslerini yeniden tazeler. Hicbir yeni arac kurmaz.
---

Bu proje icin Serena ve context-mode indekslerini tazele. Kurulum yapma, sadece mevcut
indeksleri guncelle. Sonunda kisa bir ozet ver.

## 1. Serena — yeniden indeksle

Proje kokunde `.serena/project.yml` var mi kontrol et.

- **Varsa**: mevcut projeyi yeniden indeksle:
```
  uvx --native-tls --from git+https://github.com/oraios/serena serena project index
```
- **Yoksa**: proje hic kurulmamis demektir, kullaniciya `/vatan-setup` calistirmasini soyle ve dur.

Serena LSP tabanli oldugu icin gunluk kucuk degisiklikleri zaten canli takip eder; bu adim
esas olarak buyuk toplu degisiklik (branch degisimi, rebase, yeni modul) sonrasi icindir.

## 2. Context-mode — yeniden indeksle

`ctx_index` context-mode'un otomatik tazelenen bir yapisi yoktur; her cagri bir anlik goruntudur.

Ayni uzanti ve haric tutma listesiyle yeniden indeksle:

- Dahil et: `.cs`, `.cshtml`, `.csproj`, `.json`, `.sql`, `.md`, `.js`, `.ts`, `.tsx`, `.css`
- Haric tut: `bin`, `obj`, `node_modules`, `Logs`, `.git`, `.serena`

Ardindan `ctx_search` ile yakin zamanda eklenen bir dosya/sinif adini arayarak yeni indeksin
isabet edip etmedigini dogrula.

## 3. Ozet

```
| Bilesen | Durum | Not |
|---|---|---|
| serena | | yeniden indekslendi mi, kac dosya |
| context-mode | | yeniden indekslendi mi, kac dosya |
```

Ne zaman tekrar `/vatan-refresh` calistirilmasi gerektigini kisaca hatirlat: yeni modul/dosya
eklendiginde, buyuk merge/rebase sonrasi, ya da `ctx_search` alakasiz sonuc donmeye basladiginda.