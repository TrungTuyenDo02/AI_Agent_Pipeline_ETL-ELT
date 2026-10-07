with report as (
    select *
    from {{ ref('stg_keyword_report') }}
    where ad_group_status = 'ACTIVE'
),
keywords as (
    select *
    from {{ ref('stg_keyword_history') }}
    where archived = false
),
ad_groups as (
    select *
    from {{ ref('stg_ad_group_history') }}
    where status = 'ACTIVE'
),
campaigns as (
    select *
    from {{ ref('stg_campaign_history') }}
    where status = 'ACTIVE'
),
advertisers as (
    select *
    from {{ ref('stg_advertiser_history') }}
    where status = 'ACTIVE'
),
joined as (
    select
        r.date_day,
        a.advertiser_name,
        r.advertiser_id,
        c.campaign_name,
        r.campaign_id,
        r.ad_group_name,
        r.ad_group_id,
        r.keyword_id,
        k.match_type,
        k.parent_type,
        k.keyword_value,
        r.spend_in_micro_dollar,
        r.clickthrough_1,
        r.clickthrough_2,
        r.impression_1,
        r.impression_2,
        r.total_conversions,
        r.total_conversions_quantity,
        r.total_conversions_value_in_micro_dollar
    from report r
    inner join keywords k
        on r.keyword_id = k.keyword_id
    inner join ad_groups g
        on r.ad_group_id = g.ad_group_id
    inner join campaigns c
        on r.campaign_id = c.campaign_id
    inner join advertisers a
        on r.advertiser_id = a.advertiser_id
)
select
    date_day,
    advertiser_name,
    advertiser_id,
    campaign_name,
    campaign_id,
    ad_group_name,
    ad_group_id,
    keyword_id,
    match_type,
    parent_type,
    keyword_value,
    cast(coalesce(sum(spend_in_micro_dollar), 0) / 1000000.0 as double) as spend,
    cast(coalesce(sum(coalesce(clickthrough_1, 0) + coalesce(clickthrough_2, 0)), 0) as bigint) as clicks,
    cast(coalesce(sum(coalesce(impression_1, 0) + coalesce(impression_2, 0)), 0) as bigint) as impressions,
    cast(coalesce(sum(total_conversions), 0) as bigint) as total_conversions,
    cast(coalesce(sum(total_conversions_quantity), 0) as bigint) as total_conversions_quantity,
    cast(coalesce(sum(total_conversions_value_in_micro_dollar), 0) / 1000000.0 as double) as total_conversions_value
from joined
group by
    date_day,
    advertiser_name,
    advertiser_id,
    campaign_name,
    campaign_id,
    ad_group_name,
    ad_group_id,
    keyword_id,
    match_type,
    parent_type,
    keyword_value
