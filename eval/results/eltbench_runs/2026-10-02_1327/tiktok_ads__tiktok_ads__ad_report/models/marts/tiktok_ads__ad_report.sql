{{ config(materialized='table') }}

with daily_metrics as (
    select
        date_day,
        ad_id,
        sum(impressions)::BIGINT as impressions,
        sum(clicks)::BIGINT as clicks,
        sum(spend)::DOUBLE as spend,
        sum(reach)::BIGINT as reach,
        sum(conversion)::BIGINT as conversion,
        sum(likes)::BIGINT as likes,
        sum(comments)::BIGINT as comments,
        sum(shares)::BIGINT as shares,
        sum(profile_visits)::BIGINT as profile_visits,
        sum(follows)::BIGINT as follows,
        sum(video_watched_2_s)::BIGINT as video_watched_2_s,
        sum(video_watched_6_s)::BIGINT as video_watched_6_s,
        sum(video_views_p_25)::BIGINT as video_views_p_25,
        sum(video_views_p_50)::BIGINT as video_views_p_50,
        sum(video_views_p_75)::BIGINT as video_views_p_75,
        sum(real_time_conversion)::BIGINT as real_time_conversion,
        sum(total_purchase_value)::DOUBLE as total_purchase_value,
        sum(total_sales_lead_value)::DOUBLE as total_sales_lead_value
    from {{ ref('stg_tiktok_ad_report_hourly') }}
    group by date_day, ad_id
), enriched as (
    select
        m.date_day,
        a.advertiser_id,
        av.advertiser_name,
        a.campaign_id,
        c.campaign_name,
        a.ad_group_id,
        g.ad_group_name,
        a.ad_id,
        a.ad_name,
        av.currency,
        g.category,
        g.gender,
        c.budget::DOUBLE as budget,
        m.impressions,
        m.clicks,
        m.spend,
        m.reach,
        m.conversion,
        m.likes,
        m.comments,
        m.shares,
        m.profile_visits,
        m.follows,
        m.video_watched_2_s,
        m.video_watched_6_s,
        m.video_views_p_25,
        m.video_views_p_50,
        m.video_views_p_75,
        m.real_time_conversion,
        m.total_purchase_value,
        m.total_sales_lead_value
    from daily_metrics m
    left join {{ ref('stg_tiktok_ad_history') }} a
        on m.ad_id = a.ad_id
    left join {{ ref('stg_tiktok_adgroup_history') }} g
        on a.ad_group_id = g.ad_group_id
        and a.advertiser_id = g.advertiser_id
        and a.campaign_id = g.campaign_id
    left join {{ ref('stg_tiktok_campaign_history') }} c
        on a.campaign_id = c.campaign_id
        and a.advertiser_id = c.advertiser_id
    left join {{ ref('stg_tiktok_advertiser') }} av
        on a.advertiser_id = av.advertiser_id
)
select
    date_day,
    advertiser_id,
    advertiser_name,
    campaign_id,
    campaign_name,
    ad_group_id,
    ad_group_name,
    ad_id,
    ad_name,
    currency,
    category,
    gender,
    budget,
    impressions,
    clicks,
    spend,
    reach,
    conversion,
    likes,
    comments,
    shares,
    profile_visits,
    follows,
    video_watched_2_s,
    video_watched_6_s,
    video_views_p_25,
    video_views_p_50,
    video_views_p_75,
    real_time_conversion,
    total_purchase_value,
    total_sales_lead_value,
    (total_purchase_value + total_sales_lead_value)::DOUBLE as total_conversion_value,
    case when clicks = 0 then 0.0 else spend / clicks end::DOUBLE as daily_cpc,
    case when impressions = 0 then 0.0 else spend * 1000 / impressions end::DOUBLE as daily_cpm,
    case when impressions = 0 then 0.0 else clicks * 100.0 / impressions end::DOUBLE as daily_ctr
from enriched
