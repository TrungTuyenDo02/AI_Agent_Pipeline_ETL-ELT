select
    cast(automation_email_id as varchar) as automation_email_id,
    cast(member_id as varchar) as member_id,
    cast(_fivetran_synced as varchar) as _fivetran_synced,
    cast(list_id as varchar) as list_id
from {{ source('raw', 'automation_recipient') }}
