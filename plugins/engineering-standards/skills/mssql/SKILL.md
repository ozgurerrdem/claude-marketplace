---
name: mssql
description: >
  Use when working with MSSQL (SQL Server): writing stored procedures and functions,
  T-SQL query optimization, indexing, transactions, locking/deadlocks, batch data
  processing, and calling SQL Server from .NET with Dapper. Covers calling stored
  procedures via Dapper, connection management, and parameter passing on the .NET side.
---

# MSSQL Standards

## Data access stance

Keep query logic in one deliberate place, not scattered as ad-hoc strings across the codebase.
The professional default is a stored procedure or function that the application calls by name;
an ORM (EF Core) is a valid choice when the team owns it end to end. Whatever the project
picks, apply it consistently and hide it behind a repository interface.

This skill assumes the **stored-procedure / function** style. If the project already uses an
ORM, follow its conventions instead of introducing raw SQL strings alongside it.

## Calling from Dapper

```csharp
public async Task<ProductDto?> GetAsync(string barcode, CancellationToken cancellationToken)
{
    var parameters = new DynamicParameters();
    parameters.Add("@Barcode", barcode, DbType.String, size: 20);

    var command = new CommandDefinition(
        "dbo.ProductGet",
        parameters,
        commandType: CommandType.StoredProcedure,
        commandTimeout: _options.CommandTimeoutSeconds,
        cancellationToken: cancellationToken);

    await using var connection = _connectionFactory.Create();
    return await connection.QuerySingleOrDefaultAsync<ProductDto>(command);
}
```

- Always pass `CommandType.StoredProcedure` explicitly.
- Pass parameters typed and sized via `DynamicParameters` — implicit conversion breaks index usage.
- Flow `CancellationToken` through `CommandDefinition`; otherwise cancellation never reaches the DB.
- For output parameters / return values, read them with `ParameterDirection.Output`.

## Connection management

The right choice depends on the workload profile:

- **High-traffic service** (hundreds of requests/sec, 1-2 queries per request): short-lived
  connection per query. Open, run, release immediately. Holding long-lived connections causes
  pool exhaustion.
- **A flow with multiple writes needing transactional integrity**: a Unit of Work / scoped
  connection may fit better.

If unclear, ask the developer: "How many DB calls does this service make per request, and does
it need transactional integrity?"

In all cases:
- The connection factory sits behind an interface (`ISqlConnectionFactory`); the connection
  string comes from options.
- Close with `await using`; trust connection pooling — never write a manual pool.
- Never run concurrent (parallel) queries on the same connection.

## Stored procedure standards

Choose one error-signaling convention per project and keep it consistent. Two common ones:

1. **Exception-based** (default, most universal): validate, raise a clear error with `THROW`,
   let the application translate the exception into a user-facing response.
2. **Status result set**: the procedure never throws for business rules; it returns a status
   column set (e.g. `HasError`, `Message`) and the caller inspects it. Useful when many
   expected business outcomes must be distinguished without exception overhead.

Exception-based template:

```sql
CREATE OR ALTER PROCEDURE dbo.ProductPriceUpdate
    @Barcode  VARCHAR(20),
    @Price    DECIMAL(18,2),
    @UserId   INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @Barcode IS NULL OR LEN(@Barcode) = 0
        THROW 50001, 'Barcode cannot be empty.', 1;

    IF dbo.CanUpsertProduct(@UserId) = 0
        THROW 50002, 'You are not authorized for this operation.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.Product WHERE Barcode = @Barcode)
        THROW 50003, 'Product not found.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.Product
        SET Price = @Price,
            UpdatedAt = SYSUTCDATETIME(),
            UpdatedByUserId = @UserId
        WHERE Barcode = @Barcode;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END
```

Rules:

- `SET NOCOUNT ON` is the first line of every procedure. Add `SET XACT_ABORT ON` in any
  procedure with a transaction.
- Validate up front and fail early; do not build deep nested `IF` pyramids. Write guard-style
  checks that exit as soon as a rule fails.
- Authorization is a validation step too; extract it into a function (`dbo.CanUpsertX(@UserId)`)
  rather than inlining it in the procedure.
- `THROW` (or `RAISERROR` on older versions) carries the error; `CATCH` re-throws unexpected
  errors with a bare `THROW;` after rollback. Do not swallow errors in `CATCH` and report success.
- `CATCH` is for unexpected errors; business-rule violations are handled up front, not funneled
  into `CATCH`.
- Never leak internal detail (`ERROR_MESSAGE()`, table/column names) into a user-facing message;
  write it to a log table if needed.
- Keep transactions open the shortest possible time. No external calls (linked server, HTTP,
  long loops) inside a transaction.
- One procedure, one responsibility. No "do everything" procedures.
- Always qualify with the schema name (`dbo.X`) for plan-cache sharing.

### Reading on the .NET side

Map exceptions to a meaningful business response at the application boundary:

```csharp
public async Task UpdatePriceAsync(string barcode, decimal price, int userId, CancellationToken cancellationToken)
{
    var parameters = new DynamicParameters();
    parameters.Add("@Barcode", barcode, DbType.String, size: 20);
    parameters.Add("@Price", price, DbType.Decimal);
    parameters.Add("@UserId", userId, DbType.Int32);

    var command = new CommandDefinition(
        "dbo.ProductPriceUpdate",
        parameters,
        commandType: CommandType.StoredProcedure,
        commandTimeout: _options.CommandTimeoutSeconds,
        cancellationToken: cancellationToken);

    await using var connection = _connectionFactory.Create();
    await connection.ExecuteAsync(command);
}
```

- A `SqlException` with a known error number (50001-50003 above) is an **expected business
  failure**; the calling layer converts it into a meaningful user response, not a 500.
- If a procedure returns multiple result sets, read them with `QueryMultipleAsync`.

## Query performance

- **Think set-based.** `CURSOR` and `WHILE` loops are a last resort; prefer bulk `UPDATE ... FROM`,
  `MERGE`, or a table variable when the problem allows.
- **Write SARGable predicates.** Do not wrap the column in a function inside `WHERE`:
  - Wrong: `WHERE CONVERT(DATE, CreatedAt) = @Day`
  - Right: `WHERE CreatedAt >= @Day AND CreatedAt < DATEADD(DAY, 1, @Day)`
- No `SELECT *`; only the columns you need.
- `NOLOCK` / `READ UNCOMMITTED` is **not used by default** — it risks dirty reads and skipped or
  double-read rows. For a genuinely tolerant reporting scenario, ask the developer explicitly.
- If you suspect parameter sniffing, consider `OPTION (RECOMPILE)` or copying to a local variable;
  do not add it blindly.
- Page large result sets: `OFFSET ... FETCH NEXT ... ROWS ONLY`.
- Use Table-Valued Parameters for bulk input; no row-by-row procedure calls.

```csharp
var table = new DataTable();
table.Columns.Add("Barcode", typeof(string));
table.Columns.Add("Price", typeof(decimal));

parameters.Add("@Products", table.AsTableValuedParameter("dbo.ProductPriceType"));
```

## Indexing

- When a new `WHERE`/`JOIN`/`ORDER BY` pattern appears, check whether a suitable index exists.
- Multi-column index order: equality (`=`) first, then range (`>`, `<`), then sort.
- Add needed columns via `INCLUDE` to avoid key lookups.
- Do not add an index for every query; it raises write cost. When proposing an index, state the
  expected benefit and cost in one sentence.

## Locking and concurrency

- Operations touching the same rows always access them in the **same order** (reversed access
  order is the most common cause of deadlocks).
- For "check-then-insert" flows with a race risk, use a unique index plus error handling or an
  appropriate lock hint; do not do check-then-write with two separate queries.
- For an operation that hits a deadlock, consider a bounded number of application-side retries
  (error number 1205); never build an infinite loop.

## Naming

Follow whatever convention exists in the database. For new objects:

- Table: singular, `PascalCase` (`Product`, `StoreStock`).
- Stored procedure: `ObjectAction` (`ProductGet`, `ProductPriceUpdate`). Mirror any existing
  schema suffix convention rather than inventing a new one.
- Parameter: `@PascalCase`.
- Keywords in UPPERCASE, identifiers in their original casing.

## Bans

- SQL strings inside application code (even parameterized) when the project uses the SP/function style.
- Building SQL by string concatenation (`EXEC('SELECT ... ' + @x)`) — injection. If dynamic SQL is
  required, use `sp_executesql` + parameters, and wrap identifiers with `QUOTENAME`.
- Practice `SELECT *`, unnecessary `DISTINCT`, unnecessary `ORDER BY`.
- Long-running external calls inside a transaction.
- Swallowing an error in `CATCH` and returning success.
- Forgetting `WHERE` on a production `DELETE`/`UPDATE` — when generating a script, first show the
  affected row count with a `SELECT`.
