{{ config(materialized='view') }}

SELECT
    CAST(id AS VARCHAR) AS id,
    CAST(segment_id AS VARCHAR) AS segment_id
FROM {{ source('raw', 'automation') }}
