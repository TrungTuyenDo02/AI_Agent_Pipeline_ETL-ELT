SELECT
    CAST(id AS VARCHAR) AS id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(list_id AS VARCHAR) AS list_id,
    CAST(segment_id AS VARCHAR) AS segment_id,
    CAST(segment_text AS VARCHAR) AS segment_text,
    CAST(start_time AS VARCHAR) AS start_time,
    CAST(create_time AS VARCHAR) AS create_time,
    CAST(status AS VARCHAR) AS status,
    CAST(title AS VARCHAR) AS title,
    CAST(trigger_settings AS VARCHAR) AS trigger_settings
FROM {{ source('raw', 'automation') }}
