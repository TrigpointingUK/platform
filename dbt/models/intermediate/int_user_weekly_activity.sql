with daily as (
    select * from {{ ref('int_user_daily_activity') }}
),

date_dim as (
    select * from {{ ref('dim_date') }}
)

select
    d.user_id,
    dd.iso_year,
    dd.iso_week,
    min(d.log_date) as week_start_date,
    sum(d.logs_count) as logs_count,
    sum(d.distinct_trigs) as distinct_trigs,
    count(*) as active_days_in_week
from daily d
inner join date_dim dd on d.log_date = dd.date_key
group by d.user_id, dd.iso_year, dd.iso_week
