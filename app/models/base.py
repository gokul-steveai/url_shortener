from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    All database models will inherit from this class.
    It acts as the central catalog for our schema.
    """
    pass