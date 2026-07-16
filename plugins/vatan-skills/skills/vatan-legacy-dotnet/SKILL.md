---
name: vatan-legacy-dotnet
description: >
  Vatan'in eski .NET Framework tabanli projelerinde (WCF servisleri, ASP.NET Web API/MVC,
  Web Forms, klasik Windows servisleri) calisirken kullanilir. IIS uzerinde barinan, TFS/TFVC
  veya Git ile yonetilen legacy kod tabanlarinda guvenli degisiklik yapma, WCF servis
  sozlesmesi ekleme, senkron/asenkron karisik kodda deadlock'tan kacinma, kademeli
  modernizasyon ve .NET (Core) tarafina tasima stratejisini kapsar.
---

# Vatan Legacy .NET Standartlari

## Temel ilke

Legacy kodda amac **guvenli degisiklik**, buyuk temizlik degil. Dokundugun yeri iyilestir,
dokunmadigin yeri birak. Kapsam disina tasan refactor teklif edilmez; gerekiyorsa ayri is
olarak gelistiriciye onerilir.

Mevcut kod stilini taklit et. Yeni ve modern bir kalibi ancak dosya genelinde tutarli
uygulayabiliyorsan getir; yarim birakilan modernizasyon en kotu sonuctur.

## Async / senkron karisimi

Legacy kodda en yaygin uretim hatasi kaynagi budur.

- `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` — ASP.NET Framework'un senkronizasyon
  baglami (SynchronizationContext) ile birlesince **deadlock** uretir. Yeni kodda kesinlikle yasak.
- Kutuphane/servis kodunda `await` sonrasi `ConfigureAwait(false)` **zorunlu** (Core'dan farkli
  olarak burada gercekten gereklidir).
- Senkron bir API'yi `Task.Run` ile sarip "async yaptim" sanmak yanlistir; thread havuzunu tuketir.
- Mevcut senkron bir metodu asenkrona cevirmek cagri zincirinin tamamini etkiler. Bunu tek basina
  baslatma; gelistiriciye kapsamini bildir.

## WCF servisleri

- Yeni bir islem eklerken: `[ServiceContract]` arayuzune `[OperationContract]` metodu, veri
  tasiyicilar icin `[DataContract]` / `[DataMember]` siniflari eklenir. Var olan sozlesme
  **kirilmaz**: metot imzasi ve `DataMember` isimleri degistirilmez, alan silinmez.
- Yeni alan eklemek geriye donuk uyumludur; zorunlu yeni alan eklemek degildir. Yeni alanlar
  `IsRequired = false` ile eklenir.
- Kirici degisiklik gerekiyorsa yeni bir operasyon (`XV2`) eklenir, eskisi bir sure yasar.
- `web.config`/`app.config` icindeki binding, quota (`maxReceivedMessageSize`, `maxStringContentLength`)
  ve timeout degerleri buyuk veri veya yavas islemlerde gozden gecirilir.
- Servis implementasyonu ince tutulur; is mantigi ayri siniflara alinir. Bu, ileride Core tarafina
  tasimayi kolaylastirir.
- Hata istemciye ham exception olarak gitmez; `FaultException` veya sozlesmeli hata modeli ile
  Turkce mesaj doner. `includeExceptionDetailInFaults` uretimde kapali.

## Veri erisimi

- Yeni kodda da kural ayni: **uygulamada SQL stringi yok**, stored procedure/fonksiyon uzerinden
  gidilir (bkz. `vatan-sql`, `vatan-postgres`).
- Legacy'de sik gorulen `SqlCommand` + `CommandType.Text` + string birlestirme varsa: dokundugun
  yerde parametreli hale getir, mumkunse SP'ye tasi. Injection riski olan bir satir gorursen
  kapsam disi bile olsa gelistiriciye bildir.
- `SqlConnection` daima `using` ile; uzun yasayan statik connection tutulmaz.

## Bagimlilik ve tasarim

- DI konteyneri yoksa uydurup projeye sokma. Ancak yeni yazilan siniflar **constructor injection**
  ile tasarlanir; statik cagri zinciri buyutulmez. Bu, ileride Core'a tasimayi mumkun kilar.
- Yeni is mantigi mumkun oldugunca `System.Web`, `HttpContext.Current`, WCF tiplerinden bagimsiz
  saf siniflara yazilir. Bu siniflar birebir Core tarafina tasinabilir.
- `HttpContext.Current` async kod icinde guvenilmez; deger gerekiyorsa metot parametresi olarak gecir.
- Kod icinde `ConfigurationManager.AppSettings["..."]` dagitilmaz; tek bir ayar sinifinda toplanir.

## Loglama

Projede ne varsa (log4net, NLog, elle dosya logu) ona uy. Yeni loglama kutuphanesi ekleme.
Mesajlar Turkce; parola/token/kisisel veri loglanmaz.

## Kaynak kontrolu

- Yeni projeler Git ile gelistirilir. Mevcut TFS/TFVC projeleri bir sure daha yerinde kalir;
  uzun vadede Git'e gecis planlanmaktadir.
- TFVC calisirken: workspace eslemesi bozulmus dosyalar (silinmis ama sunucuda duran, ya da
  yerelde olup eklenmeyen) is basina temizlenir; "pending changes" temiz birakilir.
- Bir isi hem TFS'te hem Git'te paralel gelistirme; her degisiklik icin tek bir kaynak kontrolu
  esas alinir. Aksi halde tarih dagilir ve degisiklikler kaybolur.

## Modernizasyon stratejisi

Buyuk yeniden yazma (big bang rewrite) onerilmez. Kademeli yol:

1. Is mantigini legacy altyapidan (WCF/Web Forms/`HttpContext`) ayrilabilir saf siniflara cek.
2. Bu siniflari paylasilan bir kutuphaneye tasi (mumkunse `netstandard2.0` hedefli).
3. Yeni uclari .NET (Core) tarafinda ac, eski ucu bir sure ayakta tut.
4. Trafigi kademeli tasi, sonra eskisini kaldir.

Bu yolu kendiliginden baslatma; degisiklik talebi geldiginde adim adim ilerlemeyi oner.

## Yasaklar

- `.Result` / `.Wait()` / `async void`.
- `await` sonrasi `ConfigureAwait(false)` unutmak (kutuphane/servis kodunda).
- Var olan WCF sozlesmesini kirmak (imza, `DataMember` adi degistirmek, alan silmek).
- Uretimde `includeExceptionDetailInFaults`.
- String birlestirme ile SQL.
- Talep edilmemis genis capli refactor.
- Legacy projeye yeni framework/kutuphane sokmak (gelistirici istemedikce).
