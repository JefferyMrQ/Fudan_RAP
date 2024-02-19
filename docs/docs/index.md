## 一、项目描述

- 设计业务解析框架以及与之对应的解析器
- 构建动态页面获取不同段落交互数据
- 利用解析器获取SQL查询语句
- 连接kylin进行数据查询
- 利用查询的每份数据按序生成图文段落

## 二、编写目的

- 实现不同分析指标模板化查询，满足固定模板的分析需求

## 三、模块与关系

#### 模块

- `./src/structual_sql_generator.py`：解析framework
- `./src/management_v3.py`：设计页面进行交互，获取交互数据，利用- `structual_sql_generator.py`和已获得数据解析framework，并实现kylin查询
- `./src/pages/display.py`：解析查询结果，以文字、图表等形式呈现

#### 关系

- `structual_sql_generator.py`&rarr;`management_v3.py`:
`management_v3.py`调用`structual_sql_generator.py`的`SQLGenerator`类，按规定传入参数，使用`SQLGenerator.integrating_sql`方法，解析得到对应framework和交互数据的SQL。
- `management_v3.py`&rarr;`display.py`
在`management_v3.py`中将定位分析类型的“坐标”和制作文字描述和图标的“展示数据”存储在`streamlit`特有的session.state中；在`display.py`中读取对应数据并设计特定的图文展示。

## 四、优化思路

- `structual_sql_generator.py`
    - 部分指标目前写的SQL比较特殊，例如含有“过去K个月+每月”、“avg+sum”，以及一些特定时间和属性值相结合的情况，都会导致主体分析框架无法正确解析这些SQL，只能在代码对应位置激活判断条件，并且按照这些激活条件额外的去写这些SQL的生成代码。因此后续可以根据业务需求，更一般化的设计这些特殊情况的解析步骤。
    - 业务对象A和业务对象B的分析应该是存在重复逻辑的，可以整合起来。
    - 一些写在代码内带有`TODO`标签的注释。
- `management_v3.py`
    - 交互数据存储方式可以改进，目前`management_v3.py`的方式是为了迎合`structual_sql_generator.SQLGenerator`的接口要求，但是不满足`display.py`的解析方法。可以依据现有结构，修改`display.py`的解析过程。或者可以参考`management_v2.py`的交互数据存储方式，其满足`display.py`的解析过程，但是不满足`structual_sql_generator.SQLGenerator`的接口要求。
- `display.py`
    - 对于不同的分析，要设计不同的展示形式，目前代码存在较高的重复，可以尝试从图文的形式着手，针对每种图文形式设计功能独立的图文生成代码，实现高度的泛化能力。
    - 数据的解析是按照`management_v2.py`的存储方式而设计的，对于目前的`management_v3.py`和`structual_sql_generator.py`来说可能不太合适，需要思考如何调用前规范化的数据存储形式。
- 其它
    - 代码种的部分配置信息可以更加规范，例如撰写`pyproject.toml`等配置文件，用来存储kylin链接的相关信息等等。
    - 目前设计的SQL查询格式不统一，不便于`display.py`的数据处理，可以尝试设计统一的SQL查询结果形式。

