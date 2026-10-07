SELECT
    CAST(id AS VARCHAR) AS member_id,
    CAST(list_id AS VARCHAR) AS list_id,
    CAST(status AS VARCHAR) AS status,
    CAST(timestamp_signup AS DATE) AS timestamp_signup
FROM {{ source('raw', 'member') }}
