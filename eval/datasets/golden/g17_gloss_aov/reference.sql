select cast(created_ts as timestamp)::date as order_date,
    cast(round(sum(cast(amount_vnd as bigint)) * 1.0 / count(*)) as bigint) as aov_vnd
from {{ source('raw', 'website_orders') }} where status = 'paid' group by 1
