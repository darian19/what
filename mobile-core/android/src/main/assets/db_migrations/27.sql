delete from metric;
delete from metric_data;
delete from instance_data;
delete from annotation;
delete from notification;
drop table metric;
CREATE TABLE metric (metric_id TEXT primary key,
						last_rowid INTEGER DEFAULT 0,
						name TEXT,
						instance_id TEXT,
						server_name TEXT,
						last_timestamp DATETIME,
                        parameters TEXT);
