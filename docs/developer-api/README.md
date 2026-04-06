# TrigpointingUK Developer API

The TrigpointingUK Developer API provides authenticated GraphQL access to trigpointing data, enabling third-party developers to build extensions and tools for the community.

## Quick Start

1. **Request access**: Contact Ian to receive an Auth0 client ID for your application.
2. **Authenticate users**: Use the Auth0 SDK to log users in with their TrigpointingUK credentials.
3. **Query the API**: Send GraphQL queries to `https://graphql.trigpointing.uk/v1/graphql` with the JWT in the `Authorization` header.

## Authentication

The API uses Auth0 JWT tokens for authentication. Your application authenticates TrigpointingUK users via Auth0, and the resulting JWT grants read access to the data.

### Auth0 Configuration

| Setting | Production | Staging |
|---------|-----------|---------|
| Domain | `auth.trigpointing.uk` | `auth.trigpointing.me` |
| Audience | `https://graphql.trigpointing.uk/` | `https://graphql.trigpointing.me/` |
| GraphQL Endpoint | `https://graphql.trigpointing.uk/v1/graphql` | `https://graphql.trigpointing.me/v1/graphql` |

### Example: Requesting a Token (JavaScript)

```javascript
import { Auth0Client } from '@auth0/auth0-spa-js';

const auth0 = new Auth0Client({
  domain: 'auth.trigpointing.uk',
  clientId: 'YOUR_CLIENT_ID',
  authorizationParams: {
    audience: 'https://graphql.trigpointing.uk/',
    scope: 'openid profile email data:read',
  },
});

// After login, get the access token
const token = await auth0.getTokenSilently();
```

### Example: Making a GraphQL Request

```javascript
const response = await fetch('https://graphql.trigpointing.uk/v1/graphql', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({
    query: `
      query {
        dim_trig(limit: 10) {
          trig_id
          trig_name
          type_name
          county
        }
      }
    `,
  }),
});

const data = await response.json();
```

## Available Tables

The API exposes tables from the analytics schema, organised into layers:

### Staging Tables (stg_*)

Normalised base data. These mirror the operational database structure with PII removed and columns renamed for clarity. Use these if you want full control over your own joins.

| Table | Description |
|-------|------------|
| `stg_trigs` | Trigonometric stations (active only, status < 90) |
| `stg_users` | Registered users (no email, password, or personal data) |
| `stg_logs` | Visit/log entries with dates, scores, and conditions |
| `stg_photos` | Photos attached to log entries |
| `stg_photo_votes` | User votes/scores on photos |
| `stg_areas` | Administrative/geographic areas with their type taxonomy |
| `stg_trig_areas` | Bridge table: which trigs are in which areas |
| `stg_trig_types` | Trig physical types joined with their parent categories |
| `stg_conditions` | Condition code lookup (Good, Damaged, Destroyed, etc.) |

### Dimension Tables (dim_*)

Pre-joined, beginner-friendly dimensions. No codes, just human-readable names. Use these for simpler queries.

| Table | Description |
|-------|------------|
| `dim_trig` | Fully denormalised trigs with type, category, condition names, and county |
| `dim_user` | Users with derived tenure and membership year |
| `dim_area` | Areas with their type names |
| `dim_trig_area` | Bridge table mapping trigs to areas with area type names |
| `dim_date` | Calendar dates with day-of-week, month, weekend flags, etc. |

### Fact Tables (fct_*)

Core activity tables with resolved names (no codes).

| Table | Description |
|-------|------------|
| `fct_logs` | One row per visit. Condition names resolved. Links to dim_trig, dim_user, dim_date. |
| `fct_photos` | One row per photo (excludes deleted). Links to user and trig. |
| `fct_photo_votes` | One row per photo vote. |

### Aggregate Tables (agg_*)

Pre-computed summaries for common queries.

| Table | Description |
|-------|------------|
| `agg_user_summary` | Per-user lifetime stats: total logs, photos, streaks, days since last log |
| `agg_trig_summary` | Per-trig engagement: total logs, photos, scores, Bayesian average |
| `agg_site_daily` | Daily site KPIs: new logs, photos, users, active users |

## Example Queries

### User Leaderboard (Top 10 by Logs)

```graphql
query {
  agg_user_summary(
    order_by: { total_logs: desc }
    limit: 10
  ) {
    user {
      username
    }
    total_logs
    total_distinct_trigs
    total_photos
    longest_weekly_streak
  }
}
```

### Trig Details with Recent Logs

```graphql
query TrigDetails($trigId: Int!) {
  dim_trig_by_pk(trig_id: $trigId) {
    trig_name
    waypoint
    type_name
    category_name
    condition_name
    county
    wgs_lat
    wgs_long
  }
  fct_logs(
    where: { trig_id: { _eq: $trigId } }
    order_by: { log_date: desc }
    limit: 20
  ) {
    user {
      username
    }
    log_date
    condition_name
    score
  }
}
```

### County Coverage for a User

```graphql
query CountyCoverage($userId: Int!) {
  fct_logs(
    where: { user_id: { _eq: $userId } }
    distinct_on: [trig_id]
  ) {
    trig {
      county
    }
  }
}
```

### Daily Activity Trend

```graphql
query DailyActivity {
  agg_site_daily(
    order_by: { date_key: desc }
    limit: 30
  ) {
    date_key
    new_logs
    active_users
    new_photos
  }
}
```

## Relationships

Tables are linked with relationships, allowing nested queries:

- `fct_logs` -> `dim_trig` (via trig_id), `dim_user` (via user_id), `dim_date` (via log_date)
- `fct_photos` -> `dim_trig`, `dim_user`
- `agg_user_summary` -> `dim_user`
- `agg_trig_summary` -> `dim_trig`
- `agg_site_daily` -> `dim_date`
- `stg_logs` -> `stg_trigs`, `stg_users`
- `stg_photos` -> `stg_logs`
- `stg_trig_areas` -> `stg_trigs`, `stg_areas`
- `dim_trig_area` -> `dim_trig`, `dim_area`

## Rate Limits and Fair Use

- The API is provided for community projects that benefit TrigpointingUK users.
- Please cache results where practical rather than querying on every page load.
- Avoid unbounded queries (always use `limit`).
- If you need write access (creating logs, updating profiles), use the core REST API at `https://api.trigpointing.uk`.

## Schema Explorer

Visit `https://graphql.trigpointing.uk` in your browser to access the Hasura Console, which provides an interactive GraphQL explorer with full schema documentation, auto-complete, and query testing.

## Changelog

| Date | Change |
|------|--------|
| 2026-04 | Initial release: stg, dim, fct, agg tables exposed via GraphQL |
