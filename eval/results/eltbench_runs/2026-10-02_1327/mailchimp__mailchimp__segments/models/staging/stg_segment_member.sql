{{ config(materialized='view') }}

select distinct
    cast(member_id as VARCHAR) as member_id,
    cast(segment_id as BIGINT) as segment_id,
    cast(list_id as VARCHAR) as list_id
from {{ source('raw', 'segment_member') }}
