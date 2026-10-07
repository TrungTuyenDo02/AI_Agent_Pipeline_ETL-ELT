select
    cast(id as varchar) as id,
    _fivetran_deleted
from {{ source('raw', 'requisition') }}
