"""
Archive job for managing prediction data retention.
Runs daily to:
1. Archive predictions older than 90 days
2. Aggregate archived data into ModelMetrics
3. Delete archived records to maintain performance
"""

import asyncio
from datetime import datetime, timedelta, date
from sqlalchemy import func, delete, and_
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import PredictionRecord, ModelMetrics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RETENTION_DAYS = 90


async def archive_old_predictions():
    """Archive predictions older than 90 days"""
    async with AsyncSessionLocal() as session:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=RETENTION_DAYS)

            # Mark predictions as archived
            old_predictions = await session.execute(
                select(PredictionRecord).where(
                    and_(
                        PredictionRecord.timestamp < cutoff_date,
                        PredictionRecord.archived == False
                    )
                )
            )

            predictions_to_archive = old_predictions.scalars().all()

            for prediction in predictions_to_archive:
                prediction.archived = True

            await session.commit()
            logger.info(f"Archived {len(predictions_to_archive)} predictions")

            return len(predictions_to_archive)

        except Exception as e:
            await session.rollback()
            logger.error(f"Archival failed: {str(e)}")
            raise


async def aggregate_metrics():
    """Aggregate daily metrics for all users"""
    async with AsyncSessionLocal() as session:
        try:
            # Get all distinct dates with predictions
            dates_result = await session.execute(
                select(func.date(PredictionRecord.timestamp).distinct())
                .where(PredictionRecord.archived == False)
            )

            dates = [row[0] for row in dates_result.fetchall()]

            for target_date in dates:
                # Group by user and date
                predictions = await session.execute(
                    select(
                        PredictionRecord.user_id,
                        func.count(PredictionRecord.id).label("count"),
                        func.avg(PredictionRecord.confidence).label("avg_confidence"),
                        func.avg(PredictionRecord.inference_time_ms).label("avg_inference_time")
                    ).where(
                        func.date(PredictionRecord.timestamp) == target_date
                    ).group_by(PredictionRecord.user_id)
                )

                rows = predictions.fetchall()

                for user_id, count, avg_conf, avg_time in rows:
                    # Check if metric already exists
                    existing = await session.execute(
                        select(ModelMetrics).where(
                            and_(
                                ModelMetrics.user_id == user_id,
                                ModelMetrics.date == target_date
                            )
                        )
                    )

                    metric = existing.scalar_one_or_none()

                    if metric:
                        metric.predictions_count = count
                        metric.avg_confidence = avg_conf or 0.0
                        metric.avg_inference_time_ms = avg_time or 0.0
                    else:
                        metric = ModelMetrics(
                            user_id=user_id,
                            predictions_count=count,
                            avg_confidence=avg_conf or 0.0,
                            avg_inference_time_ms=avg_time or 0.0,
                            date=target_date
                        )
                        session.add(metric)

            await session.commit()
            logger.info(f"Aggregated metrics for {len(dates)} dates")

        except Exception as e:
            await session.rollback()
            logger.error(f"Aggregation failed: {str(e)}")
            raise


async def cleanup_archived_records():
    """Delete archived records older than 180 days to save space"""
    async with AsyncSessionLocal() as session:
        try:
            cleanup_date = datetime.utcnow() - timedelta(days=180)

            # Delete archived predictions
            await session.execute(
                delete(PredictionRecord).where(
                    and_(
                        PredictionRecord.timestamp < cleanup_date,
                        PredictionRecord.archived == True
                    )
                )
            )

            await session.commit()
            logger.info("Cleaned up old archived records")

        except Exception as e:
            await session.rollback()
            logger.error(f"Cleanup failed: {str(e)}")
            raise


async def run_archive_job():
    """Main archive job - run daily"""
    logger.info("Starting archive job")

    try:
        archived_count = await archive_old_predictions()
        await aggregate_metrics()
        await cleanup_archived_records()

        logger.info(f"Archive job completed. Archived {archived_count} predictions")

    except Exception as e:
        logger.error(f"Archive job failed: {str(e)}")


# For use with scheduler like APScheduler
def start_archive_scheduler():
    """
    Start a scheduler to run archive job daily.
    Usage in app.py:

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_archive_job, 'cron', hour=2)  # 2 AM daily
    scheduler.start()
    """
    pass


if __name__ == "__main__":
    # Run once when executed directly
    asyncio.run(run_archive_job())
