with logs as (
    select * from {{ ref('fct_logs') }}
)

select
    user_id,
    log_date,
    count(*) as logs_count,
    count(distinct trig_id) as distinct_trigs,
    sum(case when has_comment then 1 else 0 end) as logs_with_comments,
    avg(score)::numeric(5, 2) as avg_score
from logs
group by user_id, log_date
