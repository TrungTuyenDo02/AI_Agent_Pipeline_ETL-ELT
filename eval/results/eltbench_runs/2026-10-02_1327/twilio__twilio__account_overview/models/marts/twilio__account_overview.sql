{{ config(materialized='table') }}

WITH latest_account_history AS (
    SELECT
        id,
        friendly_name,
        status,
        type,
        updated_at,
        row_number() OVER (
            PARTITION BY id
            ORDER BY updated_at DESC
        ) AS rn
    FROM {{ ref('stg_account_history') }}
),
account_attributes AS (
    SELECT
        id,
        friendly_name,
        status,
        type
    FROM latest_account_history
    WHERE rn = 1
),
message_activity AS (
    SELECT
        message.account_id,
        account_attributes.friendly_name AS account_name,
        account_attributes.status AS account_status,
        account_attributes.type AS account_type,
        CAST(message.date_sent AS DATE) AS date_day,
        CAST(date_trunc('week', message.date_sent) AS DATE) AS date_week,
        CAST(date_trunc('month', message.date_sent) AS DATE) AS date_month,
        message.price_unit,
        message.direction,
        message.status,
        message.price
    FROM {{ ref('stg_message') }} AS message
    LEFT JOIN account_attributes
        ON message.account_id = account_attributes.id
)
SELECT
    account_id,
    account_name,
    account_status,
    account_type,
    date_day,
    date_week,
    date_month,
    price_unit,
    count(*) FILTER (WHERE starts_with(direction, 'outbound')) AS total_outbound_messages,
    count(*) FILTER (WHERE NOT starts_with(direction, 'outbound')) AS total_inbound_messages,
    count(*) FILTER (WHERE status = 'accepted') AS total_accepted_messages,
    count(*) FILTER (WHERE status = 'scheduled') AS total_scheduled_messages,
    count(*) FILTER (WHERE status = 'canceled') AS total_canceled_messages,
    count(*) FILTER (WHERE status = 'queued') AS total_queued_messages,
    count(*) FILTER (WHERE status = 'sending') AS total_sending_messages,
    count(*) FILTER (WHERE status = 'sent') AS total_sent_messages,
    count(*) FILTER (WHERE status = 'failed') AS total_failed_messages,
    count(*) FILTER (WHERE status = 'delivered') AS total_delivered_messages,
    count(*) FILTER (WHERE status = 'undelivered') AS total_undelivered_messages,
    count(*) FILTER (WHERE status = 'receiving') AS total_receiving_messages,
    count(*) FILTER (WHERE status = 'received') AS total_received_messages,
    count(*) FILTER (WHERE status = 'read') AS total_read_messages,
    count(*) AS total_messages,
    sum(price) AS total_messages_spend
FROM message_activity
GROUP BY
    account_id,
    account_name,
    account_status,
    account_type,
    date_day,
    date_week,
    date_month,
    price_unit
