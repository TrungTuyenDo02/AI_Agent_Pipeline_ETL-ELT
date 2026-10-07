{{ config(materialized='view') }}

with ranked as (
    select
        "CAMPAIGN_ID"::BIGINT as campaign_id,
        "ADVERTISER_ID"::BIGINT as advertiser_id,
        "CAMPAIGN_NAME"::VARCHAR as campaign_name,
        "BUDGET"::DOUBLE as budget,
        row_number() over (partition by "CAMPAIGN_ID" order by "UPDATED_AT" desc) as row_num
    from {{ source('raw', 'tiktok_campaign_history') }}
)
select
    campaign_id,
    advertiser_id,
    campaign_name,
    budget
from ranked
where row_num = 1
