with logs as (
    select * from {{ ref('stg_logs') }}
),

conditions as (
    select * from {{ ref('stg_conditions') }}
)

select
    l.log_id,
    l.user_id,
    l.trig_id,
    l.log_date,
    l.log_time,
    c.condition_name,
    l.score,
    l.log_source,
    l.fb_number,
    l.comment is not null and trim(l.comment) <> '' as has_comment,
    l.upd_timestamp
from logs l
left join conditions c on l.condition_code = c.condition_code
