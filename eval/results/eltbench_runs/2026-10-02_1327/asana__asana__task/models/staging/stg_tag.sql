SELECT
    CAST(id AS BIGINT) AS id,
    CAST(name AS VARCHAR) AS name
FROM {{ source('raw', 'tag') }}
