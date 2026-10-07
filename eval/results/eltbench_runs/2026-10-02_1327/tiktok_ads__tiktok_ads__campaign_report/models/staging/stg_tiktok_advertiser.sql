SELECT
    CAST(ID AS BIGINT) AS advertiser_id,
    CAST(NAME AS VARCHAR) AS advertiser_name,
    CAST(CURRENCY AS VARCHAR) AS currency,
    CAST(TIMEZONE AS VARCHAR) AS timezone,
    CAST(UPPER(STATUS) AS VARCHAR) AS status
FROM {{ source('raw', 'tiktok_advertiser') }}
