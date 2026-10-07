with hourly_daily as (
    select
        cast(stat_time_hour as date) as date_day,
        ad_group_id,
        sum(coalesce(impressions, 0))::bigint as impressions,
        sum(coalesce(clicks, 0))::bigint as clicks,
        sum(coalesce(spend, 0.0))::double as spend,
        sum(coalesce(reach, 0))::bigint as reach,
        sum(coalesce(conversion, 0))::bigint as conversion,
        sum(coalesce(likes, 0))::bigint as likes,
        sum(coalesce(comments, 0))::bigint as comments,
        sum(coalesce(shares, 0))::bigint as shares,
        sum(coalesce(profile_visits, 0))::bigint as profile_visits,
        sum(coalesce(follows, 0))::bigint as follows,
        sum(coalesce(video_watched_2_s, 0))::bigint as video_watched_2_s,
        sum(coalesce(video_watched_6_s, 0))::bigint as video_watched_6_s,
        sum(coalesce(video_views_p_25, 0))::bigint as video_views_p_25,
        sum(coalesce(video_views_p_50, 0))::bigint as video_views_p_50,
        sum(coalesce(video_views_p_75, 0))::bigint as video_views_p_75,
        sum(coalesce(real_time_conversion, 0))::bigint as real_time_conversion,
        sum(coalesce(total_purchase_value, 0.0))::double as total_purchase_value,
        sum(coalesce(total_sales_lead_value, 0.0))::double as total_sales_lead_value
    from {{ ref('stg_tiktok_adgroup_report_hourly') }}
    group by 1, 2
), latest_history as (
    select
        ad_group_id,
        advertiser_id,
        ad_group_name,
        category,
        gender,
        row_number() over (
            partition by ad_group_id, advertiser_id
            order by updated_at desc
        ) as row_num
    from {{ ref('stg_tiktok_adgroup_history') }}
), joined as (
    select
        h.date_day,
        c.advertiser_id,
        h.ad_group_id,
        c.ad_group_name,
        c.category,
        c.gender,
        h.impressions,
        h.clicks,
        h.spend,
        h.reach,
        h.conversion,
        h.likes,
        h.comments,
        h.shares,
        h.profile_visits,
        h.follows,
        h.video_watched_2_s,
        h.video_watched_6_s,
        h.video_views_p_25,
        h.video_views_p_50,
        h.video_views_p_75,
        h.real_time_conversion,
        h.total_purchase_value,
        h.total_sales_lead_value
    from hourly_daily h
    left join latest_history c
        on h.ad_group_id = c.ad_group_id
       and c.row_num = 1
)
select
    date_day,
    advertiser_id,
    ad_group_id,
    ad_group_name,
    category,
    gender,
    cast(0.0 as double) as budget,
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
    cast(total_purchase_value + total_sales_lead_value as double) as total_conversion_value,
    case when clicks = 0 then 0.0 else spend / clicks end as daily_cpc,
    case when impressions = 0 then 0.0 else spend / impressions * 1000 end as daily_cpm,
    case when impressions = 0 then 0.0 else clicks::double / impressions * 100 end as daily_ctr
from joined
