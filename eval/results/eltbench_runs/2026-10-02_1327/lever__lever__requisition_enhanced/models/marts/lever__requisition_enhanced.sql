WITH requisitions AS (
    SELECT
        CAST(backfill AS VARCHAR) AS is_backfill,
        CAST(compensation_band_currency AS VARCHAR) AS compensation_band_currency,
        CAST(compensation_band_interval AS VARCHAR) AS compensation_band_interval,
        CAST(compensation_band_max AS BIGINT) AS compensation_band_max,
        CAST(compensation_band_min AS BIGINT) AS compensation_band_min,
        CAST(created_at AS VARCHAR) AS created_at,
        CAST(creator_id AS VARCHAR) AS creator_user_id,
        CAST(employment_status AS VARCHAR) AS employment_status,
        CAST(headcount_hired AS VARCHAR) AS headcount_hired,
        CAST(headcount_total AS BIGINT) AS headcount_total_allotted,
        CAST(hiring_manager_id AS VARCHAR) AS hiring_manager_user_id,
        CAST(id AS VARCHAR) AS requisition_id,
        CAST(internal_notes AS VARCHAR) AS internal_notes,
        CAST(location AS VARCHAR) AS job_location,
        CAST(name AS VARCHAR) AS job_title,
        CAST(owner_id AS VARCHAR) AS owner_user_id,
        CAST(requisition_code AS BIGINT) AS requisition_code,
        CAST(status AS VARCHAR) AS status,
        CAST(team AS VARCHAR) AS job_team
    FROM {{ ref('stg_requisition') }}
    WHERE COALESCE(_fivetran_deleted, FALSE) <> TRUE
), posting_counts AS (
    SELECT
        requisition_id,
        COUNT(DISTINCT posting_id)::BIGINT AS count_postings
    FROM {{ ref('stg_requisition_posting') }}
    WHERE COALESCE(_fivetran_deleted, FALSE) <> TRUE
    GROUP BY requisition_id
), offer_counts AS (
    SELECT
        requisition_id,
        COUNT(DISTINCT offer_id)::BIGINT AS count_offers
    FROM {{ ref('stg_requisition_offer') }}
    WHERE COALESCE(_fivetran_deleted, FALSE) <> TRUE
    GROUP BY requisition_id
)
SELECT
    r.is_backfill,
    r.compensation_band_currency,
    r.compensation_band_interval,
    r.compensation_band_max,
    r.compensation_band_min,
    r.created_at,
    r.creator_user_id,
    r.employment_status,
    r.headcount_hired,
    r.headcount_total_allotted,
    r.hiring_manager_user_id,
    r.requisition_id,
    r.internal_notes,
    r.job_location,
    r.job_title,
    r.owner_user_id,
    r.requisition_code,
    r.status,
    r.job_team,
    COALESCE(p.count_postings, 0)::BIGINT AS count_postings,
    CASE WHEN COALESCE(p.count_postings, 0) > 0 THEN 'true' ELSE 'false' END AS has_posting,
    COALESCE(o.count_offers, 0)::BIGINT AS count_offers,
    CASE WHEN COALESCE(o.count_offers, 0) > 0 THEN 'true' ELSE 'false' END AS has_offer
FROM requisitions AS r
LEFT JOIN posting_counts AS p
    ON r.requisition_id = p.requisition_id
LEFT JOIN offer_counts AS o
    ON r.requisition_id = o.requisition_id
