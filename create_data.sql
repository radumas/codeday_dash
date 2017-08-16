DROP TABLE public.bluetooth_avg_jan;
WITH agg AS (
SELECT analysis_id,
date_trunc('hour'::text, datetime_bin)::TIME + trunc(date_part('minute'::text, datetime_bin) / 15::double precision) * '00:15:00'::interval AS "Time", AVG(tt)::INT
FROM bluetooth.aggr_5min
WHERE EXTRACT('isodow' FROM datetime_bin) <6 AND datetime_bin >= '2017-01-01' 
AND datetime_bin < '2017-02-01'
GROUP BY analysis_id, "Time" 
)
SELECT segment_id, segment_name, "Time", avg
INTO public.bluetooth_avg_jan
FROM agg
INNER JOIN (SELECT DISTINCT segment_id, analysis_id, start_road ||': ' || start_crossstreet ||' to '||end_crossstreet as segment_name, (generate_series(0,287) * interval '5 minutes')::TIME "Time"
FROM bluetooth.ref_segments) all_segs USING (analysis_id, "Time");

ALTER TABLE public.bluetooth_avg_jan OWNER TO rdumas;