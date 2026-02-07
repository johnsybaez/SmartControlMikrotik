"""Script para poblar la base de datos con datos de ejemplo"""
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import SessionLocal, init_db
from app.db.models import User, Router, Device, Plan, PlanAssignment
from app.core.security import hash_password
from datetime import datetime

def populate_sample_data():
    """Populate database with sample data for testing"""
    print("Initializing database...")
    init_db()
    
    db = SessionLocal()
    try:
        # Check if we already have data
        user_count = db.query(User).count()
        if user_count > 0:
            print(f"Database already has {user_count} users. Skipping user creation.")
        else:
            print("Creating sample users...")
            users = [
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    full_name="Administrator",
                    email="admin@smartcontrol.com",
                    role="admin",
                    is_active=True
                ),
                User(
                    username="operator",
                    password_hash=hash_password("operator123"),
                    full_name="Operator User",
                    email="operator@smartcontrol.com",
                    role="operator",
                    is_active=True
                )
            ]
            db.add_all(users)
            db.commit()
            print(f"✓ Created {len(users)} users")
        
        # Check if we already have plans
        plan_count = db.query(Plan).count()
        if plan_count > 0:
            print(f"Database already has {plan_count} plans. Skipping plan creation.")
        else:
            print("Creating sample service plans...")
            plans = [
                Plan(
                    name="Plan Básico 10 Mbps",
                    upload_limit="10M",
                    download_limit="10M",
                    burst_upload="15M",
                    burst_download="15M",
                    burst_threshold="5M/5M",
                    burst_time="10s/10s",
                    priority=8,
                    price=299,
                    description="Plan básico de 10 Mbps",
                    is_active=True
                ),
                Plan(
                    name="Plan Hogar 20 Mbps",
                    upload_limit="20M",
                    download_limit="20M",
                    burst_upload="30M",
                    burst_download="30M",
                    burst_threshold="10M/10M",
                    burst_time="15s/15s",
                    priority=6,
                    price=499,
                    description="Plan ideal para hogares",
                    is_active=True
                ),
                Plan(
                    name="Plan Premium 50 Mbps",
                    upload_limit="50M",
                    download_limit="50M",
                    burst_upload="75M",
                    burst_download="75M",
                    burst_threshold="25M/25M",
                    burst_time="20s/20s",
                    priority=4,
                    price=799,
                    description="Plan premium de alta velocidad",
                    is_active=True
                ),
                Plan(
                    name="Plan Ultra 100 Mbps",
                    upload_limit="100M",
                    download_limit="100M",
                    burst_upload="150M",
                    burst_download="150M",
                    burst_threshold="50M/50M",
                    burst_time="30s/30s",
                    priority=2,
                    price=1299,
                    description="Plan ultra rápido para usuarios exigentes",
                    is_active=True
                ),
                Plan(
                    name="Plan Empresarial 200 Mbps",
                    upload_limit="200M",
                    download_limit="200M",
                    burst_upload="250M",
                    burst_download="250M",
                    burst_threshold="100M/100M",
                    burst_time="30s/30s",
                    priority=1,
                    price=1999,
                    description="Plan empresarial de máxima velocidad",
                    is_active=True
                )
            ]
            db.add_all(plans)
            db.commit()
            print(f"✓ Created {len(plans)} service plans")
        
        # Check if we already have a router
        router_count = db.query(Router).count()
        if router_count > 0:
            print(f"Database already has {router_count} routers.")
        else:
            print("Note: Add routers through the web interface")
        
        # Check devices
        device_count = db.query(Device).count()
        print(f"Current device count: {device_count}")
        
        # Check plan assignments
        assignment_count = db.query(PlanAssignment).count()
        print(f"Current plan assignment count: {assignment_count}")
        
        print("\n✅ Sample data population completed!")
        print("\nDefault credentials:")
        print("  Admin - username: admin, password: admin123")
        print("  Operator - username: operator, password: operator123")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    populate_sample_data()
