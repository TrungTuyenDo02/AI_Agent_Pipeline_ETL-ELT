{{ config(materialized='view') }}

select
    "ID"::BIGINT as advertiser_id,
    "NAME"::VARCHAR as advertiser_name,
    "CURRENCY"::VARCHAR as currency
from {{ source('raw', 'tiktok_advertiser') }}
