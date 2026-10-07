SELECT
    CAST(id AS VARCHAR) AS id,
    NULLIF(CAST(segment_id AS VARCHAR), 'null') AS segment_id,
    CAST(send_time AS TIMESTAMP) AS send_time,
    CAST(status AS VARCHAR) AS status
FROM {{ source('raw', 'campaign') }}
