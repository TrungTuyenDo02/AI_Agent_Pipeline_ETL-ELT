{{ config(materialized='view') }}

SELECT
    CAST(id AS BIGINT) AS advertiser_id,
    CAST(updated_time AS TIMESTAMP) AS updated_time,
    TRIM(name) AS advertiser_name,
    UPPER(currency) AS currency_code,
    UPPER(country) AS country,
    UPPER(status) AS status
FROM {{ source('raw', 'advertiser_history') }}
