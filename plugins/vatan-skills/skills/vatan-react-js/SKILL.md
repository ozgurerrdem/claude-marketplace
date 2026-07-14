---
name: vatan-react-js
description: >
  Vatan frontend projelerinde React ile calisirken kullanilir. Yeni React uygulamasi kurma,
  bilesen (component) yazma, state yonetimi, sunucu verisi cekme, form ve validasyon, routing,
  API katmani, hata yonetimi, performans ve klasor yapisi konularini kapsar. TypeScript,
  Vite, TanStack Query, react-hook-form + zod tabanli kurumsal React standartlarini tanimlar.
  Ekranlarda gosterilen tum metinler Turkce olur.
---

# Vatan React Standartlari

## Temel felsefe

Backend'deki ilkelerin aynisi: sade, kurumsal, buyumeye acik. Bilesen bir SP gibi dusunulur —
tek isten sorumlu, girdisi belli, yan etkisi olculu.

- TypeScript zorunlu. `any` yasak; tip bilinmiyorsa `unknown` + daraltma.
- Class component yok. Fonksiyon bilesen + hook.
- Erken soyutlama yok. Ucuncu tekrarda ortak bilesen/hook cikarilir.
- Ekrandaki tum metinler ve hata mesajlari **Turkce**.

## Proje iskeleti

Vite + React + TypeScript. Klasor yapisi **ozelliğe (feature) gore**, tipe gore degil:

```
src/
  app/                 -> giris noktasi, router, global provider'lar
  shared/
    api/               -> http client, tipli endpoint fonksiyonlari
    components/        -> gercekten paylasilan UI bilesenleri
    hooks/             -> paylasilan hook'lar
    lib/               -> saf yardimci fonksiyonlar
    types/             -> paylasilan tipler
  features/
    urun/
      components/
      hooks/
      api.ts
      types.ts
      UrunListesiSayfasi.tsx
    stok/
      ...
```

Kural: bir dosya sadece kendi feature'i icinden veya `shared/` icinden import eder.
Feature'lar birbirini dogrudan import etmez; ortak ihtiyac `shared/`'a cikar.

## Bilesen kurallari

```tsx
type UrunKartiProps = {
  urun: Urun;
  onSecim: (barkod: string) => void;
};

export function UrunKarti({ urun, onSecim }: UrunKartiProps) {
  if (!urun.aktif) {
    return null;
  }

  return (
    <button type="button" onClick={() => onSecim(urun.barkod)}>
      <span>{urun.ad}</span>
      <span>{formatlaFiyat(urun.fiyat)}</span>
    </button>
  );
}
```

- Bir bilesen ya **sunum** yapar ya **veri getirir**; ikisini ayni dosyada karistirma.
  Veri cekme sayfa/container seviyesinde, sunum bilesenleri props ile beslenir.
- Props tipi `type` ile ustte tanimlanir. Props destructuring imzada yapilir.
- 150 satiri asan bilesen bolunme adayidir.
- Erken donus (`if (...) return null`) tercih edilir; ic ice ternary zinciri yasak.
- Liste render'inda `key` daima kararli bir kimlik olur (`urun.barkod`), asla `index`.
- Inline stil ve sihirli renk kodu yok; tasarim token'i / stil sistemi uzerinden.

## Hook kurallari

- Hook'lar sadece bilesen ya da baska hook'un en ust seviyesinde cagrilir. Kosul/dongude yok.
- `useEffect` **son care**. Su durumlarda kullanma:
  - Turetilebilir deger icin (render sirasinda hesapla).
  - Kullanici olayina tepki icin (event handler'a yaz).
  - Sunucu verisi cekmek icin (bunun yeri TanStack Query).
  `useEffect` gercek dis dunya senkronizasyonu icindir (abonelik, timer, DOM API).
- Her `useEffect` gerekiyorsa temizleme (`return () => ...`) yazilir.
- Ozel hook'lar `use` onekiyle ve tek isten sorumlu (`useUrunListesi`, `useOturum`).
- `useMemo`/`useCallback` **olculmeden** eklenmez; varsayilan olarak yazma.

## State yonetimi

Uc kategoriye ayirilir, karistirilmaz:

| Tip | Cozum |
|---|---|
| Sunucu verisi | TanStack Query (`useQuery` / `useMutation`) |
| Yerel UI state | `useState`, karmasiksa `useReducer` |
| Gercekten global state (oturum, tema, yetki) | Context, buyurse Zustand |

Sunucu verisini Redux/Context'e kopyalama. Onbellek, yeniden deneme, tazeleme ve
yukleniyor/hata durumlarini query kutuphanesi yonetir.

```tsx
export function useUrun(barkod: string) {
  return useQuery({
    queryKey: ["urun", barkod],
    queryFn: ({ signal }) => urunGetir(barkod, signal),
    staleTime: 60_000,
  });
}
```

- `queryKey` daima dizi ve tum bagimliliklari icerir.
- Mutation sonrasi ilgili key `invalidateQueries` ile tazelenir; tum cache temizlenmez.
- `signal` API katmanina aktarilir ki bilesen unmount olunca istek iptal edilsin
  (backend'deki `CancellationToken` karsiligi).

## API katmani

Bilesen icinde `fetch`/`axios` cagrisi yapilmaz. Tek bir http istemcisi + tipli endpoint
fonksiyonlari:

```ts
// shared/api/http.ts
const BASE_URL = import.meta.env.VITE_API_URL;

export async function istek<T>(yol: string, secenekler: RequestInit = {}): Promise<T> {
  const yanit = await fetch(`${BASE_URL}${yol}`, {
    ...secenekler,
    headers: { "Content-Type": "application/json", ...secenekler.headers },
  });

  if (!yanit.ok) {
    throw new ApiHatasi(yanit.status, await hataMesajiCoz(yanit));
  }

  return (await yanit.json()) as T;
}
```

```ts
// features/urun/api.ts
export function urunGetir(barkod: string, signal?: AbortSignal): Promise<Urun> {
  return istek<Urun>(`/urun/${barkod}`, { signal });
}
```

- API tipleri (`Urun`, `UrunListesiYaniti`) elle veya OpenAPI'den uretilir; `any` yok.
- Backend URL'i ve ortam farklari `.env` uzerinden (`VITE_...`). Kod icine gomulmez.
- Gizli anahtar frontend'e konmaz — tarayiciya giden her sey acik kabul edilir.

## Form ve validasyon

`react-hook-form` + `zod`. Elle `useState` ile form state tutma.

```ts
const urunSemasi = z.object({
  barkod: z.string().min(1, "Barkod zorunludur."),
  fiyat: z.coerce.number().positive("Fiyat sifirdan buyuk olmalidir."),
});

type UrunFormu = z.infer<typeof urunSemasi>;
```

Hata mesajlari Turkce ve semanin icinde. Frontend validasyonu kullanici deneyimi icindir;
**gercek dogrulama backend'de tekrar yapilir**, ona guvenilir.

## Hata ve yukleniyor durumlari

- Her veri cekilen ekranda uc durum acikca ele alinir: yukleniyor / hata / bos sonuc.
- Beklenmeyen render hatalari icin route seviyesinde `ErrorBoundary`.
- Kullaniciya ham exception mesaji gosterilmez; anlasilir Turkce mesaj + yeniden deneme secenegi.
- Konsola `console.log` birakilmaz.

## Routing

`react-router` ile merkezi route tanimi. Sayfa bilesenleri `lazy` + `Suspense` ile bolunur.
Yetkilendirme route sarmalayicisinda kontrol edilir; her bilesende tekrar edilmez.

## Performans

Once olc, sonra optimize et.

- Liste sanallastirma (virtualization) yalnizca yuzlerce satirda.
- Buyuk bagimliliklar (grafik, tarih kutuphanesi) dinamik import ile.
- Resimler boyutlandirilmis ve `loading="lazy"`.
- Gereksiz `memo` sarmalamak cozum degil; once render sebebini bul (prop kimligi degisimi,
  context genisligi).

## Erisilebilirlik ve kalite

- Anlamli HTML: `button` tiklanabilir, `div` degil. Form alanlarina `label`.
- ESLint + Prettier zorunlu; `eslint-plugin-react-hooks` acik.
- Strict TypeScript (`strict: true`), `noUncheckedIndexedAccess` onerilir.
- Bilesenler ileride test edilebilir yazilir (yan etki hook'a izole, saf fonksiyonlar disarida).
  Istenmedikce test dosyasi yazilmaz.

## Cikti kurallari

- Yorum satiri ekleme.
- Tum dosyayi yeniden yazma; degisen bilesen/hook veya diff ver.
- Onsoz yok, once kod.
- Kutuphane onerirken once tek ve yerlesik olani ver; alternatifleri sorulmadikca acma.

## Yasaklar

- `any`, `@ts-ignore`.
- Class component, `componentDidMount` kaliplari.
- Sunucu verisini global store'a kopyalamak.
- Veri cekmek icin `useEffect` + `fetch` ikilisi.
- Bilesen icinde dogrudan `fetch`/`axios`.
- `index` degerini `key` olarak kullanmak.
- Ingilizce kullanici arayuzu metni.
- Ilgisiz dosyalarda kendiliginden refactor.
