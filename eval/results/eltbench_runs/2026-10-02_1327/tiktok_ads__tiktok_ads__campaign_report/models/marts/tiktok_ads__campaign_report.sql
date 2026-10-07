WITH campaign_advertisers AS (
    SELECT
        campaign_id,
        advertiser_id
    FROM {{ ref('stg_tiktok_campaign_history') }}
    GROUP BY campaign_id, advertiser_id
),
daily_metrics AS (
    SELECT
        CAST(timezone(a.timezone, timezone('UTC', r.stat_time_hour)) AS DATE) AS date_day,
        ca.advertiser_id,
        a.advertiser_name,
        r.campaign_id,
        a.currency,
        SUM(r.impressions)::BIGINT AS impressions,
        SUM(r.clicks)::BIGINT AS clicks,
        SUM(r.spend)::DOUBLE AS spend,
        SUM(r.reach)::BIGINT AS reach,
        SUM(r.conversion)::BIGINT AS conversion,
        SUM(r.likes)::BIGINT AS likes,
        SUM(r.comments)::BIGINT AS comments,
        SUM(r.shares)::BIGINT AS shares,
        SUM(r.profile_visits)::BIGINT AS profile_visits,
        SUM(r.follows)::BIGINT AS follows,
        SUM(r.video_watched_2_s)::BIGINT AS video_watched_2_s,
        SUM(r.video_watched_6_s)::BIGINT AS video_watched_6_s,
        SUM(r.video_views_p_25)::BIGINT AS video_views_p_25,
        SUM(r.video_views_p_50)::BIGINT AS video_views_p_50,
        SUM(r.video_views_p_75)::BIGINT AS video_views_p_75,
        SUM(r.real_time_conversion)::BIGINT AS real_time_conversion,
        SUM(r.total_purchase_value)::DOUBLE AS total_purchase_value,
        SUM(r.total_sales_lead_value)::DOUBLE AS total_sales_lead_value
    FROM {{ ref('stg_tiktok_campaign_report_hourly') }} r
    INNER JOIN campaign_advertisers ca
        ON r.campaign_id = ca.campaign_id
    INNER JOIN {{ ref('stg_tiktok_advertiser') }} a
        ON ca.advertiser_id = a.advertiser_id
    GROUP BY
        CAST(timezone(a.timezone, timezone('UTC', r.stat_time_hour)) AS DATE),
        ca.advertiser_id,
        a.advertiser_name,
        r.campaign_id,
        a.currency
),
history_candidates AS (
    SELECT
        d.date_day,
        d.advertiser_id,
        d.advertiser_name,
        d.campaign_id,
        h.campaign_name,
        d.currency,
        d.impressions,
        d.clicks,
        d.spend,
        d.reach,
        d.conversion,
        d.likes,
        d.comments,
        d.shares,
        d.profile_visits,
        d.follows,
        d.video_watched_2_s,
        d.video_watched_6_s,
        d.video_views_p_25,
        d.video_views_p_50,
        d.video_views_p_75,
        d.real_time_conversion,
        d.total_purchase_value,
        d.total_sales_lead_value,
        ROW_NUMBER() OVER (
            PARTITION BY d.date_day, d.advertiser_id, d.advertiser_name, d.campaign_id, d.currency
            ORDER BY h.updated_at DESC NULLS LAST
        ) AS history_rank
    FROM daily_metrics d
    LEFT JOIN {{ ref('stg_tiktok_campaign_history') }} h
        ON d.campaign_id = h.campaign_id
        AND d.advertiser_id = h.advertiser_id
        AND h.updated_at < d.date_day + INTERVAL '1 day'
)
SELECT
    date_day,
    advertiser_id,
    advertiser_name,
    campaign_id,
    campaign_name,
    currency,
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
    CAST(total_purchase_value + total_sales_lead_value AS DOUBLE) AS total_conversion_value,
    CAST(CASE WHEN clicks = 0 THEN 0.0 ELSE spend / clicks END AS DOUBLE) AS daily_cpc,
    CAST(CASE WHEN impressions = 0 THEN 0.0 ELSE spend * 1000.0 / impressions END AS DOUBLE) AS daily_cpm,
    CAST(CASE WHEN impressions = 0 THEN 0.0 ELSE clicks * 100.0 / impressions END AS DOUBLE) AS daily_ctr
FROM history_candidates
WHERE history_rank = 1
