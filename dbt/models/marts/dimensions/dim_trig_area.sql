with trig_areas as (
    select * from {{ ref('stg_trig_areas') }}
),

areas as (
    select area_id, area_type_name from {{ ref('stg_areas') }}
)

select
    ta.trig_id,
    ta.area_id,
    a.area_type_name
from trig_areas ta
inner join areas a on ta.area_id = a.area_id
