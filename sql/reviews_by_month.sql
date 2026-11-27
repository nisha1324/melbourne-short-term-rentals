-- Reviews per month, a rough guide to stays over time. Only listings still in
-- the snapshot are counted, so earlier years are undercounted (listings that
-- have since been removed take their reviews with them).
SELECT date_trunc('month', date)::DATE AS month, count(*) AS reviews
FROM reviews
GROUP BY 1
ORDER BY 1;
