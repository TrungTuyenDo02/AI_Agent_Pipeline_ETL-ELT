SELECT
    CAST(id AS VARCHAR) AS campaign_id,
    CAST(list_id AS VARCHAR) AS list_id,
    CAST(send_time AS TIMESTAMP) AS send_timestamp
FROM {{ source('raw', 'campaign') }}
