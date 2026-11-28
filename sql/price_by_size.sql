-- Entire homes by bedrooms: quoted nightly price and price per guest.
SELECT bed_band,
       CASE bed_band WHEN 0 THEN 'Studio' WHEN 1 THEN '1 bedroom' WHEN 5 THEN '5+ bedrooms'
                     ELSE bed_band || ' bedrooms' END                          AS size,
       count(*)                                                                AS listings,
       CAST(round(quantile_cont(price, 0.25), 0) AS INTEGER)                   AS price_p25,
       CAST(round(median(price), 0) AS INTEGER)                                AS price_median,
       CAST(round(quantile_cont(price, 0.75), 0) AS INTEGER)                   AS price_p75,
       median(accommodates)                                                    AS median_guests,
       CAST(round(median(price / accommodates), 0) AS INTEGER)                 AS per_guest_median
FROM priced_homes
GROUP BY bed_band
ORDER BY bed_band;
