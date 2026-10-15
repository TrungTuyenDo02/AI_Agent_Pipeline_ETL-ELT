select strptime(order_date, '%d/%m/%Y')::date as order_date, count(*) as cancelled_count,
    sum(cast(replace(total_amount, '.', '') as bigint)) as cancelled_vnd
from {{ source('raw', 'shopee_orders') }} where status = 'CANCELLED' group by 1
