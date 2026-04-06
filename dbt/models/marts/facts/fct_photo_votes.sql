with votes as (
    select * from {{ ref('stg_photo_votes') }}
)

select
    vote_id,
    photo_id,
    user_id,
    score,
    voted_at
from votes
