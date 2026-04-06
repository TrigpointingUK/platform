with source as (
    select * from {{ source('trigpointing', 'tlog') }}
)

select
    id as log_id,
    trig_id,
    user_id,
    date as log_date,
    "time" as log_time,
    osgb_eastings,
    osgb_northings,
    osgb_gridref,
    fb_number,
    trim(condition) as condition_code,
    comment,
    score,
    trim(source) as log_source,
    upd_timestamp
from source
