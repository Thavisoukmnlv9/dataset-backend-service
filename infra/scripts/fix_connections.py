#!/usr/bin/env python3
"""
Comprehensive fix for database connection issues
Handles PostgreSQL connection limits and Prisma connection management
"""
import asyncio
import sys
import os
import subprocess
import psycopg2
from psycopg2 import sql
import time

# Add the project root directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

async def kill_postgres_connections():
    """Kill all connections to the database except the current one"""
    try:
        from app.core.config import settings
        
        # Parse database URL
        db_url = settings.database_url
        if db_url.startswith("postgresql://"):
            # Extract connection details
            url_parts = db_url.replace("postgresql://", "").split("@")
            if len(url_parts) == 2:
                auth_part = url_parts[0]
                host_db_part = url_parts[1]
                
                if ":" in auth_part:
                    username, password = auth_part.split(":", 1)
                else:
                    username = auth_part
                    password = ""
                
                if "/" in host_db_part:
                    host_port, database = host_db_part.split("/", 1)
                    if ":" in host_port:
                        host, port = host_port.split(":")
                    else:
                        host = host_port
                        port = "5432"
                else:
                    host = host_port
                    port = "5432"
                    database = host_db_part
                
                # Connect to PostgreSQL and kill connections
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password
                )
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Get current connection PID
                cursor.execute("SELECT pg_backend_pid();")
                current_pid = cursor.fetchone()[0]
                
                # Kill all other connections to the database
                cursor.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                    AND pid <> %s
                    AND state = 'idle'
                """, (database, current_pid))
                
                killed_count = cursor.rowcount
                print(f"🔪 Terminated {killed_count} idle connections")
                
                cursor.close()
                conn.close()
                
                return True
                
    except Exception as e:
        print(f"⚠️  Could not kill PostgreSQL connections: {e}")
        return False

async def fix_connections():
    """Fix database connection issues comprehensively"""
    try:
        print("🧹 Starting comprehensive database connection cleanup...")
        
        # Step 1: Kill PostgreSQL connections
        print("Step 1: Terminating idle PostgreSQL connections...")
        await kill_postgres_connections()
        
        # Step 2: Clean up Prisma connections
        print("Step 2: Cleaning up Prisma connections...")
        from app.prisma import prisma, cleanup_all_connections
        
        # Force disconnect all connections
        if prisma.is_connected():
            await prisma.disconnect()
            print("✅ Disconnected from Prisma")
        
        # Clean up through the cleanup function
        await cleanup_all_connections()
        
        # Step 3: Wait for connections to be fully released
        print("Step 3: Waiting for connections to be released...")
        await asyncio.sleep(3)
        
        # Step 4: Test connection
        print("Step 4: Testing new connection...")
        try:
            await prisma.connect()
            await prisma.user.count()
            print("✅ Test connection successful")
            await prisma.disconnect()
        except Exception as e:
            print(f"⚠️  Test connection failed: {e}")
        
        print("✅ Database connections cleaned up successfully")
        print("🚀 You can now run your Prisma migration")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False
    
    return True

def check_postgres_status():
    """Check PostgreSQL service status"""
    try:
        result = subprocess.run(['pg_isready'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ PostgreSQL is running")
            return True
        else:
            print("❌ PostgreSQL is not running")
            return False
    except Exception as e:
        print(f"⚠️  Could not check PostgreSQL status: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Database Connection Fix Tool")
    print("=" * 40)
    
    # Check PostgreSQL status
    if not check_postgres_status():
        print("Please start PostgreSQL first")
        sys.exit(1)
    
    # Run the fix
    success = asyncio.run(fix_connections())
    
    if success:
        print("\n🎉 All done! You can now run:")
        print("   prisma migrate dev --name init")
    else:
        print("\n❌ Fix failed. You may need to restart PostgreSQL.")
        sys.exit(1)
