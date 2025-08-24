"""
Volume Database Manager for Comic Metadata Manager
Handles caching and storage of volume information to reduce API calls
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path


class VolumeDatabase:
    """Manages volume information storage and retrieval"""
    
    def __init__(self, db_path: str = 'config/volumes.db'):
        """Initialize the volume database
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create volumes table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS volumes (
                        id INTEGER PRIMARY KEY,
                        volume_folder TEXT NOT NULL,
                        status TEXT DEFAULT 'available',
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_issues INTEGER DEFAULT 0,
                        issues_with_files INTEGER DEFAULT 0,
                        metadata_processed BOOLEAN DEFAULT FALSE,
                        xml_generated BOOLEAN DEFAULT FALSE,
                        metadata_injected BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                # Create volume_details table for storing full volume information
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS volume_details (
                        volume_id INTEGER PRIMARY KEY,
                        details_json TEXT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (volume_id) REFERENCES volumes (id)
                    )
                ''')
                
                # Create cache_metadata table for tracking cache validity
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cache_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Migrate existing database schema if needed
                self.migrate_database_schema(cursor)
                
                conn.commit()
                print(f"✅ Volume database initialized: {self.db_path}")
                
        except Exception as e:
            print(f"❌ Error initializing volume database: {e}")
    
    def migrate_database_schema(self, cursor):
        """Migrate existing database schema by adding missing columns"""
        try:
            # Check if metadata_injected column exists
            cursor.execute("PRAGMA table_info(volumes)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns if they don't exist
            if 'metadata_injected' not in columns:
                print("🔄 Adding missing column: metadata_injected")
                cursor.execute('ALTER TABLE volumes ADD COLUMN metadata_injected BOOLEAN DEFAULT FALSE')
            
            if 'total_issues' not in columns:
                print("🔄 Adding missing column: total_issues")
                cursor.execute('ALTER TABLE volumes ADD COLUMN total_issues INTEGER DEFAULT 0')
            
            if 'issues_with_files' not in columns:
                print("🔄 Adding missing column: issues_with_files")
                cursor.execute('ALTER TABLE volumes ADD COLUMN issues_with_files INTEGER DEFAULT 0')
            
            if 'metadata_processed' not in columns:
                print("🔄 Adding missing column: metadata_processed")
                cursor.execute('ALTER TABLE volumes ADD COLUMN metadata_processed BOOLEAN DEFAULT FALSE')
            
            if 'xml_generated' not in columns:
                print("🔄 Adding missing column: xml_generated")
                cursor.execute('ALTER TABLE volumes ADD COLUMN xml_generated BOOLEAN DEFAULT FALSE')
            
            print("✅ Database schema migration completed")
            
        except Exception as e:
            print(f"⚠️ Warning: Database schema migration failed: {e}")
            print("This is not critical, but some features may not work correctly")
    
    def store_volumes(self, volumes: List[Dict[str, Any]]) -> bool:
        """Store a list of volumes in the database
        
        Args:
            volumes: List of volume dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clear existing volumes
                cursor.execute('DELETE FROM volumes')
                
                # Insert new volumes
                for volume in volumes:
                    cursor.execute('''
                        INSERT INTO volumes (id, volume_folder, status, last_updated)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        volume['id'],
                        volume.get('volume_folder', f'Volume {volume["id"]}'),
                        volume.get('status', 'available'),
                        datetime.now()
                    ))
                
                # Update cache metadata
                cursor.execute('''
                    INSERT OR REPLACE INTO cache_metadata (key, value, last_updated)
                    VALUES (?, ?, ?)
                ''', ('volumes_count', str(len(volumes)), datetime.now()))
                
                # Store the total volumes from Kapowarr stats for comparison
                cursor.execute('''
                    INSERT OR REPLACE INTO cache_metadata (key, value, last_updated)
                    VALUES (?, ?, ?)
                ''', ('kapowarr_total_volumes', str(len(volumes)), datetime.now()))
                
                conn.commit()
                print(f"✅ Stored {len(volumes)} volumes in database")
                return True
                
        except Exception as e:
            print(f"❌ Error storing volumes: {e}")
            return False
    
    def get_volumes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve volumes from the database
        
        Args:
            limit: Maximum number of volumes to return (None for all)
            
        Returns:
            List of volume dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if limit:
                    cursor.execute('''
                        SELECT id, volume_folder, status, last_updated, 
                               total_issues, issues_with_files, metadata_processed, xml_generated, metadata_injected
                        FROM volumes 
                        ORDER BY id 
                        LIMIT ?
                    ''', (limit,))
                else:
                    cursor.execute('''
                        SELECT id, volume_folder, status, last_updated, 
                               total_issues, issues_with_files, metadata_processed, xml_generated, metadata_injected
                        FROM volumes 
                        ORDER BY id
                    ''')
                
                rows = cursor.fetchall()
                volumes = []
                
                for row in rows:
                    volumes.append({
                        'id': row[0],
                        'volume_folder': row[1],
                        'status': row[2],
                        'last_updated': row[3],
                        'total_issues': row[4],
                        'issues_with_files': row[5],
                        'metadata_processed': bool(row[6]),
                        'xml_generated': bool(row[7]),
                        'metadata_injected': bool(row[8])
                    })
                
                return volumes
                
        except Exception as e:
            print(f"❌ Error retrieving volumes: {e}")
            return []
    
    def store_volume_details(self, volume_id: int, details: Dict[str, Any]) -> bool:
        """Store detailed volume information
        
        Args:
            volume_id: ID of the volume
            details: Volume details dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Store details as JSON
                details_json = json.dumps(details, ensure_ascii=False)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO volume_details (volume_id, details_json, last_updated)
                    VALUES (?, ?, ?)
                ''', (volume_id, details_json, datetime.now()))
                
                # Update volume metadata
                issues = details.get('issues', [])
                total_issues = len(issues)
                issues_with_files = sum(1 for issue in issues if issue.get('files'))
                
                # Update volume folder if available in details
                volume_folder = None
                if 'folder' in details:
                    # Use the path mapping utility to convert Kapowarr path to local path
                    from utils import map_kapowarr_to_local_path
                    from settings_manager import settings_manager
                    kapowarr_parent_folder = settings_manager.get_setting('kapowarr_parent_folder', '/comics-1')
                    volume_folder = map_kapowarr_to_local_path(
                        details['folder'], 
                        kapowarr_parent_folder, 
                        'comics'  # Changed from '/comics' to 'comics' for relative path
                    )
                
                if volume_folder:
                    cursor.execute('''
                        UPDATE volumes 
                        SET total_issues = ?, issues_with_files = ?, volume_folder = ?, last_updated = ?
                        WHERE id = ?
                    ''', (total_issues, issues_with_files, volume_folder, datetime.now(), volume_id))
                else:
                    cursor.execute('''
                        UPDATE volumes 
                        SET total_issues = ?, issues_with_files = ?, last_updated = ?
                        WHERE id = ?
                    ''', (total_issues, issues_with_files, datetime.now(), volume_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Error storing volume details: {e}")
            return False
    
    def get_volume_details(self, volume_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve detailed volume information
        
        Args:
            volume_id: ID of the volume
            
        Returns:
            Volume details dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT details_json, last_updated
                    FROM volume_details 
                    WHERE volume_id = ?
                ''', (volume_id,))
                
                row = cursor.fetchone()
                if row:
                    details = json.loads(row[0])
                    details['_cached_at'] = row[1]
                    return details
                
                return None
                
        except Exception as e:
            print(f"❌ Error retrieving volume details: {e}")
            return None
    
    def update_volume_status(self, volume_id: int, **kwargs) -> bool:
        """Update volume status and metadata
        
        Args:
            volume_id: ID of the volume
            **kwargs: Fields to update (metadata_processed, xml_generated, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                fields = []
                values = []
                
                for key, value in kwargs.items():
                    if key in ['metadata_processed', 'xml_generated', 'metadata_injected', 'total_issues', 'issues_with_files']:
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                if fields:
                    fields.append("last_updated = ?")
                    values.append(datetime.now())
                    values.append(volume_id)
                    
                    query = f"UPDATE volumes SET {', '.join(fields)} WHERE id = ?"
                    cursor.execute(query, values)
                    conn.commit()
                    return True
                
                return False
                
        except Exception as e:
            print(f"❌ Error updating volume status: {e}")
            return False
    
    def is_cache_valid(self, max_age_hours: int = 24) -> bool:
        """Check if the volume cache is still valid
        
        Args:
            max_age_hours: Maximum age of cache in hours
            
        Returns:
            True if cache is valid, False otherwise
        """
        try:
            print(f"🔍 Checking cache validity with max_age_hours={max_age_hours}")
            print(f"🔍 Database path: {self.db_path}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if cache_metadata table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache_metadata'")
                table_exists = cursor.fetchone()
                print(f"🔍 cache_metadata table exists: {table_exists is not None}")
                
                if not table_exists:
                    print("⚠️ cache_metadata table does not exist")
                    return False
                
                cursor.execute('''
                    SELECT last_updated FROM cache_metadata 
                    WHERE key = 'volumes_count'
                ''')
                
                row = cursor.fetchone()
                print(f"🔍 Found cache_metadata row: {row}")
                
                if row:
                    last_updated = datetime.fromisoformat(row[0])
                    max_age = timedelta(hours=max_age_hours)
                    cache_age = datetime.now() - last_updated
                    is_valid = cache_age < max_age
                    
                    print(f"🔍 Last updated: {last_updated}")
                    print(f"🔍 Cache age: {cache_age}")
                    print(f"🔍 Max age: {max_age}")
                    print(f"🔍 Is valid: {is_valid}")
                    
                    return is_valid
                else:
                    print("⚠️ No volumes_count key found in cache_metadata")
                    return False
                
        except Exception as e:
            print(f"❌ Error checking cache validity: {e}")
            return False
    
    def check_kapowarr_stats_changed(self, current_total_volumes: int) -> bool:
        """Check if Kapowarr stats have changed since last cache update
        
        Args:
            current_total_volumes: Current total volumes from Kapowarr stats
            
        Returns:
            True if stats have changed, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT value FROM cache_metadata 
                    WHERE key = 'kapowarr_total_volumes'
                ''')
                
                row = cursor.fetchone()
                if row:
                    cached_total = int(row[0])
                    return current_total_volumes != cached_total
                
                # If no cached stats, consider it changed
                return True
                
        except Exception as e:
            print(f"❌ Error checking Kapowarr stats: {e}")
            return True
    
    def get_last_kapowarr_stats(self) -> Optional[int]:
        """Get the last known total volumes from Kapowarr stats
        
        Returns:
            Total volumes count or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT value FROM cache_metadata 
                    WHERE key = 'kapowarr_total_volumes'
                ''')
                
                row = cursor.fetchone()
                if row:
                    return int(row[0])
                
                return None
                
        except Exception as e:
            print(f"❌ Error getting last Kapowarr stats: {e}")
            return None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache
        
        Returns:
            Dictionary with cache information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get volumes count
                cursor.execute('SELECT COUNT(*) FROM volumes')
                volumes_count = cursor.fetchone()[0]
                
                # Get cache age
                cursor.execute('''
                    SELECT last_updated FROM cache_metadata 
                    WHERE key = 'volumes_count'
                ''')
                
                row = cursor.fetchone()
                cache_age = None
                if row:
                    last_updated = datetime.fromisoformat(row[0])
                    cache_age = datetime.now() - last_updated
                
                # Get processing statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN metadata_processed THEN 1 ELSE 0 END) as metadata_processed,
                        SUM(CASE WHEN xml_generated THEN 1 ELSE 0 END) as xml_generated
                    FROM volumes
                ''')
                
                stats_row = cursor.fetchone()
                stats = {
                    'total': stats_row[0] if stats_row[0] else 0,
                    'metadata_processed': stats_row[1] if stats_row[1] else 0,
                    'xml_generated': stats_row[2] if stats_row[2] else 0
                }
                
                # Get Kapowarr stats comparison
                last_kapowarr_total = self.get_last_kapowarr_stats()
                
                return {
                    'volumes_count': volumes_count,
                    'cache_age': cache_age,
                    'processing_stats': stats,
                    'database_path': str(self.db_path),
                    'last_kapowarr_total': last_kapowarr_total
                }
                
        except Exception as e:
            print(f"❌ Error getting cache info: {e}")
            return {}
    
    def clear_cache(self) -> bool:
        """Clear all cached data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM volumes')
                cursor.execute('DELETE FROM volume_details')
                cursor.execute('DELETE FROM cache_metadata')
                
                conn.commit()
                print("✅ Volume cache cleared")
                return True
                
        except Exception as e:
            print(f"❌ Error clearing cache: {e}")
            return False
    
    def cleanup_old_data(self, days_old: int = 30) -> bool:
        """Clean up old volume details data
        
        Args:
            days_old: Remove data older than this many days
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days_old)
                
                cursor.execute('''
                    DELETE FROM volume_details 
                    WHERE last_updated < ?
                ''', (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    print(f"✅ Cleaned up {deleted_count} old volume details")
                
                return True
                
        except Exception as e:
            print(f"❌ Error cleaning up old data: {e}")
            return False

    def update_paths_to_relative(self) -> bool:
        """Update existing volume folders to use relative paths instead of absolute paths"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all volumes with absolute paths
                cursor.execute("SELECT id, volume_folder FROM volumes WHERE volume_folder LIKE '/comics/%'")
                volumes_to_update = cursor.fetchall()
                
                if not volumes_to_update:
                    print("✅ No volumes with absolute paths found, nothing to update")
                    return True
                
                print(f"🔄 Found {len(volumes_to_update)} volumes with absolute paths, updating to relative...")
                
                updated_count = 0
                for volume_id, old_folder in volumes_to_update:
                    # Convert /comics/... to comics/...
                    new_folder = old_folder.replace('/comics/', 'comics/')
                    
                    cursor.execute('''
                        UPDATE volumes 
                        SET volume_folder = ?, last_updated = ?
                        WHERE id = ?
                    ''', (new_folder, datetime.now(), volume_id))
                    
                    updated_count += 1
                    print(f"  Updated volume {volume_id}: {old_folder} → {new_folder}")
                
                conn.commit()
                print(f"✅ Successfully updated {updated_count} volume paths to relative format")
                return True
                
        except Exception as e:
            print(f"❌ Error updating paths to relative: {e}")
            return False

    def force_schema_migration(self) -> bool:
        """Force database schema migration by recreating the database with new schema"""
        try:
            print("🔄 Forcing database schema migration...")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get existing data
                cursor.execute("SELECT id, volume_folder, status, last_updated FROM volumes")
                existing_volumes = cursor.fetchall()
                
                cursor.execute("SELECT volume_id, details_json, last_updated FROM volume_details")
                existing_details = cursor.fetchall()
                
                cursor.execute("SELECT key, value, last_updated FROM cache_metadata")
                existing_cache = cursor.fetchall()
                
                print(f"📊 Backing up {len(existing_volumes)} volumes, {len(existing_details)} details, {len(existing_cache)} cache entries")
                
                # Drop and recreate tables with new schema
                cursor.execute("DROP TABLE IF EXISTS volumes")
                cursor.execute("DROP TABLE IF EXISTS volume_details")
                cursor.execute("DROP TABLE IF EXISTS cache_metadata")
                
                # Recreate tables with new schema
                cursor.execute('''
                    CREATE TABLE volumes (
                        id INTEGER PRIMARY KEY,
                        volume_folder TEXT NOT NULL,
                        status TEXT DEFAULT 'available',
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_issues INTEGER DEFAULT 0,
                        issues_with_files INTEGER DEFAULT 0,
                        metadata_processed BOOLEAN DEFAULT FALSE,
                        xml_generated BOOLEAN DEFAULT FALSE,
                        metadata_injected BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE volume_details (
                        volume_id INTEGER PRIMARY KEY,
                        details_json TEXT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (volume_id) REFERENCES volumes (id)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE cache_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Restore existing data
                for volume in existing_volumes:
                    cursor.execute('''
                        INSERT INTO volumes (id, volume_folder, status, last_updated)
                        VALUES (?, ?, ?, ?)
                    ''', volume)
                
                for detail in existing_details:
                    cursor.execute('''
                        INSERT INTO volume_details (volume_id, details_json, last_updated)
                        VALUES (?, ?, ?)
                    ''', detail)
                
                for cache_entry in existing_cache:
                    cursor.execute('''
                        INSERT INTO cache_metadata (key, value, last_updated)
                        VALUES (?, ?, ?)
                    ''', cache_entry)
                
                conn.commit()
                print("✅ Database schema migration completed successfully")
                return True
                
        except Exception as e:
            print(f"❌ Error during schema migration: {e}")
            return False


# Global volume database instance
volume_db = VolumeDatabase()
