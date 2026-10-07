select
    cast(user_id as varchar) as user_id,
    cast(amplitude_id as bigint) as amplitude_id,
    cast(event_time as timestamp) as event_time,
    cast(session_id as bigint) as session_id
from {{ source('raw', 'event') }}
