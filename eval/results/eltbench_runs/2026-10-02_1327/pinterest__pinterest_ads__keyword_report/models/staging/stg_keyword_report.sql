select
    cast(date as date) as date_day,
    cast(keyword_id as bigint) as keyword_id,
    cast(ad_group_id as bigint) as ad_group_id,
    cast(ad_group_name as varchar) as ad_group_name,
    upper(cast(ad_group_status as varchar)) as ad_group_status,
    cast(campaign_id as bigint) as campaign_id,
    cast(advertiser_id as bigint) as advertiser_id,
    cast(impression_1 as bigint) as impression_1,
    cast(impression_2 as bigint) as impression_2,
    cast(clickthrough_1 as bigint) as clickthrough_1,
    cast(clickthrough_2 as bigint) as clickthrough_2,
    cast(spend_in_micro_dollar as bigint) as spend_in_micro_dollar,
    cast(total_conversions as bigint) as total_conversions,
    cast(total_conversions_quantity as bigint) as total_conversions_quantity,
    cast(total_conversions_value_in_micro_dollar as bigint) as total_conversions_value_in_micro_dollar
from {{ source('raw', 'keyword_report') }}
