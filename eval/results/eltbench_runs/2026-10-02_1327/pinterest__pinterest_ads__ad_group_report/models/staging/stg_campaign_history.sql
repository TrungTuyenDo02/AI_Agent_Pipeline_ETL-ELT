SELECT
    CAST(id AS BIGINT) AS id,
    CAST(name AS VARCHAR) AS name,
    CAST(status AS VARCHAR) AS status,
    CAST(advertiser_id AS BIGINT) AS advertiser_id
FROM {{ source('raw', 'campaign_history') }}
