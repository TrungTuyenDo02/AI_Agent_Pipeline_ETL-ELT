{{ config(materialized='view') }}

select distinct
    cast(id as VARCHAR) as id,
    cast(automation_id as VARCHAR) as automation_id,
    cast(status as VARCHAR) as status
from {{ source('raw', 'automation_email') }}
