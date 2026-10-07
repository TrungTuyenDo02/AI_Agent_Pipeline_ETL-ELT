SELECT
    CAST(id AS BIGINT) AS advertiser_id,
    CAST(name AS VARCHAR) AS advertiser_name,
    CAST(status AS VARCHAR) AS advertiser_status,
    CAST(currency AS VARCHAR) AS currency
FROM {{ source('raw', 'advertiser_history') }}
