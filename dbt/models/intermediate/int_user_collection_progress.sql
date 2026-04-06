-- Per-user collection progress for diverse medal types.
-- Tracks how many distinct "things" each user has collected through their logging activity.

with logs as (
    select * from {{ ref('fct_logs') }}
),

date_dim as (
    select * from {{ ref('dim_date') }}
),

trig_dim as (
    select * from {{ ref('dim_trig') }}
),

trig_areas as (
    select * from {{ ref('stg_trig_areas') }}
),

-- Days of the week the user has logged on (1=Mon..7=Sun)
dow_coverage as (
    select
        l.user_id,
        count(distinct dd.day_of_week) as distinct_days_of_week,
        array_agg(distinct dd.day_of_week_name order by dd.day_of_week_name) as days_of_week_logged
    from logs l
    inner join date_dim dd on l.log_date = dd.date_key
    group by l.user_id
),

-- Months of the year the user has logged in (1-12)
month_coverage as (
    select
        l.user_id,
        count(distinct dd.month) as distinct_months_of_year,
        array_agg(distinct dd.month_name order by dd.month_name) as months_of_year_logged
    from logs l
    inner join date_dim dd on l.log_date = dd.date_key
    group by l.user_id
),

-- Trig name first letter collection (A-Z)
letter_coverage as (
    select
        l.user_id,
        count(distinct t.name_first_letter) as distinct_first_letters
    from logs l
    inner join trig_dim t on l.trig_id = t.trig_id
    where t.name_first_letter is not null
    group by l.user_id
),

-- County coverage
county_coverage as (
    select
        l.user_id,
        count(distinct t.county) as distinct_counties
    from logs l
    inner join trig_dim t on l.trig_id = t.trig_id
    where t.county is not null and trim(t.county) <> ''
    group by l.user_id
),

-- Trig type and category coverage
type_coverage as (
    select
        l.user_id,
        count(distinct t.type_name) as distinct_trig_types,
        count(distinct t.category_name) as distinct_trig_categories
    from logs l
    inner join trig_dim t on l.trig_id = t.trig_id
    where t.type_name is not null
    group by l.user_id
),

-- Condition codes reported
condition_coverage as (
    select
        user_id,
        count(distinct condition_name) as distinct_condition_names
    from logs
    where condition_name is not null and trim(condition_name) <> ''
    group by user_id
),

area_coverage_simple as (
    select
        user_id,
        jsonb_object_agg(area_type_code, area_count) as distinct_areas_by_type
    from (
        select
            l.user_id,
            ta.area_type_code,
            count(distinct ta.area_id) as area_count
        from logs l
        inner join trig_areas ta on l.trig_id = ta.trig_id
        group by l.user_id, ta.area_type_code
    ) sub
    group by user_id
),

-- All users who have logged
all_users as (
    select distinct user_id from logs
)

select
    u.user_id,
    coalesce(dow.distinct_days_of_week, 0) as distinct_days_of_week,
    dow.days_of_week_logged,
    coalesce(mth.distinct_months_of_year, 0) as distinct_months_of_year,
    mth.months_of_year_logged,
    coalesce(let.distinct_first_letters, 0) as distinct_first_letters,
    coalesce(cty.distinct_counties, 0) as distinct_counties,
    coalesce(typ.distinct_trig_types, 0) as distinct_trig_types,
    coalesce(typ.distinct_trig_categories, 0) as distinct_trig_categories,
    coalesce(cnd.distinct_condition_names, 0) as distinct_condition_names,
    coalesce(ac.distinct_areas_by_type, '{}'::jsonb) as distinct_areas_by_type
from all_users u
left join dow_coverage dow on u.user_id = dow.user_id
left join month_coverage mth on u.user_id = mth.user_id
left join letter_coverage let on u.user_id = let.user_id
left join county_coverage cty on u.user_id = cty.user_id
left join type_coverage typ on u.user_id = typ.user_id
left join condition_coverage cnd on u.user_id = cnd.user_id
left join area_coverage_simple ac on u.user_id = ac.user_id
