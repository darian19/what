ALTER TABLE notification RENAME TO notification_22;
CREATE TABLE notification  (_id integer primary key autoincrement,
                            notification_id TEXT UNIQUE ON CONFLICT IGNORE,
                            metric_id TEXT REFERENCES metric(metric_id) ON DELETE CASCADE,
                            timestamp DATETIME,
                            read INTEGER,
                            description TEXT);
INSERT INTO notification SELECT * FROM notification_22;
DROP TABLE notification_22;

