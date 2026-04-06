{{
    config(
        materialized='table'
    )
}}

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('1900-01-01' as date)",
        end_date="cast(current_date + interval '365 days' as date)"
    ) }}
)

select
    date_day as date_key,
    extract(year from date_day)::int as year,
    extract(quarter from date_day)::int as quarter,
    extract(month from date_day)::int as month,
    to_char(date_day, 'Month') as month_name,
    extract(isoyear from date_day)::int as iso_year,
    extract(week from date_day)::int as iso_week,
    extract(dow from date_day)::int as day_of_week_sunday_zero,
    case extract(isodow from date_day)::int
        when 1 then 'Monday'
        when 2 then 'Tuesday'
        when 3 then 'Wednesday'
        when 4 then 'Thursday'
        when 5 then 'Friday'
        when 6 then 'Saturday'
        when 7 then 'Sunday'
    end as day_of_week_name,
    extract(isodow from date_day)::int as day_of_week,
    extract(day from date_day)::int as day_of_month,
    extract(doy from date_day)::int as day_of_year,
    extract(isodow from date_day)::int in (6, 7) as is_weekend,
    extract(day from date_day)::int = 1 as is_first_day_of_month,
    date_day = (date_trunc('month', date_day) + interval '1 month' - interval '1 day')::date as is_last_day_of_month,
    to_char(date_day, 'YYYY-MM') as year_month,
    to_char(date_day, 'IYYY') || '-W' || lpad(extract(week from date_day)::text, 2, '0') as year_week
from date_spine
