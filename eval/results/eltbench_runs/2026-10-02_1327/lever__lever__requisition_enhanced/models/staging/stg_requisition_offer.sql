SELECT
    CAST(offer_id AS VARCHAR) AS offer_id,
    CAST(requisition_id AS VARCHAR) AS requisition_id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(_fivetran_synced AS TIMESTAMP) AS _fivetran_synced
FROM {{ source('raw', 'requisition_offer') }}
