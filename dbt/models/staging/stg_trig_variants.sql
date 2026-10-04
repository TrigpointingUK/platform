with source as (
    select * from {{ source('trigpointing', 'trig_variant') }}
)

select
    id as variant_id,
    group_code as variant_group_code,
    group_name as variant_group_name,
    code as variant_code,
    name as variant_name,
    sort_order
from source
