with source as (
    select * from {{ source('trigpointing', 'trig') }}
)

select
    id as trig_id,
    waypoint,
    name as trig_name,
    current_use,
    historic_use,
    type_id,
    wgs_lat,
    wgs_long,
    wgs_height,
    osgb_eastings,
    osgb_northings,
    osgb_gridref,
    osgb_height,
    fb_number,
    stn_number,
    stn_number_active,
    stn_number_passive,
    stn_number_osgb36,
    trim(condition) as condition_code,
    postcode,
    town,
    crt_date,
    crt_user_id,
    admin_user_id,
    admin_timestamp,
    upd_timestamp
from source
where status_id < 90
