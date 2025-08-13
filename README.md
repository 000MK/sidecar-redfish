# sidecar-redfish

Implement sidecar Redfish API  


## Startup Service
Enter your python virtual environment and run
```bash
cd ${PROJECT_ROOT}

# For dev
python app.py --proj-name=sidecar-redfish --env=dev
python app.py --proj-name=sidecar-redfish --env-file=.env-dev # `env-file` is higher priority than `env`

# For prod
python app.py --proj-name=sidecar-redfish --env=prod
python app.py --proj-name=sidecar-redfish --env-file=.env 
```


## Repo Structure  
```
{project_name}/
|--.github/        # 放置github action設定檔
|--etc/            # 放置無法歸類的檔案或設定檔
|--mylib/
   |--adapters/    # 放置adapter
   |--auth/        # 放置auth
   |--common/      # 放置共用常數、定義…
      |--proj_error.py # 共同的error,exception (redfish有規範回應的錯誤格式)
   |--db/          # 放置db
   |--managements/ # 放置管理
   |--models/      # 放置 ORM Model 或 Redfish Model
   |--routers/     # 放置blueprint
      |--account_service_router.py # redfish AccountService api
      |--session_service_router.py # redfish SessionService api
      |--...
   |--services/    # Logic Layer
   |--utils/       # 放置工具
|--test/           # 放置 unit test
|--.env            # 環境變數設定檔
|--.env-dev        # 開發環境變數設定檔
|--.env-test       # 測試環境變數設定檔
|--app.py          # Flask main app
|--load_dotenv.py  # 環境變數模組
|--requirements.txt
```

## Folder Structure
```
/home/user/
   |--logs/
      |--sidecar-redfish/
   |--service/
      |--RestAPI
      |--sidecar-redfish/ # RedfishAPI to be deployed here
      |--webUI
   |--data/
      |--sidecar-redfish/
         |--CertificateService/
         |--EventService/
         |--LogService/
         |--TelemetryService/
```

## Other Documents
* [AccountService,SessionService Planning Doc](https://docs.google.com/document/d/102J-SfI7yyY3LnNWWcaKx2A0af6lKepY4VmaWh-lwR8/edit?tab=t.0)  
* [TelemetryService,LogService Planning Doc](https://docs.google.com/document/d/1it9xa68h63bwkTzLaEP8XFASAtCUq-e_cG31ZxOPdvQ/edit?tab=t.0#heading=h.xz9w99bxf8cn)  

## Response JSON
Use `jsonify()` to handle response JSON with specific encoding  
```python
return jsonify({
    "examples": examples
}), HTTPStatus.OK
```

, and json encoded by `MyJSONProvider` before responding.  
```python
class MyJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        kwargs.setdefault(
            "ensure_ascii", False
        )  # Not use unicode (ex: "μs/cm", not "\u03bcs/cm")
        # kwargs.setdefault("indent", None)  # if requires pretty
        return json.dumps(obj, **kwargs)
```


## Error Handling  
Use ProjRedfishError/ProjError to raise your Exception  
```python
raise ProjError(code=HTTPStatus.BAD_REQUEST, message="some exception")
# or
raise ProjRedfishError(code=ProjRedfishErrorCode.GENERAL_ERROR, message="some exception")
```

, and error handled by `@api.errorhandler`.  
```python
@api.errorhandler(ProjError)
def handle_proj_error(e):
    return e.to_redfish_error_dict(), e.code

@api.errorhandler(ProjRedfishError)
def handle_proj_redfish_error(e):
    return e.to_dict(), e.http_status
```



## Testing ##
Use pytest framework to test    

#### Install
```
pip install pytest
pip install pytest-html
pip install pytest-cov
```

#### Run
Beforehand: Enter your python virtual environment
```bash
cd ${PROJECT_ROOT}
# Run whole test cases
pytest --proj-name=${PROJECT_NAME}
pytest -v --proj-name=${PROJECT_NAME}
pytest -v test/ --proj-name=${PROJECT_NAME}
pytest -v test/ --html=/tmp/report.html --env-file=.env-test --proj-name=${PROJECT_NAME}
# or Run specific test cases
pytest -v test/test_root_router.py --proj-name=${PROJECT_NAME}
# Generate html report at /tmp/report.html & coverage report at /tmp/htmlcov/
pytest --html=/tmp/report.html --self-contained-html --cov=. --cov-report=html:/tmp/htmlcov/ --proj-name=${PROJECT_NAME}
```
Or use VSCode by `.vscode/launch.json`
```json
{
  "version": "0.2.0",
  "configurations": [
    {
        "name": "Python: pytest",
        "type": "python",
        "request": "launch",
        "module": "pytest",
        "args": [
            "test/", 
            "--html=/tmp/report.html",
            "--env-file=.env-test"
        ],
        "justMyCode": false,
    }
  ]
}
```

## API Namespace
支援不同專案會有不同namespace  
Step1: 定義namespace
```python
# namespace必須給名字，用於比對使用 (給''則一律加入至app)
Chassis_ns = Namespace('Chassis')
Chassis_ThermalSubsystem_Fans_ns = Namespace('Chassis.ThermalSubsystem.Fans')
```
Step2: 定義 SupportedApiNamespaceNames  
```yaml
# 在 redfish_info.yaml 中定義
SupportedApiNamespaceNames:
  - "Chassis"
  - "Chassis.ThermalSubsystem.Fans"
```
Step3: 呼叫  
```python
MyNamespaceHelper(api).register_namespaces(
    "mylib.routers.Chassis_router", 
    ["Chassis_ns", "Chassis_ThermalSubsystem_Fans_ns"]
)
```
(註) 有漂亮的方法，歡迎改寫。


## Flask-SQLAlchemy example ##

#### Install dependencies
```bash
pip install Flask-SQLAlchemy
```

#### How to use
1. Define your model inherit from `MyOrmBaseModel`  
```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from mylib.models.my_orm_base_model import MyOrmBaseModel

@dataclass
class ExampleModel(MyOrmBaseModel):
    # Define table name
    __tablename__ = 'examples'
    # Define columns
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(32))
```

2. Add `@dataclass` decorator to your model  
```python
from dataclasses import dataclass
@dataclass
class ExampleModel(MyOrmBaseModel):
    # **Note** You must add data type hint for dataclass
    # {COLUMN_NAME}: Mapped[{DATA_TYPE}] = mapped_column({DATA_TYPE})
    pass
```

3. Initialize db  
```python
from flask import Flask, jsonify
from mylib.db.extensions import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/user/storage/examples.db'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'max_overflow': 1,
    'pool_timeout': 10,
}
db.init_app(app)
```

4. Use model  
```python
from mylib.models.example_model import ExampleModel

@app.route('/examples')
def examples():
    examples = ExampleModel.all()
    return jsonify({
        "examples": examples
    })
```
Response:  
```json
{
  "examples": [
    {
      "id": 1,
      "title": "this is a example title 1"
    },
    {
      "id": 2,
      "title": "this is a example title 2"
    }
  ]
}
```
