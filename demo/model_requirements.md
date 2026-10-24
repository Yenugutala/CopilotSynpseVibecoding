# Gold model requirements (input for demo/generate.sh)

One `##` section per gold model. The heading is the model name. The text is the plain-English requirement.

## customer_order_summary
One row per customer showing customer id, full name, email, country, signup date, total number of orders,
total quantity, total revenue (quantity x unit price), first order date and last order date.
Exclude cancelled orders. Keep customers who have no orders, with totals of 0.
