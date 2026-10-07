SELECT
    CAST(id AS BIGINT) AS id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(_fivetran_synced AS TIMESTAMP) AS _fivetran_synced,
    CAST(email AS VARCHAR) AS email,
    CAST(name AS VARCHAR) AS name
FROM {{ source('raw', 'user') }}
