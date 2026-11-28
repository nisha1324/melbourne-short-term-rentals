-- Short stays (1-3 nights) starting in the 60 days after the scrape, by which nights they cover.
WITH s AS (
    SELECT *, CASE WHEN gf_weekend THEN 1 WHEN has_weekend THEN 2 ELSE 3 END AS band
    FROM priced_homes
    WHERE ratio IS NOT NULL AND stay_nights BETWEEN 1 AND 3 AND lead_days < 60
)
SELECT band,
       ['Includes 25 or 26 Sep (Grand Final eve and day)', 'Includes a Friday or Saturday night (other weeks)',
        'Sunday to Thursday nights only'][band]                                     AS stay_covers,
       count(*)                                                                     AS listings,
       CAST(round(median(price), 0) AS INTEGER)                                     AS price_median,
       round(100 * (median(ratio) - 1), 1)                                          AS vs_peers_pct
FROM s
GROUP BY band
ORDER BY band;
