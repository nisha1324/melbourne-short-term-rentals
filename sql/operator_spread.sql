-- Operators (hosts with 10 or more active listings) by how many councils their listings
-- are in, with what their portfolios look like. Medians are across operators.
--   main_council_share = share of an operator's listings in the council where it has most
WITH ops AS (
    SELECT *,
           CASE WHEN councils = 1 THEN 1 WHEN councils <= 3 THEN 2 WHEN councils <= 9 THEN 3 ELSE 4 END AS spread
    FROM hosts WHERE host_band >= 4
)
SELECT spread AS band,
       ['1 council', '2-3 councils', '4-9 councils', '10+ councils'][spread]           AS councils,
       count(*)                                                                         AS operators,
       CAST(sum(listings) AS BIGINT)                                                    AS active_listings,
       median(listings)                                                                 AS median_listings,
       round(100.0 * sum(entire_homes) / sum(listings), 1)                              AS entire_pct,
       round(100 * median(in_main_council / listings), 1)                               AS median_main_council_pct,
       round(100.0 * sum(in_inner3) / sum(listings), 1)                                 AS inner3_pct
FROM ops
GROUP BY spread
ORDER BY spread;
