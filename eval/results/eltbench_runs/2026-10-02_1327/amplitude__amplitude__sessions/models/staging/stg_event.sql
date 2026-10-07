SELECT
    CAST(id AS BIGINT) AS id,
    CAST(user_id AS VARCHAR) AS user_id,
    CAST(session_id AS BIGINT) AS session_id,
    CAST(event_time AS TIMESTAMP) AS event_time
FROM {{ source('raw', 'event') }}
