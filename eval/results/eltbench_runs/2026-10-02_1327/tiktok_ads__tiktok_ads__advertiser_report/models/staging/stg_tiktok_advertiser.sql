{{ config(materialized='table') }}

SELECT
    CAST(ID AS BIGINT) AS advertiser_id,
    CAST(NAME AS VARCHAR) AS advertiser_name,
    CAST(CURRENCY AS VARCHAR) AS currency,
    CAST(STATUS AS VARCHAR) AS status
FROM {{ source('raw', 'tiktok_advertiser') }}
