---
description: Kurulu pluginlerin gercekten calisip calismadigini test eder, hicbir sey kurmaz.
---

Kurulu marketplace pluginlerini test et. **Hicbir sey kurma, hicbir dosya degistirme.**
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

### 6a. Once hangi standart seti yuklu, onu tespit et

`vatan-skills` ve `engineering-standards` birbirinin alternatifidir; ortama gore biri kurulur.
Ikisinin SP hata konvansiyonu FARKLIDIR, dolayisiyla checklist de farklidir.

Yuklu skill listesine bak ve asagidakilerden hangisinin gecerli oldugunu belirle:

- `vatan-skills` yuklu     -> 6b + 6c uygula
- `engineering-standards`  -> 6b + 6d uygula
- ikisi de yuklu           -> `vatan-skills` onceliklidir; 6b + 6c uygula
- hicbiri yuklu degil      -> 6. adimi ATLA. "Standart seti yuklu degil, davranis testi
  uygulanmadi" diye tek satir yaz; bunu hata olarak raporlama.

Hangi setin secildigini raporda acikca belirt.

### 6b. Ortak gorev ve kontroller

Su gorevi yerine getir:

> "Barkoda gore urun fiyati guncelleyen bir servis metodu ve cagirdigi stored procedure'u yaz.
> Yetkisiz kullanici ve bulunamayan urun durumlarini ele al."

Her iki set icin de gecerli kontroller:

| Kontrol | Beklenen |
|---|---|
| Dapper + `CommandType.StoredProcedure` + `CancellationToken` | Evet |
| Uygulama kodunda inline SQL stringi | Hayir |
| EF Core onerilmis mi (proje zaten EF Core kullanmiyorsa) | Hayir |
| Log mesajlari Turkce ve parametreli mi | Evet |
| Kod satirlarina yorum eklenmis mi | Hayir |
| `SET NOCOUNT ON` ilk satirda mi | Evet |
| Dogrulamalar basta mi, derin ic ice `IF` piramidi yok mu | Evet |

### 6c. Sadece `vatan-skills` yukluyse

| Kontrol | Beklenen |
|---|---|
| SP `@Sorun BIT` / `@Mesaj VARCHAR(250)` ile basliyor mu | Evet |
| Dogrulamalar `IF @Sorun = 0 AND ...` zinciri mi | Evet |
| THROW / RAISERROR kullanilmis mi | Hayir |
| Her kod yolunda tek sonuc kumesi (Sorun, Mesaj) donuyor mu | Evet |

### 6d. Sadece `engineering-standards` yukluyse

Bu set kurumsal `@Sorun`/`@Mesaj` duzenini ICERMEZ; varsayilani exception-based'dir.
`@Sorun`/`@Mesaj` beklemek burada YANLIS pozitif uretir.

| Kontrol | Beklenen |
|---|---|
| Is kurallari icin `THROW` (veya eski surumde `RAISERROR`) kullanilmis mi | Evet |
| Transaction varsa `SET XACT_ABORT ON` eklenmis mi | Evet |
| `CATCH` icinde rollback + bare `THROW;` ile yeniden firlatma var mi | Evet |
| Yetki kontrolu ayri bir fonksiyona (`dbo.CanUpsertX`) cikarilmis mi | Evet |
| `CATCH` icinde hata yutulup basari donuluyor mu | Hayir |

### 6e. Raporlama

Hangi skill'in tetiklendigini acikca belirt. Skill yuklu olup tetiklenmediyse bunu raporla —
en sik gorulen sessiz hatadir.

Skill kendi konvansiyonuna uygun cikti verdiyse BASARILI say. Baska bir setin kuralina
uymadigi icin basarisiz isaretleme.

## Rapor

```
| Plugin | Yuklu mu | Calisti mi | Not |
```
