-- Hosts by size, counted two ways: by ACTIVE listings (used in this project) and by all
-- their listings in the snapshot (Inside Airbnb's calculated_host_listings_count, which
-- also counts dormant listings carried over from earlier scrapes). A host with no active
-- listing appears only in the second count.
WITH snap AS (
    SELECT host_id, max(host_listings_in_snapshot) AS n FROM listings GROUP BY host_id
), act AS (
    SELECT host_id, listings AS n FROM hosts
), banded AS (
    SELECT 'active' AS counted, n FROM act UNION ALL SELECT 'snapshot', n FROM snap
)
SELECT CASE WHEN n = 1 THEN 1 WHEN n <= 4 THEN 2 WHEN n <= 9 THEN 3 WHEN n <= 49 THEN 4 ELSE 5 END AS band,
       ['1 listing', '2-4 listings', '5-9 listings', '10-49 listings', '50+ listings'][band]      AS host_size,
       count(*) FILTER (WHERE counted = 'active')                                                 AS hosts_by_active_listings,
       count(*) FILTER (WHERE counted = 'snapshot')                                               AS hosts_by_all_listings
FROM banded
GROUP BY band
ORDER BY band;
