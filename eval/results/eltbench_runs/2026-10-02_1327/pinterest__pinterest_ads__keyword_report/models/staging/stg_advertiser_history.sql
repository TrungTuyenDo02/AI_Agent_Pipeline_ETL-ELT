select
    cast(id as bigint) as advertiser_id,
    cast(name as varchar) as advertiser_name,
    upper(cast(status as varchar)) as status
from {{ source('raw', 'advertiser_history') }}
