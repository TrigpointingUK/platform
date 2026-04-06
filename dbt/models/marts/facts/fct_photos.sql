with photos as (
    select * from {{ ref('stg_photos') }}
),

logs as (
    select log_id, user_id, trig_id from {{ ref('stg_logs') }}
)

select
    p.photo_id,
    p.log_id,
    l.user_id,
    l.trig_id,
    p.photo_type,
    p.is_public,
    p.created_at,
    p.created_at::date as created_date
from photos p
left join logs l on p.log_id = l.log_id
where not p.is_deleted
