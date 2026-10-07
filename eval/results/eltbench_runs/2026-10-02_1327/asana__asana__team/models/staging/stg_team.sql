SELECT
    CAST(id AS BIGINT) AS id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(_fivetran_synced AS TIMESTAMP) AS _fivetran_synced,
    CAST(name AS VARCHAR) AS name,
    CAST(organization_id AS BIGINT) AS organization_id
FROM {{ source('raw', 'team') }}
