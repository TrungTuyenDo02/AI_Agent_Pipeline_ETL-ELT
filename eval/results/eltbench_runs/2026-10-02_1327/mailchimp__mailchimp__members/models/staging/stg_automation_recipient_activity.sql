select
    cast(action as varchar) as action,
    cast(automation_email_id as varchar) as automation_email_id,
    cast(member_id as varchar) as member_id,
    cast(timestamp as varchar) as activity_timestamp,
    cast(_fivetran_synced as varchar) as _fivetran_synced,
    cast(bounce_type as varchar) as bounce_type,
    cast(ip as varchar) as ip,
    cast(list_id as varchar) as list_id,
    cast(url as varchar) as url
from {{ source('raw', 'automation_recipient_activity') }}
