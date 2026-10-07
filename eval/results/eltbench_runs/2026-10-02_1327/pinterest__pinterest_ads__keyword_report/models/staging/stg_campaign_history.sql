select
    cast(id as bigint) as campaign_id,
    cast(name as varchar) as campaign_name,
    upper(cast(status as varchar)) as status,
    cast(advertiser_id as bigint) as advertiser_id
from {{ source('raw', 'campaign_history') }}
