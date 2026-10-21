# Cloud adaptation

1. Implement a source adapter for Google Ads keyword historical metrics with approved credentials and quotas; preserve keyword, geography, language, month and extraction timestamp. Keep language/geo IDs mapped explicitly.
2. Generate NDJSON with `python3 pipeline.py`. Create a sandbox `raw` dataset and load `output/keyword_monthly.ndjson` into `raw.keyword_monthly` using `bigquery.schema.json`.
3. Set your project and region in `workflow_settings.yaml`, create reporting/assertion datasets and configure Dataform credentials. Compile before executing. Require unique-key/non-null/non-negative assertions to pass before downstream consumption.
4. Connect reporting.search_demand to a Looker Studio sandbox only after reconciling source totals. If adding a Sheets keyword interface, treat it as validated configuration, not a credential store.

The batch ID hashes sorted rows; rerunning the same extraction is idempotent locally. In the cloud, use a staging load and a MERGE on batch/key to obtain equivalent behaviour. Append-only loads may duplicate raw rows; latest-snapshot modelling deduplicates reporting rows but does not control raw storage. Scheduled ingestion, retry/backoff, IAM, billing and live source authentication remain integration work.

Reference: https://cloud.google.com/dataform/docs/overview
