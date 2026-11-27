-- How big the market is depends on which listings count. Each row is a
-- separate definition over the whole snapshot (they are not nested steps).
SELECT 1 AS row_no, 'All listings in the snapshot' AS definition, count(*) AS listings, count(DISTINCT host_id) AS hosts
FROM listings
UNION ALL
SELECT 2, 'Found in this scrape (not carried over from an earlier one)', count(*), count(DISTINCT host_id)
FROM listings WHERE scrape_source = 'city scrape'
UNION ALL
SELECT 3, 'With a quoted price', count(*), count(DISTINCT host_id)
FROM listings WHERE price IS NOT NULL
UNION ALL
SELECT 4, 'At least one open night in the next 365 days', count(*), count(DISTINCT host_id)
FROM listings WHERE availability_365 > 0
UNION ALL
SELECT 5, 'Reviewed in the last 12 months (the active market used here)', count(*), count(DISTINCT host_id)
FROM active
UNION ALL
SELECT 6, 'Active and with a quoted price', count(*), count(DISTINCT host_id)
FROM active WHERE price IS NOT NULL
ORDER BY row_no;
