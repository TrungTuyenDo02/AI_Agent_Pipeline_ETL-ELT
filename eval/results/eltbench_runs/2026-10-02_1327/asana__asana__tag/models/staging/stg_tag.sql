SELECT
    CAST(id AS BIGINT) AS id,
    CAST(name AS VARCHAR) AS name,
    CAST(created_at AS VARCHAR) AS created_at
FROM {{ source('raw', 'tag') }}
