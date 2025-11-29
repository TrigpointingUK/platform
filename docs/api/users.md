# Users Directory API

The `/v1/users/browse` endpoint powers the new trigpointing.me `/users` page. It
returns a cursor-based listing of public members with pre-computed activity
metrics so the frontend can implement infinite scrolling without heavy client
side aggregation.

## `GET /v1/users/browse`

| Query          | Type     | Description                                                                 |
| -------------- | -------- | --------------------------------------------------------------------------- |
| `q`            | string   | Optional substring filter applied to usernames (case-insensitive).          |
| `limit`        | integer  | Page size between 5 and 100. Defaults to 40, matching the frontend request. |
| `sort`         | enum     | `trigs` (default), `photos`, `joined`, or `name`.                           |
| `direction`    | enum     | `desc` (default) or `asc`.                                                  |
| `cursor`       | string   | Opaque token issued by the previous response to fetch the next slice.       |

### Response

```json
{
  "items": [
    {
      "id": 42,
      "name": "alice",
      "member_since": "2016-05-01",
      "stats": {
        "total_logs": 512,
        "total_trigs_logged": 211,
        "total_photos": 87
      },
      "profile_path": "/profile/42"
    }
  ],
  "next_cursor": "eyJzb3J0X3ZhbHVlIjoiMjAxNi0wNS0wMSIsInVzZXJfaWQiOjQyfQ",
  "total": 8123,
  "applied_filters": {
    "query": null,
    "sort": "trigs",
    "direction": "desc",
    "limit": 40
  }
}
```

Totals are calculated directly in SQL using grouped subqueries:

- `total_logs`: raw visit count (all logs for the member)
- `total_trigs_logged`: distinct trigpoints visited
- `total_photos`: uploaded photos that have not been deleted

The cursor compares the requested sort field and the row id to ensure stable
ordering even when underlying data changes. Clients should pass the `next_cursor`
value verbatim to request the following slice.

Because the endpoint aggregates everything server-side it remains efficient even
when searching or resorting; the frontend only needs to supply the filters and
render the returned subset. Additional metrics can be added later by extending
the SQL subqueries and including new sort aliases.


