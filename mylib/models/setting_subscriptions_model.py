from typing import List
from dataclasses import dataclass
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy import Column, String, Integer, JSON, DateTime, func
from mylib.db.extensions import db
from mylib.models.my_orm_base_model import MyOrmBaseModel
from flask import abort
from typing import Any
import json
from datetime import datetime
from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy.ext.mutable import MutableDict

class JSONDateTime(TypeDecorator):
    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        # 这里把 dict 序列化成 str；自定义 default 来处理 datetime
        return json.dumps(value, default=lambda o: o.isoformat() if isinstance(o, datetime) else (_ for _ in ()).throw(TypeError))

    def process_result_value(self, value, dialect):
        # 反序列化时你可能就直接拿原始 dict，或者再加逻辑把字符串解析回 datetime
        return json.loads(value)
    
@dataclass
class SubscriptionModel(MyOrmBaseModel):
    __tablename__ = 'subscriptions'

    # 對應 Redfish Subscription 資料
    Id:      Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, unique=True)
    # 必要欄位
    Destination:           Mapped[str] = mapped_column(String(255), nullable=False)
    Context:               Mapped[str] = mapped_column(String(255), nullable=False)
    Protocol:              Mapped[str] = mapped_column(String(50), nullable=False)
    # 選填欄位
    DeliveryRetryPolicy:Mapped[str] = mapped_column(String(50), nullable=True)
    RegistryPrefixes:     Mapped[list] = mapped_column(JSON, nullable=True)
    ResourceTypes:        Mapped[list] = mapped_column(JSON, nullable=True)
    SubscriptionType:    Mapped[str] = mapped_column(String(50), nullable=True)
    EventFormatType:     Mapped[str] = mapped_column(String(50), nullable=True)
    # 各協定設定
    Settings: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONDateTime), default=dict)
    # 時間戳記
    created_at:            Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:            Mapped[str] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (f"SubscriptionModel(Id={self.Id}, Destination={self.Destination}, "
                f"Context={self.Context}, Protocol={self.Protocol})")

    @classmethod
    def sub_all(cls):
        return db.session.query(cls).all()

    @classmethod
    def sub_get_by_id(cls, sub_id: str):
        return db.session.get(cls, sub_id)

    @classmethod
    def sub_post(cls, data):
        """
        新增或更新 Subscription。
        data 需包含 "Context"、"Destination"、"Protocol" 等欄位。
        """
        # 轉 dict
        if not isinstance(data, dict):
            data = {col.name: getattr(data, col.name) for col in data.__table__.columns}

        # 檢查是否存在
        sub_id = data.get("Id")
        if sub_id:
            sub = cls.sub_get_by_id(sub_id) or abort(404, f"Subscription {sub_id} not found")
            action = "更新訂閱"
        else:
            sub = cls()
            db.session.add(sub)
            action = "新增訂閱"

        print(f"{action}: {sub_id or '(new)'}")

        common_fields: dict[str, Any] = {
            "Context":              "",
            "Destination":          "",
            "Protocol":             "",
            "SubscriptionType":     None,
            "DeliveryRetryPolicy":  "TerminateAfterRetries",
            "EventFormatType":      "Event",
            "RegistryPrefixes":     None,   
            "ResourceTypes":        None, 
        }

        for field, default in common_fields.items():
            # 如果 data 裡有該欄位就用它，否則就用預設值
            value = data.get(field, default)
            setattr(sub, field, value)
        # 將不是common_fields的欄位存入 Setting 
        setting = sub.Settings or {}
        for key, val in data.items():
            if key not in common_fields and key != "Id":
                setting[key] = val

        sub.Settings = setting

        db.session.commit()
        return sub.Id

    @classmethod
    def sub_delete(cls, sub_id: str):
        sub = cls.sub_get_by_id(sub_id)
        if sub:
            db.session.delete(sub)
            db.session.commit()
            return True
        return False
