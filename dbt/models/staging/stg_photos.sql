with source as (
    select * from {{ source('trigpointing', 'tphoto') }}
)

select
    id as photo_id,
    tlog_id as log_id,
    trim(type) as photo_type,
    filename,
    filesize,
    height,
    width,
    name as photo_name,
    text_desc as photo_description,
    trim(public_ind) = 'Y' as is_public,
    trim(deleted_ind) = 'Y' as is_deleted,
    trim(source) as photo_source,
    crt_timestamp as created_at
from source
