CREATE TABLE annotation (annotation_id TEXT primary key,
                         timestamp DATETIME,
                         created DATETIME,
                         device TEXT,
                         user TEXT,
                         instance_id,
                         message TEXT,
                         data TEXT);
CREATE INDEX annotation_timestamp_idx on annotation(timestamp);
CREATE INDEX annotation_instance_id_idx on annotation(instance_id);
