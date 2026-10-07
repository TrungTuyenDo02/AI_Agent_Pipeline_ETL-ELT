SELECT
    CAST(id AS VARCHAR) AS campaign_id,
    CAST(list_id AS VARCHAR) AS list_id,
    CAST(status AS VARCHAR) AS status
FROM {{ source('raw', 'campaign') }}
WHERE lower(_fivetran_deleted) = 'false'
