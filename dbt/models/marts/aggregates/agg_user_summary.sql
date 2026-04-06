with users as (
    select * from {{ ref('dim_user') }}
),

daily as (
    select * from {{ ref('int_user_daily_activity') }}
),

photos as (
    select * from {{ ref('fct_photos') }}
),

votes as (
    select * from {{ ref('fct_photo_votes') }}
),

streaks as (
    select * from {{ ref('int_user_streaks') }}
),

log_totals as (
    select
        user_id,
        sum(logs_count) as total_logs,
        min(log_date) as first_log_date,
        max(log_date) as last_log_date,
        (current_date - max(log_date))::int as days_since_last_log
    from daily
    group by user_id
),

trig_counts as (
    select
        user_id,
        count(distinct trig_id) as total_distinct_trigs
    from {{ ref('fct_logs') }}
    group by user_id
),

photo_counts as (
    select
        user_id,
        count(*) as total_photos
    from photos
    group by user_id
),

vote_counts as (
    select
        user_id,
        count(*) as total_photo_votes_cast
    from votes
    group by user_id
),

weekly_streak_summary as (
    select
        user_id,
        max(case when is_current then streak_length else 0 end) as current_weekly_streak,
        max(streak_length) as longest_weekly_streak
    from streaks
    where streak_type = 'weekly'
    group by user_id
),

monthly_streak_summary as (
    select
        user_id,
        max(case when is_current then streak_length else 0 end) as current_monthly_streak,
        max(streak_length) as longest_monthly_streak
    from streaks
    where streak_type = 'monthly'
    group by user_id
),

daily_streak_summary as (
    select
        user_id,
        max(case when is_current then streak_length else 0 end) as current_daily_streak,
        max(streak_length) as longest_daily_streak
    from streaks
    where streak_type = 'daily'
    group by user_id
)

select
    u.user_id,
    u.username,
    u.member_since_date,
    coalesce(lt.total_logs, 0) as total_logs,
    coalesce(tc.total_distinct_trigs, 0) as total_distinct_trigs,
    coalesce(pc.total_photos, 0) as total_photos,
    coalesce(vc.total_photo_votes_cast, 0) as total_photo_votes_cast,
    lt.first_log_date,
    lt.last_log_date,
    lt.days_since_last_log,
    coalesce(ws.current_weekly_streak, 0) as current_weekly_streak,
    coalesce(ws.longest_weekly_streak, 0) as longest_weekly_streak,
    coalesce(ms.current_monthly_streak, 0) as current_monthly_streak,
    coalesce(ms.longest_monthly_streak, 0) as longest_monthly_streak,
    coalesce(ds.current_daily_streak, 0) as current_daily_streak,
    coalesce(ds.longest_daily_streak, 0) as longest_daily_streak
from users u
left join log_totals lt on u.user_id = lt.user_id
left join trig_counts tc on u.user_id = tc.user_id
left join photo_counts pc on u.user_id = pc.user_id
left join vote_counts vc on u.user_id = vc.user_id
left join weekly_streak_summary ws on u.user_id = ws.user_id
left join monthly_streak_summary ms on u.user_id = ms.user_id
left join daily_streak_summary ds on u.user_id = ds.user_id
where lt.total_logs > 0
