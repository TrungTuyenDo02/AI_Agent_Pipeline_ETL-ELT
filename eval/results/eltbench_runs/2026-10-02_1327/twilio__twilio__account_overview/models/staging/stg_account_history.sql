{{ config(materialized='table') }}

SELECT
    id,
    try_strptime(updated_at, '%Y-%m-%d %H:%M:%S.%f UTC') AS updated_at,
    try_strptime(_fivetran_synced, '%Y-%m-%d %H:%M:%S.%f UTC') AS _fivetran_synced,
    try_strptime(created_at, '%Y-%m-%d %H:%M:%S.%f UTC') AS created_at,
    friendly_name,
    owner_account_id,
    status,
    type
FROM {{ source('raw', 'account_history') }}
