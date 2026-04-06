-- Evaluated medal state per user per medal.
-- Joins user metrics with seed-defined medal definitions and tiers to determine
-- current tier, next threshold, and progress percentage.

with metrics as (
    select * from {{ ref('int_user_medal_metrics') }}
),

definitions as (
    select * from {{ ref('medal_definitions') }}
),

tiers as (
    select * from {{ ref('medal_tiers') }}
),

-- Cross join every user with every medal definition
user_medals as (
    select distinct
        m.user_id,
        d.medal_id,
        d.code,
        d.name,
        d.description,
        d.category,
        d.medal_type,
        d.metric_key,
        d.icon,
        d.sort_order
    from (select distinct user_id from metrics) m
    cross join definitions d
),

-- Attach the user's current metric value for each medal
with_values as (
    select
        um.*,
        coalesce(m.metric_value, 0) as current_value
    from user_medals um
    left join metrics m
        on um.user_id = m.user_id
        and um.metric_key = m.metric_key
),

-- Find the highest tier earned (current_value >= threshold)
highest_earned as (
    select
        wv.user_id,
        wv.medal_id,
        max(t.tier_level) as highest_tier_level
    from with_values wv
    inner join tiers t
        on wv.medal_id = t.medal_id
        and wv.current_value >= t.threshold
    group by wv.user_id, wv.medal_id
),

-- Find the next tier to work toward (lowest tier above current value)
next_tier as (
    select distinct on (wv.user_id, wv.medal_id)
        wv.user_id,
        wv.medal_id,
        t.threshold as next_tier_threshold,
        t.tier_name as next_tier_name
    from with_values wv
    inner join tiers t
        on wv.medal_id = t.medal_id
        and wv.current_value < t.threshold
    order by wv.user_id, wv.medal_id, t.tier_level
)

select
    wv.user_id,
    wv.medal_id,
    wv.code,
    wv.name,
    wv.description,
    wv.category,
    wv.medal_type,
    wv.icon,
    wv.sort_order,
    wv.current_value,
    he.highest_tier_level,
    ht.tier_name as highest_tier_name,
    nt.next_tier_threshold,
    nt.next_tier_name,
    case
        when nt.next_tier_threshold is not null and nt.next_tier_threshold > 0
        then least(100.0, round(100.0 * wv.current_value / nt.next_tier_threshold, 1))
        when he.highest_tier_level is not null
        then 100.0
        else 0.0
    end as progress_pct
from with_values wv
left join highest_earned he
    on wv.user_id = he.user_id
    and wv.medal_id = he.medal_id
left join tiers ht
    on he.medal_id = ht.medal_id
    and he.highest_tier_level = ht.tier_level
left join next_tier nt
    on wv.user_id = nt.user_id
    and wv.medal_id = nt.medal_id
