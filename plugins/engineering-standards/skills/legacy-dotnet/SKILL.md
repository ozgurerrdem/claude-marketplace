---
name: legacy-dotnet
description: >
  Use when working in legacy .NET Framework projects (WCF services, ASP.NET Web API/MVC,
  Web Forms, classic Windows services). Covers making safe changes in IIS-hosted code
  bases managed by TFVC or Git, adding WCF service contracts, avoiding deadlocks in mixed
  sync/async code, incremental modernization, and a migration strategy toward modern
  .NET (Core).
---

# Legacy .NET Standards

## Core principle

In legacy code the goal is a **safe change**, not a grand cleanup. Improve what you touch, leave
what you do not. Do not propose refactors beyond the scope of the request; if one is warranted,
suggest it to the developer as separate work.

Mimic the existing code style. Introduce a new, modern pattern only if you can apply it
consistently across the file; a half-finished modernization is the worst outcome.

## Async / sync mixing

This is the most common source of production bugs in legacy code.

- `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` — combined with ASP.NET Framework's
  `SynchronizationContext`, these cause **deadlocks**. Strictly banned in new code.
- In library/service code, `ConfigureAwait(false)` after `await` is **mandatory** (unlike Core,
  here it genuinely matters).
- Wrapping a synchronous API in `Task.Run` and thinking you "made it async" is wrong; it exhausts
  the thread pool.
- Converting an existing synchronous method to async ripples through the entire call chain. Do not
  start this alone; report the scope to the developer first.

## WCF services

- When adding a new operation: add an `[OperationContract]` method to the `[ServiceContract]`
  interface, and `[DataContract]` / `[DataMember]` classes for the data carriers. Do not **break**
  the existing contract: never change a method signature or `DataMember` name, never remove a field.
- Adding a new field is backward compatible; adding a required new field is not. Add new fields
  with `IsRequired = false`.
- If a breaking change is needed, add a new operation (`XV2`) and keep the old one alive for a while.
- Review binding, quota (`maxReceivedMessageSize`, `maxStringContentLength`), and timeout values in
  `web.config`/`app.config` for large payloads or slow operations.
- Keep the service implementation thin; move business logic into separate classes. This makes a
  later move to Core easier.
- Errors do not reach the client as raw exceptions; return a clear message via `FaultException` or
  a contract-defined fault model. `includeExceptionDetailInFaults` is off in production.

## Data access

- The rule holds in new code too: **no SQL strings in the application**; go through stored
  procedures/functions (see `mssql`, `postgresql`).
- Legacy often has `SqlCommand` + `CommandType.Text` + string concatenation: where you touch it,
  make it parameterized, and move it to a procedure when feasible. If you see a line with injection
  risk, report it to the developer even if it is out of scope.
- Always wrap `SqlConnection` in `using`; never hold a long-lived static connection.

## Dependencies and design

- If there is no DI container, do not invent one and force it into the project. But design new
  classes with **constructor injection**; do not grow the static call chain. This keeps a later move
  to Core possible.
- Write new business logic in pure classes that are independent of `System.Web`, `HttpContext.Current`,
  and WCF types wherever possible. Such classes port to Core almost as-is.
- `HttpContext.Current` is unreliable inside async code; if you need a value, pass it as a method parameter.
- Do not scatter `ConfigurationManager.AppSettings["..."]` through the code; collect settings in a
  single configuration class.

## Logging

Use whatever the project already has (log4net, NLog, hand-rolled file logging). Do not add a new
logging library. Messages follow the project's language; never log passwords, tokens, or personal data.

## Source control

- New projects are developed with Git. Existing TFVC projects may stay in place for a while;
  plan a Git migration over the longer term.
- When working in TFVC: clean up files with broken workspace mappings (deleted but still on the
  server, or present locally but not added) as part of the task; leave "pending changes" clean.
- Do not develop the same work in parallel on both TFVC and Git — pick one source of truth per
  change to avoid divergence and lost history.

## Modernization strategy

A big-bang rewrite is not recommended. The incremental path:

1. Pull business logic out of the legacy infrastructure (WCF/Web Forms/`HttpContext`) into pure,
   separable classes.
2. Move those classes into a shared library (targeting `netstandard2.0` where possible).
3. Open new endpoints on the modern .NET (Core) side while keeping the old endpoint alive for a while.
4. Shift traffic gradually, then retire the old one.

Do not start this path on your own; when a change request arrives, propose progressing step by step.

## Bans

- `.Result` / `.Wait()` / `async void`.
- Forgetting `ConfigureAwait(false)` after `await` (in library/service code).
- Breaking an existing WCF contract (changing a signature or `DataMember` name, removing a field).
- `includeExceptionDetailInFaults` in production.
- Building SQL by string concatenation.
- Unrequested large-scale refactors.
- Introducing a new framework/library into a legacy project (unless the developer asks).
