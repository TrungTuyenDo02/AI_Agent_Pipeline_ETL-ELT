select
    cast(id as bigint) as ad_group_id,
    cast(campaign_id as bigint) as campaign_id,
    cast(name as varchar) as ad_group_name,
    upper(cast(status as varchar)) as status
from {{ source('raw', 'ad_group_history') }}
