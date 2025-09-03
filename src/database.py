import os
import json
from sqlalchemy import create_engine, Column, String, Text, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = None
SessionLocal = None

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    try:
        engine = create_engine(DATABASE_URL)
        metadata = MetaData()
        user_tokens = Table('user_tokens', metadata,
            Column('user_id', String, primary_key=True),
            Column('token_data', Text, nullable=False)
        )
        metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database connection established and table checked.")
    except Exception as e:
        logger.error(f"Failed to connect to database or setup table: {e}")
        engine = None

def save_creds(user_id: str, creds: Credentials):
    """Saves or updates a user's credentials in the database."""
    if not SessionLocal:
        logger.error("Database not configured. Cannot save credentials.")
        return
    
    session = SessionLocal()
    try:
        token_json = json.dumps({
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        })
        
        existing = session.query(user_tokens).filter_by(user_id=str(user_id)).first()
        if existing:
            session.query(user_tokens).filter_by(user_id=str(user_id)).update({"token_data": token_json})
        else:
            new_token = user_tokens.insert().values(user_id=str(user_id), token_data=token_json)
            session.execute(new_token)
            
        session.commit()
        logger.info(f"Credentials saved for user {user_id}")
    except SQLAlchemyError as e:
        logger.error(f"Database error while saving credentials for user {user_id}: {e}")
        session.rollback()
    finally:
        session.close()

def get_creds(user_id: str) -> Credentials | None:
    """Retrieves a user's credentials object from the database."""
    if not SessionLocal:
        logger.error("Database not configured. Cannot get credentials.")
        return None
        
    session = SessionLocal()
    try:
        result = session.query(user_tokens).filter_by(user_id=str(user_id)).first()
        if result and result.token_data:
            token_data = json.loads(result.token_data)
            creds = Credentials(**token_data)
            logger.info(f"Credentials retrieved for user {user_id}")
            return creds
        return None
    except (SQLAlchemyError, json.JSONDecodeError) as e:
        logger.error(f"Database or JSON error while getting credentials for user {user_id}: {e}")
        return None
    finally:
        session.close()

def delete_token(user_id: str):
    """Deletes a user's token from the database."""
    if not SessionLocal:
        logger.error("Database not configured. Cannot delete token.")
        return

    session = SessionLocal()
    try:
        session.query(user_tokens).filter_by(user_id=str(user_id)).delete()
        session.commit()
        logger.info(f"Token deleted for user {user_id}")
    except SQLAlchemyError as e:
        logger.error(f"Database error while deleting token for user {user_id}: {e}")
        session.rollback()
    finally:
        session.close()