with types as (
    select * from {{ source('trigpointing', 'trig_type') }}
),

categories as (
    select * from {{ source('trigpointing', 'trig_category') }}
)

select
    t.id as type_id,
    t.code as type_code,
    t.name as type_name,
    t.description as type_description,
    t.sort_order as type_sort_order,
    t.legacy_physical_type,
    c.id as category_id,
    c.code as category_code,
    c.name as category_name,
    c.sort_order as category_sort_order
from types t
inner join categories c on t.category_id = c.id
