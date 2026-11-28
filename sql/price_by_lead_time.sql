-- Nightly price by how far ahead the quoted stay starts, against each listing's peers.
SELECT CASE WHEN lead_days <= 1 THEN 1 WHEN lead_days <= 6 THEN 2 WHEN lead_days <= 13 THEN 3
            WHEN lead_days <= 29 THEN 4 WHEN lead_days <= 89 THEN 5 ELSE 6 END       AS band,
       ['0-1 days', '2-6 days', '7-13 days', '14-29 days', '30-89 days', '90+ days'][band] AS starts_in,
       count(*)                                                                     AS listings,
       CAST(round(median(price), 0) AS INTEGER)                                     AS price_median,
       round(100 * (median(ratio) - 1), 1)                                          AS vs_peers_pct
FROM priced_homes
WHERE ratio IS NOT NULL
GROUP BY band
ORDER BY band;
