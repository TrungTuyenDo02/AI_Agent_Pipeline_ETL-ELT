{{ config(materialized='view') }}

select distinct
    cast(action as VARCHAR) as action,
    cast(automation_email_id as VARCHAR) as automation_email_id,
    cast(member_id as VARCHAR) as member_id,
    cast(list_id as VARCHAR) as list_id
from {{ source('raw', 'automation_recipient_activity') }}
