---
name: postgresql
description: >
  Use when working with PostgreSQL: writing PL/pgSQL functions and procedures, schema
  design, upserts, indexing, concurrency and locking, JSONB, pagination, and performance.
  Covers calling functions/procedures from .NET with Npgsql + Dapper, parameter typing,
  and connection and timeout management on the .NET side.
---

# PostgreSQL Standards

## Data access stance

Keep query logic in one deliberate place. The default here is a PL/pgSQL function or procedure
that the application calls by name, hidden behind a repository interface. An ORM is a valid
project choice; if the project uses one, follow its conventions rather than mixing in raw SQL.

Function vs procedure:
- **FUNCTION**: read operations that return a value or a result set, and write operations that
  inherit the transaction from the caller.
- **PROCEDURE**: multi-step writes that need to manage `COMMIT`/`ROLLBACK` internally.

## Calling with Npgsql + Dapper

Read (function returning a result set):

```csharp
public async Task<IReadOnlyList<ProductDto>> ListAsync(int storeId, CancellationToken cancellationToken)
{
    var parameters = new DynamicParameters();
    parameters.Add("p_store_id", storeId, DbType.Int32);

    var command = new CommandDefinition(
        "SELECT * FROM app.product_list(@p_store_id)",
        parameters,
        commandTimeout: _options.CommandTimeoutSeconds,
        cancellationToken: cancellationToken);

    await using var connection = _connectionFactory.Create();
    var result = await connection.QueryAsync<ProductDto>(command);
    return result.AsList();
}
```

Procedure call:

```csharp
var command = new CommandDefinition(
    "product_price_update",
    parameters,
    commandType: CommandType.StoredProcedure,
    cancellationToken: cancellationToken);

await connection.ExecuteAsync(command);
```

- In Npgsql, `CommandType.StoredProcedure` emits `CALL` and **cannot be used for functions that
  return a result set** — those are called with `SELECT * FROM fn(...)`. Do not confuse the two.
- Parameter names must exactly match the function signature (keep the `p_` prefix convention).
- For ambiguously typed parameters (`text` vs `varchar`, `jsonb`, arrays) specify the type
  explicitly; otherwise you get `function ... does not exist`. Prefer `text` over `varchar(n)`
  for large text columns.
- Always flow `CancellationToken` through `CommandDefinition`.
- Connection pooling is handled by Npgsql; open connections short-lived and release them.

## Function standards

```sql
CREATE OR REPLACE FUNCTION app.product_price_update(
    p_barcode text,
    p_price   numeric(18,2),
    p_user    text
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_affected integer;
BEGIN
    IF p_barcode IS NULL OR length(p_barcode) = 0 THEN
        RAISE EXCEPTION 'Barcode cannot be empty.' USING ERRCODE = 'P0001';
    END IF;

    UPDATE app.product
    SET price = p_price,
        updated_at = now(),
        updated_by = p_user
    WHERE barcode = p_barcode;

    GET DIAGNOSTICS v_affected = ROW_COUNT;

    IF v_affected = 0 THEN
        RAISE EXCEPTION 'Product not found. Barcode: %', p_barcode USING ERRCODE = 'P0002';
    END IF;

    RETURN true;
END;
$$;
```

- Use `CREATE OR REPLACE`; if the signature changes, note that a `DROP FUNCTION` is required first
  (PostgreSQL overloads, so the old signature silently survives — a common mistake).
- Raise errors with `RAISE EXCEPTION`, a clear message, and a meaningful `ERRCODE`.
- Do not use `SECURITY DEFINER` unless required; if you do, pin `SET search_path`.
- Mark volatility correctly: read-only functions `STABLE`, pure computations `IMMUTABLE`, writers
  the default `VOLATILE`.
- One function, one responsibility.

## Upsert

Prefer `INSERT ... ON CONFLICT`; "SELECT then INSERT" creates a race condition.

```sql
INSERT INTO app.product (barcode, price, updated_at)
VALUES (p_barcode, p_price, now())
ON CONFLICT (barcode)
DO UPDATE SET
    price = EXCLUDED.price,
    updated_at = now()
WHERE app.product.price IS DISTINCT FROM EXCLUDED.price;
```

- `ON CONFLICT` requires a unique constraint/index on the target columns.
- Add an `IS DISTINCT FROM` change check to avoid pointless writes.
- Do bulk upserts with a single `INSERT ... SELECT unnest(...)`; no row loop.

## Concurrency and locking

- Prevent concurrent entry to the same resource with an **advisory lock**:

```sql
IF NOT pg_try_advisory_xact_lock(hashtext('product_sync')) THEN
    RAISE EXCEPTION 'Operation already running.' USING ERRCODE = '55P03';
END IF;
```

  `pg_try_advisory_xact_lock` is released automatically at transaction end; `pg_advisory_lock`
  needs manual release and leaks the lock if forgotten — default to the xact version.
- For row locks use `SELECT ... FOR UPDATE`; use `NOWAIT` to fail fast or `SKIP LOCKED` for the
  queue-processing pattern.
- Avoid long transactions; they block `VACUUM` and cause table bloat.
- Access resources in a consistent order to avoid deadlocks.

## Performance

- Write SARGable predicates: `WHERE created_at >= @day AND created_at < @day + interval '1 day'`;
  do not wrap the column in a function. If a function is unavoidable, create an **expression index**.
- No `SELECT *`; only the columns you need.
- Inspect plans with `EXPLAIN (ANALYZE, BUFFERS)`.
- Index types: default `btree`; `GIN` for search inside JSONB and arrays; `GIN` + `to_tsvector`
  for full-text; `pg_trgm` for similarity.
- Build indexes on large tables with `CREATE INDEX CONCURRENTLY` (does not lock the table; cannot
  run inside a transaction).
- For deep pagination use keyset pagination (`WHERE id > @lastId ORDER BY id LIMIT n`) instead of
  `LIMIT ... OFFSET`.
- `now()` returns the transaction start time; use `clock_timestamp()` for the real instant.

## Schema and types

- Naming is `snake_case` (tables, columns, functions, parameters).
- Time columns are `timestamptz` (UTC). Do not use `timestamp` (without time zone).
- Money/rates are `numeric`, never `float`/`double`.
- `text` is enough for strings; if a length limit is a business rule, use `varchar(n)` or `CHECK`.
- Semi-structured data is `jsonb` (not `json`). Extract queried fields into separate columns when possible.
- Every table has a primary key; if there is no natural key, use `bigint generated always as identity`.
- Index foreign-key columns (PostgreSQL does not do this automatically — a commonly missed point).

## Bans

- SQL strings inside application code (when the project uses the function/procedure style).
- Dynamic SQL by string concatenation — if required, use `format()` + `%I` / `%L` and
  `EXECUTE ... USING` for parameter passing.
- Using `pg_advisory_lock` and forgetting to release it.
- Doing `CREATE OR REPLACE` on a changed signature without `DROP`, leaving a stale overload behind.
- Long-running transactions with external service calls inside them.
- `UPDATE`/`DELETE` without `WHERE`; when generating a script, first show the affected row count
  with a `SELECT`.
