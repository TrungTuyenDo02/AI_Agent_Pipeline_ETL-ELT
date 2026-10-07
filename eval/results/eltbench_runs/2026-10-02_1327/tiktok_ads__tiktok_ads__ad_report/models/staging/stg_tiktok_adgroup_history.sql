{{ config(materialized='view') }}

with ranked as (
    select
        try_cast("ADGROUP_ID" as BIGINT) as ad_group_id,
        try_cast("ADVERTISER_ID" as BIGINT) as advertiser_id,
        try_cast("CAMPAIGN_ID" as BIGINT) as campaign_id,
        "ADGROUP_NAME"::VARCHAR as ad_group_name,
        "GENDER"::VARCHAR as gender,
        "CATEGORY"::VARCHAR as category,
        try_cast("BUDGET" as DOUBLE) as budget,
        row_number() over (partition by "ADGROUP_ID" order by "UPDATED_AT" desc) as row_num
    from {{ source('raw', 'tiktok_adgroup_history') }}
)
select
    ad_group_id,
    advertiser_id,
    campaign_id,
    ad_group_name,
    gender,
    category,
    budget
from ranked
where row_num = 1
