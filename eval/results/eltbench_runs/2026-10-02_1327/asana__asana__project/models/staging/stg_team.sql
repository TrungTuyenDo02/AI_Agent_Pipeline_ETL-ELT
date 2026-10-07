SELECT
    CAST(id AS BIGINT) AS id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(name AS VARCHAR) AS name
FROM {{ source('raw', 'team') }}
