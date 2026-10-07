{{ config(materialized='table') }}

SELECT
    CAST(AD_ID AS BIGINT) AS ad_id,
    CAST(UPDATED_AT AS TIMESTAMP) AS updated_at,
    CAST(ADVERTISER_ID AS BIGINT) AS advertiser_id,
    CAST(OPERATION_STATUS AS VARCHAR) AS operation_status,
    CAST(SECONDARY_STATUS AS VARCHAR) AS secondary_status
FROM {{ source('raw', 'tiktok_ad_history') }}
