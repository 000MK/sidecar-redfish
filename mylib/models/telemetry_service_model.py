from typing import List
from dataclasses import dataclass
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey
from mylib.db.extensions import db
from mylib.models.my_orm_base_model import MyOrmBaseModel


@dataclass
class TelemetryServiceModel(MyOrmBaseModel):
    __tablename__ = 'telemetry_service'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, nullable=False)
    resource : Mapped[str] = mapped_column(String(128), unique=False, nullable=False)
    metric_id : Mapped[str] = mapped_column(String(128), nullable=False)
    property : Mapped[str] = mapped_column(String(128), nullable=False)
    value : Mapped[str] = mapped_column(String(64), nullable=False)
        
    def __repr__(self):
        return f"TelemetryServiceModel(resource={self.resource}, metric_id=\"{self.metric_id}\", property=\"{self.property}\", value=\"{self.value}\")"
    
    @classmethod
    def all(cls):
        ret = db.session.query(cls).all()
        return ret
    
    @classmethod
    def get_by_property(cls, resource: str, metric_id: str, property: str):
        stmt = db.select(TelemetryServiceModel).where(
            TelemetryServiceModel.resource == resource, 
            TelemetryServiceModel.metric_id == metric_id, 
            TelemetryServiceModel.property == property
        )
        setting = db.session.execute(stmt).scalar_one_or_none()
        return setting

    @classmethod
    def save_metric_value(cls, resource: str, metric_id: str, property: str, value: str):
        try:
            fetched_setting = cls.get_by_property(resource, metric_id, property)
            if fetched_setting:
                fetched_setting.value = str(value)
                db.session.commit()
            else:
                new_setting = cls(resource=resource, metric_id=metric_id, property=property, value=str(value))
                db.session.add(new_setting)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f" * Error updating telemetry service {metric_id} {property}: {e}")
            return False
        return True
