---
description: Kurulu pluginlerin gercekten calisip calismadigini test eder, hicbir sey kurmaz.
---

Kurulu Vatan marketplace pluginlerini test et. **Hicbir sey kurma, hicbir dosya degistirme.**
Sorun bulursan cozmeye calisma, sadece raporla.

## 1. Envanter

- Yuklu skill'leri listele: isim + geldigi plugin.
- Elindeki MCP tool listesini yazdir.

## 2. Serena

Projeyi aktive et. Bir servis sinifini `find_symbol` ile bul, `find_referencing_symbols` ile
cagrildigi yerleri cikar. Ayni bilgiye dosya okuyarak ulassaydin kac dosya okuman gerekecegini
tahmin et.

## 3. Context7

`use context7` diyerek projede kullanilan bir kutuphanenin (orn. Npgsql, Dapper) guncel
dokumanini getir. Surum bilgisi donuyor mu, teyit et.

## 4. Context-mode

- `ctx_search` ile bir arama yap.
- `ctx_execute` ile `git log --oneline -30` calistir; ayni komutu ham kabukta da calistir.
  Iki ciktinin uzunlugunu karsilastir.
- `ctx_stats` ile oturum tasarrufunu yazdir.

## 5. RTK

```
rtk --version
rtk hook check
rtk gain
```

Hook etkinse `git status` calistir ve ciktinin sikistirilmis gelip gelmedigini yorumla.

## 6. Skill davranis testi (en onemli adim)

Su gorevi yerine getir:

> "Barkoda gore urun fiyati guncelleyen bir servis metodu ve cagirdigi stored procedure'u yaz.
> Yetkisiz kullanici ve bulunamayan urun durumlarini ele al."

Sonra ciktiyi kendi kurallarina gore denetle:

| Kontrol | Beklenen |
|---|---|
| SP `@Sorun BIT` / `@Mesaj VARCHAR(250)` ile basliyor mu | Evet |
| Dogrulamalar `IF @Sorun = 0 AND ...` zinciri mi | Evet |
| THROW / RAISERROR kullanilmis mi | Hayir |
| Her kod yolunda tek sonuc kumesi (Sorun, Mesaj) donuyor mu | Evet |
| Dapper + `CommandType.StoredProcedure` + `CancellationToken` | Evet |
| Uygulama kodunda inline SQL stringi | Hayir |
| EF Core onerilmis mi | Hayir |
| Log mesajlari Turkce ve parametreli mi | Evet |
| Kod satirlarina yorum eklenmis mi | Hayir |

Hangi skill'in tetiklendigini acikca belirt. Hicbiri tetiklenmediyse bunu raporla — skill
yuklu olup tetiklenmemesi en sik gorulen sessiz hatadir.

## Rapor

```
| Plugin | Yuklu mu | Calisti mi | Not |
```
