#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize database
"""

from app import app, db

def init_database():
    """Initialize database tables"""
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database tables initialized")

        # No longer add default devices
        # Devices will be registered on first connection
        print("Database cleared, waiting for device connection...")

if __name__ == "__main__":
    init_database()
