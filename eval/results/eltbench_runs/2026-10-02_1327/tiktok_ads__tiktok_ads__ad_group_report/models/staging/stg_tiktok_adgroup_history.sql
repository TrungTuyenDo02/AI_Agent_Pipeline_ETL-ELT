select
    try_cast("ADGROUP_ID" as bigint) as ad_group_id,
    try_cast("ADVERTISER_ID" as bigint) as advertiser_id,
    cast("UPDATED_AT" as timestamp) as updated_at,
    cast("ADGROUP_NAME" as varchar) as ad_group_name,
    cast("GENDER" as varchar) as gender,
    cast("CATEGORY" as varchar) as category
from {{ source('raw', 'tiktok_adgroup_history') }}
