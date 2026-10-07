{{ config(materialized='table') }}

WITH latest_advertiser_history AS (
    SELECT
        advertiser_id,
        advertiser_name,
        currency_code,
        country,
        ROW_NUMBER() OVER (
            PARTITION BY advertiser_id
            ORDER BY updated_time DESC
        ) AS history_rank
    FROM {{ ref('stg_advertiser_history') }}
),
report_with_advertiser AS (
    SELECT
        r.date_day,
        h.advertiser_name,
        r.advertiser_id,
        h.currency_code,
        h.country,
        r.spend_in_micro_dollar,
        r.clickthrough_1,
        r.clickthrough_2,
        r.impression_1,
        r.impression_2,
        r.total_conversions,
        r.total_conversions_quantity,
        r.total_conversions_value_in_micro_dollar
    FROM {{ ref('stg_advertiser_report') }} AS r
    LEFT JOIN latest_advertiser_history AS h
        ON r.advertiser_id = h.advertiser_id
       AND h.history_rank = 1
)
SELECT
    date_day,
    advertiser_name,
    advertiser_id,
    currency_code,
    country,
    COALESCE(SUM(CAST(spend_in_micro_dollar AS DOUBLE)) / 1000000.0, 0.0) AS spend,
    COALESCE(SUM(COALESCE(clickthrough_1, 0) + COALESCE(clickthrough_2, 0)), 0)::BIGINT AS clicks,
    COALESCE(SUM(COALESCE(impression_1, 0) + COALESCE(impression_2, 0)), 0)::BIGINT AS impressions,
    COALESCE(SUM(COALESCE(total_conversions, 0)), 0)::BIGINT AS total_conversions,
    COALESCE(SUM(COALESCE(total_conversions_quantity, 0)), 0)::BIGINT AS total_conversions_quantity,
    COALESCE(SUM(CAST(total_conversions_value_in_micro_dollar AS DOUBLE)) / 1000000.0, 0.0) AS total_conversions_value
FROM report_with_advertiser
GROUP BY
    date_day,
    advertiser_name,
    advertiser_id,
    currency_code,
    country
