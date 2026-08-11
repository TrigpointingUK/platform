# Serving photos through CloudFlare and CloudFront

## Why

Photos were handed out as direct S3 URLs (`https://trigpointinguk-photos.s3.amazonaws.com/451/P451921_r1.jpg`)
and the buckets are anonymously readable. CloudFlare never saw that traffic, so every
image view by every browser and every bot was a billable S3 `GetObject` plus egress.

S3 egress grew from 65.6 GB in January 2026 to 176.7 GB in July, tracking ~300 GB in
August. The cost only becomes visible partway through each month because AWS gives
100 GB/month of free internet egress account-wide, resetting on the 1st — that free
tier boundary, not a scraper, is what produces the on/off sawtooth in Cost Explorer.

## Request path

```
browser -> CloudFlare (proxied, cache rules) -> CloudFront -> S3
```

CloudFront is in the path because S3 resolves the bucket from the `Host` header.
CloudFlare would forward `Host: photos.trigpointing.uk`, S3 would look for a bucket
of that name and return `NoSuchBucket`. Rewriting the header at the CloudFlare edge
requires Host Header Override, which is a **Pro+ entitlement** — both zones are on
Free, and the API rejects it with `not entitled to use the HostHeader override`.
CloudFront sets the origin `Host` itself, so it sidesteps the problem.

It is also cheaper than fronting S3 directly. Data transfer from S3 to CloudFront is
free, and CloudFront's perpetual free tier (1 TB egress, 10M requests/month) is
roughly 3x current photo traffic. CloudFlare absorbs most requests before CloudFront
sees them.

| Resource | File |
|---|---|
| ACM certs (us-east-1) + DNS validation records | `terraform/common/photos-cdn.tf` |
| CloudFront distributions, one per environment | `terraform/common/photos-cdn.tf` |
| `photos.*` proxied CNAMEs pointing at CloudFront | `terraform/common/cloudflare.tf` |
| Cache rule, 30d edge TTL / 7d browser TTL | `terraform/{staging,production}/cache_rules.tf` |

Buckets differ per environment: production uses `trigpointinguk-photos`
(`server.id = 1`), staging uses `trigpointinguk-test` (`server.id = 3`).

ACM certificates for CloudFront must live in **us-east-1** regardless of where the
origin is, hence the `aws.us_east_1` provider alias in `terraform/common/main.tf`.
The DNS validation records must be **unproxied** — CloudFlare's proxy would mask the
CNAME and validation would never complete.

## Cutover

Applying the Terraform moves no traffic on its own. The API builds `photo_url` from
`server.url` (see `api/api/v1/endpoints/photos.py` and `api/services/archive_service.py`),
which is a database value. The switch is a DB update, and it must come *after* the
Terraform apply is verified.

1. Apply `terraform/common`, then `terraform/production`. Expect the first apply to
   sit for several minutes on ACM validation and CloudFront distribution deployment.

2. Verify the new hostname serves bytes before changing anything:

   ```bash
   curl -sI https://photos.trigpointing.uk/000/I00001.jpg | head -20
   ```

   Expect `HTTP/2 200`, `content-type: image/jpeg`, and both a `cf-cache-status`
   header (CloudFlare) and an `x-cache` header (CloudFront). Repeat the request —
   the second should show `cf-cache-status: HIT`. If you get `NoSuchBucket`, the
   DNS record is still pointing at S3 rather than CloudFront.

3. Run the `server.url` migration, with `make postgres-tunnel` running (see the
   `db-access` skill). Revision `c9d0e1f2a3b4`, "point photo server urls at the CDN":

   ```bash
   make migrate-status ENV=staging     # confirm c9d0e1f2a3b4 is pending
   make migrate-staging
   make migrate-production             # requires typing 'production' to confirm
   ```

   The migration rewrites only the hostname inside `server.url`, so it does not
   care whether the stored value ends in a trailing slash, and it matches on the
   bucket hostname rather than on `server.id` — which makes it correct in both
   databases without needing to know which one it is running against. It logs the
   full `server` table before and after, plus a row count per statement, so the
   `make migrate-*` output is the audit trail.

4. Confirm the API now emits the new host:

   ```bash
   curl -s "https://api.trigpointing.uk/v1/photos?limit=1" | grep -o '"photo_url":"[^"]*"'
   ```

## Rollback

```bash
make downgrade-staging    # and the production equivalent
```

The downgrade is the exact inverse hostname swap and has been verified byte-for-byte
against a local Postgres. The S3 buckets remain publicly readable and were never
locked down to the CDN, so rolling back restores fully working direct-S3 URLs with
no infrastructure change needed. The CDN can be left standing while rolled back —
it simply stops receiving traffic.

## Terraform provider pin

`terraform/common` pins `cloudflare/cloudflare` to exactly `5.12.0`. Version 5.23.0
cannot read the saved state of the `cloudflare_list_item` redirect resources and
fails every plan with `UpgradeResourceState ... AttributeName("redirect"): invalid
JSON`. Because `.terraform.lock.hcl` is gitignored, a loose `~> 5.0` constraint means
any fresh clone or `terraform init -upgrade` picks up the break.

`terraform/staging` and `terraform/production` still carry `~> 5.0` and currently
resolve to 5.12.0 via their local lock files. They have no `cloudflare_list_item`
resources so they are not affected today, but they carry the same latent hazard.

## Not done here

- **Buckets remain publicly readable**, so the CDN can still be bypassed by anything
  holding a direct S3 URL. This was deliberate: direct S3 URLs are likely embedded in
  old forum posts, wiki pages and third-party sites, and breaking them is not worth
  the risk without evidence. The S3 access logs (`terraform/common/s3-access-logs.tf`)
  will show how much traffic bypasses the CDN. Locking the buckets to CloudFront-only
  via an origin access control is the follow-up once that is known.
- **Avatars** are still hardcoded to `trigpointinguk-avatars.s3.amazonaws.com` in
  `web/src/components/logs/LogCard.tsx` and `web/src/routes/UserProfile.tsx`. The
  bucket is ~1 MB total, so this is not a cost issue, but it is the same pattern.
- **`trigpointinguk-maps`** is fully public and holds multi-GB offline map packs
  (`satellite-0-14.tar.gz` is 2.48 GB) advertised in a public `map_downloads.yaml`.
  A handful of downloads a day accounts for the August step-change. Access logging
  is now enabled on it, so the next fortnight's logs will confirm or rule this out.
- **`trigpointinguk-maps/OS_API_KEY.txt`** is world-readable. Left for separate
  investigation.
