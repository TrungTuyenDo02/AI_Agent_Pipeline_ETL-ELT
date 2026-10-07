select
    cast(posting_id as varchar) as posting_id,
    cast(requisition_id as varchar) as requisition_id,
    _fivetran_deleted
from {{ source('raw', 'requisition_posting') }}
