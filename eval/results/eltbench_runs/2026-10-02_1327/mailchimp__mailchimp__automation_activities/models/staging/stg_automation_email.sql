{{ config(materialized='view') }}

SELECT
    CAST(id AS VARCHAR) AS id,
    CAST(automation_id AS VARCHAR) AS automation_id
FROM {{ source('raw', 'automation_email') }}
