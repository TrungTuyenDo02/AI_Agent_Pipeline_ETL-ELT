select
    cast(id as varchar) as id,
    cast(posting_id as varchar) as posting_id,
    cast(type as varchar) as type,
    cast(opportunity_id as varchar) as opportunity_id
from {{ source('raw', 'application') }}
