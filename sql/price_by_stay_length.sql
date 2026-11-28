-- Nightly price by the length of the quoted stay, against each listing's peers.
SELECT CASE WHEN stay_nights = 1 THEN 1 WHEN stay_nights = 2 THEN 2 WHEN stay_nights <= 6 THEN 3
            WHEN stay_nights <= 27 THEN 4 ELSE 5 END                                AS band,
       ['1 night', '2 nights', '3-6 nights', '7-27 nights', '28+ nights'][band]     AS quoted_stay,
       count(*)                                                                     AS listings,
       CAST(round(median(price), 0) AS INTEGER)                                     AS price_median,
       round(100 * (median(ratio) - 1), 1)                                          AS vs_peers_pct
FROM priced_homes
WHERE ratio IS NOT NULL
GROUP BY band
ORDER BY band;
