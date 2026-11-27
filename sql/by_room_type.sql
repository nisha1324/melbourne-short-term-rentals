-- Active listings by room type, with the nightly price quoted for each.
SELECT
    room_type,
    count(*)                                                  AS active_listings,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1)        AS share_pct,
    count(price)                                              AS with_price,
    CAST(round(quantile_cont(price, 0.25), 0) AS INTEGER)                      AS price_p25,
    CAST(round(median(price), 0) AS INTEGER)                                   AS price_median,
    CAST(round(quantile_cont(price, 0.75), 0) AS INTEGER)                      AS price_p75,
    round(median(accommodates), 1)                            AS median_guests
FROM active
GROUP BY room_type
ORDER BY active_listings DESC;
