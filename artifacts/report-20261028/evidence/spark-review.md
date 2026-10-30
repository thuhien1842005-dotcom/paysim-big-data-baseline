# Spark review evidence

Evidence type: `derived_snapshot`.

This is a faithful summary transcribed from read-only tool outputs obtained during the review. It is not an original MongoDB export or an original fsck log. The source data continued changing after each query; timestamps and batch cutoffs below identify the observations actually used. No pipeline was rerun and no system data or configuration was modified.

## MongoDB snapshot

Captured at `2026-10-28T14:37:20.128Z`, equivalent to **21:37:20 on 28 October 2026, Asia/Saigon**. Database: `paysim`. Run: `run-20261028-115020`.

| Run field | Observed value |
| --- | --- |
| status | running |
| started_at | 2026-10-28T11:50:20.741Z |
| dataset_rows | 6362620 |
| source_rows / unique_events_emitted / events_emitted | 365700 |
| source_row | 365700 |
| source_cycle | 1 |
| source_progress_pct as stored | 0.0574763226469599 |
| events_per_second | 50 |
| instant_emission_rate | 49.993788621682526 |
| actual_emission_rate | 47.6859875385219 |
| start_row | 1 |
| max_events | 0 |
| loop_dataset | true |
| random_seed | 2026 |
| duplicate_rate / null_rate / late_event_rate | 0 / 0 / 0 |
| duplicates_injected / delivery_errors | 0 / 0 |
| run updated_at | 2026-10-28T14:37:19.252Z |

Derived progress is `365700 / 6362620 * 100 = 5.74763226469599%`. The stored source_progress_pct is a fraction. This run had not consumed a complete dataset cycle at this snapshot.

Evaluation snapshot: `processed=365300`, `ground_truth_missing=0`, `updated_at=2026-10-28T14:37:12.716Z`. Model confusion: TP 148, FP 18473, TN 346630, FN 49. Rule confusion: TP 44, FP 7932, TN 357171, FN 153. The latest ranking had top_k 100, fraud_in_top_k 0, precision_at_k 0, recall_at_k 0, pr_auc 0; this refers to the latest batch rather than the cumulative run.

### Latest completed metric

Batch `1040`, created at `2026-10-28T14:37:12.839Z`.

| Metric | Observed value |
| --- | --- |
| input_rows / processed_rows | 500 / 500 |
| processed_total / emitted_snapshot | 365300 / 365300 |
| batch_duration_seconds | 2.769662602000608 |
| processing_throughput | 180.52740418231284 |
| ingest_throughput | 49.994321819925645 |
| consumer_lag | 0 |
| latency_p50_ms / latency_p95_ms | 6774 / 10806 |
| ingest_latency_p95_ms | 17 |
| bronze_write_seconds | 0.11366113199983374 |
| silver_write_seconds | 0.14726165300089633 |
| gold_write_seconds | 0.538310084000841 |
| storage_write_seconds | 0.7992328690015711 |
| sql_query_duration_ms | 84.00740800061612 |
| scoring_latency_ms_per_1k | 1273.5455699948943 |
| mongo_write_latency_ms | 110.67858699971111 |
| mongo_write_operations | 236 |
| mongo_write_success_rate | 1 |
| event_completeness | 1 |
| aggregate_correctness / transformation_correctness | true / true |
| invalid_rows / duplicate_removed / late_event_rows | 0 / 0 / 0 |
| alerts | 31 |
| bronze_bytes | 183969412 |
| silver_bytes | 270239724 |
| gold_bytes | 205303560 |
| storage_size_bytes | 659512696 |
| cumulative_raw_bytes | 142546354 |
| small_file_count | 22227 |
| compression_ratio | 0.7748372539234947 |

### Last 60 recorded batches at that cutoff

Batch IDs **981–1040 inclusive**, 60 records, total processed rows **40200**.

| Metric | Arithmetic mean | Minimum | Maximum |
| --- | --- | --- | --- |
| batch_duration_seconds | 11.23853449018358 | 1.687466126997606 | 105.54657043000043 |
| processing_throughput | 202.56678807143786 | 8.027194336749437 | 592.011883389596 |
| silver_write_seconds | 2.632425309966614 | 0.12116324599992367 | 51.4499531750007 |
| storage_write_seconds | 5.165199998083638 | 0.3510495180016733 | 73.18760105100228 |
| sql_query_duration_ms | 479.4653381330136 | 56.68544699801714 | 4862.150853001367 |
| latency_p95_ms | 126631.41666666667 | 9453 | 1015291 |
| consumer_lag | 1594.0833333333333 | 0 | 8411 |

All 60 records had aggregate_correctness=true and transformation_correctness=true. Total invalid_rows=0 and duplicate_removed=0. No fault injection was enabled, so these observations do not establish robustness under injected faults.

Derived sum of recorded batch durations: `11.23853449018358 * 60 = 674.3120694110148 seconds`. Derived pooled throughput: `40200 / 674.3120694110148 = 59.61631390509312 events/s`. The arithmetic mean of per-batch throughput is not the pooled throughput. The mean and maximum of batch p95 values are not the p95 of all events across the window.

### Query used

The following JavaScript was piped through standard input to `docker compose exec -T mongodb mongosh paysim --quiet`. The query did not write database state.

```javascript
const run='run-20261028-115020';
const latest=db.pipeline_metrics.find({run_id:run}).sort({created_at:-1}).limit(1).toArray()[0];
const a=db.pipeline_metrics.find({run_id:run,batch_id:{$lte:latest.batch_id}}).sort({batch_id:-1}).limit(60).toArray();
function stats(k){const v=a.map(x=>x[k]).filter(x=>typeof x==='number');return {mean:v.reduce((s,x)=>s+x,0)/v.length,min:Math.min(...v),max:Math.max(...v)}}
print(EJSON.stringify({captured_at:new Date(),run:db.runs.findOne({_id:run}),evaluation:db.evaluation_totals.findOne({_id:run}),latest:latest,window:{batches:a.length,first_batch:a[a.length-1].batch_id,last_batch:a[0].batch_id,total_rows:a.reduce((s,x)=>s+x.processed_rows,0),duration:stats('batch_duration_seconds'),throughput:stats('processing_throughput'),silver_write:stats('silver_write_seconds'),storage_write:stats('storage_write_seconds'),query_ms:stats('sql_query_duration_ms'),p95_ms:stats('latency_p95_ms'),invalid_rows:a.reduce((s,x)=>s+x.invalid_rows,0),duplicates:a.reduce((s,x)=>s+x.duplicate_removed,0),correct:a.every(x=>x.aggregate_correctness&&x.transformation_correctness),lag:stats('consumer_lag')}},null,2));
```

Run, evaluation and metric reads were sequential queries, not an atomic transaction. Their own timestamps and the frozen latest batch cutoff should be retained when citing them.

## HDFS read-only check

Command: `docker compose exec -T namenode hdfs fsck /data/paysim`, with terminal output limited using PowerShell `Select-Object -Last 40`.

The observed footer was `FSCK ended at Wed Oct 28 14:37:46 UTC 2026 in 309 milliseconds`, equivalent to **21:37:46 on 28 October 2026, Asia/Saigon**.

| Field | Observed value |
| --- | --- |
| Path / status | /data/paysim / HEALTHY |
| DataNodes / racks | 1 / 1 |
| Total dirs / symlinks | 108 / 0 |
| Total replicated size | 660754374 B |
| Total files | 22697 |
| Validated blocks | 22678 |
| Average block size | 29136 B |
| Minimally replicated blocks | 22678 (100%) |
| Replication factor / average block replication | 1 / 1.0 |
| Missing blocks / corrupt blocks / missing replicas | 0 / 0 / 0 |
| Over-replicated / under-replicated / mis-replicated blocks | 0 / 0 / 0 |
| Blocks queued for replication | 0 |
| Erasure coded block groups | 0 |

The HDFS total includes checkpoint/model and other files beyond the three data tiers. It must not be equated to the pipeline small_file_count. The root hdfs-fsck.txt is a different, older observation from 27 October and showed corruption; that older result is not the current state of /data/paysim at this check.

## Effective Spark configuration

A subsequent read-only Spark REST query to `http://localhost:4040/api/v1/applications` and `/applications/local-1793188200362/environment` observed:

```json
{
  "application_id": "local-1793188200362",
  "application_name": "PaySim-Big-Data-Baseline",
  "appSparkVersion": "4.0.0",
  "startTime": "2026-10-28T11:49:59.160GMT",
  "completed": false,
  "spark.driver.memory": "2g",
  "spark.master": "local[2]",
  "spark.sql.shuffle.partitions": "2"
}
```

The REST response itself did not contain a capture timestamp. It was obtained after the 21:37:46 fsck observation. Do not assign the MongoDB timestamp to it. Container environment read at the fsck step reported MAX_OFFSETS_PER_TRIGGER=1000, TRIGGER_SECONDS=10, TRAIN_MAX_ROWS=300000, MODEL_THRESHOLD=0.50.

REST query code, piped to `docker compose exec -T spark python3`:

```python
import json,urllib.request
base='http://localhost:4040/api/v1/applications'
apps=json.load(urllib.request.urlopen(base))
app=apps[0]['id']
env=json.load(urllib.request.urlopen(base+'/'+app+'/environment'))
print(json.dumps({'app':apps[0],'properties':{k:v for k,v in env['sparkProperties'] if k in ['spark.master','spark.driver.memory','spark.sql.shuffle.partitions']}}))
```

## Code comparison and evidence limits

- `spark/pipeline.py:423–451`, `:476–500`, `:699–717`: seven selected statistics/quantile action invocations in the annotated BEFORE become three aggregate invocations in AFTER. Derived reduction `(7-3)/7*100 = 57.14285714285714%` refers only to those selected calls, not total jobs or elapsed time.
- `spark/pipeline.py:814–827`: shuffle partition setting 4 becomes 2, a 50% setting reduction; the effective value 2 was confirmed by REST.
- `spark/pipeline.py:506–521`: Silver write adds repartition(run_id,type) before partitionBy(run_id,type). It can reduce multiple writers for each output key but adds a shuffle; timing gains are workload dependent.
- Commit d70fb26 records the Spark code changes. The artifacts/opt1-20261017-*, opt2-20261018-* and opt3-20261018-* directories contained only compiled pyc files during this audit. Original A/B JSON/CSV measurements were not present.
- The MongoDB database inventory contained admin, config, local and paysim. No separate A/B benchmark database was present. Existing operational runs do not establish comparable BEFORE and AFTER conditions.
- Consequently no percentage measured speedup, write-time reduction or file-count reduction is established for the Spark changes by the retained evidence.

Metric interpretation limits:

1. pipeline.py:778 sums Bronze/Silver/Gold files across the HDFS base, including multiple runs. The latest 22227 files are not files solely from the selected run.
2. pipeline.py:780 divides cumulative raw bytes of one run by Bronze bytes from the whole base. Its 0.7748 ratio is not a controlled compression benchmark.
3. pipeline.py:524–569 and :783 measure transform plus Gold write in scoring latency, not pure model inference.
4. pipeline.py:718 freezes duration before HDFS summaries, telemetry writes and unpersist; it does not cover every operation in the streaming trigger.
5. pipeline.py:552–559 measures end-to-end latency at scoring, not when the dashboard renders.
6. dropDuplicates in pipeline.py:471 is scoped to each foreachBatch DataFrame; no cross-batch deduplication guarantee follows.

No local AGENTS.md was found at the workspace root or checked ancestor directories during this audit.
