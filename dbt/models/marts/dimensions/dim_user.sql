with users as (
    select * from {{ ref('stg_users') }}
)

select
    user_id,
    username,
    member_since_date,
    extract(year from member_since_date)::int as member_since_year,
    (current_date - member_since_date)::int as tenure_days
from users
