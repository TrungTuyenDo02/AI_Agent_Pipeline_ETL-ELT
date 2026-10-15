select cast(created_ts as timestamp)::date as order_date, count(*) as refund_count,
    sum(cast(amount_vnd as bigint)) as refund_vnd
from {{ source('raw', 'website_orders') }} where status = 'refunded' group by 1
