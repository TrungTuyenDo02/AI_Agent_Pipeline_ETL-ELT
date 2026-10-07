select
    cast(interview_id as varchar) as interview_id,
    cast(posting_id as varchar) as posting_id
from {{ source('raw', 'posting_interview') }}
