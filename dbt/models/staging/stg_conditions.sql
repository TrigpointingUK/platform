with source as (
    select * from {{ source('trigpointing', 'condition') }}
)

select
    trim(code) as condition_code,
    trim(name) as condition_name,
    description as condition_description,
    sort_order
from source
