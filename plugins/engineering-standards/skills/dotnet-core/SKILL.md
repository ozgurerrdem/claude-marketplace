---
name: dotnet-core
description: >
  Use when writing, refactoring, or making architectural decisions in modern .NET
  projects. Applies to C#, ASP.NET Core, Web API, MVC, Worker Service, gRPC, minimal
  APIs, class libraries, and any data access approach behind repository abstractions.
  Defines Clean Architecture layering, dependency injection, service design, error
  handling, logging, caching (in-memory/distributed), async/CancellationToken,
  configuration, resilience, and code quality standards. Also applies when scaffolding
  a new project skeleton.
---

# .NET Clean Architecture Standards

## Core philosophy

Simple, professional, forward-looking. Every decision passes this test: **can another
engineer safely change this code two years from now?**

- No over-engineering. No speculative abstraction, no single-implementation interface,
  no "we might need it later" layer.
- No under-engineering either. Spaghetti code, business logic inside controllers,
  static singletons, and copy-paste blocks are unacceptable.
- Write code so unit tests can be added later (constructor injection, pure methods,
  external dependencies behind interfaces). But do not write test files or mention
  tests unless explicitly asked.

## Solution structure

```
Company.X.Domain          -> entities, value objects, domain rules, interface contracts
Company.X.Application     -> services, DTOs, use cases, validation
Company.X.Infrastructure  -> data access, external API clients, cache, files, messaging
Company.X.Web / .Api      -> controllers, endpoints, middleware, Program.cs
```

Dependencies always point inward: `Web -> Application -> Domain`, `Infrastructure -> Domain`.
Domain references nothing. Application does not reference Infrastructure; interfaces are
declared in Application/Domain, implementations live in Infrastructure (Dependency Inversion).

For small services four layers may be overkill; keep at least `Api + Application + Infrastructure`.
Discuss layer merging with the developer before collapsing them.

## Dependency injection

Each project registers itself in an extension method. `Program.cs` only calls them.

```csharp
public static class ApplicationServiceRegistration
{
    public static IServiceCollection AddApplication(this IServiceCollection services)
    {
        services.AddScoped<IProductService, ProductService>();
        services.AddScoped<IStockService, StockService>();
        return services;
    }
}
```

```csharp
public static class InfrastructureServiceRegistration
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<DatabaseOptions>(configuration.GetSection(DatabaseOptions.SectionName));
        services.AddSingleton<ISqlConnectionFactory, SqlConnectionFactory>();
        services.AddScoped<IProductRepository, ProductRepository>();
        return services;
    }
}
```

```csharp
builder.Services
    .AddApplication()
    .AddInfrastructure(builder.Configuration);
```

Lifetime rules:
- `Singleton`: connection factory, cache service, typed `HttpClient` clients, options.
- `Scoped`: repositories, business services, UnitOfWork.
- `Transient`: lightweight, stateless helpers.
- Never inject a scoped dependency into a singleton. Use `IServiceScopeFactory` if needed.

## Configuration

No magic strings. Each settings block is an options class:

```csharp
public sealed class DatabaseOptions
{
    public const string SectionName = "Database";
    public string ConnectionString { get; init; } = string.Empty;
    public int CommandTimeoutSeconds { get; init; } = 30;
}
```

Inject `IOptions<T>` (static) or `IOptionsMonitor<T>` (changes at runtime) into services.
Secrets (passwords, tokens, connection strings) never live in code or the repository; they
come from environment variables or a secret store. Validate options at startup with
`ValidateOnStart()` so misconfiguration fails fast rather than at first use.

## Service design

Keep services thin. A service method: validate input -> run the use case -> return a result.

- Controller/endpoint: model binding, service call, HTTP result only. No business logic.
- Repository: data access only. No business rules.
- Service: business logic. Never sees HTTP types (`IActionResult`, `HttpContext`).
- A class over ~300 lines or a method over ~50 lines is a split candidate.
- No static mutable state. Prefer an injectable time source (`TimeProvider`) over
  `DateTime.Now`; at minimum use `DateTime.UtcNow`.

## Error handling

If the project has no `Result<T>` type, do not invent one and spread it everywhere. Rule:

- **Expected business failure** (not found, insufficient stock, validation error): part of
  the normal flow. If the project has a `Result`/`Outcome` type, use it. Otherwise design a
  meaningful return type (`bool TryX(out ...)`, a nullable return, or a small result record)
  and tell the developer in one sentence.
- **Unexpected failure** (dropped connection, null reference, corrupt data): surfaces as an
  exception. Never swallowed.

```csharp
public sealed record Result<T>(bool Success, T? Value, string? Error)
{
    public static Result<T> Ok(T value) => new(true, value, null);
    public static Result<T> Fail(string error) => new(false, default, error);
}
```

Hard bans:
- `catch (Exception) { }` — empty catch.
- `catch (Exception ex) { throw ex; }` — destroys the stack trace. Use `throw;`.
- Throwing exceptions for control flow.
- Showing raw exception messages to the user.

The API layer has global exception-handling middleware (or `IExceptionHandler`); it logs the
unexpected error and returns a sanitized message to the client (ideally as
`ProblemDetails`/RFC 7807).

## Logging

Inject `ILogger<T>`. Do not add another logging library unless asked.

Messages are in the project's language, structured with named parameters:

```csharp
_logger.LogInformation("Product price updated. Barcode: {Barcode}, NewPrice: {Price}", barcode, price);
_logger.LogWarning("Product not found. Barcode: {Barcode}", barcode);
_logger.LogError(ex, "Price update failed. Barcode: {Barcode}", barcode);
```

- Never build log messages with string interpolation (`$"..."`). Use placeholders.
- Level discipline: `Information` business events, `Warning` expected-but-undesired states,
  `Error` exceptions, `Debug` development detail. `Critical` only when the service cannot stay up.
- Do not log excessively on the hot path (code that runs on every request).
- Never log passwords, tokens, national IDs, card data, or other sensitive PII.
- Prefer correlation/trace IDs (via `ILogger` scopes or OpenTelemetry) so a request can be
  followed across services.

## Async rules

- Every IO-bound method is `async Task` / `async Task<T>`.
- Every async method takes `CancellationToken cancellationToken` as its last parameter and
  flows it down (DB, HTTP, cache). Expect the caller to pass it rather than defaulting it.
- `async void` only in event handlers. Nowhere else.
- `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` are banned — they cause deadlocks and
  thread-pool starvation.
- Use `ConfigureAwait(false)` in library code; unnecessary in ASP.NET Core application code.
- Use `Task.WhenAll` for independent parallel work. Never run concurrent operations on the
  same `DbConnection`/`DbContext`.
- Prefer `IAsyncEnumerable<T>` for large streaming results.

## Caching

If the service runs across multiple pods/instances, a **distributed cache (e.g. Redis)** is
required; for a single instance or pod-local, cheaply reproducible data, **in-memory** is
enough. The developer decides — if unclear, ask: "Does this service run across multiple
pods/instances? Should the cache be in-memory or distributed?"

Cache key format: `app-service-operationSpecificData`

```
catalog-product-barcode:8690000000001
portal-campaign-store:160
```

Cache-aside with stampede protection (single production per key):

```csharp
public async Task<ProductDto?> GetAsync(string barcode, CancellationToken cancellationToken)
{
    var key = $"{AppName}-product-barcode:{barcode}";

    if (_cache.TryGetValue(key, out ProductDto? cached))
        return cached;

    var gate = _locks.GetOrAdd(key, _ => new SemaphoreSlim(1, 1));
    await gate.WaitAsync(cancellationToken);
    try
    {
        if (_cache.TryGetValue(key, out cached))
            return cached;

        var product = await _repository.GetAsync(barcode, cancellationToken);
        if (product is not null)
            _cache.Set(key, product, TimeSpan.FromMinutes(5));

        return product;
    }
    finally
    {
        gate.Release();
    }
}
```

- Every cache entry gets a TTL. No indefinite cache.
- On data change, invalidate the affected key (`Remove`); never flush the whole cache.
- Access the cache behind an interface (`ICacheService`) so in-memory <-> distributed swaps
  happen in one place.
- The lock dictionary must not grow unbounded; if the key count is very high, expire locks.

## HTTP clients and resilience

`new HttpClient()` is banned (socket exhaustion). Use `IHttpClientFactory` or a typed client:

```csharp
services.AddHttpClient<ISupplierClient, SupplierClient>(client =>
{
    client.BaseAddress = new Uri(options.BaseUrl);
    client.Timeout = TimeSpan.FromSeconds(30);
});
```

Timeout, retry, and circuit-breaker policies matter for external calls. On .NET 8+ prefer the
built-in `AddStandardResilienceHandler` (Microsoft.Extensions.Http.Resilience) or Polly. Do not
add resilience blindly — confirm the failure mode with the developer, but do surface when an
external call has no timeout at all.

## Code quality (clean, static-analysis friendly)

- Everything is `internal`/`private` except public classes and methods. Classes not designed
  for inheritance are `sealed`.
- Immutable fields are `readonly`; data-carrying types are `record` or use `init`-only properties.
- Nullable reference types enabled (`<Nullable>enable</Nullable>`). The `!` (null-forgiving)
  operator only where non-null is genuinely provable.
- No magic numbers or strings; use constants or options.
- No unused usings, fields, or parameters.
- Extract a repeated block into a method on the third occurrence (not the first).
- Every `IDisposable` you create is closed with `using`.
- More than three nested `if` levels — flatten with guard clauses / early returns.

## Naming

- Class/method/property: `PascalCase`. Local variable/parameter: `camelCase`.
  Private field: `_camelCase`.
- Interfaces prefixed with `I`. Async methods suffixed with `Async`.
- Prefer English for code identifiers; whatever the existing project convention is, stay
  consistent. Never mix languages within a project.
- User-facing and log strings follow the project's chosen language, consistently.

## Output style (rules while this skill is active)

- Do **not** add comments. Never write a comment on any line unless the developer explicitly
  asks. Code should explain itself; if it does not, fix the naming.
- Do not rewrite the whole file. Provide only the changed method, line, or diff. If the full
  file is wanted, the developer says so.
- No preamble or summary; code first.
- Give a single solution first: the most professional, corporate, growth-ready, and simple one.
  Do not lay out alternatives unless asked.
- Cover edge cases as short bullets, not long prose.
- If you see a pattern that conflicts with the existing code style, ask first; do not start a
  one-sided refactor.

## Bans

- SQL strings inside application code. (See `mssql`, `postgresql`.)
- `async void`, `.Result`, `.Wait()`.
- Static mutable state, service locator (`IServiceProvider.GetService` in application code).
- Speculative single-implementation interfaces, unnecessary generic repositories.
- Mixed-language identifiers within one project.
- Comments (unless asked).
- Cleanup/refactor in unrelated files. Only the requested change is made.
