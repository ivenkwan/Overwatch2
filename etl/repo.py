from dagster import Definitions, load_assets_from_modules

from assets import ledger_ingest, graph_projection
from daily_pipeline import daily_update_job, daily_update_schedule
from detection import t1_detection_job, t1_detection_schedule

all_assets = load_assets_from_modules([ledger_ingest, graph_projection])

defs = Definitions(
    assets=all_assets,
    jobs=[daily_update_job, t1_detection_job],
    schedules=[daily_update_schedule, t1_detection_schedule],
)
