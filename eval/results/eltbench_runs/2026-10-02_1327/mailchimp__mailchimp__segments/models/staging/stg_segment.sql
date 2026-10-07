{{ config(materialized='view') }}

select distinct
    cast(id as BIGINT) as id,
    cast(list_id as VARCHAR) as list_id,
    cast(member_count as BIGINT) as member_count,
    cast(name as VARCHAR) as name,
    cast(type as VARCHAR) as type,
    cast(updated_at as VARCHAR) as updated_at,
    cast(created_at as VARCHAR) as created_at
from {{ source('raw', 'segment') }}
