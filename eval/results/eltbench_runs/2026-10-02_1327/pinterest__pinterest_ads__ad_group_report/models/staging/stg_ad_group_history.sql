SELECT
    CAST(id AS BIGINT) AS id,
    CAST(campaign_id AS BIGINT) AS campaign_id,
    CAST(created_time AS VARCHAR) AS created_time,
    CAST(name AS VARCHAR) AS name,
    CAST(status AS VARCHAR) AS status,
    CAST(start_time AS VARCHAR) AS start_time,
    CAST(end_time AS VARCHAR) AS end_time
FROM {{ source('raw', 'ad_group_history') }}
