WITH joined_data AS (
    SELECT
        c.date_day,
        a.advertiser_name,
        c.advertiser_id,
        c.campaign_name,
        c.campaign_id,
        c.campaign_status,
        c.spend_in_micro_dollar,
        c.clickthrough_1,
        c.clickthrough_2,
        c.impression_1,
        c.impression_2,
        c.total_conversions,
        c.total_conversions_quantity,
        c.total_conversions_value_in_micro_dollar
    FROM {{ ref('stg_campaign_report') }} AS c
    LEFT JOIN {{ ref('stg_advertiser_history') }} AS a
        ON c.advertiser_id = a.advertiser_id
),
aggregated AS (
    SELECT
        date_day,
        advertiser_name,
        advertiser_id,
        campaign_name,
        campaign_id,
        campaign_status,
        CAST(COALESCE(SUM(spend_in_micro_dollar), 0) / 1000000.0 AS DOUBLE) AS spend,
        CAST(COALESCE(SUM(clickthrough_1), 0) + COALESCE(SUM(clickthrough_2), 0) AS BIGINT) AS clicks,
        CAST(COALESCE(SUM(impression_1), 0) + COALESCE(SUM(impression_2), 0) AS BIGINT) AS impressions,
        CAST(COALESCE(SUM(total_conversions), 0) AS BIGINT) AS total_conversions,
        CAST(COALESCE(SUM(total_conversions_quantity), 0) AS BIGINT) AS total_conversions_quantity,
        CAST(COALESCE(SUM(total_conversions_value_in_micro_dollar), 0) / 1000000.0 AS DOUBLE) AS total_conversions_value
    FROM joined_data
    GROUP BY
        date_day,
        advertiser_name,
        advertiser_id,
        campaign_name,
        campaign_id,
        campaign_status
)
SELECT
    date_day,
    advertiser_name,
    advertiser_id,
    campaign_name,
    campaign_id,
    campaign_status,
    spend,
    clicks,
    impressions,
    total_conversions,
    total_conversions_quantity,
    total_conversions_value
FROM aggregated
