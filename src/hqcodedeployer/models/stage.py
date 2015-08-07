from hqlib.sql import Base
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship


class Stage(Base):

    __tablename__ = 'cd_stages'

    id = Column(Integer, primary_key=True)
    app = Column(String, nullable=False)
    type = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    job = relationship('Job', uselist=False)
