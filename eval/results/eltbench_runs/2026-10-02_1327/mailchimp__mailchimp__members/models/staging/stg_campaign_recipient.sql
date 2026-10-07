select
    cast(campaign_id as varchar) as campaign_id,
    cast(member_id as varchar) as member_id,
    cast(list_id as varchar) as list_id,
    cast(combination_id as varchar) as combination_id,
    cast(_fivetran_synced as varchar) as _fivetran_synced
from {{ source('raw', 'campaign_recipient') }}
