{{ config(materialized='table') }}

WITH latest_ad_history AS (
    SELECT
        ad_id,
        advertiser_id,
        updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY ad_id
            ORDER BY updated_at DESC
        ) AS history_rank
    FROM {{ ref('stg_tiktok_ad_history') }}
),
resolved_ad_history AS (
    SELECT
        ad_id,
        advertiser_id
    FROM latest_ad_history
    WHERE history_rank = 1
),
hourly_metrics AS (
    SELECT
        h.stat_time_hour::DATE AS date_day,
        ah.advertiser_id,
        SUM(h.clicks)::BIGINT AS clicks,
        SUM(h.impressions)::BIGINT AS impressions,
        SUM(h.spend)::DOUBLE AS spend,
        SUM(h.reach)::BIGINT AS reach,
        SUM(h.conversion)::BIGINT AS conversion,
        SUM(h.likes)::BIGINT AS likes,
        SUM(h.comments)::BIGINT AS comments,
        SUM(h.shares)::BIGINT AS shares,
        SUM(h.profile_visits)::BIGINT AS profile_visits,
        SUM(h.follows)::BIGINT AS follows,
        SUM(h.video_watched_2_s)::BIGINT AS video_watched_2_s,
        SUM(h.video_watched_6_s)::BIGINT AS video_watched_6_s,
        SUM(h.video_views_p_25)::BIGINT AS video_views_p_25,
        SUM(h.video_views_p_50)::BIGINT AS video_views_p_50,
        SUM(h.video_views_p_75)::BIGINT AS video_views_p_75,
        SUM(h.real_time_conversion)::BIGINT AS real_time_conversion,
        SUM(h.total_purchase_value)::DOUBLE AS total_purchase_value,
        SUM(h.total_sales_lead_value)::DOUBLE AS total_sales_lead_value
    FROM {{ ref('stg_tiktok_ad_report_hourly') }} AS h
    INNER JOIN resolved_ad_history AS ah
        ON h.ad_id = ah.ad_id
    GROUP BY
        h.stat_time_hour::DATE,
        ah.advertiser_id
)
SELECT
    m.date_day AS date_day,
    m.advertiser_id AS advertiser_id,
    a.advertiser_name AS advertiser_name,
    a.currency AS currency,
    m.clicks AS clicks,
    m.impressions AS impressions,
    m.spend AS spend,
    m.reach AS reach,
    m.conversion AS conversion,
    m.likes AS likes,
    m.comments AS comments,
    m.shares AS shares,
    m.profile_visits AS profile_visits,
    m.follows AS follows,
    m.video_watched_2_s AS video_watched_2_s,
    m.video_watched_6_s AS video_watched_6_s,
    m.video_views_p_25 AS video_views_p_25,
    m.video_views_p_50 AS video_views_p_50,
    m.video_views_p_75 AS video_views_p_75,
    m.real_time_conversion AS real_time_conversion,
    m.total_purchase_value AS total_purchase_value,
    m.total_sales_lead_value AS total_sales_lead_value,
    (m.total_purchase_value + m.total_sales_lead_value)::DOUBLE AS total_conversion_value,
    CASE
        WHEN m.clicks = 0 THEN 0.0
        ELSE m.spend / m.clicks
    END::DOUBLE AS daily_cpc,
    CASE
        WHEN m.impressions = 0 THEN 0.0
        ELSE m.spend / m.impressions * 1000.0
    END::DOUBLE AS daily_cpm,
    CASE
        WHEN m.impressions = 0 THEN 0.0
        ELSE m.clicks::DOUBLE / m.impressions * 100.0
    END::DOUBLE AS daily_ctr
FROM hourly_metrics AS m
INNER JOIN {{ ref('stg_tiktok_advertiser') }} AS a
    ON m.advertiser_id = a.advertiser_id
