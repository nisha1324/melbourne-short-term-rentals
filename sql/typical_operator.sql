-- The typical operator: medians across hosts with 10-49, 50+ and 10+ active listings.
--   one_council_mostly_pct = operators with 75% or more of their listings in one council
--   vs_peers_pct           = median, across operators, of the median price ratio of their
--                            scored entire homes (Part 2), minus 1
WITH ops AS (SELECT * FROM hosts WHERE host_band >= 4),
groups AS (
    SELECT 1 AS row_no, '10-49 listings' AS operators, * FROM ops WHERE host_band = 4
    UNION ALL SELECT 2, '50+ listings', * FROM ops WHERE host_band = 5
    UNION ALL SELECT 3, 'All operators (10+)', * FROM ops
)
SELECT row_no, operators,
       count(*)                                                              AS hosts,
       median(listings)                                                      AS median_listings,
       median(councils)                                                      AS median_councils,
       round(100 * median(entire_homes / listings), 1)                       AS median_entire_pct,
       round(100.0 * count(*) FILTER (WHERE entire_homes = listings) / count(*), 1) AS only_entire_pct,
       round(100.0 * count(*) FILTER (WHERE in_main_council >= 0.75 * listings) / count(*), 1)
                                                                             AS one_council_mostly_pct,
       round(100.0 * count(*) FILTER (WHERE in_inner3 > 0) / count(*), 1)    AS any_inner3_pct,
       round(100 * (median(median_ratio) - 1), 1)                            AS vs_peers_pct,
       round(100.0 * count(*) FILTER (WHERE superhost) / count(*), 1)        AS superhost_pct
FROM groups
GROUP BY row_no, operators
ORDER BY row_no;
