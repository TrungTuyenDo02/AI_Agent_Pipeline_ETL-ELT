WITH report AS (
    SELECT
        date AS date_day,
        ad_group_id,
        ad_group_name,
        ad_group_status,
        campaign_id,
        advertiser_id,
        impression_1,
        impression_2,
        clickthrough_1,
        clickthrough_2,
        spend_in_micro_dollar,
        total_conversions,
        total_conversions_quantity,
        total_conversions_value_in_micro_dollar
    FROM {{ ref('stg_ad_group_report') }}
),
ad_groups AS (
    SELECT
        id AS ad_group_id,
        created_time AS created_at,
        start_time,
        end_time
    FROM {{ ref('stg_ad_group_history') }}
),
campaigns AS (
    SELECT
        id AS campaign_id,
        name AS campaign_name,
        status AS campaign_status
    FROM {{ ref('stg_campaign_history') }}
),
advertisers AS (
    SELECT
        id AS advertiser_id,
        name AS advertiser_name
    FROM {{ ref('stg_advertiser_history') }}
)
SELECT
    report.date_day AS date_day,
    advertisers.advertiser_name AS advertiser_name,
    report.advertiser_id AS advertiser_id,
    campaigns.campaign_name AS campaign_name,
    campaigns.campaign_status AS campaign_status,
    report.campaign_id AS campaign_id,
    report.ad_group_name AS ad_group_name,
    report.ad_group_id AS ad_group_id,
    ad_groups.created_at AS created_at,
    ad_groups.start_time AS start_time,
    ad_groups.end_time AS end_time,
    report.ad_group_status AS ad_group_status,
    CAST(COALESCE(report.spend_in_micro_dollar, 0) AS DOUBLE) / 1000000.0 AS spend,
    CAST(COALESCE(report.clickthrough_1, 0) + COALESCE(report.clickthrough_2, 0) AS BIGINT) AS clicks,
    CAST(COALESCE(report.impression_1, 0) + COALESCE(report.impression_2, 0) AS BIGINT) AS impressions,
    CAST(COALESCE(report.total_conversions, 0) AS BIGINT) AS total_conversions,
    CAST(COALESCE(report.total_conversions_quantity, 0) AS BIGINT) AS total_conversions_quantity,
    CAST(COALESCE(report.total_conversions_value_in_micro_dollar, 0) AS DOUBLE) / 1000000.0 AS total_conversions_value
FROM report
LEFT JOIN ad_groups
    ON report.ad_group_id = ad_groups.ad_group_id
LEFT JOIN campaigns
    ON report.campaign_id = campaigns.campaign_id
LEFT JOIN advertisers
    ON report.advertiser_id = advertisers.advertiser_id
