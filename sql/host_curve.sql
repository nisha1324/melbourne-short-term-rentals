-- Concentration curve: the share of active listings run by the largest p% of hosts,
-- for p = 0, 1, ..., 100 (hosts rounded to the nearest whole host). Feeds chart 09.
WITH ranked AS (
    SELECT listings, row_number() OVER (ORDER BY listings DESC, host_id) AS rk FROM hosts
), tot AS (
    SELECT count(*) AS n, sum(listings) AS total FROM hosts
)
SELECT p                                                                      AS share_of_hosts_pct,
       CAST(round(p * any_value(t.n) / 100.0) AS INTEGER)                     AS hosts,
       round(100.0 * coalesce(sum(r.listings) FILTER (WHERE r.rk <= round(p * t.n / 100.0)), 0)
             / any_value(t.total), 2)                                         AS share_of_listings_pct
FROM ranked r, tot t, range(0, 101) s(p)
GROUP BY p, t.n
ORDER BY p;
