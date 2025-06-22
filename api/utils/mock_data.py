from db import SessionLocal
from models.knowledge import Knowledge
from models.predictor import Predictor
# Import other models as needed

def insert_mock_data():
    db = SessionLocal()
    try:
        # Example: Add a mock admin user to Knowledge and Predictor
        if not db.query(Knowledge).first():
            knowledge = Knowledge(name="Mock Knowledge", description="Demo knowledge asset")
            db.add(knowledge)
            db.commit()
            db.refresh(knowledge)
            predictor = Predictor(name="Mock Predictor", framework="sklearn", scores={"acc": 0.99}, knowledge_id=knowledge.id)
            db.add(predictor)
            db.commit()
        # Add more mock data for other models as needed
    finally:
        db.close()
