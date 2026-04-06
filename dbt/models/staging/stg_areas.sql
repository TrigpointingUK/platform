with areas as (
    select * from {{ source('trigpointing', 'area') }}
),

area_types as (
    select * from {{ source('trigpointing', 'area_type') }}
)

select
    a.id as area_id,
    a.name as area_name,
    a.code as area_code,
    at.id as area_type_id,
    at.code as area_type_code,
    at.name as area_type_name
from areas a
inner join area_types at on a.area_type_id = at.id
