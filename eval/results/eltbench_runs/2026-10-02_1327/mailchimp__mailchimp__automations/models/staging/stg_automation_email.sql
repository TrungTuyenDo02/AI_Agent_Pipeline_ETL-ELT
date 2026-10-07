SELECT
    CAST(id AS VARCHAR) AS id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(automation_id AS VARCHAR) AS automation_id
FROM {{ source('raw', 'automation_email') }}
