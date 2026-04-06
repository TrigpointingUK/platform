with date_dim as (
    select * from {{ ref('dim_date') }}
),

logs as (
    select * from {{ ref('fct_logs') }}
),

photos as (
    select * from {{ ref('fct_photos') }}
),

users as (
    select * from {{ ref('dim_user') }}
),

votes as (
    select * from {{ ref('fct_photo_votes') }}
),

log_stats as (
    select
        log_date as date_key,
        count(*) as new_logs,
        count(distinct user_id) as active_users
    from logs
    group by log_date
),

photo_stats as (
    select
        created_date as date_key,
        count(*) as new_photos
    from photos
    group by created_date
),

user_stats as (
    select
        member_since_date as date_key,
        count(*) as new_users
    from users
    group by member_since_date
),

vote_stats as (
    select
        voted_at::date as date_key,
        count(*) as new_photo_votes
    from votes
    group by voted_at::date
)

select
    d.date_key,
    d.year,
    d.month,
    d.day_of_week_name,
    d.is_weekend,
    d.year_month,
    coalesce(ls.new_logs, 0) as new_logs,
    coalesce(ls.active_users, 0) as active_users,
    coalesce(ps.new_photos, 0) as new_photos,
    coalesce(us.new_users, 0) as new_users,
    coalesce(vs.new_photo_votes, 0) as new_photo_votes
from date_dim d
left join log_stats ls on d.date_key = ls.date_key
left join photo_stats ps on d.date_key = ps.date_key
left join user_stats us on d.date_key = us.date_key
left join vote_stats vs on d.date_key = vs.date_key
where d.date_key <= current_date
    and (ls.new_logs is not null
        or ps.new_photos is not null
        or us.new_users is not null
        or vs.new_photo_votes is not null)
