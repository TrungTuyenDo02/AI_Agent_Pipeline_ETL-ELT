select
    cast(id as varchar) as id,
    cast(archived_at as varchar) as archived_at
from {{ source('raw', 'opportunity') }}
