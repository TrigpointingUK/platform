with trigs as (
    select * from {{ ref('stg_trigs') }}
),

trig_types as (
    select * from {{ ref('stg_trig_types') }}
),

conditions as (
    select * from {{ ref('stg_conditions') }}
),

-- Derive county from the area hierarchy (county area_type_code)
trig_counties as (
    select
        ta.trig_id,
        a.area_name as county
    from {{ ref('stg_trig_areas') }} ta
    inner join {{ ref('stg_areas') }} a on ta.area_id = a.area_id
    where ta.area_type_code = 'ceremonial_county'
)

select
    t.trig_id,
    t.waypoint,
    t.trig_name,
    tt.type_name,
    tt.category_name,
    c.condition_name,
    tc.county,
    t.town,
    t.postcode,
    t.wgs_lat,
    t.wgs_long,
    t.osgb_gridref,
    t.osgb_height,
    t.current_use,
    t.historic_use,
    t.fb_number,
    t.stn_number,
    upper(left(t.trig_name, 1)) as name_first_letter
from trigs t
left join trig_types tt on t.type_id = tt.type_id
left join conditions c on t.condition_code = c.condition_code
left join trig_counties tc on t.trig_id = tc.trig_id
