DELETE FROM instance_data;
INSERT INTO instance_data SELECT 5 AS "aggregation", 
       instance_id, 
       (timestamp/300000)*300000 AS "timestamp", 
       CASE WHEN MAX(rowid) < 1000 
            THEN -MAX(anomaly_score) 
            ELSE MAX(anomaly_score) 
        END AS "anomaly_score"
FROM metric 
    JOIN metric_data 
    ON metric.metric_id = metric_data.metric_id  
    GROUP BY 1, 2, 3;
INSERT INTO instance_data SELECT 60 AS "aggregation", 
       instance_id, 
       (timestamp/3600000)*3600000 AS "timestamp", 
       CASE WHEN MAX(rowid) < 1000 
            THEN -MAX(anomaly_score) 
            ELSE MAX(anomaly_score) 
       END AS "anomaly_score"
FROM metric 
    JOIN metric_data 
    ON metric.metric_id = metric_data.metric_id  
    GROUP BY 1, 2, 3;
INSERT INTO instance_data SELECT 480 AS "aggregation", 
       instance_id, 
       (timestamp/28800000)*28800000 AS "timestamp", 
       CASE WHEN MAX(rowid) < 1000 
            THEN -MAX(anomaly_score) 
            ELSE MAX(anomaly_score) 
        END AS "anomaly_score"
FROM metric 
    JOIN metric_data 
    ON metric.metric_id = metric_data.metric_id  
    GROUP BY 1, 2, 3;
