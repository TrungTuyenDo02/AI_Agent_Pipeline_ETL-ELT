select
    cast(id as varchar) as id,
    canceled_at,
    cast(opportunity_id as varchar) as opportunity_id
from {{ source('raw', 'interview') }}
