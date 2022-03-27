from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://yvfctofzlacjco:9bfd0804305d837b8319bc12af8e0c156e8af3f148b7f93c7d556e174ffa608c@ec2-54-216-48-43.eu-west-1.compute.amazonaws.com:5432/d2lgih4j5md8qu"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
