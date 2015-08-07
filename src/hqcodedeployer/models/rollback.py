from hqlib.sql import Base
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship


class Rollback(Base):

    __tablename__ = 'cd_rollbacks'

    id = Column(Integer, primary_key=True)
    environment = Column(String, nullable=False)
    app = Column(String, nullable=False)
    type = Column(String, nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    job = relationship('Job', uselist=False)
