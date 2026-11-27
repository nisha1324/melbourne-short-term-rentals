-- Active listings per council (LGA), how many are entire homes, and their median price.
SELECT
    a.lga,
    count(*)                                                                   AS active_listings,
    count(*) FILTER (WHERE room_type = 'Entire home/apt')                      AS entire_homes,
    round(100.0 * count(*) FILTER (WHERE room_type = 'Entire home/apt') / count(*), 1) AS entire_home_pct,
    CAST(round(median(price) FILTER (WHERE room_type = 'Entire home/apt'), 0) AS INTEGER)      AS entire_home_median_price,
    count(price) FILTER (WHERE room_type = 'Entire home/apt')                  AS entire_homes_with_price,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1)                         AS share_of_market_pct
FROM active a
GROUP BY a.lga
ORDER BY active_listings DESC, a.lga;
