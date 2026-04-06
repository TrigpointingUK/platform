with trigs as (
    select * from {{ ref('dim_trig') }}
),

logs as (
    select * from {{ ref('fct_logs') }}
),

photos as (
    select * from {{ ref('fct_photos') }}
),

log_stats as (
    select
        trig_id,
        count(*) as total_logs,
        count(distinct user_id) as total_distinct_loggers,
        min(log_date) as first_logged_date,
        max(log_date) as last_logged_date,
        sum(score) as sum_score,
        avg(score)::numeric(5, 2) as avg_score,
        percentile_cont(0.5) within group (order by score)::numeric(5, 2) as median_score
    from logs
    group by trig_id
),

-- Bayesian prior: global mean score (m) and median log count per trig (C).
-- bayesian_score = (C * m + sum_score) / (C + total_logs)
-- This pulls trigs with few ratings toward the global average.
bayesian_prior as (
    select
        avg(avg_score)::numeric(5, 2) as global_mean,
        percentile_cont(0.5) within group (order by total_logs) as prior_weight
    from log_stats
),

photo_stats as (
    select
        trig_id,
        count(*) as total_photos
    from photos
    group by trig_id
)

select
    t.trig_id,
    t.trig_name,
    t.type_name,
    t.category_name,
    t.county,
    coalesce(ls.total_logs, 0) as total_logs,
    coalesce(ls.total_distinct_loggers, 0) as total_distinct_loggers,
    coalesce(ps.total_photos, 0) as total_photos,
    ls.first_logged_date,
    ls.last_logged_date,
    ls.avg_score,
    ls.median_score,
    case
        when ls.total_logs > 0
        then ((bp.prior_weight * bp.global_mean + ls.sum_score) / (bp.prior_weight + ls.total_logs))::numeric(5, 2)
    end as bayesian_score
from trigs t
left join log_stats ls on t.trig_id = ls.trig_id
left join photo_stats ps on t.trig_id = ps.trig_id
cross join bayesian_prior bp
