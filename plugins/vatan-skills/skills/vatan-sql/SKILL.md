---
name: vatan-sql
description: >
  Vatan projelerinde MSSQL (SQL Server) tarafinda calisirken kullanilir. Stored procedure
  ve fonksiyon yazma, T-SQL sorgu optimizasyonu, indeks, transaction, kilit/deadlock,
  toplu veri isleme ve Dapper ile SQL Server cagrisi yapma konularini kapsar. .NET
  tarafinda Dapper ile SP cagirma, connection yonetimi ve parametre gecisi de buradadir.
---

# Vatan MSSQL Standartlari

## Altin kural

**Uygulama kodunda SQL stringi bulunmaz.** Sorgu mantigi stored procedure veya fonksiyonda
yasar. .NET tarafi sadece SP adini ve parametreleri bilir.

Bunun anlami: yeni bir veri erisimi gerekiyorsa once SP/fonksiyon yazilir, sonra Dapper ile
cagrilir. Inline `SELECT ...` yazma; `.sql` dosyasina gomup okuma da yapma.

Projede halihazirda EF Core gibi bir ORM varsa onun kalibina uy; ama yeni is icin varsayilan
daima SP/fonksiyondur.

## Dapper ile cagirma

```csharp
public async Task<UrunDto?> GetirAsync(string barkod, CancellationToken cancellationToken)
{
    var parametreler = new DynamicParameters();
    parametreler.Add("@Barkod", barkod, DbType.String, size: 20);

    var komut = new CommandDefinition(
        "dbo.UrunGetirSX",
        parametreler,
        commandType: CommandType.StoredProcedure,
        commandTimeout: _options.KomutZamanAsimiSaniye,
        cancellationToken: cancellationToken);

    await using var connection = _connectionFactory.Olustur();
    return await connection.QuerySingleOrDefaultAsync<UrunDto>(komut);
}
```

- `CommandType.StoredProcedure` daima acikca verilir.
- Parametreler `DynamicParameters` ile tipli ve boyutlu gecilir (implicit conversion indeks
  kullanimini bozar).
- `CancellationToken` `CommandDefinition` uzerinden aktarilir; aksi halde iptal DB'ye inmez.
- Cikti parametresi / donus degeri gerekiyorsa `ParameterDirection.Output` ile alinir.

## Connection yonetimi

Dogru secim proje profiline gore degisir:

- **Yuksek trafikli servis** (saniyede yuzlerce istek, istek basina 1-2 sorgu): sorgu basina
  kisa omurlu connection. Ac, calistir, hemen birak. Uzun yasayan connection tutmak pool
  tukenmesine (pool exhaustion) yol acar.
- **Islem basina birden fazla yazma iceren, transaction butunlugu gereken akis**: Unit of Work
  / scoped connection uygun olabilir.

Belirsizse gelistiriciye sor: "Bu servis istek basina kac DB cagrisi yapiyor, transaction
butunlugu gerekiyor mu?"

Her durumda:
- Connection factory arayuz arkasinda (`ISqlConnectionFactory`), connection string options'tan gelir.
- `await using` ile kapatilir; connection pooling'e guvenilir, manuel havuz yazilmaz.
- Ayni connection uzerinde es zamanli (paralel) sorgu calistirilmaz.

## Stored procedure yazim kurallari

Hata yonetimi **bayrak tabanlidir**: SP exception firlatmaz, `@Sorun` / `@Mesaj` ile durum doner.
Cagiran taraf sonuc kumesindeki `Sorun` degerine bakar.

```sql
CREATE OR ALTER PROCEDURE dbo.UrunFiyatGuncelleIUX
    @Barkod     VARCHAR(20),
    @Fiyat      DECIMAL(18,2),
    @U_ID       INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @Sorun BIT = 0, @Mesaj VARCHAR(250) = '';

    IF @Sorun = 0 AND (@Barkod IS NULL OR LEN(@Barkod) = 0)
    BEGIN
        SET @Sorun = 1;
        SET @Mesaj = 'Barkod bos olamaz.';
    END

    IF @Sorun = 0 AND dbo.CanUpsertUrun(@U_ID) = 0
    BEGIN
        SET @Sorun = 1;
        SET @Mesaj = 'Bu islem icin yetkiniz bulunmamaktadir.';
    END

    IF @Sorun = 0 AND NOT EXISTS (SELECT 1 FROM dbo.Urun WHERE Barkod = @Barkod)
    BEGIN
        SET @Sorun = 1;
        SET @Mesaj = 'Urun bulunamadi.';
    END

    IF @Sorun = 1
    BEGIN
        SELECT @Sorun AS Sorun, @Mesaj AS Mesaj;
        RETURN;
    END

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.Urun
        SET Fiyat = @Fiyat,
            GuncellemeTarihi = SYSUTCDATETIME(),
            GuncelleyenKullanici = @U_ID
        WHERE Barkod = @Barkod;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @Sorun = 1;
        SET @Mesaj = 'Fiyat guncelleme sirasinda beklenmeyen bir hata olustu.';
    END CATCH

    SELECT @Sorun AS Sorun, @Mesaj AS Mesaj;
END
```

Kurallar:

- `SET NOCOUNT ON` her SP'nin ilk satiri. Transaction iceren SP'lerde ayrica `SET XACT_ABORT ON`.
- SP basinda `DECLARE @Sorun BIT = 0, @Mesaj VARCHAR(250) = '';` tanimlanir. Uretilen bir kimlik
  varsa (`@NewId INT = 0` gibi) o da burada tanimlanip sonuc kumesinde geri doner.
- **Dogrulamalar zincirleme yazilir**: her kontrol `IF @Sorun = 0 AND ...` ile baslar. Boylece ilk
  hata bulunduktan sonraki kontroller degerlendirilmez, ic ice `IF` yigini olusmaz.
- Yetki kontrolu de bir dogrulama adimidir; ayri fonksiyona (`dbo.CanUpsertX(@U_ID)`) cikarilir,
  SP icine gomulmez.
- Yazma islemine gecmeden once tek bir `IF @Sorun = 1` blogunda sonuc dondurulup `RETURN` edilir.
- Erken cikan ozel akislar (sadece etiketleme, sadece not ekleme gibi) kendi blogunda isini yapar,
  `SELECT 0 AS Sorun` ile basari dondurup `RETURN;` ile cikar.
- SP **daima tek bir sonuc kumesi** doner: en az `Sorun`, `Mesaj`. Basari durumunda da doner
  (`Sorun = 0`). Hicbir kod yolu sonuc dondurmeden bitmez.
- Mesajlar Turkce, kullaniciya gosterilebilir netlikte. Ic hata detayi (`ERROR_MESSAGE()`,
  tablo/kolon adi) kullaniciya donen `@Mesaj` icine konmaz; gerekiyorsa ayri bir log tablosuna yazilir.
- `CATCH` beklenmeyen hatalar icindir; is kurali ihlali `CATCH`'e dusurulerek yonetilmez.
- Transaction mumkun olan en kisa sure acik kalir. Icinde harici cagri (linked server, HTTP,
  uzun dongu) yapilmaz.
- SP tek bir isten sorumlu olur. "Her isi yapan" SP yazilmaz.
- Sema adi daima yazilir (`dbo.X`), plan cache paylasimi icin.

### .NET tarafinda okuma

```csharp
public sealed record SpSonucu(bool Sorun, string Mesaj);

public async Task<SpSonucu> FiyatGuncelleAsync(string barkod, decimal fiyat, int kullaniciId, CancellationToken cancellationToken)
{
    var parametreler = new DynamicParameters();
    parametreler.Add("@Barkod", barkod, DbType.String, size: 20);
    parametreler.Add("@Fiyat", fiyat, DbType.Decimal);
    parametreler.Add("@U_ID", kullaniciId, DbType.Int32);

    var komut = new CommandDefinition(
        "dbo.UrunFiyatGuncelleIUX",
        parametreler,
        commandType: CommandType.StoredProcedure,
        commandTimeout: _options.KomutZamanAsimiSaniye,
        cancellationToken: cancellationToken);

    await using var connection = _connectionFactory.Olustur();
    var sonuc = await connection.QuerySingleAsync<SpSonucu>(komut);

    if (sonuc.Sorun)
        _logger.LogWarning("Fiyat guncelleme reddedildi. Barkod: {Barkod}, Mesaj: {Mesaj}", barkod, sonuc.Mesaj);

    return sonuc;
}
```

- `Sorun = 1` bir **is hatasidir**, exception degildir; cagiran katman bunu kullaniciya donen
  anlamli bir yanita cevirir.
- `@Mesaj` icerigi degistirilmeden kullaniciya gosterilebilir; uzerine ek metin uydurma.
- SP birden fazla sonuc kumesi doniyorsa `QueryMultipleAsync` kullanilir; ilk kume daima
  `Sorun`/`Mesaj` olur.

## Sorgu performansi

- **Set-based dusun.** `CURSOR` ve `WHILE` dongusu son care; toplu `UPDATE ... FROM`,
  `MERGE`, tablo degiskeni ile cozulebiliyorsa oyle cozulur.
- **SARGable yaz.** `WHERE` icinde kolonu fonksiyona sokma:
  - Yanlis: `WHERE CONVERT(DATE, Tarih) = @Gun`
  - Dogru: `WHERE Tarih >= @Gun AND Tarih < DATEADD(DAY, 1, @Gun)`
- `SELECT *` yok; sadece gereken kolonlar.
- `NOLOCK` / `READ UNCOMMITTED` **varsayilan olarak kullanilmaz** — kirli okuma, atlanan ve
  cift okunan satir riski uretir. Gercekten tolere edilebilir bir raporlama senaryosuysa
  gelistiriciye acikca sor.
- Parametre sniffing suphesi varsa `OPTION (RECOMPILE)` veya lokal degiskene kopyalama
  degerlendirilir; korlemesine eklenmez.
- Buyuk sonuc kumesi sayfalanir: `OFFSET ... FETCH NEXT ... ROWS ONLY`.
- Toplu veri girisi icin Table-Valued Parameter kullanilir; satir satir SP cagirma yok.

```csharp
var tablo = new DataTable();
tablo.Columns.Add("Barkod", typeof(string));
tablo.Columns.Add("Fiyat", typeof(decimal));

parametreler.Add("@Urunler", tablo.AsTableValuedParameter("dbo.UrunFiyatTipi"));
```

## Indeks

- Yeni bir `WHERE`/`JOIN`/`ORDER BY` deseni geldiginde uygun indeks var mi kontrol edilir.
- Cok kolonlu indekste kolon sirasi: once esitlik (`=`), sonra aralik (`>`, `<`), sonra siralama.
- Gereken kolonlar `INCLUDE` ile eklenerek key lookup onlenir.
- Her sorguya indeks acilmaz; yazma maliyetini artirir. Indeks onerisi verirken beklenen
  fayda ve maliyeti tek cumleyle belirt.

## Kilit ve es zamanlilik

- Ayni satirlara dokunan islemler daima **ayni sirada** erisir (deadlock'un en yaygin sebebi
  ters sirali erisimdir).
- Yaris kosulu ihtimali olan "kontrol et - yoksa ekle" akislarinda tekil indeks + hata yakalama
  ya da uygun kilit ipucu kullanilir; iki ayri sorgu ile kontrol-sonra-yaz yapilmaz.
- Deadlock alan islem icin uygulama tarafinda sinirli sayida yeniden deneme dusunulur
  (hata no 1205); sonsuz dongu kurulmaz.

## Isimlendirme

Mevcut veritabaninda hangi konvansiyon varsa ona uyulur. Yeni nesnelerde:

- Tablo: tekil, `PascalCase` (`Urun`, `MagazaStok`).
- SP: `NesneIslemEki` (`UrunGetirSX`, `UrunFiyatGuncelleIUX`). Var olan sema ekleri
  (`SX`, `IUX` vb.) taklit edilir, yenisi uydurulmaz.
- Parametre: `@PascalCase`.
- Anahtar kelimeler BUYUK HARF, tanimlayicilar orijinal haliyle.

## Yasaklar

- Uygulama kodunda SQL stringi (parametreli olsa bile).
- String birlestirme ile SQL kurma (`EXEC('SELECT ... ' + @x)`) — injection. Dinamik SQL sart
  ise `sp_executesql` + parametre kullanilir, tanimlayicilar `QUOTENAME` ile sarilir.
- Alistirma amacli `SELECT *`, gereksiz `DISTINCT`, gereksiz `ORDER BY`.
- Transaction icinde uzun suren dis cagri.
- `CATCH` icinde hatayi yutup basari donmek.
- Uretim verisinde `DELETE`/`UPDATE` yazarken `WHERE` unutmak — script uretirken once
  `SELECT` ile etkilenecek satir sayisi gosterilir.
