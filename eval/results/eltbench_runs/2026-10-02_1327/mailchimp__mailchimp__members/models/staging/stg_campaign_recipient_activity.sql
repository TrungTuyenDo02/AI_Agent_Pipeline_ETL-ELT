select
    cast(action as varchar) as action,
    cast(campaign_id as varchar) as campaign_id,
    cast(member_id as varchar) as member_id,
    cast(timestamp as varchar) as activity_timestamp,
    cast(_fivetran_synced as varchar) as _fivetran_synced,
    cast(bounce_type as varchar) as bounce_type,
    cast(combination_id as varchar) as combination_id,
    cast(ip as varchar) as ip,
    cast(list_id as varchar) as list_id,
    cast(url as varchar) as url
from {{ source('raw', 'campaign_recipient_activity') }}
