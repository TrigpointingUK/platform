with source as (
    select * from {{ source('trigpointing', 'tphotovote') }}
)

select
    id as vote_id,
    tphoto_id as photo_id,
    user_id,
    score,
    upd_timestamp as voted_at
from source
