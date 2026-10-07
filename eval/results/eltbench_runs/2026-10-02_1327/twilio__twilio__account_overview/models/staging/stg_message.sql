{{ config(materialized='table') }}

SELECT
    id,
    _fivetran_synced,
    account_id,
    body,
    created_at,
    date_sent,
    direction,
    error_code,
    error_message,
    message_from,
    messaging_service_sid,
    num_media,
    num_segments,
    price,
    upper(price_unit) AS price_unit,
    status,
    message_to,
    updated_at
FROM {{ source('raw', 'message') }}
