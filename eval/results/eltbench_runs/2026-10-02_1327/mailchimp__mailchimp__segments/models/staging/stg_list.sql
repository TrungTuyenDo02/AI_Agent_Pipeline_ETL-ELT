{{ config(materialized='view') }}

select distinct
    cast(id as VARCHAR) as id,
    cast(name as VARCHAR) as name
from {{ source('raw', 'list') }}
