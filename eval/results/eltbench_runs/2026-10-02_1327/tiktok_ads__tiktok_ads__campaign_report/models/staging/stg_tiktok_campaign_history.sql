SELECT
    CAST(CAMPAIGN_ID AS BIGINT) AS campaign_id,
    CAST(UPDATED_AT AS TIMESTAMP) AS updated_at,
    CAST(ADVERTISER_ID AS BIGINT) AS advertiser_id,
    CAST(CAMPAIGN_NAME AS VARCHAR) AS campaign_name,
    CAST(UPPER(OPERATION_STATUS) AS VARCHAR) AS operation_status,
    CAST(CREATE_TIME AS TIMESTAMP) AS create_time
FROM {{ source('raw', 'tiktok_campaign_history') }}
