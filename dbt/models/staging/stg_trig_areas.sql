with source as (
    select * from {{ source('trigpointing', 'trig_area') }}
)

select
    trig_id,
    area_id,
    area_type_id,
    area_type_code
from source
