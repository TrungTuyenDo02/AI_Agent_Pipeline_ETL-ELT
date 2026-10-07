{{ config(materialized='view') }}

with ranked as (
    select
        "AD_ID"::BIGINT as ad_id,
        "ADVERTISER_ID"::BIGINT as advertiser_id,
        "ADGROUP_ID"::BIGINT as ad_group_id,
        "CAMPAIGN_ID"::BIGINT as campaign_id,
        "AD_NAME"::VARCHAR as ad_name,
        row_number() over (partition by "AD_ID" order by "UPDATED_AT" desc) as row_num
    from {{ source('raw', 'tiktok_ad_history') }}
)
select
    ad_id,
    advertiser_id,
    ad_group_id,
    campaign_id,
    ad_name
from ranked
where row_num = 1
