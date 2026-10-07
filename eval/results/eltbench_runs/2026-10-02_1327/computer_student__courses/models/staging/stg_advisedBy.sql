SELECT
    CAST(p_id AS BIGINT) AS p_id,
    CAST(p_id_dummy AS BIGINT) AS p_id_dummy
FROM {{ source('raw', 'advisedBy') }}
