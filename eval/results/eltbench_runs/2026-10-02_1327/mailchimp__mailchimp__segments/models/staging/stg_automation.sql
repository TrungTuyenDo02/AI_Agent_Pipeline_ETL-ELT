{{ config(materialized='view') }}

select distinct
    cast(id as VARCHAR) as id,
    cast(list_id as VARCHAR) as list_id,
    cast(status as VARCHAR) as status
from {{ source('raw', 'automation') }}
