# README #

因為多人開發的關係，這個資料夾有兩種models:  
* Redfish Model  (以Redfish官方Schema為基礎)  
* ORM Model  (以DB Table為基礎)  



## Redfish Model

請注意!  
因為來源是Redfish官方，所以檔名使用`rf_`，class名稱使用`Rf`作為開頭  

### Model定義方式(以PowerSupply為例)
schema文件：https://redfish.dmtf.org/schemas/v1/PowerSupply.v1_6_0.json  
在`definitions.PowerSupply.properties`可找到定義的欄位  

#### 欄位：Actions
```json
"Actions": {
    "$ref": "#/definitions/Actions",
    "description": "The available actions for this resource.",
    "longDescription": "This property shall contain the available actions for this resource."
}
```
`$ref`是定義內部欄位，有兩種寫法

1)優先定義在 rf_power_supply_model.py 檔案內 (與schema檔的定義一致)
```python
class RfActions(BaseModel):
    ...
class RfPowerSupplyModel(BaseModel):
    #...(略)
    Actions: Optional[RfActions] = Field(default=None)
```

2)次之，定義在inner class內
```python
class RfPowerSupplyModel(BaseModel):
    #...(略)
    class RfActions(BaseModel):
        #...(略)
    Actions: Optional[RfActions] = Field(default=None)
```
#### 欄位：InputNominalVoltageType
```json
"InputNominalVoltageType": {
    "anyOf": [
        {
            "$ref": "http://redfish.dmtf.org/schemas/v1/Circuit.json#/definitions/NominalVoltageType"
        },
        {
            "type": "null"
        }
    ],
    "description": "The nominal voltage ...",
    "longDescription": "This property shall ...",
    "readonly": true
},
```
沒定義type資訊，則進一步看`anyOf`資訊  
anyOf看到`$ref`外部引用  
因為階層是`v1/Circuit.json`，屬schema第一層，所以需新增`rf_circuit_model.py`檔，對齊Redfish Schema規範  
(別因為`PowerSupply`需要`NominalVoltageType`就把`NominalVoltageType`定義在`PowerSupply`裡)  
NominalVoltageType定義在`rf_circuit_model.py`裡，是一個Enum  
Circuit與NomiaVoltageType定義如下：  
```python
class RfNominalVoltageType(str, Enum):
    """
    @see https://redfish.dmtf.org/schemas/v1/Circuit.json#/definitions/NominalVoltageType
    """
    AC100To127V = "AC100To127V"
    AC100To240V = "AC100To240V"
    AC100To277V = "AC100To277V"
    #...(略)

class RfCircuitModel(BaseModel):
    #...(略)
```
(註) redfish的model統一`Rf`開頭  
(註) 正常的model統一`Model`結尾，Enum的不用Model結尾  


#### 欄位：Assembly
```json
"Assembly": {
    "$ref": "http://redfish.dmtf.org/schemas/v1/Assembly.json#/definitions/Assembly",
    "description": "The link ...",
    "longDescription": "This property ...",
    "readonly": true
}
```
直接看到`$ref`外部引用，因為階層是`v1/Assembly.json`，屬schema第一層  
所以需新增`rf_assembly_model.py`檔，對齊Redfish Schema規範  
一路追查$ref，最終定義在 https://redfish.dmtf.org/schemas/v1/Assembly.v1_5_1.json#/definitions/Assembly  
欄位在AssemblyData.properties裡  





## ORM Model

orm model的命名方式是 {TABLE_NAME}.py，請注意! 
ex:  
- account.py : 代表table <accounts>  
- role.py : 代表table <roles>  






 