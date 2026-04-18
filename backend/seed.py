import uuid
from datetime import datetime

import bcrypt

from database import Base, engine, SessionLocal
import models

Base.metadata.create_all(bind=engine)
print("DB 초기화 완료")

db = SessionLocal()
try:
    existing = db.query(models.User).filter_by(email="admin@interx.com").first()
    if existing:
        print("테스트 계정 이미 존재")
    else:
        password_hash = bcrypt.hashpw("interx1234".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        admin = models.User(
            id=str(uuid.uuid4()),
            email="admin@interx.com",
            password_hash=password_hash,
            name="관리자",
            created_at=datetime.utcnow(),
        )
        db.add(admin)
        db.commit()
        print("테스트 계정 생성됨: admin@interx.com / interx1234")
finally:
    db.close()
