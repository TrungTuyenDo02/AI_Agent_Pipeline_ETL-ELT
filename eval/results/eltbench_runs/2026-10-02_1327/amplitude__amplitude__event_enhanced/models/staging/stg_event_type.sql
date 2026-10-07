select
    cast(id as bigint) as id,
    cast(project_name as bigint) as project_name,
    cast(name as varchar) as name,
    cast(totals as bigint) as totals,
    cast(value as varchar) as value
from {{ source('raw', 'event_type') }}
