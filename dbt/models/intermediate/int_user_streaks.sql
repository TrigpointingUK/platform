-- Gap-and-island analysis for consecutive periods of user activity.
-- Produces one row per streak per user per streak type.

with daily as (
    select
        user_id,
        log_date,
        (log_date - '1900-01-01'::date) as day_number
    from {{ ref('int_user_daily_activity') }}
    where log_date is not null
),

weekly as (
    select
        user_id,
        iso_year,
        iso_week,
        -- Compute a continuous week number for gap detection
        (iso_year * 53 + iso_week) as week_number
    from {{ ref('int_user_weekly_activity') }}
),

monthly as (
    select
        user_id,
        year,
        month,
        -- Compute a continuous month number for gap detection
        (year * 12 + month) as month_number
    from {{ ref('int_user_monthly_activity') }}
),

yearly as (
    select
        user_id,
        year
    from {{ ref('int_user_yearly_activity') }}
),

-- Daily streaks: consecutive calendar days with activity
daily_islands as (
    select
        user_id,
        log_date,
        day_number,
        day_number - row_number() over (
            partition by user_id order by day_number
        ) as island_id
    from daily
),

daily_streaks as (
    select
        user_id,
        'daily' as streak_type,
        to_char(min(log_date), 'YYYYMMDD')::int as streak_start,
        to_char(max(log_date), 'YYYYMMDD')::int as streak_end,
        count(*) as streak_length,
        max(day_number) as max_day_number
    from daily_islands
    group by user_id, island_id
),

-- Weekly streaks: consecutive ISO weeks with activity
weekly_islands as (
    select
        user_id,
        iso_year,
        iso_week,
        week_number,
        week_number - row_number() over (
            partition by user_id order by week_number
        ) as island_id
    from weekly
),

weekly_streaks as (
    select
        user_id,
        'weekly' as streak_type,
        min(iso_year * 100 + iso_week) as streak_start,
        max(iso_year * 100 + iso_week) as streak_end,
        count(*) as streak_length,
        max(week_number) as max_week_number
    from weekly_islands
    group by user_id, island_id
),

-- Monthly streaks: consecutive months with activity
monthly_islands as (
    select
        user_id,
        year,
        month,
        month_number,
        month_number - row_number() over (
            partition by user_id order by month_number
        ) as island_id
    from monthly
),

monthly_streaks as (
    select
        user_id,
        'monthly' as streak_type,
        min(year * 100 + month) as streak_start,
        max(year * 100 + month) as streak_end,
        count(*) as streak_length,
        max(month_number) as max_month_number
    from monthly_islands
    group by user_id, island_id
),

-- Yearly streaks: consecutive years with activity
yearly_islands as (
    select
        user_id,
        year,
        year - row_number() over (
            partition by user_id order by year
        ) as island_id
    from yearly
),

yearly_streaks as (
    select
        user_id,
        'yearly' as streak_type,
        min(year) as streak_start,
        max(year) as streak_end,
        count(*) as streak_length,
        max(year) as max_year
    from yearly_islands
    group by user_id, island_id
),

-- Determine "current" boundaries
current_boundaries as (
    select
        (current_date - '1900-01-01'::date) as current_day_number,
        extract(isoyear from current_date)::int * 53
            + extract(week from current_date)::int as current_week_number,
        extract(year from current_date)::int * 12
            + extract(month from current_date)::int as current_month_number,
        extract(year from current_date)::int as current_year
    from (select 1) as dummy
)

select
    user_id,
    streak_type,
    streak_start,
    streak_end,
    streak_length,
    -- A daily streak is current if its last day is yesterday or today
    max_day_number >= (select current_day_number - 1 from current_boundaries) as is_current
from daily_streaks

union all

select
    user_id,
    streak_type,
    streak_start,
    streak_end,
    streak_length,
    -- A weekly streak is current if its last week is within 1 week of now
    max_week_number >= (select current_week_number - 1 from current_boundaries) as is_current
from weekly_streaks

union all

select
    user_id,
    streak_type,
    streak_start,
    streak_end,
    streak_length,
    -- A monthly streak is current if its last month is within 1 month of now
    max_month_number >= (select current_month_number - 1 from current_boundaries) as is_current
from monthly_streaks

union all

select
    user_id,
    streak_type,
    streak_start,
    streak_end,
    streak_length,
    -- A yearly streak is current if it includes the current or previous year
    max_year >= (select current_year - 1 from current_boundaries) as is_current
from yearly_streaks
