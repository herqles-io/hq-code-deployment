from hqlib.sql import Base
from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship

class Deploy(Base):

    __tablename__ = 'cd_deploys'

    id = Column(Integer, primary_key=True)
    environment = Column(String, nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    job = relationship('Job', uselist=False)
    stage_id = Column(Integer, ForeignKey('cd_stages.id'), nullable=False)
    stage = relationship('Stage', uselist=False)
