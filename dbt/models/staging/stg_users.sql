with source as (
    select * from {{ source('trigpointing', 'user') }}
)

select
    id as user_id,
    name as username,
    crt_date as member_since_date,
    about,
    upd_timestamp
from source
