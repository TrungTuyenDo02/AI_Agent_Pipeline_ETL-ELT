{{ config(materialized='view') }}

select distinct
    cast(campaign_id as VARCHAR) as campaign_id,
    cast(member_id as VARCHAR) as member_id,
    cast(list_id as VARCHAR) as list_id
from {{ source('raw', 'unsubscribe') }}
