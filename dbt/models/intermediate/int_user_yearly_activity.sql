with monthly as (
    select * from {{ ref('int_user_monthly_activity') }}
),

weekly as (
    select * from {{ ref('int_user_weekly_activity') }}
)

select
    m.user_id,
    m.year,
    sum(m.logs_count) as logs_count,
    sum(m.distinct_trigs) as distinct_trigs,
    count(distinct m.month) as active_months,
    count(distinct (w.iso_year, w.iso_week)) as active_weeks,
    sum(m.active_days_in_month) as active_days
from monthly m
left join weekly w on m.user_id = w.user_id and m.year = w.iso_year
group by m.user_id, m.year
