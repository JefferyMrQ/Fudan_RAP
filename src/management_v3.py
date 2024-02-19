import streamlit as st
import sqlalchemy as sa
import pandas as pd
from functools import wraps
import datetime
from dateutil.relativedelta import relativedelta
import calendar
import re
from typing import Optional
from structural_sql_generator_v3 import SQLGenerator


st.set_page_config(layout='wide')

TABLE_NAME = 'data'  # TODO：全局变量，和FetchData类中定义的部分变量可以写一个配置文件，然后读取

DIM_LST = ['省份', '行业', '客户等级', '客户类型', '产品名']
PROV_LST = ['上海', '云南', '内蒙古',
            '北京', '吉林', '四川', '天津', '宁夏',
            '安徽', '山东', '山西', '广东', '广西',
            '新疆', '本部', '江苏', '江西', '河北',
            '河南', '浙江', '海南', '湖北', '湖南',
            '甘肃', '福建', '西藏', '贵州', '辽宁',
            '重庆', '陕西', '青海', '黑龙江']
HY_LST = ['交通物流行业', '企业客户一部', '证券保险客户拓展部', '文化旅游拓展部', '教育行业拓展部',
          '重要客户服务部', '工业互联网BU', '银行客户拓展部', '医疗健康BU', '智慧城市BU', '生态环境拓展部',
          '政务行业拓展部', '企业客户二部', '传媒与互联网客户拓展部', '农业行业拓展部']
CUST_LEVEL_LST = ['0', '1', '2', '3']
CUST_TYPE_LST = ['政府', '企业']
PROD_LST = ['固网基础业务_数据网元',
            '固网基础业务_互联网专线',
            '固网基础业务_固话',
            '固网基础业务_宽带',
            '固网基础业务_其他',
            '移网基础业务_工作手机',
            '移网基础业务_行业短信',
            '创新业务_IDC',
            '创新业务_物联网',
            '创新业务_云计算',
            '创新业务_IT服务',
            '创新业务_大数据',
            '信息安全']
DIM_VAL_DICT = dict(zip(DIM_LST, [PROV_LST, HY_LST, CUST_LEVEL_LST, CUST_TYPE_LST, PROD_LST]))  # dim: dim_val_lst

# initialize records/paragraphs
if 'records' not in st.session_state:
    st.session_state['records'] = {}

# initialize records/paragraphs params
if 'records_params' not in st.session_state:
    st.session_state['records_params'] = {}

# initialize records/paragraphs data
if 'records_data' not in st.session_state:
    st.session_state['records_data'] = {}


def del_btn_click(index: int):
    '''
    callback of delete button, delete the key-value pair from records
    '''
    del st.session_state['records'][index]
    del st.session_state['records_params'][index]

def setup_tmpl_1(func):
    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        name = instance.expander.text_input('请输入段落名称', placeholder='必填')
        date = instance.expander.date_input('请选择时间', datetime.date(2023, 3, 1))
        # prov = self.expander.selectbox('请选择省份', PROV_LST)
        # cust_level = self.expander.selectbox('请选择客户等级', ['全部', '0, '1', '2', '3'])
        # cust_type = self.expander.selectbox('请选择客户类型', ['全部', '政府', '企业'])
        metric = func(instance, *args, **kwargs)
        desc = instance.expander.text_input('请输入段落描述', placeholder='可选')
        return name, date, metric, desc
    return wrapper

def setup_tmpl_2(func):
    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        name = instance.expander.text_input('请输入段落名称', placeholder='必填')
        date = instance.expander.date_input('请选择时间', datetime.date(2023, 3, 1))
        k, metric = func(instance, *args, **kwargs)
        desc = instance.expander.text_input('请输入段落描述', placeholder='可选')
        return name, date, k, metric, desc
    return wrapper

def setup_one_dim_dig_tmpl(func):
    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        name = instance.expander.text_input('请输入段落名称', placeholder='必填')
        date = instance.expander.date_input('请选择时间', datetime.date(2023, 3, 1))

        dim = instance.expander.selectbox('请选择分析维度', DIM_LST)
        # * 根据structural_sql_generator，添加对AB业务对象dim的区分
        if dim == '产品名':
            dim_A = None
            dim_B = dim
        else:
            dim_A = dim
            dim_B = None

        sub_anlys, metric = func(instance, *args, **kwargs)
        desc = instance.expander.text_input('请输入段落描述', placeholder='可选')
        return name, date, dim_A, dim_B, sub_anlys, metric, desc
    return wrapper

def setup_two_dim_dig_tmpl(func):
    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        name = instance.expander.text_input('请输入段落名称', placeholder='必填')
        date = instance.expander.date_input('请选择时间', datetime.date(2023, 3, 1))

        trigger = instance.expander.checkbox('客户类型与其它维度交叉下钻')
        # 二维下钻
        if trigger:
            cust_type_dim = '客户类型'
            cust_type_dim_val = instance.expander.selectbox('请选择客户类型', DIM_VAL_DICT[cust_type_dim])
            anot_dim = instance.expander.selectbox('请选择分析维度', DIM_LST)  # another dimension
            anot_dim_val = instance.expander.selectbox('请选择维度值', DIM_VAL_DICT[anot_dim])
            
            dim = cust_type_dim + '-' + anot_dim
            dim_val = cust_type_dim_val + '-' + anot_dim_val
        # 一维下钻
        else:
            dim = instance.expander.selectbox('请选择分析维度', ['全部'] + DIM_LST)  # "全部"表示不分维度
            if dim == '全部':
                dim_val = None
            else:
                dim_val = instance.expander.selectbox('请选择维度值', DIM_VAL_DICT[dim])

        # * 根据structural_sql_generator，添加对AB业务对象dim的区分
        if '产品名' in dim:
            dim_A = None
            dim_val_A = None
            dim_B = dim
            dim_val_B = dim_val
        else:
            dim_A = dim
            dim_val_A = dim_val
            dim_B = None
            dim_val_B = None
            
        k, metric = func(instance, *args, **kwargs)
        desc = instance.expander.text_input('请输入段落描述', placeholder='可选')
        return name, date, dim_A, dim_val_A, dim_B, dim_val_B, k, metric, desc
    return wrapper


class BuildOneParagraph:
    # all paragraph groups
    groups = ['收入分析', '客户数分析', '客单价分析', '客群分维度分析', '收入趋势分析',
              '客户发展分析', '计划达成分析', '排名分析','关键客群收入分析', 
              '关键客群趋势分析', '关键客群发展分析', '关键客群计划达成分析', '关键客群排名分析']

    def __init__(self, index: int) -> None:
        self.index = index
        self.expander = st.expander('新建段落')

    def build_btn_click(self, index: int, name: str, group: str, desc: str):
        '''
        callback of build button, add a new key-value pair to records
        '''
        st.session_state['records'][index] = [name, group, desc]

    def show_build_btn(self, index: int, name: str, group: str, desc: str):
        '''
        show build button
        '''
        build_btn = self.expander.button(
            '创建', on_click=self.build_btn_click, args=(index, name, group, desc))
        if build_btn:
            st.write('创建成功！')

    def save_fetch_params(self, group: str, params: dict):
        '''
        save fetch params to session state
        :param group: the group of the paragraph
        :param params: the params of the paragraph
        '''
        st.session_state['records_params'][self.index] = [group, params]

    def select_group(self) -> str:
        '''
        select one group
        '''
        group = self.expander.selectbox('选择段落类型', self.groups)
        return group

    def display_options(self, group: str):
        '''
        display customization options according to the chosen group 
        '''
        params = {'table_name': TABLE_NAME,
                  'group': group,
                  'metric': None,
                  'date': None,
                  'sub_anlys': None,
                  'dim_A': None,
                  'dim_val_A': None,
                  'dim_B': None,
                  'dim_val_B': None,
                  'k': None,
                  'desig_cust': None}  # base template
        if group == '收入分析':
            # 从客户端获取用户定义的数据
            # name, date, cust_level, cust_type, metric, desc = self.setup_income_analysis()
            name, date, metric, desc = self.setup_income_analysis()
            # 设置fetch数据需要的信息
            params.update({'date': date, 'metric': metric})
        elif group == '客户数分析':
            name, date, metric, desc = self.setup_num_cust_analysis()
            params.update({'date': date, 'metric': metric})
        elif group == '客单价分析':
            name, date, metric, desc = self.setup_avg_spend_per_cust_analysis()
            params.update({'date': date, 'metric': metric})
        elif group == '客群分维度分析':
            name, date, dim_A, dim_B, sub_anlys, metric, desc = self.setup_cust_dim_analysis()
            params.update({'date': date, 'dim_A': dim_A, 'dim_B': dim_B, 'sub_anlys': sub_anlys, 'metric': metric})
        elif group == '收入趋势分析':
            name, date, dim_A, dim_val_A, dim_B, dim_val_B, k, metric, desc = self.setup_income_trend_analysis()
            params.update({'date': date, 'dim_A': dim_A, 'dim_val_A': dim_val_A, 'dim_B': dim_B, 'dim_val_B': dim_val_B, 'k': k, 'metric': metric})
        elif group == '客户发展分析':
            name, date, dim_A, dim_val_A, dim_B, dim_val_B, k, metric, desc = self.setup_cust_dev_analysis()
            params.update({'date': date, 'dim_A': dim_A, 'dim_val_A': dim_val_A, 'dim_B': dim_B, 'dim_val_B': dim_val_B, 'k': k, 'metric': metric})
        elif group == '计划达成分析':
            name, date, k, metric, desc = self.setup_plan_achieve_analysis()
            params.update({'date': date, 'k': k, 'metric': metric})
        elif group == '排名分析':
            name, date, dim_A, dim_B, sub_anlys, metric, desc = self.setup_ranking_analysis()
            params.update({'date': date, 'dim_A': dim_A, 'dim_B': dim_B, 'sub_anlys': sub_anlys, 'metric': metric})
        elif group == '关键客群收入分析':
            name, date, metric, desc = self.setup_key_cust_income_analysis()
            params.update({'date': date, 'metric': metric})
        elif group == '关键客群趋势分析':
            name, date, k, metric, desc = self.setup_key_cust_trend_analysis()
            params.update({'date': date, 'k': k, 'metric': metric})
        elif group == '关键客群发展分析':
            name, date, k, metric, desc = self.setup_key_cust_dev_analysis()
            params.update({'date': date, 'k': k, 'metric': metric})
        elif group == '关键客群计划达成分析':
            name, date, k, metric, desc = self.setup_key_cust_plan_achieve_analysis()
            params.update({'date': date, 'k': k, 'metric': metric})
        elif group == '关键客群排名分析':
            name, date, dim_A, dim_B, sub_anlys, metric, desc = self.setup_key_cust_ranking_analysis()
            params.update({'date': date, 'dim_A': dim_A, 'dim_B': dim_B, 'sub_anlys': sub_anlys, 'metric': metric})

        # 提交按钮
        self.show_build_btn(self.index, name, group, desc)
        # save fetching params to session state
        self.save_fetch_params(group, params)

    @setup_tmpl_1
    def setup_income_analysis(self) -> str:
        '''
        收入分析
        '''
        metric = self.expander.selectbox('请选择需要计算的指标', ['（按月）收入',
                                                        '（同比）收入增长额',
                                                        '（同比）收入增长率', 
                                                        '（今年）累计收入'])

        return metric

    @setup_tmpl_1
    def setup_num_cust_analysis(self) -> str:
        '''
        客户数分析
        '''
        metric = self.expander.selectbox('请选择需要计算的指标', ['（按月）存量客户数',
                                                        '（按月）新增客户数', 
                                                        '（按月）流失客户数',
                                                        '（今年）累计新增客户数', 
                                                        '（今年）累计流失客户数', 
                                                        '（按月）总客户数',
                                                        '（同比）客户增长值', 
                                                        '（同比）客户增长率'])
        return metric

    @setup_tmpl_1
    def setup_avg_spend_per_cust_analysis(self) -> str:
        '''
        客单价分析
        '''
        metric = self.expander.selectbox('请选择需要计算的指标', ['（按月）客单价',
                                                        '（按月）新增客户单价', 
                                                        '（按月）流失客户单价', 
                                                        '（按月）存量客户单价'])
        return metric

    @setup_one_dim_dig_tmpl
    def setup_cust_dim_analysis(self) -> tuple:
        '''
        客群分维度分析
        :return: sub_anlys 子分析, metric 指标
        '''
        sub_anlys = self.expander.selectbox(
            '请选择子分析类型', ['收入分析', '客户数分析', '客单价分析'])
        if sub_anlys == '收入分析':
            org_func = self.setup_income_analysis.__wrapped__
        elif sub_anlys == '客户数分析':
            org_func = self.setup_num_cust_analysis.__wrapped__
        elif sub_anlys == '客单价分析':
            org_func = self.setup_avg_spend_per_cust_analysis.__wrapped__
        metric = org_func(self)
        return sub_anlys, metric

    @setup_two_dim_dig_tmpl
    def setup_income_trend_analysis(self) -> tuple:
        '''
        收入趋势分析
        '''
        metric = self.expander.selectbox('请选择指标', ['过去K个月每月收入', 
                                                   '过去K个月每月收入同比增长率', 
                                                   '（今年）每月累计收入',
                                                   '最近收入同比增长连续为正（负）的月份数', 
                                                   '过去K个月每月客单价'])
        if 'K' in metric:
            max_val = 36
            k = self.expander.number_input('请输入K的值', min_value=1, max_value=max_val, help=f'最大取值为{max_val}')
            return k, metric
        else:
            return None, metric

    @setup_two_dim_dig_tmpl
    def setup_cust_dev_analysis(self) -> tuple:
        '''
        客户发展分析
        '''
        metric = self.expander.selectbox('请选择指标', ['过去K个月每月存量客户数', 
                                                   '过去K个月每月新增客户数', 
                                                   '过去K个月每月流失客户数',
                                                   '过去K个月每月总客户数', 
                                                   '过去K个月每月客户数（同比）增长额', 
                                                   '过去K个月每月客户数（同比）增长率', 
                                                   '（今年）累计新增客户数', 
                                                   '（今年）累计流失客户数', 
                                                   '最近总客户数同比增长连续为正（负）的月份数', 
                                                   '最近净增客户数连续为正（负）的月份数', 
                                                   '本月存量、新增、流失客户占比',
                                                   '本月存量客户收入',
                                                   '本月存量客户收入（同比）增长额', 
                                                   '本月存量客户收入（同比）增长率', 
                                                   '本月新增客户收入',
                                                   '本月新增客户收入（同比）增长额', 
                                                   '本月新增客户收入（同比）增长率', 
                                                   '本月流失客户收入',
                                                   '本月流失客户收入（同比）增长额', 
                                                   '本月流失客户收入（同比）增长率'])
        if 'K' in metric:
            max_val = 36
            k = self.expander.number_input('请输入K的值', min_value=1, max_value=max_val, help=f'最大取值为{max_val}')
            return k, metric
        else:
            return None, metric

    @setup_tmpl_2
    def setup_plan_achieve_analysis(self) -> tuple:
        '''
        计划达成分析
        '''
        metric = self.expander.selectbox('请选择指标', ['（今年）累计收入', 
                                                   '（今年）每月累计收入', 
                                                   '过去K个月每月收入', 
                                                   '本月总客户数', 
                                                   '过去K个月每月总客户数',
                                                   '过去K个月每月净增客户数'])
        if 'K' in metric:
            max_val = 36
            k = self.expander.number_input('请输入K的值', min_value=1, max_value=max_val, help=f'最大取值为{max_val}')
            return k, metric
        else:
            return None, metric

    @setup_one_dim_dig_tmpl
    def setup_ranking_analysis(self):
        '''
        排名分析
        '''
        sub_anlys = self.expander.selectbox(
            '请选择子分析类型', ['收入分析', '客户数分析'])
        if sub_anlys == '收入分析':
            metric = self.expander.selectbox('请选择指标', ['（按月）收入', 
                                                       '（同比）收入增长额',
                                                       '（同比）收入增长率',
                                                       '（今年）累计收入', 
                                                       '（今年）累计收入增长率', 
                                                       '（按月）新增客户收入',
                                                       '（按月）流失客户收入'])
        elif sub_anlys == '客户数分析':
            metric = self.expander.selectbox('请选择指标', ['（按月）新增客户数', '（按月）流失客户数'])
        return sub_anlys, metric

    @setup_tmpl_1
    def setup_key_cust_income_analysis(self):
        '''
        关键客群收入分析
        '''
        metric = self.expander.selectbox('请选择指标', ['关键客群（按月）收入占比', 
                                                   '关键客群（今年）累计收入占比',
                                                   '关键客群vs非关键客群：（按月）收入', 
                                                   '关键客群vs非关键客群：（按月）收入（同比）增长额', 
                                                   '关键客群vs非关键客群：（按月）收入（同比）增长率', 
                                                   '关键客群vs非关键客群：（今年）累计收入', 
                                                   '关键客群vs非关键客群：（按月）客单价'])
        return metric
    
    @setup_tmpl_2
    def setup_key_cust_trend_analysis(self):
        '''
        关键客群趋势分析
        '''
        metric = self.expander.selectbox('请选择指标', ['关键客群过去K个月收入占比',
                                                    '关键客群收入占比连续提升（下降）的月份数',
                                                    '关键客群vs整体客群：过去K个月收入（同比）增长率',
                                                    '关键客群vs非关键客群：过去K个月收入（同比）增长率'])
        if 'K' in metric:
            max_val = 36
            k = self.expander.number_input('请输入K的值', min_value=1, max_value=max_val, help=f'最大取值为{max_val}')
            return k, metric
        else:
            return None, metric
    
    @setup_tmpl_2
    def setup_key_cust_dev_analysis(self):
        '''
        关键客群发展分析
        '''
        metric = self.expander.selectbox('请选择指标', ['关键客群过去K个月每月存量客户数',
                                                    '关键客群过去K个月每月新增客户数',
                                                    '关键客群过去K个月每月流失客户数',
                                                    '关键客群过去K个月每月总客户数',
                                                    '关键客群过去K个月每月客户数（同比）增长额',
                                                    '关键客群过去K个月每月客户数（同比）增长率',
                                                    '关键客群过去K个月存量、新增、流失客户占比',
                                                    '关键客群（今年）累计新增客户数',
                                                    '关键客群（今年）累计流失客户数',
                                                    '关键客群最近总客户数同比增长连续为正（负）的月份数',
                                                    '关键客群最近净增客户数连续为正（负）的月份数',
                                                    '关键客群本月存量、新增、流失客户占比',
                                                    '关键客群本月存量客户收入',
                                                    '关键客群本月存量客户收入（同比）增长额',
                                                    '关键客群本月存量客户收入（同比）增长率',
                                                    '关键客群本月新增客户收入',
                                                    '关键客群本月新增客户收入（同比）增长额',
                                                    '关键客群本月新增客户收入（同比）增长率',
                                                    '关键客群本月流失客户收入',
                                                    '关键客群本月流失客户收入（同比）增长额',
                                                    '关键客群本月流失客户收入（同比）增长率'])
        if 'K' in metric:
            max_val = 36
            k = self.expander.number_input('请输入K的值', min_value=1, max_value=max_val, help=f'最大取值为{max_val}')
            return k, metric
        else:
            return None, metric
    
    @setup_tmpl_2
    def setup_key_cust_plan_achieve_analysis(self):
        '''
        关键客群计划达成分析
        '''
        metric = self.expander.selectbox('请选择指标', ['关键客群（今年）累计收入',
                                                    '关键客群（今年）每月累计收入',
                                                    '关键客群过去K个月每月收入',
                                                    '关键客群本月总客户数',
                                                    '关键客群过去K个月每月客户数',
                                                    '关键客群过去K个月每月净增客户数'])
        if 'K' in metric:
            max_val = 36
            k = self.expander.number_input('请输入K的值', min_value=1, max_value=max_val, help=f'最大取值为{max_val}')
            return k, metric
        else:
            return None, metric
    
    @setup_one_dim_dig_tmpl
    def setup_key_cust_ranking_analysis(self):
        '''
        关键客群排名分析
        '''
        sub_anlys = self.expander.selectbox(
            '请选择子分析类型', ['收入分析', '客户数分析'])
        if sub_anlys == '收入分析':
            metric = self.expander.selectbox('请选择指标', ['指定客群（按月）收入',
                                                        '指定客群（同比）收入增长额',
                                                        '指定客群（同比）收入增长率',
                                                        '指定客群（今年）累计收入',
                                                        '指定客群（今年）累计收入增长率',
                                                        '指定客群（按月）新增客户收入',
                                                        '指定客群（按月）流失客户收入'])
        elif sub_anlys == '客户数分析':
            metric = self.expander.selectbox('请选择指标', ['指定客群（按月）新增客户数', '指定客群（按月）流失客户数'])
        return sub_anlys, metric
    

# initialize the number of records, namely how many rows we need to display
if 'rows' not in st.session_state:
    st.session_state['rows'] = 0

def increase_rows():
    '''
    callback for increasing one row for display
    '''
    # st.session_state['rows'] += 1
    st.session_state['rows'] = len(st.session_state['records']) + 1

# the button to add a record
add_btn = st.button(':heavy_plus_sign:', on_click=increase_rows)

# use a empty widget to display the expander iteratively
with st.empty():
    if st.session_state['rows'] != len(st.session_state['records']):  # 这样判断是为了保证从另一个页面返回时，能够正常保存最后一个record
        # display_expander(st.session_state['rows'])

        build = BuildOneParagraph(st.session_state['rows'])
        group = build.select_group()  # 选择一个客群
        build.display_options(group)  # 根据选择的客群展示对应的选项


# 展示建立的记录
st.subheader('result')
num_col, name_col, group_col, desc_col, oper_col = st.columns(5)
num_col.checkbox('全选')
name_col.text('名称')
group_col.text('分组')
desc_col.text('描述')
oper_col.text('操作')

# record number counter
counter = 1
for index, records_info in st.session_state['records'].items():
    name, group, desc = records_info
    num_col.checkbox(f'{counter}')
    name_col.write(name)
    group_col.write(group)
    desc_col.write(desc)
    oper_col.button('删除', key=f'del{index}',
                    on_click=del_btn_click, args=(index,))

    counter += 1

# st.write(st.session_state['records_params'])

def fetch(index: int, gp: list):
    '''
    fetch data
    :param index: index of the record
    :param gp: group and params of the record
    '''
    group, params = gp
    sql_generator = SQLGenerator(**params)
    sql = sql_generator.integrating_sql()
    st.write(st.session_state['records'][index])
    st.code(sql, language='sql')
    
    # TODO: fetch data from kylin; save coordinates and diaplay params to session_state
    # * 可以参考management_v2.py的写法，根据不同group的分析，调用不同的fetch函数，存储不同的display参数
    # * 也可以统一写一个FetchData的类，存储相同规范格式的数据，然后再display.py中根据不同的group，提取相应的diaplay参数
        
if st.button('提交'):
    # 从kylin获取数据，并保存到session_state里面
    for index, gp in st.session_state['records_params'].items():  # gp: group and params of the record
        fetch(index, gp)
        

    # date, customer_level, customer_type, metric = temp_data
    # fetch = Fetch_data(st.session_state['rows'])
    # fetch.income_analysis(date, customer_level, customer_type, metric)
