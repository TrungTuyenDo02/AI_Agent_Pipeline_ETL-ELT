{{ config(materialized='view') }}

SELECT
    CAST(date AS DATE) AS date_day,
    CAST(advertiser_id AS BIGINT) AS advertiser_id,
    CAST(impression_1 AS BIGINT) AS impression_1,
    CAST(impression_2 AS BIGINT) AS impression_2,
    CAST(clickthrough_1 AS BIGINT) AS clickthrough_1,
    CAST(clickthrough_2 AS BIGINT) AS clickthrough_2,
    CAST(spend_in_micro_dollar AS BIGINT) AS spend_in_micro_dollar,
    CAST(total_conversions AS BIGINT) AS total_conversions,
    CAST(total_conversions_quantity AS BIGINT) AS total_conversions_quantity,
    CAST(total_conversions_value_in_micro_dollar AS BIGINT) AS total_conversions_value_in_micro_dollar
FROM {{ source('raw', 'advertiser_report') }}
