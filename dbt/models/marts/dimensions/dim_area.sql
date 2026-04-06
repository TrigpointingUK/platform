with areas as (
    select * from {{ ref('stg_areas') }}
)

select
    area_id,
    area_name,
    area_type_name
from areas
