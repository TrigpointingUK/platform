-- Unpivots all medal-relevant metrics into a long-format (user_id, metric_key, metric_value)
-- table. Each metric_key corresponds to exactly one medal_definitions.metric_key.

with user_summary as (
    select * from {{ ref('agg_user_summary') }}
),

collection_progress as (
    select * from {{ ref('int_user_collection_progress') }}
),

logs as (
    select * from {{ ref('fct_logs') }}
),

date_dim as (
    select * from {{ ref('dim_date') }}
),

photos as (
    select * from {{ ref('fct_photos') }}
),

votes as (
    select * from {{ ref('fct_photo_votes') }}
),

daily_activity as (
    select * from {{ ref('int_user_daily_activity') }}
),

streaks as (
    select * from {{ ref('int_user_streaks') }}
),

-- Metrics from agg_user_summary (directly available columns)
summary_metrics as (
    select
        user_id,
        unnest(array[
            'total_logs',
            'total_distinct_trigs',
            'total_photos',
            'total_photo_votes_cast',
            'longest_daily_streak',
            'longest_weekly_streak',
            'longest_monthly_streak'
        ]) as metric_key,
        unnest(array[
            total_logs,
            total_distinct_trigs,
            total_photos,
            total_photo_votes_cast,
            longest_daily_streak,
            longest_weekly_streak,
            longest_monthly_streak
        ]) as metric_value
    from user_summary
),

-- Metrics from int_user_collection_progress (directly available columns)
collection_metrics as (
    select
        user_id,
        unnest(array[
            'distinct_days_of_week',
            'distinct_months_of_year',
            'distinct_first_letters',
            'distinct_counties',
            'distinct_trig_types',
            'distinct_trig_categories',
            'distinct_condition_names'
        ]) as metric_key,
        unnest(array[
            distinct_days_of_week,
            distinct_months_of_year,
            distinct_first_letters,
            distinct_counties,
            distinct_trig_types,
            distinct_trig_categories,
            distinct_condition_names
        ]) as metric_value
    from collection_progress
),

-- Area-type metrics extracted from the jsonb column
area_metrics as (
    select
        user_id,
        unnest(array[
            'distinct_countries',
            'distinct_os_explorer_maps',
            'distinct_os_landranger_maps',
            'distinct_historic_counties'
        ]) as metric_key,
        unnest(array[
            coalesce((distinct_areas_by_type->>'country')::int, 0),
            coalesce((distinct_areas_by_type->>'os_explorer')::int, 0),
            coalesce((distinct_areas_by_type->>'os_landranger')::int, 0),
            coalesce((distinct_areas_by_type->>'historic_county')::int, 0)
        ]) as metric_value
    from collection_progress
),

-- Longest yearly streak (not in agg_user_summary)
yearly_streak_metric as (
    select
        user_id,
        'longest_yearly_streak' as metric_key,
        max(streak_length) as metric_value
    from streaks
    where streak_type = 'yearly'
    group by user_id
),

-- Special calendar event: Christmas Day logging (count of distinct years)
christmas_metric as (
    select
        l.user_id,
        'christmas_day_count' as metric_key,
        count(distinct dd.year)::int as metric_value
    from logs l
    inner join date_dim dd on l.log_date = dd.date_key
    where dd.month = 12 and dd.day_of_month = 25
    group by l.user_id
),

-- Special calendar event: New Year's Day logging
new_year_metric as (
    select
        l.user_id,
        'new_years_day_count' as metric_key,
        count(distinct dd.year)::int as metric_value
    from logs l
    inner join date_dim dd on l.log_date = dd.date_key
    where dd.month = 1 and dd.day_of_month = 1
    group by l.user_id
),

-- Special calendar event: Leap Day logging
leap_day_metric as (
    select
        l.user_id,
        'leap_day_count' as metric_key,
        count(distinct dd.year)::int as metric_value
    from logs l
    inner join date_dim dd on l.log_date = dd.date_key
    where dd.month = 2 and dd.day_of_month = 29
    group by l.user_id
),

-- Logs with comments
comment_metric as (
    select
        user_id,
        'total_logs_with_comments' as metric_key,
        count(*)::int as metric_value
    from logs
    where has_comment
    group by user_id
),

-- Years with activity
years_active_metric as (
    select
        l.user_id,
        'total_years_active' as metric_key,
        count(distinct dd.year)::int as metric_value
    from logs l
    inner join date_dim dd on l.log_date = dd.date_key
    group by l.user_id
),

-- Photo votes received (votes on the user's own photos)
votes_received_metric as (
    select
        p.user_id,
        'total_photo_votes_received' as metric_key,
        count(*)::int as metric_value
    from votes v
    inner join photos p on v.photo_id = p.photo_id
    where v.user_id <> p.user_id
    group by p.user_id
),

-- Weekend logs (Saturday or Sunday)
weekend_metric as (
    select
        l.user_id,
        'total_weekend_logs' as metric_key,
        count(*)::int as metric_value
    from logs l
    inner join date_dim dd on l.log_date = dd.date_key
    where dd.is_weekend
    group by l.user_id
),

-- Multi-trig days (days with 2+ distinct trigs logged)
multi_trig_metric as (
    select
        user_id,
        'total_multi_trig_days' as metric_key,
        count(*)::int as metric_value
    from daily_activity
    where distinct_trigs >= 2
    group by user_id
),

-- High score logs (score >= 8)
high_score_metric as (
    select
        user_id,
        'total_high_score_logs' as metric_key,
        count(*)::int as metric_value
    from logs
    where score >= 8
    group by user_id
),

-- Distinct decades with activity
decade_metric as (
    select
        l.user_id,
        'distinct_decades_active' as metric_key,
        count(distinct (dd.year / 10))::int as metric_value
    from logs l
    inner join date_dim dd on l.log_date = dd.date_key
    group by l.user_id
)

select user_id, metric_key, metric_value from summary_metrics
union all
select user_id, metric_key, metric_value from collection_metrics
union all
select user_id, metric_key, metric_value from area_metrics
union all
select user_id, metric_key, metric_value from yearly_streak_metric
union all
select user_id, metric_key, metric_value from christmas_metric
union all
select user_id, metric_key, metric_value from new_year_metric
union all
select user_id, metric_key, metric_value from leap_day_metric
union all
select user_id, metric_key, metric_value from comment_metric
union all
select user_id, metric_key, metric_value from years_active_metric
union all
select user_id, metric_key, metric_value from votes_received_metric
union all
select user_id, metric_key, metric_value from weekend_metric
union all
select user_id, metric_key, metric_value from multi_trig_metric
union all
select user_id, metric_key, metric_value from high_score_metric
union all
select user_id, metric_key, metric_value from decade_metric
