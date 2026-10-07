SELECT
    CAST(id AS VARCHAR) AS automation_id,
    CAST(list_id AS VARCHAR) AS list_id,
    CAST(status AS VARCHAR) AS status
FROM {{ source('raw', 'automation') }}
WHERE lower(_fivetran_deleted) = 'false'
