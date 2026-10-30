from __future__ import annotations

import math
import os
import time
from datetime import datetime, timezone

UTC = timezone.utc
from typing import Callable, Iterable

from pymongo import ASCENDING, DESCENDING, InsertOne, MongoClient, UpdateOne
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.classification import (
    DecisionTreeClassifier,
    GBTClassifier,
    LogisticRegression,
    RandomForestClassifier,
)
from pyspark.ml.feature import OneHotEncoder, StringIndexer, VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import DataFrame, SparkSession, functions as F, types as T
from pyspark.sql.streaming import StreamingQuery


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "paysim.transactions")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "paysim")
HDFS_BASE = os.getenv("HDFS_BASE", "hdfs://namenode:9000/data/paysim")
MODEL_PATH = os.getenv("MODEL_PATH", f"{HDFS_BASE}/models/baseline")
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", f"{HDFS_BASE}/checkpoints/scoring")
DATA_PATH = os.getenv("DATA_PATH", "/data/paysim.csv")
TRAIN_MAX_ROWS = env_int("TRAIN_MAX_ROWS", 300_000)
MAX_OFFSETS_PER_TRIGGER = env_int("MAX_OFFSETS_PER_TRIGGER", 10_000)
TRIGGER_SECONDS = env_int("TRIGGER_SECONDS", 3)
MODEL_THRESHOLD = env_float("MODEL_THRESHOLD", 0.50)
HDFS_STARTUP_TIMEOUT_SECONDS = env_int("HDFS_STARTUP_TIMEOUT_SECONDS", 300)
HDFS_RETRY_INTERVAL_SECONDS = env_int("HDFS_RETRY_INTERVAL_SECONDS", 5)

TRANSACTION_TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
CANDIDATE_TYPES = ["CASH_OUT", "TRANSFER"]

PAYSiM_SCHEMA = T.StructType(
    [
        T.StructField("step", T.IntegerType(), True),
        T.StructField("type", T.StringType(), True),
        T.StructField("amount", T.DoubleType(), True),
        T.StructField("nameOrig", T.StringType(), True),
        T.StructField("oldbalanceOrg", T.DoubleType(), True),
        T.StructField("newbalanceOrig", T.DoubleType(), True),
        T.StructField("nameDest", T.StringType(), True),
        T.StructField("oldbalanceDest", T.DoubleType(), True),
        T.StructField("newbalanceDest", T.DoubleType(), True),
        T.StructField("isFraud", T.IntegerType(), True),
        T.StructField("isFlaggedFraud", T.IntegerType(), True),
    ]
)

EVENT_SCHEMA = T.StructType(
    [
        T.StructField("event_id", T.StringType(), True),
        T.StructField("run_id", T.StringType(), True),
        T.StructField("source_row", T.LongType(), True),
        T.StructField("source_cycle", T.IntegerType(), True),
        T.StructField("step", T.IntegerType(), True),
        T.StructField("type", T.StringType(), True),
        T.StructField("amount", T.DoubleType(), True),
        T.StructField("nameOrig", T.StringType(), True),
        T.StructField("oldbalanceOrg", T.DoubleType(), True),
        T.StructField("newbalanceOrig", T.DoubleType(), True),
        T.StructField("nameDest", T.StringType(), True),
        T.StructField("oldbalanceDest", T.DoubleType(), True),
        T.StructField("newbalanceDest", T.DoubleType(), True),
        T.StructField("event_time", T.StringType(), True),
        T.StructField("emitted_at_ms", T.LongType(), True),
    ]
)


def hdfs_path_exists(spark: SparkSession, path: str) -> bool:
    hadoop_configuration = spark.sparkContext._jsc.hadoopConfiguration()
    filesystem = spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
        hadoop_configuration
    )
    return filesystem.exists(spark.sparkContext._jvm.org.apache.hadoop.fs.Path(path))


def hdfs_content_summary(spark: SparkSession, path: str) -> dict:
    hadoop_configuration = spark.sparkContext._jsc.hadoopConfiguration()
    filesystem = spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
        hadoop_configuration
    )
    hadoop_path = spark.sparkContext._jvm.org.apache.hadoop.fs.Path(path)
    if not filesystem.exists(hadoop_path):
        return {"bytes": 0, "files": 0}
    summary = filesystem.getContentSummary(hadoop_path)
    return {"bytes": int(summary.getLength()), "files": int(summary.getFileCount())}


def _hdfs_file_readable(filesystem, hadoop_path) -> bool:
    try:
        stream = filesystem.open(hadoop_path)
        try:
            stream.read()
        finally:
            stream.close()
        return True
    except Exception:
        return False


def repair_checkpoint_if_needed(spark: SparkSession, checkpoint_path: str) -> None:
    try:
        hadoop_configuration = spark.sparkContext._jsc.hadoopConfiguration()
        filesystem = spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
            hadoop_configuration
        )
        PathCls = spark.sparkContext._jvm.org.apache.hadoop.fs.Path
        root_path = PathCls(checkpoint_path)
        if not filesystem.exists(root_path):
            return

        metadata_path = PathCls(f"{checkpoint_path.rstrip('/')}/metadata")
        if filesystem.exists(metadata_path) and not _hdfs_file_readable(
            filesystem, metadata_path
        ):
            print(
                f"Corrupt checkpoint metadata detected at {metadata_path}; resetting checkpoint.",
                flush=True,
            )
            filesystem.delete(root_path, True)
            return

        for subdir in ("commits", "offsets"):
            sub_path = PathCls(f"{checkpoint_path.rstrip('/')}/{subdir}")
            if not filesystem.exists(sub_path):
                continue
            statuses = filesystem.listStatus(sub_path)
            batch_files = []
            for status in statuses:
                if status.isFile():
                    name = status.getPath().getName()
                    if name.isdigit():
                        batch_files.append((int(name), status.getPath()))
            batch_files.sort(key=lambda item: item[0], reverse=True)
            for batch_num, file_path in batch_files[:5]:
                if not _hdfs_file_readable(filesystem, file_path):
                    print(
                        f"Removing unreadable checkpoint file {file_path} from interrupted shutdown.",
                        flush=True,
                    )
                    filesystem.delete(file_path, False)
                    if subdir == "offsets":
                        commit_path = PathCls(
                            f"{checkpoint_path.rstrip('/')}/commits/{batch_num}"
                        )
                        if filesystem.exists(commit_path):
                            filesystem.delete(commit_path, False)
    except Exception as error:
        print(f"Checkpoint inspection warning: {error}", flush=True)


def start_stream_with_hdfs_retry(
    start_query: Callable[[], StreamingQuery],
) -> StreamingQuery:
    deadline = time.monotonic() + HDFS_STARTUP_TIMEOUT_SECONDS
    attempt = 0

    while True:
        attempt += 1
        try:
            return start_query()
        except Exception as error:
            if "SafeModeException" not in str(error):
                raise

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    "HDFS remained in Safe Mode for "
                    f"{HDFS_STARTUP_TIMEOUT_SECONDS} seconds while starting "
                    "the Spark stream. Reset the baseline volumes if HDFS "
                    "reports corrupt blocks."
                ) from error

            wait_seconds = min(HDFS_RETRY_INTERVAL_SECONDS, remaining)
            print(
                "HDFS is still in Safe Mode; retrying Spark stream startup "
                f"in {wait_seconds:.0f}s (attempt {attempt}).",
                flush=True,
            )
            time.sleep(wait_seconds)


def add_features(dataframe: DataFrame) -> DataFrame:
    return (
        dataframe.withColumn("log_amount", F.log1p(F.coalesce(F.col("amount"), F.lit(0.0))))
        .withColumn("hour_of_day", ((F.col("step") - 1) % 24).cast("double"))
        .withColumn(
            "destination_type",
            F.when(F.col("nameDest").startswith("M"), F.lit("MERCHANT")).otherwise(
                F.lit("CUSTOMER")
            ),
        )
        .withColumn(
            "destination_balance_available",
            (~F.col("nameDest").startswith("M")).cast("integer"),
        )
    )


def train_or_load_model(spark: SparkSession) -> PipelineModel:
    # CHAPTER 7: so sánh classifier trên CÙNG dữ liệu và feature.
    # Muốn đổi phiên bản: chỉ để MỘT block 7 (BEFORE hoặc AFTER A/B/C) chạy.
    # Comment cả block đang bật, bỏ comment cả block muốn thử; không đổi
    # TRAIN_MAX_ROWS, feature, class_weight hoặc MODEL_THRESHOLD giữa các lượt.
    # Mỗi block có model_path riêng để không vô tình load classifier của lượt cũ.
    # Nếu sửa feature/preset, đổi suffix đường dẫn để train lại; giữ model cũ.
    #
    # Quan sát dashboard: PR-AUC, Recall@K, Precision@K, F1, Alert rate,
    # Scoring latency. PR-AUC/Top-K là batch gần nhất, F1 là cộng dồn theo run;
    # so cùng phạm vi, ghi nhiều batch, không kết luận từ một batch cuối.
    # Decision Tree được chọn theo AP validation trong benchmark; Random Forest
    # có F1 tốt hơn ở ngưỡng 0.50. Không có model tốt nhất ở mọi metric.
    #
    # Thực hành: dùng cùng START_ROW, MAX_EVENTS, RANDOM_SEED và tốc độ phát.
    # Kết thúc lượt phát cũ, chờ Spark xử lý hết rồi mới đổi model.
    # pipeline.py được COPY vào image: phải build/recreate Spark, restart chưa đủ
    # (docker compose up -d --build --force-recreate spark; giữ cấu hình RAM cũ).
    # Sau khi Spark sẵn sàng, tạo lượt replayer với RUN_ID mới; dashboard tự
    # hiển thị run mới nhất. Không gộp prediction của hai model vào cùng RUN_ID.
    # Không reset volume hoặc xóa model/checkpoint để chuyển classifier.

    # BEFORE Start — 7: Logistic Regression, mốc so sánh tuyến tính.
    # model_path = MODEL_PATH
    # classifier = LogisticRegression(
    #     featuresCol="features",
    #     labelCol="label",
    #     weightCol="class_weight",
    #     maxIter=20,
    #     regParam=0.01,
    #     elasticNetParam=0.0,
    # )
    # BEFORE END — 7

    # AFTER Start — 7A: Decision Tree học các điều kiện phân nhánh.
    # Giới hạn độ sâu/mẫu lá để hạn chế quá khớp; cảnh báo sai vẫn có thể tăng.
    model_path = MODEL_PATH.rstrip("/") + "-decision-tree-v1"
    classifier = DecisionTreeClassifier(
        featuresCol="features",
        labelCol="label",
        weightCol="class_weight",
        maxDepth=5,
        maxBins=32,
        minInstancesPerNode=20,
        seed=2026,
    )
    # AFTER END — 7A

    # AFTER Start — 7B: Random Forest kết hợp nhiều cây để so chất lượng/chi phí.
    # model_path = MODEL_PATH.rstrip("/") + "-random-forest-v1"
    # classifier = RandomForestClassifier(
    #     featuresCol="features",
    #     labelCol="label",
    #     weightCol="class_weight",
    #     maxDepth=5,
    #     maxBins=32,
    #     minInstancesPerNode=20,
    #     numTrees=40,
    #     featureSubsetStrategy="auto",
    #     seed=2026,
    # )
    # AFTER END — 7B

    # AFTER Start — 7C: GBT học nối tiếp các cây để giảm lỗi của tập hợp trước.
    # model_path = MODEL_PATH.rstrip("/") + "-gbt-v1"
    # classifier = GBTClassifier(
    #     featuresCol="features",
    #     labelCol="label",
    #     weightCol="class_weight",
    #     maxDepth=5,
    #     maxBins=32,
    #     minInstancesPerNode=20,
    #     maxIter=20,
    #     stepSize=0.1,
    #     seed=2026,
    # )
    # AFTER END — 7C

    if hdfs_path_exists(spark, model_path):
        print(f"Loading Spark MLlib model from {model_path}", flush=True)
        return PipelineModel.load(model_path)

    print(
        f"Training baseline Spark MLlib model from first {TRAIN_MAX_ROWS:,} rows...",
        flush=True,
    )
    training = (
        spark.read.option("header", True)
        .schema(PAYSiM_SCHEMA)
        .csv(DATA_PATH)
        .limit(TRAIN_MAX_ROWS)
        .filter(F.col("type").isin(CANDIDATE_TYPES))
        .withColumn("label", F.col("isFraud").cast("double"))
    )
    training = add_features(training)

    counts = {row["label"]: row["count"] for row in training.groupBy("label").count().collect()}
    positives = int(counts.get(1.0, 0))
    negatives = int(counts.get(0.0, 0))
    if positives == 0 or negatives == 0:
        raise RuntimeError(
            f"Training sample must contain both classes; positives={positives}, negatives={negatives}"
        )
    positive_weight = negatives / positives
    training = training.withColumn(
        "class_weight",
        F.when(F.col("label") == 1.0, F.lit(positive_weight)).otherwise(F.lit(1.0)),
    )

    type_indexer = StringIndexer(
        inputCol="type", outputCol="type_index", handleInvalid="keep"
    )
    type_encoder = OneHotEncoder(inputCol="type_index", outputCol="type_vector")
    assembler = VectorAssembler(
        inputCols=["type_vector", "log_amount", "hour_of_day"],
        outputCol="features",
        handleInvalid="keep",
    )
    model = Pipeline(stages=[type_indexer, type_encoder, assembler, classifier]).fit(
        training
    )
    model.write().overwrite().save(model_path)
    print(
        f"Model trained: positives={positives}, negatives={negatives}, "
        f"positive_weight={positive_weight:.1f}",
        flush=True,
    )
    return model


def chunks(items: list, size: int) -> Iterable[list]:
    for position in range(0, len(items), size):
        yield items[position : position + size]


def safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_predictions(database, run_id: str, predictions: list[dict]) -> dict:
    if not predictions:
        return {
            "processed": 0,
            "ground_truth_missing": 0,
            "model": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "rule": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "ranking": {
                "pr_auc": 0.0,
                "top_k": 0,
                "fraud_in_top_k": 0,
                "precision_at_k": 0.0,
                "recall_at_k": 0.0,
            },
        }

    labels: dict[str, int] = {}
    event_ids = [item["event_id"] for item in predictions]
    for event_id_chunk in chunks(event_ids, 1_000):
        cursor = database.ground_truth.find(
            {"run_id": run_id, "event_id": {"$in": event_id_chunk}},
            {"event_id": 1, "isFraud": 1},
        )
        labels.update({item["event_id"]: int(item["isFraud"]) for item in cursor})

    result = {
        "processed": 0,
        "ground_truth_missing": 0,
        "model": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        "rule": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        "ranking": {},
    }
    labelled_predictions = []
    for item in predictions:
        actual = labels.get(item["event_id"])
        if actual is None:
            result["ground_truth_missing"] += 1
            continue
        result["processed"] += 1
        labelled_predictions.append({**item, "actual": actual})
        for detector, prediction_field in [
            ("model", "prediction"),
            ("rule", "rule_prediction"),
        ]:
            predicted = int(item[prediction_field])
            if predicted == 1 and actual == 1:
                result[detector]["tp"] += 1
            elif predicted == 1 and actual == 0:
                result[detector]["fp"] += 1
            elif predicted == 0 and actual == 0:
                result[detector]["tn"] += 1
            else:
                result[detector]["fn"] += 1

    ranked = sorted(
        labelled_predictions, key=lambda item: float(item.get("risk_score", 0.0)), reverse=True
    )
    positives = sum(int(item["actual"]) for item in ranked)
    true_positives = 0
    precision_sum = 0.0
    for rank, item in enumerate(ranked, start=1):
        if int(item["actual"]) == 1:
            true_positives += 1
            precision_sum += true_positives / rank
    top_k = min(100, len(ranked))
    fraud_in_top_k = sum(int(item["actual"]) for item in ranked[:top_k])
    result["ranking"] = {
        "pr_auc": precision_sum / positives if positives else 0.0,
        "top_k": top_k,
        "fraud_in_top_k": fraud_in_top_k,
        "precision_at_k": fraud_in_top_k / top_k if top_k else 0.0,
        "recall_at_k": fraud_in_top_k / positives if positives else 0.0,
    }
    return result


def update_evaluation(database, run_id: str, result: dict) -> None:
    increments = {
        "processed": result["processed"],
        "ground_truth_missing": result["ground_truth_missing"],
    }
    for detector in ["model", "rule"]:
        for metric in ["tp", "fp", "tn", "fn"]:
            increments[f"{detector}.{metric}"] = result[detector][metric]
    database.evaluation_totals.update_one(
        {"_id": run_id},
        {
            "$inc": increments,
            "$set": {
                "run_id": run_id,
                "latest_ranking": result.get("ranking", {}),
                "updated_at": datetime.now(UTC),
            },
            "$setOnInsert": {"created_at": datetime.now(UTC)},
        },
        upsert=True,
    )


def prepare_mongo() -> MongoClient:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30_000)
    client.admin.command("ping")
    database = client[MONGO_DATABASE]
    database.fraud_alerts.create_index(
        [("run_id", ASCENDING), ("event_id", ASCENDING)], unique=True
    )
    database.fraud_alerts.create_index(
        [("run_id", ASCENDING), ("risk_score", DESCENDING)]
    )
    database.pipeline_metrics.create_index(
        [("run_id", ASCENDING), ("batch_id", ASCENDING)], unique=True
    )
    database.live_aggregates.create_index(
        [("run_id", ASCENDING), ("type", ASCENDING)], unique=True
    )
    database.recent_transactions.create_index(
        [("run_id", ASCENDING), ("scored_at", DESCENDING)]
    )
    return client


def build_batch_processor(spark: SparkSession, model: PipelineModel, mongo_client):
    database = mongo_client[MONGO_DATABASE]

    def process_batch(batch: DataFrame, batch_id: int) -> None:
        batch_started = time.perf_counter()

        # ĐIỂM TỐI ƯU 1A: gom các action đầu batch vào một aggregation.
        # Muốn đổi phiên bản: chỉ để MỘT block cùng mã 1A được thực thi.
        # BEFORE Start — 1A
        # if batch.rdd.isEmpty():
        #     return
        # batch = batch.persist()
        # total_rows = batch.count()
        # raw_bytes = int(
        #     batch.select(F.sum(F.length("raw_json")).alias("bytes"))
        #     .first()["bytes"]
        #     or 0
        # )
        # BEFORE END — 1A

        # Tối ưu: giảm số action và số lần Spark phải khởi tạo job cho một batch.
        # Tham chiếu: dashboard → Micro-batch duration, Processing throughput,
        # Processing latency p95; kiến thức → Action và lazy evaluation.
        # AFTER Start — 1A
        batch = batch.persist()
        batch_stats = batch.agg(
            F.count("*").alias("rows"),
            F.sum(F.length("raw_json")).alias("bytes"),
        ).first()
        total_rows = int(batch_stats["rows"])
        raw_bytes = int(batch_stats["bytes"] or 0)
        if total_rows == 0:
            batch.unpersist()
            return
        # AFTER END — 1A

        run_ids = [row["run_id"] for row in batch.select("run_id").distinct().collect()]

        bronze_started = time.perf_counter()
        batch.write.mode("append").partitionBy("run_id").parquet(
            f"{HDFS_BASE}/bronze"
        )
        bronze_write_seconds = time.perf_counter() - bronze_started

        valid_condition = (
            F.col("event_id").isNotNull()
            & F.col("run_id").isNotNull()
            & F.col("amount").isNotNull()
            & (F.col("amount") >= 0)
            & F.col("type").isin(TRANSACTION_TYPES)
        )
        well_formed = batch.filter(valid_condition).persist()
        well_formed_rows = well_formed.count()
        valid = (
            well_formed.dropDuplicates(["run_id", "event_id"])
            .withColumn("processed_at", F.current_timestamp())
        )
        valid = add_features(valid).persist()

        # ĐIỂM TỐI ƯU 1B: gom hai action trên DataFrame valid.
        # Muốn đổi phiên bản: chỉ để MỘT block cùng mã 1B được thực thi.
        # BEFORE Start — 1B
        # valid_rows = valid.count()
        # late_event_rows = valid.filter(
        #     F.col("event_time")
        #     < F.col("ingested_at") - F.expr("INTERVAL 1 MINUTE")
        # ).count()
        # BEFORE END — 1B

        # Tham chiếu: dashboard → Event completeness và Late event rate.
        # AFTER Start — 1B
        valid_stats = valid.agg(
            F.count("*").alias("rows"),
            F.sum(
                F.when(
                    F.col("event_time")
                    < F.col("ingested_at") - F.expr("INTERVAL 1 MINUTE"),
                    1,
                ).otherwise(0)
            ).alias("late_rows"),
        ).first()
        valid_rows = int(valid_stats["rows"])
        late_event_rows = int(valid_stats["late_rows"] or 0)
        # AFTER END — 1B
        invalid_rows = total_rows - well_formed_rows
        duplicate_removed = well_formed_rows - valid_rows

        silver_started = time.perf_counter()

        # ĐIỂM TỐI ƯU 3: repartition trước khi ghi Silver để giảm file nhỏ.
        # Muốn đổi phiên bản: chỉ để MỘT block cùng mã 3 được thực thi.
        # BEFORE Start — 3
        # valid.write.mode("append").partitionBy("run_id", "type").parquet(
        #     f"{HDFS_BASE}/silver"
        # )
        # BEFORE END — 3

        # Tối ưu: giảm Small files và Write duration trên dashboard.
        # Tham chiếu: dashboard → Storage → Small files / Write duration;
        # kiến thức → partition dữ liệu và shuffle.
        # AFTER Start — 3
        valid.repartition("run_id", "type").write.mode("append").partitionBy(
            "run_id", "type"
        ).parquet(f"{HDFS_BASE}/silver")
        # AFTER END — 3
        silver_write_seconds = time.perf_counter() - silver_started

        scoring_started = time.perf_counter()
        transformed = model.transform(valid)
        scored = (
            transformed.withColumn(
                "risk_score_raw", vector_to_array(F.col("probability"))[1]
            )
            .withColumn(
                "risk_score",
                F.when(
                    F.col("type").isin(CANDIDATE_TYPES), F.col("risk_score_raw")
                ).otherwise(F.lit(0.0)),
            )
            .withColumn(
                "prediction",
                F.when(
                    F.col("type").isin(CANDIDATE_TYPES)
                    & (F.col("risk_score") >= F.lit(MODEL_THRESHOLD)),
                    F.lit(1),
                ).otherwise(F.lit(0)),
            )
            .withColumn(
                "rule_prediction",
                F.when(
                    F.col("type").isin(CANDIDATE_TYPES)
                    & (F.col("amount") >= F.lit(1_000_000.0)),
                    F.lit(1),
                ).otherwise(F.lit(0)),
            )
            .withColumn("scored_at", F.current_timestamp())
            .withColumn(
                "end_to_end_latency_ms",
                F.greatest(
                    F.lit(0),
                    F.unix_millis(F.current_timestamp()) - F.col("emitted_at_ms"),
                ),
            )
            .drop("rawPrediction", "probability", "features", "type_vector")
            .persist()
        )

        gold_started = time.perf_counter()
        scored.write.mode("append").partitionBy("run_id").parquet(
            f"{HDFS_BASE}/gold"
        )
        gold_write_seconds = time.perf_counter() - gold_started
        scoring_seconds = time.perf_counter() - scoring_started

        prediction_rows = [
            row.asDict(recursive=True)
            for row in scored.select(
                "event_id", "run_id", "prediction", "rule_prediction", "risk_score"
            ).collect()
        ]
        alerts = [
            row.asDict(recursive=True)
            for row in scored.filter(F.col("prediction") == 1)
            .select(
                "event_id",
                "run_id",
                "source_row",
                "step",
                "event_time",
                "type",
                "amount",
                "nameOrig",
                "nameDest",
                "risk_score",
                "prediction",
                "rule_prediction",
                "scored_at",
                "end_to_end_latency_ms",
            )
            .collect()
        ]
        recent_transactions = [
            row.asDict(recursive=True)
            for row in scored.select(
                "event_id",
                "run_id",
                "source_row",
                "source_cycle",
                "event_time",
                "type",
                "amount",
                "nameOrig",
                "nameDest",
                "risk_score",
                "prediction",
                "rule_prediction",
                "scored_at",
                "end_to_end_latency_ms",
            )
            .limit(200)
            .collect()
        ]
        mongo_write_started = time.perf_counter()
        mongo_write_operations = 0
        if alerts:
            operations = []
            for alert in alerts:
                alert["_id"] = alert["event_id"]
                operations.append(
                    UpdateOne(
                        {"_id": alert["_id"]}, {"$set": alert}, upsert=True
                    )
                )
            database.fraud_alerts.bulk_write(operations, ordered=False)
            mongo_write_operations += len(operations)

        if recent_transactions:
            recent_operations = []
            for transaction in recent_transactions:
                transaction["_id"] = transaction["event_id"]
                recent_operations.append(
                    UpdateOne(
                        {"_id": transaction["_id"]},
                        {"$set": transaction},
                        upsert=True,
                    )
                )
            database.recent_transactions.bulk_write(
                recent_operations, ordered=False
            )
            mongo_write_operations += len(recent_operations)
            stale_ids = [
                item["_id"]
                for item in database.recent_transactions.find(
                    {"run_id": run_ids[0]}, {"_id": 1}
                )
                .sort("scored_at", DESCENDING)
                .skip(2_000)
                .limit(1_000)
            ]
            if stale_ids:
                database.recent_transactions.delete_many({"_id": {"$in": stale_ids}})

        sql_started = time.perf_counter()
        aggregate_rows = scored.groupBy("run_id", "type").agg(
            F.count("*").alias("transactions"),
            F.sum("amount").alias("total_amount"),
            F.sum("prediction").alias("model_alerts"),
            F.sum("rule_prediction").alias("rule_alerts"),
        )
        aggregate_values = aggregate_rows.collect()
        sql_aggregate_seconds = time.perf_counter() - sql_started
        aggregate_operations = []
        for row in aggregate_values:
            item = row.asDict()
            aggregate_operations.append(
                UpdateOne(
                    {"run_id": item["run_id"], "type": item["type"]},
                    {
                        "$inc": {
                            "transactions": int(item["transactions"]),
                            "total_amount": float(item["total_amount"] or 0.0),
                            "model_alerts": int(item["model_alerts"] or 0),
                            "rule_alerts": int(item["rule_alerts"] or 0),
                        },
                        "$set": {"updated_at": datetime.now(UTC)},
                    },
                    upsert=True,
                )
            )
        if aggregate_operations:
            database.live_aggregates.bulk_write(aggregate_operations, ordered=False)
            mongo_write_operations += len(aggregate_operations)

        for run_id in run_ids:
            run_predictions = [
                item for item in prediction_rows if item["run_id"] == run_id
            ]
            evaluation = evaluate_predictions(database, run_id, run_predictions)
            update_evaluation(database, run_id, evaluation)
        mongo_write_seconds = time.perf_counter() - mongo_write_started

        # ĐIỂM TỐI ƯU 1C.1: gom hai lần tính quantile vào một lời gọi.
        # Muốn đổi phiên bản: đổi cả hai cặp block 1C.1 và 1C.2.
        # BEFORE Start — 1C.1
        # latency_values = scored.approxQuantile(
        #     "end_to_end_latency_ms", [0.5, 0.95], 0.05
        # )
        # ingest_latency_values = scored.approxQuantile(
        #     "ingest_latency_ms", [0.95], 0.05
        # )
        # BEFORE END — 1C.1

        # Tham chiếu: dashboard → Ingest latency p95 và End-to-end latency p95.
        # AFTER Start — 1C.1
        latency_values, ingest_latency_values = scored.approxQuantile(
            ["end_to_end_latency_ms", "ingest_latency_ms"],
            [0.5, 0.95],
            0.05,
        )
        # AFTER END — 1C.1
        duration = max(time.perf_counter() - batch_started, 0.001)
        alert_count = len(alerts)
        bronze_summary = hdfs_content_summary(spark, f"{HDFS_BASE}/bronze")
        silver_summary = hdfs_content_summary(spark, f"{HDFS_BASE}/silver")
        gold_summary = hdfs_content_summary(spark, f"{HDFS_BASE}/gold")
        for run_id in run_ids:
            run_rows = sum(1 for item in prediction_rows if item["run_id"] == run_id)
            run = database.runs.find_one({"_id": run_id}) or {}
            evaluation_total = database.evaluation_totals.find_one({"_id": run_id}) or {}
            previous_metric = database.pipeline_metrics.find_one(
                {"run_id": run_id}, sort=[("batch_id", DESCENDING)]
            ) or {}
            cumulative_raw_bytes = int(previous_metric.get("cumulative_raw_bytes", 0)) + raw_bytes
            emitted_snapshot = int(run.get("events_emitted", 0))
            processed_total = int(evaluation_total.get("processed", 0))
            consumer_lag = max(0, emitted_snapshot - processed_total)
            aggregate_count = sum(int(item["transactions"] or 0) for item in aggregate_values)
            metric_document = {
                "run_id": run_id,
                "batch_id": int(batch_id),
                "input_rows": total_rows,
                "processed_rows": run_rows,
                "invalid_rows": invalid_rows,
                "duplicate_removed": duplicate_removed,
                "late_event_rows": late_event_rows,
                "event_completeness": valid_rows / total_rows if total_rows else 1.0,
                "transformation_correctness": aggregate_count == valid_rows,
                "alerts": alert_count,
                "batch_duration_seconds": duration,
                "processing_throughput": valid_rows / duration,
                "ingest_throughput": float(run.get("instant_emission_rate", 0.0)),
                "consumer_lag": consumer_lag,
                "emitted_snapshot": emitted_snapshot,
                "processed_total": processed_total,
                # ĐIỂM TỐI ƯU 1C.2: chọn đúng p95 theo shape của kết quả 1C.1.
                # Khi đổi 1C.1, bắt buộc đổi cặp block 1C.2 này cùng lúc.
                # BEFORE Start — 1C.2
                # "ingest_latency_p95_ms": (
                #     float(ingest_latency_values[0])
                #     if ingest_latency_values
                #     else 0.0
                # ),
                # BEFORE END — 1C.2
                # AFTER Start — 1C.2
                "ingest_latency_p95_ms": (
                    float(ingest_latency_values[-1])
                    if ingest_latency_values
                    else 0.0
                ),
                # AFTER END — 1C.2
                "latency_p50_ms": float(latency_values[0]) if latency_values else 0.0,
                "latency_p95_ms": float(latency_values[-1]) if latency_values else 0.0,
                "bronze_write_seconds": bronze_write_seconds,
                "silver_write_seconds": silver_write_seconds,
                "gold_write_seconds": gold_write_seconds,
                "storage_write_seconds": bronze_write_seconds + silver_write_seconds + gold_write_seconds,
                "bronze_bytes": bronze_summary["bytes"],
                "silver_bytes": silver_summary["bytes"],
                "gold_bytes": gold_summary["bytes"],
                "storage_size_bytes": bronze_summary["bytes"] + silver_summary["bytes"] + gold_summary["bytes"],
                "small_file_count": bronze_summary["files"] + silver_summary["files"] + gold_summary["files"],
                "cumulative_raw_bytes": cumulative_raw_bytes,
                "compression_ratio": cumulative_raw_bytes / bronze_summary["bytes"] if bronze_summary["bytes"] else 0.0,
                "sql_query_duration_ms": sql_aggregate_seconds * 1000,
                "aggregate_correctness": aggregate_count == valid_rows,
                "scoring_latency_ms_per_1k": scoring_seconds * 1000 * 1000 / valid_rows if valid_rows else 0.0,
                "mongo_write_latency_ms": mongo_write_seconds * 1000,
                "mongo_write_operations": mongo_write_operations,
                "mongo_write_success_rate": 1.0,
                "created_at": datetime.now(UTC),
            }
            database.pipeline_metrics.update_one(
                {"run_id": run_id, "batch_id": int(batch_id)},
                {"$set": metric_document},
                upsert=True,
            )

        scored.unpersist()
        valid.unpersist()
        well_formed.unpersist()
        batch.unpersist()
        print(
            f"batch={batch_id} input={total_rows} valid={valid_rows} "
            f"alerts={alert_count} duration={duration:.2f}s",
            flush=True,
        )

    return process_batch


def main() -> None:
    process_started = time.perf_counter()
    spark = (
        SparkSession.builder.appName("PaySim-Big-Data-Baseline")
        .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")

        # ĐIỂM TỐI ƯU 2: khớp số shuffle partition với local[2].
        # Muốn đổi phiên bản: chỉ để MỘT block cùng mã 2 được thực thi.
        # BEFORE dưới đây tương đương cấu hình 4 từ spark-submit trước tối ưu.
        # BEFORE Start — 2
        # .config("spark.sql.shuffle.partitions", "4")
        # BEFORE END — 2

        # Tối ưu: giảm chi phí shuffle trong dropDuplicates, groupBy và write.
        # Tham chiếu: dashboard → Query duration, Micro-batch duration,
        # Processing throughput, Write duration và Small files.
        # Lưu ý: 2 là kết quả benchmark cho cấu hình lớp học, không phải giá trị
        # mặc định cho mọi cluster Spark.
        # AFTER Start — 2
        .config("spark.sql.shuffle.partitions", "2")
        # AFTER END — 2
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    mongo_client = prepare_mongo()
    database = mongo_client[MONGO_DATABASE]
    database.system_metrics.update_one(
        {"_id": "spark"},
        {
            "$inc": {"restart_count": 1},
            "$set": {"status": "starting", "started_at": datetime.now(UTC)},
        },
        upsert=True,
    )
    model = train_or_load_model(spark)

    kafka_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .option("maxOffsetsPerTrigger", MAX_OFFSETS_PER_TRIGGER)
        .option("kafkaConsumer.pollTimeoutMs", "180000")
        .option("kafka.request.timeout.ms", "120000")
        .option("kafka.default.api.timeout.ms", "120000")
        .option("kafka.session.timeout.ms", "30000")
        .load()
    )

    parsed = (
        kafka_stream.select(
            F.col("value").cast("string").alias("raw_json"),
            F.col("partition").alias("kafka_partition"),
            F.col("offset").alias("kafka_offset"),
            F.col("timestamp").alias("kafka_timestamp"),
        )
        .withColumn("event", F.from_json(F.col("raw_json"), EVENT_SCHEMA))
        .select("raw_json", "kafka_partition", "kafka_offset", "kafka_timestamp", "event.*")
        .withColumn("event_time", F.to_timestamp("event_time"))
        .withColumn("ingested_at", F.current_timestamp())
        .withColumn(
            "ingest_latency_ms",
            F.greatest(
                F.lit(0),
                F.unix_millis("kafka_timestamp") - F.col("emitted_at_ms"),
            ),
        )
    )

    processor = build_batch_processor(spark, model, mongo_client)
    repair_checkpoint_if_needed(spark, CHECKPOINT_PATH)
    query = start_stream_with_hdfs_retry(
        lambda: (
            parsed.writeStream.foreachBatch(processor)
            .option("checkpointLocation", CHECKPOINT_PATH)
            .trigger(processingTime=f"{TRIGGER_SECONDS} seconds")
            .start()
        )
    )

    with open("/tmp/pipeline-ready", "w", encoding="utf-8") as ready_file:
        ready_file.write("ready\n")
    database.system_metrics.update_one(
        {"_id": "spark"},
        {
            "$set": {
                "status": "running",
                "ready_at": datetime.now(UTC),
                "recovery_time_seconds": time.perf_counter() - process_started,
            }
        },
    )
    print("PaySim streaming pipeline is ready.", flush=True)
    query.awaitTermination()


if __name__ == "__main__":
    main()
