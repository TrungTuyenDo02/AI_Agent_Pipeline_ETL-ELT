SELECT
    CAST(id AS VARCHAR) AS id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(_fivetran_synced AS TIMESTAMP) AS _fivetran_synced,
    CASE WHEN COALESCE(backfill, FALSE) THEN 'true' ELSE 'false' END AS backfill,
    CAST(compensation_band_currency AS VARCHAR) AS compensation_band_currency,
    CAST(compensation_band_interval AS VARCHAR) AS compensation_band_interval,
    CAST(compensation_band_max AS BIGINT) AS compensation_band_max,
    CAST(compensation_band_min AS BIGINT) AS compensation_band_min,
    CAST(created_at AS VARCHAR) AS created_at,
    CAST(creator_id AS VARCHAR) AS creator_id,
    CASE
        WHEN lower(employment_status) = 'full-time' THEN 'full-time'
        WHEN lower(employment_status) = 'part-time' THEN 'part-time'
        WHEN lower(employment_status) = 'intern' THEN 'intern'
        WHEN lower(employment_status) = 'contractor' THEN 'contractor'
        WHEN lower(employment_status) = 'temp-worker' THEN 'temp-worker'
        ELSE employment_status
    END AS employment_status,
    CASE
        WHEN lower(trim(COALESCE(headcount_infinite, ''))) IN ('true', '1', 'yes') THEN 'unlimited'
        ELSE CAST(headcount_hired AS VARCHAR)
    END AS headcount_hired,
    CAST(headcount_total AS BIGINT) AS headcount_total,
    CAST(hiring_manager_id AS VARCHAR) AS hiring_manager_id,
    CAST(internal_notes AS VARCHAR) AS internal_notes,
    CAST(location AS VARCHAR) AS location,
    CAST(name AS VARCHAR) AS name,
    CAST(owner_id AS VARCHAR) AS owner_id,
    CAST(requisition_code AS BIGINT) AS requisition_code,
    CASE
        WHEN lower(status) = 'open' THEN 'open'
        WHEN lower(status) = 'onhold' THEN 'onHold'
        WHEN lower(status) = 'closed' THEN 'closed'
        WHEN lower(status) = 'draft' THEN 'draft'
        ELSE status
    END AS status,
    CAST(team AS VARCHAR) AS team
FROM {{ source('raw', 'requisition') }}
