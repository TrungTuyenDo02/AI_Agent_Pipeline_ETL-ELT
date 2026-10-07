SELECT
    CAST(date AS DATE) AS date,
    CAST(ad_group_id AS BIGINT) AS ad_group_id,
    CAST(ad_group_name AS VARCHAR) AS ad_group_name,
    CAST(ad_group_status AS VARCHAR) AS ad_group_status,
    CAST(campaign_id AS BIGINT) AS campaign_id,
    CAST(advertiser_id AS BIGINT) AS advertiser_id,
    CAST(impression_1 AS BIGINT) AS impression_1,
    CAST(impression_2 AS BIGINT) AS impression_2,
    CAST(clickthrough_1 AS BIGINT) AS clickthrough_1,
    CAST(clickthrough_2 AS BIGINT) AS clickthrough_2,
    CAST(spend_in_micro_dollar AS BIGINT) AS spend_in_micro_dollar,
    CAST(total_conversions AS BIGINT) AS total_conversions,
    CAST(total_conversions_quantity AS BIGINT) AS total_conversions_quantity,
    CAST(total_conversions_value_in_micro_dollar AS BIGINT) AS total_conversions_value_in_micro_dollar
FROM {{ source('raw', 'ad_group_report') }}
