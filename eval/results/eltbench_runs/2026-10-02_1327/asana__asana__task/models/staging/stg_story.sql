SELECT
    CAST(id AS BIGINT) AS id,
    CAST(target_id AS BIGINT) AS target_id
FROM {{ source('raw', 'story') }}
