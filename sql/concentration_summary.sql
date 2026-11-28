-- Market-wide concentration, for all active listings and for active entire homes.
--   hhi              = sum of squared host shares, 0-10,000 (10,000 = one host runs everything)
--   equivalent_hosts = 10,000 / hhi: how many equal-sized hosts would give the same concentration
--   hosts_for_half   = the fewest hosts (largest first) that together run half the listings
-- Operators are hosts with 10 or more active listings of any type (host_band 4-5);
-- single-listing hosts have exactly one active listing.
WITH per_host AS (
    SELECT 1 AS market_no, 'All active listings' AS market, host_id, host_band, count(*) AS n
    FROM host_listings GROUP BY host_id, host_band
    UNION ALL
    SELECT 2, 'Active entire homes', host_id, host_band, count(*)
    FROM host_listings WHERE is_entire GROUP BY host_id, host_band
), ranked AS (
    SELECT *,
           row_number() OVER w                                       AS rk,
           sum(n) OVER (w ROWS UNBOUNDED PRECEDING)                  AS cum,
           sum(n) OVER (PARTITION BY market_no)                      AS total
    FROM per_host
    WINDOW w AS (PARTITION BY market_no ORDER BY n DESC, host_id)
)
SELECT market_no, market,
       count(*)                                                          AS hosts,
       CAST(sum(n) AS BIGINT)                                            AS listings,
       round(sum(n) / count(*), 2)                                       AS listings_per_host,
       round(10000.0 * sum(n * n) / (max(total) * max(total)), 1)        AS hhi,
       CAST(round(max(total) * max(total) / sum(n * n), 0) AS INTEGER)   AS equivalent_hosts,
       min(rk) FILTER (WHERE 2 * cum >= total)                           AS hosts_for_half,
       round(100.0 * min(rk) FILTER (WHERE 2 * cum >= total) / count(*), 1) AS hosts_for_half_pct,
       count(*) FILTER (WHERE host_band >= 4)                            AS operators,
       round(100.0 * coalesce(sum(n) FILTER (WHERE host_band >= 4), 0) / max(total), 1) AS operator_share_pct,
       round(100.0 * coalesce(sum(n) FILTER (WHERE host_band = 1), 0) / max(total), 1)  AS single_listing_share_pct
FROM ranked
GROUP BY market_no, market
ORDER BY market_no;
