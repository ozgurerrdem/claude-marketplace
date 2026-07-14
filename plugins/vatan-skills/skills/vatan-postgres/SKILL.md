---
name: vatan-postgres
description: >
  Vatan projelerinde PostgreSQL tarafinda calisirken kullanilir. PL/pgSQL fonksiyon ve
  prosedur yazma, sema tasarimi, upsert, indeks, es zamanlilik ve kilitleme, JSONB, sayfalama
  ve performans konularini kapsar. .NET tarafinda Npgsql + Dapper ile fonksiyon/prosedur
  cagirma, parametre tiplemesi, connection ve zaman asimi yonetimi de buradadir.
---

# Vatan PostgreSQL Standartlari

## Altin kural

**Uygulama kodunda SQL stringi bulunmaz.** Sorgu mantigi PL/pgSQL fonksiyonunda veya
prosedurunde yasar; .NET tarafi sadece adi ve parametreleri bilir.

Fonksiyon mu prosedur mu:
- **FUNCTION**: deger ya da sonuc kumesi donduren okuma islemleri ve transaction'i cagirandan
  devralan yazma islemleri.
- **PROCEDURE**: icinde `COMMIT`/`ROLLBACK` yonetmesi gereken, cok adimli yazma islemleri.

## Npgsql + Dapper ile cagirma

Okuma (sonuc kumesi donduren fonksiyon):

```csharp
public async Task<IReadOnlyList<UrunDto>> ListeleAsync(int magazaId, CancellationToken cancellationToken)
{
    var parametreler = new DynamicParameters();
    parametreler.Add("p_magaza_id", magazaId, DbType.Int32);

    var komut = new CommandDefinition(
        "SELECT * FROM ext.urun_listele(@p_magaza_id)",
        parametreler,
        commandTimeout: _options.KomutZamanAsimiSaniye,
        cancellationToken: cancellationToken);

    await using var connection = _connectionFactory.Olustur();
    var sonuc = await connection.QueryAsync<UrunDto>(komut);
    return sonuc.AsList();
}
```

Prosedur cagrisi:

```csharp
var komut = new CommandDefinition(
    "urun_fiyat_guncelle",
    parametreler,
    commandType: CommandType.StoredProcedure,
    cancellationToken: cancellationToken);

await connection.ExecuteAsync(komut);
```

- Npgsql'de `CommandType.StoredProcedure` `CALL` uretir; **sonuc kumesi donduren fonksiyonlar
  icin kullanilamaz** — onlar `SELECT * FROM fn(...)` ile cagrilir. Bu ayrimi karistirma.
- Parametre adlari fonksiyon imzasiyla birebir ayni olmali (`p_` oneki konvansiyonu korunur).
- Belirsiz tipli parametrelerde (`text` vs `varchar`, `jsonb`, dizi) tip acikca verilir;
  aksi halde `function ... does not exist` hatasi alinir. Buyuk metin kolonlarinda
  `varchar(n)` yerine `text` tercih edilir.
- `CancellationToken` daima `CommandDefinition` uzerinden gecirilir.
- Baglanti havuzu Npgsql tarafindadir; connection kisa omurlu acilip birakilir.

## Fonksiyon yazim kurallari

```sql
CREATE OR REPLACE FUNCTION ext.urun_fiyat_guncelle(
    p_barkod    text,
    p_fiyat     numeric(18,2),
    p_kullanici text
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_etkilenen integer;
BEGIN
    IF p_barkod IS NULL OR length(p_barkod) = 0 THEN
        RAISE EXCEPTION 'Barkod bos olamaz.' USING ERRCODE = 'P0001';
    END IF;

    UPDATE ext.urun
    SET fiyat = p_fiyat,
        guncelleme_tarihi = now(),
        guncelleyen_kullanici = p_kullanici
    WHERE barkod = p_barkod;

    GET DIAGNOSTICS v_etkilenen = ROW_COUNT;

    IF v_etkilenen = 0 THEN
        RAISE EXCEPTION 'Urun bulunamadi. Barkod: %', p_barkod USING ERRCODE = 'P0002';
    END IF;

    RETURN true;
END;
$$;
```

- `CREATE OR REPLACE` kullanilir; imza degisiyorsa once `DROP FUNCTION` gerektigini belirt
  (PostgreSQL asiri yukleme yapar, eski imza sessizce hayatta kalir — sik yapilan hata).
- Hata `RAISE EXCEPTION` ile, Turkce mesaj ve anlamli `ERRCODE` ile firlatilir.
- `SECURITY DEFINER` gerekmedikce kullanilmaz; kullanilirsa `SET search_path` sabitlenir.
- Volatilite dogru isaretlenir: salt okuma fonksiyonlari `STABLE`, hesaplama fonksiyonlari
  `IMMUTABLE`, yazanlar varsayilan `VOLATILE`.
- Fonksiyon tek isten sorumludur.

## Upsert

`INSERT ... ON CONFLICT` tercih edilir; "once SELECT sonra INSERT" yaris kosulu uretir.

```sql
INSERT INTO ext.urun (barkod, fiyat, guncelleme_tarihi)
VALUES (p_barkod, p_fiyat, now())
ON CONFLICT (barkod)
DO UPDATE SET
    fiyat = EXCLUDED.fiyat,
    guncelleme_tarihi = now()
WHERE ext.urun.fiyat IS DISTINCT FROM EXCLUDED.fiyat;
```

- `ON CONFLICT` icin hedef kolonlarda benzersiz kisit/indeks sart.
- Gereksiz yazmayi engellemek icin `IS DISTINCT FROM` ile degisiklik kontrolu eklenir.
- Toplu upsert tek `INSERT ... SELECT unnest(...)` ile yapilir; satir dongusu kurulmaz.

## Es zamanlilik ve kilit

- Ayni kaynaga es zamanli girmeyi engellemek icin **advisory lock**:

```sql
IF NOT pg_try_advisory_xact_lock(hashtext('urun_senkron')) THEN
    RAISE EXCEPTION 'Islem zaten calisiyor.' USING ERRCODE = '55P03';
END IF;
```

  `pg_try_advisory_xact_lock` transaction sonunda otomatik birakilir; `pg_advisory_lock`
  manuel birakma gerektirir ve unutulursa kilit sizdirir — varsayilan olarak xact surumunu kullan.
- Satir kilidi gerektiginde `SELECT ... FOR UPDATE`; beklemeden donmek icin `NOWAIT` veya
  `SKIP LOCKED` (kuyruk isleme deseni).
- Uzun transaction'lardan kacinilir; `VACUUM`'u engeller ve tablo sismesine (bloat) yol acar.
- Deadlock riskine karsi kaynaklara daima ayni sirada erisilir.

## Performans

- SARGable yaz: `WHERE tarih >= @gun AND tarih < @gun + interval '1 day'`, kolonu fonksiyona sokma.
  Fonksiyon zorunluysa **ifade indeksi** acilir.
- `SELECT *` yok; sadece gereken kolonlar.
- Plan incelemesi `EXPLAIN (ANALYZE, BUFFERS)` ile yapilir.
- Indeks tipleri: varsayilan `btree`; JSONB ve dizi icinde arama icin `GIN`; metin arama icin
  `GIN` + `to_tsvector`; benzerlik icin `pg_trgm`.
- Buyuk tablolarda indeks olusturmak icin `CREATE INDEX CONCURRENTLY` (tabloyu kilitlemez;
  transaction icinde calistirilamaz).
- Sayfalama `LIMIT ... OFFSET` yerine derin sayfalarda anahtar tabanli (`WHERE id > @sonId
  ORDER BY id LIMIT n`) yapilir.
- `now()` transaction baslangic zamanini verir; gercek anlik zaman icin `clock_timestamp()`.

## Sema ve tip

- Isimlendirme `snake_case` (tablo, kolon, fonksiyon, parametre).
- Zaman kolonlari `timestamptz` (UTC). `timestamp` (zaman dilimsiz) kullanilmaz.
- Para/oran `numeric`, asla `float`/`double`.
- Metin icin `text` yeterlidir; uzunluk kisiti is kuraliysa `varchar(n)` ya da `CHECK`.
- Yarı yapili veri `jsonb` (`json` degil). Sorgulanan alanlar mumkunse ayri kolona cikarilir.
- Her tabloda birincil anahtar; dogal anahtar yoksa `bigint generated always as identity`.
- Yabanci anahtar kolonlarina indeks acilir (PostgreSQL otomatik acmaz — sik atlanan nokta).

## Yasaklar

- Uygulama kodunda SQL stringi.
- String birlestirme ile dinamik SQL — zorunluysa `format()` + `%I` / `%L` ve `EXECUTE ... USING`
  ile parametre gecisi.
- `pg_advisory_lock` kullanip birakmayi unutmak.
- Fonksiyon imzasi degisirken `DROP` etmeden `CREATE OR REPLACE` yapip eski asiri yuklemeyi
  ortada birakmak.
- Uzun suren transaction ve icinde harici servis cagrisi.
- `WHERE` olmadan `UPDATE`/`DELETE`; script uretirken once etkilenecek satir sayisi `SELECT`
  ile gosterilir.
