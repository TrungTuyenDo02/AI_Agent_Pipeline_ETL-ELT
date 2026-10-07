WITH activities AS (
    SELECT
        a.action_type,
        a.campaign_id,
        a.member_id,
        a.list_id,
        a.activity_timestamp,
        a.ip_address,
        a.url,
        c.send_timestamp,
        md5(
            concat(
                coalesce(CAST(a.campaign_id AS VARCHAR), '_dbt_utils_surrogate_key_null_'), '-',
                coalesce(CAST(a.member_id AS VARCHAR), '_dbt_utils_surrogate_key_null_'), '-',
                coalesce(CAST(a.activity_timestamp AS VARCHAR), '_dbt_utils_surrogate_key_null_'), '-',
                coalesce(CAST(a.action_type AS VARCHAR), '_dbt_utils_surrogate_key_null_')
            )
        ) AS activity_id,
        md5(
            concat(
                coalesce(CAST(a.campaign_id AS VARCHAR), '_dbt_utils_surrogate_key_null_'), '-',
                coalesce(CAST(a.member_id AS VARCHAR), '_dbt_utils_surrogate_key_null_')
            )
        ) AS email_id
    FROM {{ ref('stg_campaign_recipient_activity') }} AS a
    INNER JOIN {{ ref('stg_campaign') }} AS c
        ON a.campaign_id = c.campaign_id
    WHERE c.send_timestamp IS NOT NULL
), enriched AS (
    SELECT
        action_type,
        campaign_id,
        member_id,
        list_id,
        CAST(activity_timestamp AS VARCHAR) AS activity_timestamp,
        ip_address,
        url,
        activity_id,
        email_id,
        CAST(send_timestamp AS VARCHAR) AS send_timestamp,
        date_diff('second', send_timestamp, activity_timestamp) / 60.0 AS time_since_send_minutes,
        date_diff('second', send_timestamp, activity_timestamp) / 3600.0 AS time_since_send_hours,
        date_diff('second', send_timestamp, activity_timestamp) / 86400.0 AS time_since_send_days
    FROM activities
)
SELECT
    action_type,
    campaign_id,
    member_id,
    list_id,
    activity_timestamp,
    ip_address,
    url,
    activity_id,
    email_id,
    send_timestamp,
    time_since_send_minutes,
    time_since_send_hours,
    time_since_send_days
FROM enriched
