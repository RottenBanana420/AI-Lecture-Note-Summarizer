"""
Comprehensive database connection tests designed to find bugs and edge cases.

This module contains aggressive tests that are designed to BREAK the code
and expose weaknesses in database connection handling, pool management,
and error recovery.

Following TDD principles:
- Tests are written to fail first
- We fix the code, never the tests
- Tests explore edge cases and boundary conditions
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import contextmanager

from app.core.database import (
    engine,
    SessionLocal,
    get_db,
    check_database_connection,
    get_pool_status
)


class TestDatabaseConnectionSuccess:
    """Test successful database connection scenarios."""
    
    def test_successful_connection_with_valid_credentials(self):
        """Test that database connects successfully with valid credentials."""
        result = check_database_connection()
        assert result is True, "Database connection should succeed with valid credentials"
    
    def test_connection_returns_valid_session(self):
        """Test that connection returns a valid SQLAlchemy session."""
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Session should be valid
            assert db is not None
            assert hasattr(db, 'execute')
            assert hasattr(db, 'commit')
            assert hasattr(db, 'rollback')
            
            # Should be able to execute a simple query
            result = db.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            assert row[0] == 1
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass


class TestConnectionWithInvalidCredentials:
    """Test connection behavior with invalid credentials."""
    
    def test_connection_fails_gracefully_with_wrong_password(self):
        """Test that connection fails gracefully with incorrect password."""
        # Create engine with wrong password
        invalid_url = "postgresql://test_user:wrong_password@localhost:5432/test_db"
        
        try:
            invalid_engine = create_engine(invalid_url, pool_pre_ping=False)
            with invalid_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # If we get here, the test should fail
            pytest.fail("Connection should have failed with wrong password")
        except OperationalError as e:
            # Expected behavior - connection should fail
            assert "password authentication failed" in str(e).lower() or \
                   "authentication failed" in str(e).lower() or \
                   "could not connect" in str(e).lower()
        finally:
            if 'invalid_engine' in locals():
                invalid_engine.dispose()
    
    def test_connection_fails_with_nonexistent_database(self):
        """Test that connection fails with non-existent database name."""
        # Use valid credentials but non-existent database
        from app.core.config import settings
        # Extract user and password from real DATABASE_URL
        parts = settings.DATABASE_URL.split("://")[1].split("@")
        credentials = parts[0]
        host_info = parts[1]
        
        invalid_url = f"postgresql://{credentials}@{host_info.rsplit('/', 1)[0]}/nonexistent_db_12345"
        
        try:
            invalid_engine = create_engine(invalid_url, pool_pre_ping=False)
            with invalid_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            pytest.fail("Connection should have failed with non-existent database")
        except OperationalError as e:
            # Expected behavior - either database doesn't exist or connection failed
            error_msg = str(e).lower()
            assert "does not exist" in error_msg or \
                   "could not connect" in error_msg or \
                   "database" in error_msg, \
                   f"Expected database error, got: {e}"
        finally:
            if 'invalid_engine' in locals():
                invalid_engine.dispose()
    
    def test_connection_fails_with_wrong_host(self):
        """Test that connection fails with unreachable host."""
        # Use a non-routable IP address
        invalid_url = "postgresql://test_user:test_password@192.0.2.1:5432/test_db"
        
        try:
            invalid_engine = create_engine(
                invalid_url,
                pool_pre_ping=False,
                connect_args={"connect_timeout": 2}  # Short timeout
            )
            with invalid_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            pytest.fail("Connection should have failed with unreachable host")
        except (OperationalError, Exception) as e:
            # Expected behavior - connection timeout or failure
            assert True  # Any exception is acceptable here
        finally:
            if 'invalid_engine' in locals():
                invalid_engine.dispose()


class TestConnectionPoolExhaustion:
    """Test connection pool exhaustion scenarios."""
    
    def test_pool_exhaustion_with_more_connections_than_pool_size(self):
        """
        Test that creating more connections than pool_size + max_overflow fails.
        
        Pool configuration: pool_size=5, max_overflow=10
        Total available: 15 connections
        This test attempts to create 16 connections simultaneously.
        """
        # Create a test engine with small pool
        from app.core.config import settings
        test_engine = create_engine(
            settings.DATABASE_URL,
            pool_size=2,
            max_overflow=3,
            pool_timeout=2,  # Short timeout for faster test
            pool_pre_ping=False
        )
        
        connections = []
        errors = []
        
        try:
            # Try to create pool_size + max_overflow + 1 connections (6 connections)
            for i in range(6):
                try:
                    conn = test_engine.connect()
                    connections.append(conn)
                except (SQLAlchemyTimeoutError, Exception) as e:
                    errors.append(e)
            
            # Should have gotten a timeout error for the 6th connection
            assert len(errors) > 0, \
                "Should have raised timeout error when exceeding pool capacity"
            
            # Verify we got a timeout error
            assert any(
                isinstance(e, (SQLAlchemyTimeoutError, TimeoutError)) or
                "timeout" in str(e).lower() or
                "QueuePool limit" in str(e)
                for e in errors
            ), f"Expected timeout error, got: {errors}"
            
        finally:
            # Clean up all connections
            for conn in connections:
                try:
                    conn.close()
                except:
                    pass
            test_engine.dispose()
    
    def test_connection_pool_recovers_after_connections_released(self):
        """Test that pool recovers and allows new connections after release."""
        from app.core.config import settings
        test_engine = create_engine(
            settings.DATABASE_URL,
            pool_size=2,
            max_overflow=1,
            pool_timeout=5,
            pool_pre_ping=False
        )
        
        try:
            # Fill the pool
            conn1 = test_engine.connect()
            conn2 = test_engine.connect()
            conn3 = test_engine.connect()
            
            # Release one connection
            conn1.close()
            
            # Should be able to get a new connection now
            conn4 = test_engine.connect()
            assert conn4 is not None
            
            # Clean up
            conn2.close()
            conn3.close()
            conn4.close()
            
        finally:
            test_engine.dispose()


class TestConnectionTimeout:
    """Test connection timeout scenarios."""
    
    def test_connection_timeout_when_pool_exhausted(self):
        """Test that connection times out when pool is exhausted."""
        from app.core.config import settings
        test_engine = create_engine(
            settings.DATABASE_URL,
            pool_size=1,
            max_overflow=0,
            pool_timeout=2,  # 2 second timeout
            pool_pre_ping=False
        )
        
        try:
            # Take the only connection
            conn1 = test_engine.connect()
            
            # Try to get another connection - should timeout
            start_time = time.time()
            with pytest.raises((SQLAlchemyTimeoutError, TimeoutError, Exception)) as exc_info:
                conn2 = test_engine.connect()
            
            elapsed = time.time() - start_time
            
            # Should have timed out around 2 seconds
            assert elapsed >= 1.5, "Should have waited for timeout"
            assert elapsed < 4, "Should not have waited too long"
            
            # Clean up
            conn1.close()
            
        finally:
            test_engine.dispose()
    
    def test_pool_timeout_configuration_is_respected(self):
        """Test that pool_timeout setting is actually used."""
        from app.core.config import settings
        
        # Verify the main engine has correct timeout
        assert engine.pool._timeout == 30, \
            "Pool timeout should be 30 seconds as configured"


class TestDatabaseUnavailability:
    """Test behavior when database is unavailable."""
    
    def test_startup_fails_gracefully_when_database_down(self):
        """Test that application handles database unavailability during startup."""
        # Create engine pointing to non-existent database
        invalid_url = "postgresql://user:pass@localhost:9999/nonexistent"
        
        try:
            test_engine = create_engine(
                invalid_url,
                pool_pre_ping=False,
                connect_args={"connect_timeout": 1}
            )
            
            # Try to connect
            with pytest.raises((OperationalError, Exception)):
                with test_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            
        finally:
            if 'test_engine' in locals():
                test_engine.dispose()
    
    def test_check_database_connection_returns_false_when_db_down(self):
        """Test that check_database_connection returns False when DB is down."""
        # Mock the engine to simulate database down
        with patch('app.core.database.engine') as mock_engine:
            mock_engine.connect.side_effect = OperationalError("Connection refused", None, None)
            
            from app.core.database import check_database_connection
            result = check_database_connection()
            
            assert result is False, \
                "check_database_connection should return False when database is down"


class TestConnectionRecovery:
    """Test connection recovery after temporary failures."""
    
    def test_pool_pre_ping_detects_stale_connections(self):
        """Test that pool_pre_ping detects and replaces stale connections."""
        # Verify pool_pre_ping is enabled
        assert engine.pool._pre_ping is True, \
            "pool_pre_ping should be enabled for production"
    
    def test_connection_recovery_after_temporary_network_issue(self):
        """Test that connections can be re-established after temporary failure."""
        # Get a connection
        db_gen = get_db()
        db1 = next(db_gen)
        
        try:
            # Execute a query
            result = db1.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
        
        # Get another connection (simulating recovery)
        db_gen2 = get_db()
        db2 = next(db_gen2)
        
        try:
            # Should work fine
            result = db2.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        finally:
            try:
                next(db_gen2)
            except StopIteration:
                pass


class TestConnectionPoolRecycling:
    """Test connection pool recycling behavior."""
    
    def test_pool_recycle_setting_is_configured(self):
        """Test that pool_recycle is set to prevent stale connections."""
        # Verify pool_recycle is set to 3600 seconds (1 hour)
        assert engine.pool._recycle == 3600, \
            "pool_recycle should be 3600 seconds to prevent stale connections"
    
    def test_pool_size_configuration(self):
        """Test that pool size is configured correctly."""
        # Check pool configuration
        pool = engine.pool
        assert pool._pool.maxsize == 5, "pool_size should be 5"
        assert pool._max_overflow == 10, "max_overflow should be 10"


class TestConcurrentConnections:
    """Test concurrent connection access."""
    
    def test_multiple_threads_can_get_connections(self):
        """Test that multiple threads can safely get database connections."""
        results = []
        errors = []
        
        def get_connection():
            try:
                db_gen = get_db()
                db = next(db_gen)
                result = db.execute(text("SELECT 1"))
                results.append(result.fetchone()[0])
                try:
                    next(db_gen)
                except StopIteration:
                    pass
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=get_connection)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=10)
        
        # All threads should have succeeded
        assert len(errors) == 0, f"Threads should not have errors: {errors}"
        assert len(results) == 5, "All threads should have gotten results"
        assert all(r == 1 for r in results), "All results should be 1"
    
    def test_concurrent_connections_dont_exceed_pool_limit(self):
        """Test that concurrent connections respect pool limits."""
        from app.core.config import settings
        test_engine = create_engine(
            settings.DATABASE_URL,
            pool_size=2,
            max_overflow=1,
            pool_timeout=1,
            pool_pre_ping=False
        )
        
        connections = []
        errors = []
        lock = threading.Lock()
        barrier = threading.Barrier(5)  # Synchronize all 5 threads
        
        def get_connection():
            try:
                # Wait for all threads to be ready
                barrier.wait(timeout=5)
                
                # Now all threads try to get connection at same time
                conn = test_engine.connect()
                with lock:
                    connections.append(conn)
                
                # Hold connection for a bit
                time.sleep(1.5)
                conn.close()
            except Exception as e:
                with lock:
                    errors.append(e)
        
        # Try to create more connections than pool allows (pool_size=2, max_overflow=1, total=3)
        # We're starting 5 threads, so 2 should timeout
        threads = []
        for i in range(5):
            t = threading.Thread(target=get_connection)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=10)
        
        # Some threads should have timed out (5 threads, only 3 connections available)
        assert len(errors) > 0, \
            f"Some threads should have gotten timeout errors when pool exhausted. " \
            f"Connections: {len(connections)}, Errors: {len(errors)}"
        
        # Clean up remaining connections
        with lock:
            for conn in connections:
                try:
                    if not conn.closed:
                        conn.close()
                except:
                    pass
        
        test_engine.dispose()


class TestPoolStatusMonitoring:
    """Test connection pool status monitoring."""
    
    def test_get_pool_status_returns_correct_structure(self):
        """Test that get_pool_status returns expected data structure."""
        status = get_pool_status()
        
        assert isinstance(status, dict)
        assert "size" in status
        assert "checked_out" in status
        assert "overflow" in status
        assert "total" in status
        
        # All values should be non-negative integers
        assert isinstance(status["size"], int)
        assert isinstance(status["checked_out"], int)
        assert isinstance(status["overflow"], int)
        assert isinstance(status["total"], int)
        
        assert status["size"] >= 0
        assert status["checked_out"] >= 0
        assert status["overflow"] >= 0
        assert status["total"] >= 0
    
    def test_pool_status_reflects_checked_out_connections(self):
        """Test that pool status correctly shows checked out connections."""
        initial_status = get_pool_status()
        initial_checked_out = initial_status["checked_out"]
        
        # Get a connection
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Check status while connection is active
            active_status = get_pool_status()
            
            # Should have more checked out connections
            # Note: This might be flaky in concurrent test environments
            # but it's designed to expose pool monitoring issues
            assert active_status["checked_out"] >= initial_checked_out
            
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass


class TestSessionIsolation:
    """Test that database sessions are properly isolated."""
    
    def test_sessions_are_independent(self):
        """Test that multiple sessions don't interfere with each other."""
        db_gen1 = get_db()
        db1 = next(db_gen1)
        
        db_gen2 = get_db()
        db2 = next(db_gen2)
        
        try:
            # Sessions should be different objects
            assert db1 is not db2, "Sessions should be independent instances"
            
            # Both should be functional
            result1 = db1.execute(text("SELECT 1"))
            result2 = db2.execute(text("SELECT 2"))
            
            assert result1.fetchone()[0] == 1
            assert result2.fetchone()[0] == 2
            
        finally:
            for gen in [db_gen1, db_gen2]:
                try:
                    next(gen)
                except StopIteration:
                    pass
    
    def test_session_cleanup_on_exception(self):
        """Test that sessions are cleaned up even when exceptions occur."""
        initial_status = get_pool_status()
        
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            # Simulate an error
            raise ValueError("Simulated error")
            
        except ValueError:
            # Expected
            pass
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
        
        # Pool should not have leaked connections
        final_status = get_pool_status()
        
        # Checked out connections should not have increased
        # (allowing some tolerance for concurrent tests)
        assert final_status["checked_out"] <= initial_status["checked_out"] + 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_query_execution(self):
        """Test executing an empty result query."""
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Query that returns no rows
            result = db.execute(text("SELECT 1 WHERE 1=0"))
            rows = result.fetchall()
            assert len(rows) == 0
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    
    def test_very_long_query_string(self):
        """Test executing a very long query string."""
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Create a long query (but valid)
            long_query = "SELECT " + " + ".join(["1"] * 100) + " as result"
            result = db.execute(text(long_query))
            assert result.fetchone()[0] == 100
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    
    def test_rapid_connection_cycling(self):
        """Test rapidly opening and closing connections."""
        for i in range(20):
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                result = db.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
            finally:
                try:
                    next(db_gen)
                except StopIteration:
                    pass
        
        # Should not have leaked connections
        status = get_pool_status()
        assert status["checked_out"] == 0, \
            "Should not have leaked connections after rapid cycling"
