---
name: react
description: >
  Use when working on React frontend projects. Covers scaffolding a new React app,
  writing components, state management, server-data fetching, forms and validation,
  routing, the API layer, error handling, performance, and folder structure. Defines
  corporate React standards based on TypeScript, Vite, TanStack Query, and
  react-hook-form + zod. User-facing strings follow the project's chosen language.
---

# React Standards

## Core philosophy

The same principles as a well-designed backend: simple, corporate, growth-ready. Think of a
component like a single use case — one responsibility, defined inputs, measured side effects.

- TypeScript is mandatory. `any` is banned; if a type is unknown, use `unknown` + narrowing.
- No class components. Function components + hooks.
- No premature abstraction. Extract a shared component/hook on the third repetition.
- All user-facing text and error messages follow the project's chosen language, consistently.

## Project skeleton

Vite + React + TypeScript. Folder structure is **feature-based**, not type-based:

```
src/
  app/                 -> entry point, router, global providers
  shared/
    api/               -> http client, typed endpoint functions
    components/        -> genuinely shared UI components
    hooks/             -> shared hooks
    lib/               -> pure helper functions
    types/             -> shared types
  features/
    product/
      components/
      hooks/
      api.ts
      types.ts
      ProductListPage.tsx
    stock/
      ...
```

Rule: a file imports only from within its own feature or from `shared/`. Features do not import
each other directly; a shared need moves up into `shared/`.

## Component rules

```tsx
type ProductCardProps = {
  product: Product;
  onSelect: (barcode: string) => void;
};

export function ProductCard({ product, onSelect }: ProductCardProps) {
  if (!product.active) {
    return null;
  }

  return (
    <button type="button" onClick={() => onSelect(product.barcode)}>
      <span>{product.name}</span>
      <span>{formatPrice(product.price)}</span>
    </button>
  );
}
```

- A component either **presents** or **fetches data**; do not mix both in one file. Data fetching
  lives at the page/container level; presentational components are fed by props.
- The props type is declared with `type` at the top. Props destructuring happens in the signature.
- A component over ~150 lines is a split candidate.
- Prefer early returns (`if (...) return null`); nested ternary chains are banned.
- List render `key` is always a stable identity (`product.barcode`), never `index`.
- No inline styles or magic color codes; go through design tokens / the styling system.

## Hook rules

- Hooks are called only at the top level of a component or another hook. Never in conditionals/loops.
- `useEffect` is a **last resort**. Do not use it for:
  - Derivable values (compute during render).
  - Reacting to a user event (put it in the event handler).
  - Fetching server data (that belongs to TanStack Query).
  `useEffect` is for real external-world synchronization (subscriptions, timers, DOM APIs).
- Every `useEffect` that needs it has cleanup (`return () => ...`).
- Custom hooks are `use`-prefixed and single-responsibility (`useProductList`, `useSession`).
- Do not add `useMemo`/`useCallback` **without measuring**; do not write them by default.

## State management

Split into three categories, never mixed:

| Type | Solution |
|---|---|
| Server data | TanStack Query (`useQuery` / `useMutation`) |
| Local UI state | `useState`, or `useReducer` when complex |
| Genuinely global state (session, theme, permissions) | Context, Zustand when it grows |

Do not copy server data into Redux/Context. Caching, retries, refetching, and loading/error states
are managed by the query library.

```tsx
export function useProduct(barcode: string) {
  return useQuery({
    queryKey: ["product", barcode],
    queryFn: ({ signal }) => getProduct(barcode, signal),
    staleTime: 60_000,
  });
}
```

- `queryKey` is always an array and contains every dependency.
- After a mutation, refresh the relevant key with `invalidateQueries`; do not flush the whole cache.
- Pass `signal` down to the API layer so the request is cancelled when the component unmounts
  (the frontend equivalent of the backend `CancellationToken`).

## API layer

No `fetch`/`axios` calls inside components. A single http client + typed endpoint functions:

```ts
// shared/api/http.ts
const BASE_URL = import.meta.env.VITE_API_URL;

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response));
  }

  return (await response.json()) as T;
}
```

```ts
// features/product/api.ts
export function getProduct(barcode: string, signal?: AbortSignal): Promise<Product> {
  return request<Product>(`/product/${barcode}`, { signal });
}
```

- API types (`Product`, `ProductListResponse`) are written by hand or generated from OpenAPI; no `any`.
- The backend URL and environment differences come from `.env` (`VITE_...`). Never hard-coded.
- No secret keys in the frontend — treat everything shipped to the browser as public.

## Forms and validation

`react-hook-form` + `zod`. Do not hand-roll form state with `useState`.

```ts
const productSchema = z.object({
  barcode: z.string().min(1, "Barcode is required."),
  price: z.coerce.number().positive("Price must be greater than zero."),
});

type ProductForm = z.infer<typeof productSchema>;
```

Error messages live in the schema, in the project's language. Frontend validation is for UX;
**real validation is repeated on the backend**, which is the source of truth.

## Error and loading states

- Every data-fetching screen explicitly handles three states: loading / error / empty result.
- Wrap unexpected render errors in a route-level `ErrorBoundary`.
- Never show raw exception messages to the user; show a clear message + a retry option.
- Do not leave `console.log` in committed code.

## Routing

Central route definitions with `react-router`. Page components are split with `lazy` + `Suspense`.
Authorization is checked in a route wrapper; not repeated in every component.

## Performance

Measure first, optimize second.

- List virtualization only for hundreds of rows.
- Large dependencies (charts, date libraries) via dynamic import.
- Images sized and `loading="lazy"`.
- Wrapping everything in `memo` is not a fix; first find the render cause (prop identity change,
  context width).

## Accessibility and quality

- Semantic HTML: a clickable thing is a `button`, not a `div`. Form fields have a `label`.
- ESLint + Prettier are mandatory; `eslint-plugin-react-hooks` enabled.
- Strict TypeScript (`strict: true`), `noUncheckedIndexedAccess` recommended.
- Write components so they can be tested later (side effects isolated in hooks, pure functions
  outside). Do not write test files unless asked.

## Output style

- Do not add comments.
- Do not rewrite the whole file; give the changed component/hook or a diff.
- No preamble; code first.
- When recommending a library, give the single established one first; do not lay out alternatives
  unless asked.

## Bans

- `any`, `@ts-ignore`.
- Class components, `componentDidMount` patterns.
- Copying server data into a global store.
- The `useEffect` + `fetch` pair for fetching data.
- Direct `fetch`/`axios` inside components.
- Using `index` as a `key`.
- Mixed-language UI text within one project.
- Unprompted refactors in unrelated files.
