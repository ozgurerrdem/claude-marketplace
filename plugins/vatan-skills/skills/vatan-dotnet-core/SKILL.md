---
name: vatan-dotnet-core
description: >
  Vatan .NET projelerinde kod yazarken, refactor ederken veya mimari kararlar alirken
  kullanilir. C#, ASP.NET Core, Web API, MVC, Worker Service, WCF, class library ve
  Dapper tabanli veri erisimi iceren tum .NET islerinde gecerlidir. Katmanli mimari,
  DI kaydi, servis tasarimi, hata yonetimi, loglama, cache (in-memory/Redis),
  async/CancellationToken, konfigurasyon ve kod kalite standartlarini tanimlar.
  Yeni proje iskeleti kurulurken de bu skill uygulanir.
---

# Vatan .NET Core Standartlari

## Temel felsefe

Basit, profesyonel, ileriye donuk. Her karar su testten gecer: **bu kod 2 yil sonra
baska bir gelistirici tarafindan guvenle degistirilebilir mi?**

- Over-engineering yok. Gereksiz soyutlama, tek implementasyonu olan interface,
  "belki lazim olur" katmani ekleme.
- Under-engineering de yok. Spagetti kod, controller icinde is mantigi, statik
  singleton'lar, kopyala-yapistir bloklar kabul edilmez.
- Kod ileride unit test eklenebilecek sekilde yazilir (constructor injection, saf
  metotlar, disariya bagimlilik interface arkasinda). Ama istenmedikce test dosyasi
  yazilmaz ve testten bahsedilmez.

## Cozum yapisi

```
Vatan.X.Domain          -> entity, value object, domain kurallari, arayuz sozlesmeleri
Vatan.X.Application     -> servisler, DTO'lar, is akisi, validasyon
Vatan.X.Infrastructure  -> Dapper repository, harici API client, cache, dosya, mesajlasma
Vatan.X.Web / .Api      -> controller, endpoint, middleware, Program.cs
```

Bagimlilik yonu daima ice dogru: `Web -> Application -> Domain`, `Infrastructure -> Domain`.
Domain hicbir seye referans vermez. Application, Infrastructure'a referans vermez;
interface Application/Domain'de tanimlanir, implementasyon Infrastructure'da olur.

Kucuk servisler icin 4 katman zorlama sayilabilir; en az `Api + Application + Infrastructure`
korunur. Katman birlestirmeyi gelistiriciye danis.

## DI kaydi

Her proje kendi kaydini extension metodunda yapar. `Program.cs` sadece cagirir.

```csharp
public static class ApplicationServiceRegistration
{
    public static IServiceCollection AddApplication(this IServiceCollection services)
    {
        services.AddScoped<IUrunService, UrunService>();
        services.AddScoped<IStokService, StokService>();
        return services;
    }
}
```

```csharp
public static class InfrastructureServiceRegistration
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<VeritabaniOptions>(configuration.GetSection(VeritabaniOptions.SectionName));
        services.AddSingleton<ISqlConnectionFactory, SqlConnectionFactory>();
        services.AddScoped<IUrunRepository, UrunRepository>();
        return services;
    }
}
```

```csharp
builder.Services
    .AddApplication()
    .AddInfrastructure(builder.Configuration);
```

Yasam suresi kurallari:
- `Singleton`: connection factory, cache servisi, HttpClient tipli client (typed client), options.
- `Scoped`: repository, is servisi, UnitOfWork.
- `Transient`: hafif, durumsuz yardimcilar.
- Scoped bagimlilik singleton icine enjekte edilmez. Gerekiyorsa `IServiceScopeFactory` kullan.

## Konfigurasyon

Sihirli string yok. Her ayar bloğu bir options sinifi:

```csharp
public sealed class VeritabaniOptions
{
    public const string SectionName = "Veritabani";
    public string BaglantiCumlesi { get; init; } = string.Empty;
    public int KomutZamanAsimiSaniye { get; init; } = 30;
}
```

Servis icinde `IOptions<T>` (sabit) veya `IOptionsMonitor<T>` (calisma aninda degisebilen)
enjekte edilir. Gizli bilgi (parola, token, connection string) koda ya da repoya yazilmaz;
ortam degiskeni veya secret store uzerinden gelir.

## Servis tasarimi

Servisler ince tutulur. Bir servis metodu: girdi dogrula -> is akisini yurut -> sonuc don.

- Controller/endpoint: sadece model baglama, servis cagirma, HTTP sonuc uretme. Is mantigi icermez.
- Repository: sadece veri erisimi. Is kurali icermez.
- Servis: is mantigi. HTTP tipi (`IActionResult`, `HttpContext`) gormez.
- 300 satiri asan sinif ve 50 satiri asan metot bolunme adayidir.
- Statik durum (static mutable field) yok. `DateTime.Now` yerine enjekte edilebilir zaman
  kaynagi (`TimeProvider`) tercih edilir; en azindan `DateTime.UtcNow` kullanilir.

## Hata yonetimi

Projede hazir bir `Result<T>` tipi yoksa uydurup her yere yayma. Kural:

- **Beklenen is hatasi** (urun bulunamadi, stok yetersiz, dogrulama hatasi): akisin normal
  parcasidir. Projede `Result`/`Outcome` benzeri bir tip varsa onu kullan. Yoksa anlamli bir
  donus tipi (`bool TryX(out ...)`, nullable donus, ya da kucuk bir sonuc kaydi) tasarla ve
  gelistiriciye tek cumleyle bildir.
- **Beklenmeyen hata** (baglanti kopmasi, null referans, bozuk veri): exception olarak
  yukselir. Yutulmaz.

```csharp
public sealed record IslemSonucu<T>(bool Basarili, T? Deger, string? Hata)
{
    public static IslemSonucu<T> Ok(T deger) => new(true, deger, null);
    public static IslemSonucu<T> Hatali(string hata) => new(false, default, hata);
}
```

Kesin yasaklar:
- `catch (Exception) { }` — bos yakalama.
- `catch (Exception ex) { throw ex; }` — stack trace'i yok eder. `throw;` kullan.
- Kontrol akisi icin exception firlatma.
- Exception mesajini kullaniciya ham gosterme.

API katmaninda global exception middleware olur; beklenmeyen hatayi loglar, istemciye
sadeleştirilmiş ve Turkce bir hata mesaji doner.

## Loglama

`ILogger<T>` enjekte edilir. Aksi belirtilmedikce ek loglama kutuphanesi eklenmez.

Mesajlar **Turkce**, yapisal (structured) parametreli:

```csharp
_logger.LogInformation("Urun fiyati guncellendi. Barkod: {Barkod}, YeniFiyat: {Fiyat}", barkod, fiyat);
_logger.LogWarning("Urun bulunamadi. Barkod: {Barkod}", barkod);
_logger.LogError(ex, "Fiyat guncelleme basarisiz. Barkod: {Barkod}", barkod);
```

- String interpolation ile log mesaji kurma (`$"..."`). Parametre yer tutucu kullan.
- Seviye disiplini: `Information` is olayi, `Warning` beklenen ama istenmeyen durum,
  `Error` exception, `Debug` gelistirme ayrintisi. `Critical` sadece servis ayakta kalamayacaksa.
- Sicak yolda (her istekte calisan kod) asiri log yazma.
- Parola, token, TC kimlik, kart bilgisi loglanmaz.

## Async kurallari

- IO yapan her metot `async Task` / `async Task<T>`.
- Her async metot son parametre olarak `CancellationToken cancellationToken` alir ve
  asagi (DB, HTTP, cache) aktarir. Varsayilan deger vermek yerine cagiranin gecmesi beklenir.
- `async void` sadece event handler'da. Baska hicbir yerde.
- `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` yasak — deadlock ve thread acligi uretir.
- Kutuphane kodunda `ConfigureAwait(false)`; ASP.NET Core uygulama kodunda gereksiz.
- Paralel bagimsiz isler icin `Task.WhenAll`. Ayni `DbConnection`/`DbContext` uzerinde
  es zamanli islem yapilmaz.
- `IAsyncEnumerable<T>` buyuk veri akislarinda tercih edilir.

## Cache

Cok pod/instance calisan bir servis ise **dagitik cache (Redis)** gerekir; tek instance veya
pod-yerel, ucuz yeniden uretilebilir veri ise **in-memory** yeterlidir. Hangisinin
kullanilacagina gelistirici karar verir — belirsizse sor:
"Bu servis coklu pod/instance calisiyor mu? Cache in-memory mi Redis mi olsun?"

Cache key formati: `projeAdi-servisAdi-islemSpesifikVeri`

```
tagprice-urun-barkod:8690000000001
portal-kampanya-magaza:160
```

Cache-aside + cache stampede korumasi (ayni anahtar icin tek uretim):

```csharp
public async Task<UrunDto?> GetirAsync(string barkod, CancellationToken cancellationToken)
{
    var key = $"{ProjeAdi}-urun-barkod:{barkod}";

    if (_cache.TryGetValue(key, out UrunDto? cached))
        return cached;

    var kilit = _kilitler.GetOrAdd(key, _ => new SemaphoreSlim(1, 1));
    await kilit.WaitAsync(cancellationToken);
    try
    {
        if (_cache.TryGetValue(key, out cached))
            return cached;

        var urun = await _repository.GetirAsync(barkod, cancellationToken);
        if (urun is not null)
            _cache.Set(key, urun, TimeSpan.FromMinutes(5));

        return urun;
    }
    finally
    {
        kilit.Release();
    }
}
```

- Her cache girdisine mutlaka sure (TTL) verilir. Suresiz cache yok.
- Veri degistiginde ilgili key invalidate edilir (`Remove`), tum cache temizlenmez.
- Cache erisimi arayuz arkasindan yapilir (`ICacheService`) ki in-memory <-> Redis gecisi
  tek yerden olsun.
- Kilit sozlugu sinirsiz buyumemeli; anahtar sayisi cok yuksekse kilitleri sureli temizle.

## HTTP client

`new HttpClient()` yasak (socket tukenmesi). `IHttpClientFactory` veya typed client:

```csharp
services.AddHttpClient<ITedarikciClient, TedarikciClient>(client =>
{
    client.BaseAddress = new Uri(options.BaseUrl);
    client.Timeout = TimeSpan.FromSeconds(30);
});
```

Zaman asimi, yeniden deneme ve devre kesici (retry/circuit breaker) gereksinimi varsa
gelistiriciye sor; varsayilan olarak ekleme.

## Kod kalitesi (Sonar ve benzeri statik analize uygun)

- `public` sinif ve metotlar disinda her sey `internal`/`private`. Miras beklenmeyen sinif `sealed`.
- Degismeyen alan `readonly`; veri tasiyan tip `record` veya `init`-only property.
- Null: nullable reference types acik (`<Nullable>enable</Nullable>`). `!` (null-forgiving)
  operatoru sadece gercekten kanitlanabilir yerde.
- Sihirli sayi ve string yok; sabit veya options.
- Kullanilmayan using, alan, parametre birakilmaz.
- Tekrarlanan blok ucuncu kez yaziliyorsa metoda cikarilir (once degil).
- `IDisposable` uretilen her nesne `using` ile kapatilir.
- Ic ice 3 seviyeden fazla `if` girinti — erken donus (`guard clause`) ile duzlestirilir.

## Isimlendirme

- Sinif/metot/property: `PascalCase`. Yerel degisken/parametre: `camelCase`.
  Private alan: `_camelCase`.
- Interface `I` onekiyle. Async metot `Async` sonekiyle.
- Kod tanimlayicilari (sinif, metot, degisken) **Ingilizce ya da Turkce olabilir; proje
  icindeki mevcut konvansiyon neyse ona uy. Ancak ingilizce öncele.** Karisik kullanma.
- Kullaniciya ve loga giden metinler **daima Turkce**.

## Kod yazma bicimi (bu skill aktifken cikti kurallari)

- Yorum satiri **ekleme**. Gelistirici acikca istemedikce hicbir kod satirina yorum yazma.
  Kod kendini anlatmali; anlatmiyorsa isimlendirmeyi duzelt.
- Tum dosyayi yeniden yazma. Sadece degisen metot, satir veya diff verilir. Tam dosya
  isteniyorsa gelistirici belirtir.
- Onsoz ve ozet yok; once kod.
- Once tek bir cozum ver: en profesyonel, kurumsal, buyumeye acik ve sade olan. Alternatifleri
  sorulmadikca acma.
- Edge-case'ler kisa madde olarak gecilir, uzun anlatilmaz.
- Mevcut kod stiliyle celisen bir kalip goruyorsan once sor, tek tarafli refactor baslatma.

## Yasaklar

- **EF Core ve benzeri ORM onerme.** Veri erisimi Dapper + stored procedure/fonksiyon ile
  yapilir. Projede zaten EF varsa ona uy, ama yeni is icin gelistirici istemedikce teklif etme.
- Kod icinde SQL stringi. (Bkz. `vatan-sql`, `vatan-postgres`)
- `async void`, `.Result`, `.Wait()`.
- Statik mutable durum, service locator (`IServiceProvider.GetService` uygulama kodunda).
- Tek implementasyonu olmayan spekülatif interface, gereksiz generic repository.
- Ingilizce log ve kullanici mesaji.
- Yorum satiri (istenmedikce).
- Ilgisiz dosyalarda temizlik/refactor. Sadece istenen degisiklik yapilir.
