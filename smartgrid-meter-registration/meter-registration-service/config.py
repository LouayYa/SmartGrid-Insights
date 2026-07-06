import os

class Config:
    # postgresql://<user>:<password>@<host>:5432/<db>  (append ?sslmode=require for hosted Postgres)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False