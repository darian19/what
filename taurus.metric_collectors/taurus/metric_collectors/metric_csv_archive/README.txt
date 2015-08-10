The tool `gen_metrics_config.py` generates the contents of metrics.json from
the metrics.csv file in this directory. The metrics.csv file is exported from
an Excel spreadsheet maintained by marketing by exporting (Save As) it as
Windows Comma Separated CSV format.

Example commands after updating metrics.csv:

    cd $PRODUCTS/taurus.metric_collectors
    python taurus/metric_collectors/gen_metrics_config.py \
        taurus/metric_collectors/metric_csv_archive/metrics.csv > \
        conf/metrics.json
