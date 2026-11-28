-- Entire homes by how many guests they take: price and price per guest.
SELECT CASE WHEN accommodates <= 2 THEN 1 WHEN accommodates <= 4 THEN 2 WHEN accommodates <= 6 THEN 3
            WHEN accommodates <= 8 THEN 4 ELSE 5 END                           AS band,
       ['1-2 guests', '3-4 guests', '5-6 guests', '7-8 guests', '9+ guests'][band] AS guests,
       count(*)                                                                AS listings,
       CAST(round(median(price), 0) AS INTEGER)                                AS price_median,
       CAST(round(median(price / accommodates), 0) AS INTEGER)                 AS per_guest_median
FROM priced_homes
GROUP BY band
ORDER BY band;
