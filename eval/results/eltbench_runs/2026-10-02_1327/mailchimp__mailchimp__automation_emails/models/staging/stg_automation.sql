SELECT
    CAST(id AS VARCHAR) AS id,
    CAST(list_id AS VARCHAR) AS list_id,
    CAST(segment_id AS VARCHAR) AS segment_id
FROM {{ source('raw', 'automation') }}
WHERE lower(COALESCE(CAST(_fivetran_deleted AS VARCHAR), 'false')) <> 'true'
