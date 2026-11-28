-- Who runs the active listings in each council. Host size is counted market-wide
-- (a host with 12 listings across Melbourne is an operator in every council it is in).
--   top10_share_pct / hosts_for_half / hhi are measured within the council; in a small
--   council the top 10 hosts are a large share of all hosts, so compare those with care.
--   single_host_entire_homes = entire homes whose host has no other active listing.
WITH per_host AS (
    SELECT lga, host_id, count(*) AS k FROM host_listings GROUP BY lga, host_id
), ranked AS (
    SELECT *,
           row_number() OVER w                                    AS rk,
           sum(k) OVER (w ROWS UNBOUNDED PRECEDING)               AS cum,
           sum(k) OVER (PARTITION BY lga)                         AS tot
    FROM per_host
    WINDOW w AS (PARTITION BY lga ORDER BY k DESC, host_id)
), conc AS (
    SELECT lga, count(*) AS hosts,
           round(100.0 * sum(k) FILTER (WHERE rk <= 10) / max(tot), 1) AS top10_share_pct,
           min(rk) FILTER (WHERE 2 * cum >= tot)                       AS hosts_for_half,
           CAST(round(10000.0 * sum(k * k) / (max(tot) * max(tot)), 0) AS INTEGER) AS hhi
    FROM ranked GROUP BY lga
)
SELECT l.lga,
       count(*)                                                                          AS active_listings,
       any_value(c.hosts)                                                                AS hosts,
       round(100.0 * count(*) FILTER (WHERE l.host_band = 1) / count(*), 1)              AS single_host_pct,
       round(100.0 * count(*) FILTER (WHERE l.host_band IN (2, 3)) / count(*), 1)        AS two_to_nine_pct,
       round(100.0 * count(*) FILTER (WHERE l.host_band >= 4) / count(*), 1)             AS operator_pct,
       count(DISTINCT l.host_id) FILTER (WHERE l.host_band >= 4)                         AS operators_present,
       count(*) FILTER (WHERE l.is_entire)                                               AS entire_homes,
       round(100.0 * count(*) FILTER (WHERE l.is_entire AND l.host_band >= 4)
             / nullif(count(*) FILTER (WHERE l.is_entire), 0), 1)                        AS operator_entire_pct,
       count(*) FILTER (WHERE l.is_entire AND l.host_band = 1)                           AS single_host_entire_homes,
       any_value(c.top10_share_pct)                                                      AS top10_share_pct,
       any_value(c.hosts_for_half)                                                       AS hosts_for_half,
       any_value(c.hhi)                                                                  AS hhi
FROM host_listings l
JOIN conc c USING (lga)
GROUP BY l.lga
ORDER BY operator_pct DESC, l.lga;
