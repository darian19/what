DROP TABLE IF EXISTS instance_data;
DROP TABLE IF EXISTS annotation;
DROP TABLE IF EXISTS notification;
DROP TABLE IF EXISTS metric_data;
DROP TABLE IF EXISTS metric;
CREATE TABLE metric    (metric_id TEXT primary key,
						last_rowid INTEGER DEFAULT 0,
						name TEXT,
						instance_id TEXT,
						server_name TEXT,
						last_timestamp DATETIME,
                        parameters TEXT);
CREATE INDEX metric_metric_instance_idx on metric(instance_id);
CREATE TABLE metric_data   (metric_id TEXT REFERENCES metric(metric_id) ON DELETE CASCADE,
                            rowid INTEGER,
		                    timestamp DATETIME,
		                    metric_value FLOAT,
		                    anomaly_score FLOAT,
		                    PRIMARY KEY (metric_id, rowid) ON CONFLICT IGNORE);
CREATE INDEX metric_data_anomaly_score_idx on metric_data(anomaly_score);
CREATE INDEX metric_data_timestamp_idx on metric_data(timestamp);
CREATE TABLE notification  (_id integer primary key autoincrement,
                            notification_id TEXT UNIQUE ON CONFLICT IGNORE,
		                    metric_id TEXT REFERENCES metric(metric_id) ON DELETE CASCADE,
		                    timestamp DATETIME,
		                    read INTEGER,
		                    description TEXT);
CREATE TABLE instance_data (aggregation INTEGER,
                            instance_id TEXT,
                            timestamp DATETIME,
                            anomaly_score FLOAT,
                            PRIMARY KEY(aggregation, instance_id, timestamp));
CREATE TABLE annotation (annotation_id TEXT PRIMARY KEY,
                         timestamp DATETIME,
                         created DATETIME,
                         device TEXT,
                         user TEXT,
                         instance_id TEXT,
                         message TEXT,
                         data TEXT);
CREATE INDEX annotation_timestamp_idx ON annotation(timestamp);
CREATE INDEX annotation_instance_id_idx ON annotation(instance_id);
