-- How many active listings each host has in the active market, in bands.
-- Counted here from host_id, not from Inside Airbnb's
-- calculated_host_listings_count, which also counts dormant listings.
WITH per_host AS (
    SELECT host_id, count(*) AS n FROM active GROUP BY host_id
), banded AS (
    SELECT CASE WHEN n = 1 THEN 1 WHEN n <= 4 THEN 2 WHEN n <= 9 THEN 3
                WHEN n <= 49 THEN 4 ELSE 5 END AS band, n
    FROM per_host
)
SELECT band,
       ['1 listing', '2-4 listings', '5-9 listings', '10-49 listings', '50+ listings'][band] AS host_size,
       count(*) AS hosts,
       CAST(sum(n) AS BIGINT) AS active_listings,
       round(100.0 * sum(n) / sum(sum(n)) OVER (), 1) AS share_of_listings_pct
FROM banded
GROUP BY band
ORDER BY band;
