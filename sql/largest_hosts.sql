-- Share of the active market run by the largest hosts. Hosts are ranked by active
-- listings for the listings column and by active entire homes for the entire-homes
-- column; the total for the top k does not depend on how ties are broken.
WITH ranked AS (
    SELECT listings, entire_homes,
           row_number() OVER (ORDER BY listings DESC, host_id)     AS rk,
           row_number() OVER (ORDER BY entire_homes DESC, host_id) AS rk_entire
    FROM hosts
), tot AS (
    SELECT count(*) AS hosts, sum(listings) AS listings, sum(entire_homes) AS entire FROM hosts
)
SELECT k                                                                         AS largest_hosts,
       round(100.0 * k / any_value(t.hosts), 2)                                  AS share_of_hosts_pct,
       CAST(sum(r.listings) FILTER (WHERE r.rk <= k) AS BIGINT)                  AS active_listings,
       round(100.0 * sum(r.listings) FILTER (WHERE r.rk <= k) / any_value(t.listings), 1) AS share_of_listings_pct,
       round(100.0 * sum(r.entire_homes) FILTER (WHERE r.rk_entire <= k) / any_value(t.entire), 1)
                                                                                 AS share_of_entire_homes_pct
FROM ranked r, tot t, (VALUES (1), (10), (50), (100), (500), (1000)) v(k)
WHERE k <= t.hosts
GROUP BY k
ORDER BY k;
