{{ config(materialized='view') }}

select
    "AD_ID"::BIGINT as ad_id,
    cast("STAT_TIME_HOUR" as date) as date_day,
    "IMPRESSIONS"::BIGINT as impressions,
    "CLICKS"::BIGINT as clicks,
    "SPEND"::DOUBLE as spend,
    "REACH"::BIGINT as reach,
    "CONVERSION"::BIGINT as conversion,
    "LIKES"::BIGINT as likes,
    "COMMENTS"::BIGINT as comments,
    "SHARES"::BIGINT as shares,
    "PROFILE_VISITS"::BIGINT as profile_visits,
    "FOLLOWS"::BIGINT as follows,
    "VIDEO_WATCHED_2_S"::BIGINT as video_watched_2_s,
    "VIDEO_WATCHED_6_S"::BIGINT as video_watched_6_s,
    "VIDEO_VIEWS_P_25"::BIGINT as video_views_p_25,
    "VIDEO_VIEWS_P_50"::BIGINT as video_views_p_50,
    "VIDEO_VIEWS_P_75"::BIGINT as video_views_p_75,
    "REAL_TIME_CONVERSION"::BIGINT as real_time_conversion,
    "TOTAL_PURCHASE_VALUE"::DOUBLE as total_purchase_value,
    "TOTAL_SALES_LEAD_VALUE"::DOUBLE as total_sales_lead_value
from {{ source('raw', 'tiktok_ad_report_hourly') }}
