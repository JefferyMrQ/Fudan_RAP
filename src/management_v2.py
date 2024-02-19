import streamlit as st
import sqlalchemy as sa
import pandas as pd
from functools import wraps
import datetime
from dateutil.relativedelta import relativedelta
import calendar
import re
from typing import Optional


st.set_page_config(layout='wide')

dim_lst = ['省份', '行业', '客户等级', '客户类型', '产品名']
prov_lst = ['上海', '云南', '内蒙古',
            '北京', '吉林', '四川', '天津', '宁夏',
            '安徽', '山东', '山西', '广东', '广西',
            '新疆', '本部', '江苏', '江西', '河北',
            '河南', '浙江', '海南', '湖北', '湖南',
            '甘肃', '福建', '西藏', '贵州', '辽宁',
            '重庆', '陕西', '青海', '黑龙江']
hy_lst = ['交通物流行业', '企业客户一部', '证券保险客户拓展部', '文化旅游拓展部', '教育行业拓展部',
          '重要客户服务部', '工业互联网BU', '银行客户拓展部', '医疗健康BU', '智慧城市BU', '生态环境拓展部',
          '政务行业拓展部', '企业客户二部', '传媒与互联网客户拓展部', '农业行业拓展部']
cust_level_lst = ['0', '1', '2', '3']
cust_type_lst = ['政府', '企业']
prod_lst = ['固网基础业务_数据网元',
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
dim_val_dict = dict(zip(dim_lst, [prov_lst, hy_lst, cust_level_lst, cust_type_lst, prod_lst]))  # dim: dim_val_lst

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
        # prov = self.expander.selectbox('请选择省份', prov_lst)
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

        dim = instance.expander.selectbox('请选择分析维度', dim_lst)

        sub_anlys, metric = func(instance, *args, **kwargs)
        desc = instance.expander.text_input('请输入段落描述', placeholder='可选')
        return name, date, dim, sub_anlys, metric, desc
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
            cust_type_dim_val = instance.expander.selectbox('请选择客户类型', dim_val_dict[cust_type_dim])
            anot_dim = instance.expander.selectbox('请选择分析维度', dim_lst)  # another dimension
            anot_dim_val = instance.expander.selectbox('请选择维度值', dim_val_dict[anot_dim])
            
            dim = cust_type_dim + '-' + anot_dim
            dim_val = cust_type_dim_val + '-' + anot_dim_val
        # 一维下钻
        else:
            dim = instance.expander.selectbox('请选择分析维度', ['全部'] + dim_lst)  # "全部"表示不分维度
            if dim == '全部':
                dim_val = None
            else:
                dim_val = instance.expander.selectbox('请选择维度值', dim_val_dict[dim])

        k, metric = func(instance, *args, **kwargs)
        desc = instance.expander.text_input('请输入段落描述', placeholder='可选')
        return name, date, dim, dim_val, k, metric, desc
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

    def save_fetch_params(self, group: str, params: list):
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
        if group == '收入分析':
            # 从客户端获取用户定义的数据
            # name, date, cust_level, cust_type, metric, desc = self.setup_income_analysis()
            name, date, metric, desc = self.setup_income_analysis()
            # 设置fetch数据需要的信息
            params = [date, metric]
        elif group == '客户数分析':
            name, date, metric, desc = self.setup_num_cust_analysis()
            params = [date, metric]
        elif group == '客单价分析':
            name, date, metric, desc = self.setup_avg_spend_per_cust_analysis()
            params = [date, metric]
        elif group == '客群分维度分析':
            name, date, dim, sub_anlys, metric, desc = self.setup_cust_dim_analysis()
            # 设置fetch数据需要的信息
            params = [date, dim, sub_anlys, metric]
        elif group == '收入趋势分析':
            name, date, dim, dim_val, k, metric, desc = self.setup_income_trend_analysis()
            params = [date, dim, dim_val, k, metric]
        elif group == '客户发展分析':
            name, date, dim, dim_val, k, metric, desc = self.setup_cust_dev_analysis()
            params = [date, dim, dim_val, k, metric]
        elif group == '计划达成分析':
            name, date, k, metric, desc = self.setup_plan_achieve_analysis()
            params = [date, k, metric]
        elif group == '排名分析':
            name, date, dim, sub_anlys, metric, desc = self.setup_ranking_analysis()
            params = [date, dim, sub_anlys, metric]
        elif group == '关键客群收入分析':
            name, date, metric, desc = self.setup_key_cust_income_analysis()
            params = [date, metric]
        elif group == '关键客群趋势分析':
            name, date, k, metric, desc = self.setup_key_cust_trend_analysis()
            params = [date, k, metric]
        elif group == '关键客群发展分析':
            name, date, k, metric, desc = self.setup_key_cust_dev_analysis()
            params = [date, k, metric]
        elif group == '关键客群计划达成分析':
            name, date, k, metric, desc = self.setup_key_cust_plan_achieve_analysis()
            params = [date, k, metric]
        elif group == '关键客群排名分析':
            name, date, dim, sub_anlys, metric, desc = self.setup_key_cust_ranking_analysis()
            params = [date, dim, sub_anlys, metric]

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

class FetchData:
    username = 'ADMIN'
    password = 'KYLIN'
    hostname_port = 'hadoop102:7070'  # hostname:port for kylin client

    project = 'FinalProject'
    table = 'data'

    dim_dict = {'省份': 'province_name', '行业': 'hy_name', '客户等级': 'customer_level',
                '客户类型': 'customer_type', '产品名': 'product_name'}  # 用于替换维度名和维度列名的字典
    cust_id_dim = 'customer_id'
    date_dim = 'account_period'
    prov_dim = 'province_name'
    hy_dim = 'hy_name'
    cust_level_dim = 'customer_level'
    cust_type_dim = 'customer_type'
    prod_dim = 'product_name'
    income_dim = 'income'
    metrics = ['fixed_data_network_element_income',
               'fixed_dedicated_internet_access_income',
               'fixed_fixed_line_income',
               'fixed_broadband_income',
               'fixed_other_income',
               'mobile_work_phone_income',
               'mobile_industry_sms_income',
               'innovative_idc_income',
               'innovative_iot_income',
               'innovative_cloud_computing_income',
               'innovative_it_services_income',
               'innovative_big_data_income',
               'information_security_income']

    month_date_alias = '月份'
    cust_level_alias = '客户等级'
    max_k = 36  # 判断指标符号连续性的最大月份数时，预设的最大探索月份数为max_k
    key_cust = 0  # 关键客群

    def __init__(self, index: int) -> None:
        self.index = index

    def fetch(self, kylin_project: str, sql: str):
        kylin_engine = sa.create_engine(f'kylin://{self.username}:{self.password}@{self.hostname_port}/{kylin_project}',
                                        connect_args={'timeout': 1000})
        df = pd.read_sql(sql, kylin_engine)
        return df

    def parse_date(self, date: datetime.date) -> list:
        '''
        parse a date to a sequence of strings, containing the start date and the end date of the month 
        '''
        _, last_day = calendar.monthrange(date.year, date.month)
        month_start = '{}-{}-{}'.format(date.year,
                                        str(date.month).rjust(2, '0'), '01')
        month_end = '{}-{}-{}'.format(date.year, str(date.month).rjust(2,
                                                                       '0'), str(last_day).rjust(2, '0'))
        return [month_start, month_end]

    def fetch_and_save(self, sql: str, date: datetime.date, group: str, metric: str) -> None:
        '''
        fetch data and save relevant information
        '''
        # 根据sql获取数据
        df = self.fetch(self.project, sql)
        # display需要的params
        display_params = [date]
        # 设定坐标，保存到session state里面
        coordinate = (self.index, group, metric)
        st.session_state['records_data'][coordinate] = [display_params, df]


# def fetch_tmpl_1(func):
#     @wraps(func)
#     def wrapper(instance, *args, **kwargs):
#         sql, date, group, metric, revise = func(instance, *args, **kwargs)
#         if revise == False:
#             instance.fetch_and_save(sql, date, group, metric)
#         else:
#             return sql
#     return wrapper

class FetchIncome(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)

    # def fetch_income_analysis(self, group: str, date: list, prov: str, hy: str, cust_level: str, cust_type: str, metric: str):
    def fetch_income(self, group: str, date: datetime.date, metric: str, return_sql: bool = False):
        '''
        fetch income analysis data from kylin
        :param group: 分析类型-'收入分析'
        :param date: 日期
        :param metric: 指标
        :param return_sql: 是否返回sql语句
        '''

        # # 计算总收入
        # total_income = "("
        # for m in self.metrics:
        #     total_income += f"sum({m})+"
        # total_income = total_income[: -1] + ")"

        def fetch_tot_income_m():
            '''
            （按月）收入
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\" 
                    from {self.table} where """

            # 重新设定时间范围，主要是消除day的影响(这里到底用那种形式比较好？)
            # date_start = '{}-{}-{}'.format(date[0].year, str(date[0].month).rjust(2, '0'), '01')
            # date_end = '{}-{}-{}'.format(date[1].year, str(date[1].month).rjust(2, '0'), '01')
            # sql += f"{date_dim} >= '{date_start}' and {date_dim} <= '{date_end}'"
            month_start, month_end = self.parse_date(date)
            sql += f"{self.date_dim} >= '{month_start}' and {self.date_dim} <= '{month_end}'"

            # if prov != '全部':
            #     sql += f" and {self.prov_dim} = '{prov}'"

            # if hy != '全部':
            #     sql += f" and {self.hy_dim} = '{hy}'"

            # if cust_level != '全部':
            #     sql += f" and {self.cust_level_dim} = '{cust_level}'"

            # if cust_type != '全部':
            #     sql += f" and {self.cust_type_dim} = '{cust_type}'"

            # if revise == False:
            #     self.fetch_and_save(sql, date, group, metric)
            # else:
            #     return sql
            return sql

        def fetch_income_growth_yoy():
            '''
            （同比）收入增长额
            '''
            # 重新设定时间范围，主要是消除day的影响
            month_start_ty, month_end_ty = self.parse_date(date)  # this year
            month_start_ly, month_end_ly = self.parse_date(
                date - relativedelta(years=1))  # last year
            sql = f"""select sum({self.income_dim}) as \"{metric}\",
                   case 
                   when ({self.date_dim} >= '{month_start_ly}') and ({self.date_dim} <= '{month_end_ly}') then '{month_start_ly[: -3]}'
                   when ({self.date_dim} >= '{month_start_ty}') and ({self.date_dim} <= '{month_end_ty}') then '{month_start_ty[: -3]}'
                   end as {self.month_date_alias}
                   from {self.table}
                   where 1 = 1"""

            # 添加group by
            sql += f""" group by {self.month_date_alias} 
                    having {self.month_date_alias} is not null"""
            return sql

        # （同比）收入增长率
        fetch_income_growth_rate_yoy = fetch_income_growth_yoy

        def fetch_income_ytd():
            '''
            （今年）累计收入
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\" 
                    from {self.table} where """

            # 时间
            # date_start = "{}-{}-{}".format(date.year, '01', '01')
            # date_end = date.strftime("%Y-%m-%d")
            td = datetime.date.today()
            year_start = "{}-{}-{}".format(td.year, '01', '01')
            month_end = td.strftime("%Y-%m-%d")
            sql += f"{self.date_dim} >= '{year_start}' and {self.date_dim} <= '{month_end}'"
            return sql

        # 根据metric判断调用哪个函数
        if metric == '（按月）收入':
            sql = fetch_tot_income_m()
        elif metric == '（同比）收入增长额':
            sql = fetch_income_growth_yoy()
        elif metric == '（同比）收入增长率':
            sql = fetch_income_growth_rate_yoy()
        elif metric == '（今年）累计收入':
            sql = fetch_income_ytd()

        if return_sql == False:
            self.fetch_and_save(sql, date, group, metric)
        else:
            return sql


class FetchNumCust(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)

    def fetch_num_cust(self, group: str, date: datetime.date, metric: str, return_sql: bool = False):
        '''
        fetch data for number of customers from kylin
        :param group: 分析类型-'客户数分析'
        :param date: 日期
        :param metric: 指标
        :param return_sql: 是否返回sql语句
        '''
        base_sql = f"select count(distinct {self.cust_id_dim}) as \"{metric}\"" + \
            f" from {self.table} where "

        month_start_tm, month_end_tm = self.parse_date(date)  # this month
        month_start_lm, month_end_lm = self.parse_date(date - relativedelta(months=1))  # last month

        def fetch_num_existing_cust_m():
            '''
            （按月）存量客户数
            '''
            sql = base_sql + \
                f"{self.date_dim} >= '{month_start_tm}' and {self.date_dim} <= '{month_end_tm}'"

            sub_sql = f"""select {self.cust_id_dim}
                       from {self.table} 
                       where {self.date_dim} >= '{month_start_lm}' and {self.date_dim} <= '{month_end_lm}'"""
            sql += f" and {self.cust_id_dim} in ({sub_sql})"
            return sql

        def fetch_num_new_cust_m():
            '''
            （按月）新增客户数
            '''
            sql = base_sql + \
                f"{self.date_dim} >= '{month_start_tm}' and {self.date_dim} <= '{month_end_tm}'"

            sub_sql = f"""select {self.cust_id_dim}
                       from {self.table} 
                       where {self.date_dim} >= '{month_start_lm}' and {self.date_dim} <= '{month_end_lm}'"""
            sql += f" and {self.cust_id_dim} not in ({sub_sql})"
            return sql

        def fetch_num_lost_cust_m():
            '''
            （按月）流失客户数
            '''
            sql = base_sql + \
                f"{self.date_dim} >= '{month_start_lm}' and {self.date_dim} <= '{month_end_lm}'"

            sub_sql = f"""select {self.cust_id_dim}
                       from {self.table} 
                       where {self.date_dim} >= '{month_start_tm}' and {self.date_dim} <= '{month_end_tm}'"""
            sql += f" and {self.cust_id_dim} not in ({sub_sql})"
            return sql

        def fetch_num_new_cust_ytd():
            '''
            （今年）累计新增客户数
            '''
            td = datetime.date.today()
            one_year_ago_td = td - relativedelta(years=1)
            year_start = "{}-{}-{}".format(td.year, '01', '01')
            dec_start_ly = "{}-{}-{}".format(one_year_ago_td.year, '12', '01')
            dec_end_ly = "{}-{}-{}".format(one_year_ago_td.year, '12', '31')

            sql = base_sql + \
                f"{self.date_dim} >= '{year_start}' and {self.date_dim} <= '{month_end_tm}'"

            sub_sql = f"""select {self.cust_id_dim}
                       from {self.table} 
                       where {self.date_dim} >= '{dec_start_ly}' and {self.date_dim} <= '{dec_end_ly}'"""
            sql += f" and {self.cust_id_dim} not in ({sub_sql})"
            return sql

        def fetch_num_lost_cust_ytd():
            '''
            （今年）累计流失客户数
            '''
            td = datetime.date.today()
            one_year_ago_td = td - relativedelta(years=1)
            year_start = "{}-{}-{}".format(td.year, '01', '01')
            dec_start_ly = "{}-{}-{}".format(one_year_ago_td.year, '12', '01')
            dec_end_ly = "{}-{}-{}".format(one_year_ago_td.year, '12', '31')

            sql = base_sql + \
                f"{self.date_dim} >= '{dec_start_ly}' and {self.date_dim} <= '{dec_end_ly}'"

            sub_sql = f"""select {self.cust_id_dim}
                       from {self.table} 
                       where {self.date_dim} >= '{year_start}' and {self.date_dim} <= '{month_end_tm}'"""
            sql += f" and {self.cust_id_dim} not in ({sub_sql})"
            return sql

        def fetch_tot_num_cust_m():
            '''
            （按月）总客户数
            '''
            sql = base_sql + \
                f"{self.date_dim} >= '{month_start_tm}' and {self.date_dim} <= '{month_end_tm}'"
            return sql

        def fetch_num_cust_growth_yoy():
            '''
            （同比）客户增长值
            '''
            sql = f"""select count(distinct {self.cust_id_dim}) as \"{metric}\",
                 case
                 when ({self.date_dim} >= '{month_start_tm}') and ({self.date_dim} <= '{month_end_tm}') then '{month_start_tm[: -3]}'
                 when ({self.date_dim} >= '{month_start_lm}') and ({self.date_dim} <= '{month_end_lm}') then '{month_start_lm[: -3]}'
                 end as {self.month_date_alias}
                 from {self.table}
                 group by {self.month_date_alias}
                 having {self.month_date_alias} is not null"""
            return sql

        fetch_num_cust_growth_rate_yoy = fetch_num_cust_growth_yoy  # （同比）客户增长率

        # 根据metric判断调用哪个函数
        if metric == '（按月）存量客户数':
            sql = fetch_num_existing_cust_m()
        elif metric == '（按月）新增客户数':
            sql = fetch_num_new_cust_m()
        elif metric == '（按月）流失客户数':
            sql = fetch_num_lost_cust_m()
        elif metric == '（今年）累计新增客户数':
            sql = fetch_num_new_cust_ytd()
        elif metric == '（今年）累计流失客户数':
            sql = fetch_num_lost_cust_ytd()
        elif metric == '（按月）总客户数':
            sql = fetch_tot_num_cust_m()
        elif metric == '（同比）客户增长值':
            sql = fetch_num_cust_growth_yoy()
        elif metric == '（同比）客户增长率':
            sql = fetch_num_cust_growth_rate_yoy()

        if return_sql == False:
            self.fetch_and_save(sql, date, group, metric)
        else:
            return sql


class FetchAvgSpendPerCust(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)

    def fetch_avg_spend_per_cust(self, group: str, date: datetime.date, metric: str, return_sql: bool = False):
        '''
        fetch data for avg spend per customer from kylin
        :param group: 分析类型-'客单价分析'
        :param date: 日期
        :param metric: 指标
        :param return_sql: 是否返回sql
        '''
        base_sql = f"""select avg(总收入) as \"{metric}\"
                    from """

        month_start_tm, month_end_tm = self.parse_date(date)  # this year
        month_start_lm, month_end_lm = self.parse_date(date - relativedelta(months=1))  # last year

        def fetch_avg_spend_per_cust_m():
            '''
            （按月）客单价
            '''
            sub_sql = f"""(select {self.cust_id_dim}, sum({self.income_dim}) as 总收入
                       from {self.table}
                       where {self.date_dim} >= '{month_start_tm}' and {self.date_dim} <= '{month_end_tm}'
                       group by {self.cust_id_dim})"""
            sql = base_sql + sub_sql
            return sql
        
        def fetch_avg_spend_per_new_cust_m():
            '''
            （按月）新增客户单价
            '''
            sub_sql = f"""(select {self.cust_id_dim}, sum({self.income_dim}) as 总收入
                       from {self.table}
                       where {self.date_dim} >= '{month_start_tm}' and {self.date_dim} <= '{month_end_tm}'
                       and {self.cust_id_dim} not in (
                       select {self.cust_id_dim}
                       from {self.table}
                       where {self.date_dim} >= '{month_start_lm}' and {self.date_dim} <= '{month_end_lm}'
                       )
                       group by {self.cust_id_dim})"""
            sql = base_sql + sub_sql
            return sql
        
        def fetch_avg_spend_per_lost_cust_m():
            '''
            （按月）流失客户单价
            '''
            sub_sql = f"""(select {self.cust_id_dim}, sum({self.income_dim}) as 总收入
                       from {self.table}
                       where {self.date_dim} >= '{month_start_lm}' and {self.date_dim} <= '{month_end_lm}'
                       and {self.cust_id_dim} not in (
                       select {self.cust_id_dim}
                       from {self.table}
                       where {self.date_dim} >= '{month_start_tm}' and {self.date_dim} <= '{month_end_tm}'
                       )
                       group by {self.cust_id_dim})"""
            sql = base_sql + sub_sql
            return sql
        
        def fetch_avg_spend_per_existing_cust_m():
            '''
            （按月）存量客户单价计算
            '''
            sub_sql = f"""(select {self.cust_id_dim}, sum({self.income_dim}) as 总收入
                       from {self.table}
                       where {self.date_dim} >= '{month_start_tm}' and {self.date_dim} <= '{month_end_tm}'
                       and {self.cust_id_dim} in (
                       select {self.cust_id_dim}
                       from {self.table}
                       where {self.date_dim} >= '{month_start_lm}' and {self.date_dim} <= '{month_end_lm}'
                       )
                       group by {self.cust_id_dim})"""

            sql = base_sql + sub_sql
            return sql
        
        if metric == '（按月）客单价':
            sql = fetch_avg_spend_per_cust_m()
        elif metric == '（按月）新增客户单价':
            sql = fetch_avg_spend_per_new_cust_m()
        elif metric == '（按月）流失客户单价':
            sql = fetch_avg_spend_per_lost_cust_m()
        elif metric == '（按月）存量客户单价':
            sql = fetch_avg_spend_per_existing_cust_m()

        if return_sql == False:
            self.fetch_and_save(sql, date, group, metric)
        else:
            return sql
        

class FetchCustDim(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)

    def fetch_and_save(self, sql: str, date: datetime.date, group: str, metric: str, dim: str, sub_anlys: str) -> None:
        '''
        fetch data and save relevant information
        '''
        # 根据sql获取数据
        df = self.fetch(self.project, sql)
        # display需要的params
        display_params = [date, dim, sub_anlys]
        # 设定坐标，保存到session state里面
        coordinate = (self.index, group, metric)
        st.session_state['records_data'][coordinate] = [display_params, df]

    def revise_sql1(self, org_sql: str, dim: str) -> str:
        '''
        (case1) revise original sql and return it
        '''
        dim_col = self.dim_dict[dim]
        sql = re.sub('^select', f'select {dim_col} as {dim},', org_sql)
        sql = re.sub('$', f'\ngroup by {dim_col}', sql)
        return sql

    def revise_sql2(self, org_sql: str, dim: str) -> str:
        '''
        (case2) revise original sql and return it
        '''
        dim_col = self.dim_dict[dim]
        sql = re.sub('^select', f'select {dim_col} as {dim},', org_sql)
        sql = re.sub('group by', f'group by {dim_col},', sql)
        return sql
    
    def revise_sql3(self, org_sql: str, dim: str) -> str:
        '''
        (case3) revise original sql and return it
        '''
        dim_col = self.dim_dict[dim]
        sql = re.sub('select', f'select {dim_col},', org_sql, count=2)
        sql = re.sub(f'select {dim_col},', f'select {dim_col} as {dim},', sql, count=1)
        sql = re.sub('group by', f'group by {dim_col},', sql)
        sql = re.sub('$', f' group by {dim_col}', sql)
        return sql

    def fetch_cust_dim(self, group: str, date: datetime.date, dim: str, sub_anlys: str, metric: str):
        '''
        fetch data for customer dimension analysis from kylin
        :param group: 分析类型-'客群分维度分析'
        :param date: 日期
        :param dim: 维度中文名，如'省份'、'客户类型'
        :param sub_anlys: 子分析类型，如'收入分析'、'客户数分析'
        :param metric: 指标，如'（按月）收入'、'（同比）收入增长额'
        '''
        def fetch_cust_dim_income():
            '''
            客群分维度分析-收入分析
            '''
            if metric == '（按月）收入' or metric == '（今年）累计收入':
                sql = FetchIncome(self.index).fetch_income(group, date, metric, return_sql=True)
                sql = self.revise_sql1(sql, dim)
            elif metric == '（同比）收入增长额' or metric == '（同比）收入增长率':
                sql = FetchIncome(self.index).fetch_income(group, date, metric, return_sql=True)
                sql = self.revise_sql2(sql, dim)
            return sql

        def fetch_cust_dim_num_cust():
            '''
            客群分维度分析-客户数分析
            '''
            if metric == '（同比）客户增长值' or metric == '（同比）客户增长率':
                sql = FetchNumCust(self.index).fetch_num_cust(group, date, metric, return_sql=True)
                sql = self.revise_sql2(sql, dim)
            else:
                sql = FetchNumCust(self.index).fetch_num_cust(group, date, metric, return_sql=True)
                sql = self.revise_sql1(sql, dim)
            return sql
            
        def fetch_cust_dim_avg_spend_per_cust():
            '''
            客群分维度分析-客单价分析
            '''
            sql = FetchAvgSpendPerCust(self.index).fetch_avg_spend_per_cust(group, date, metric, return_sql=True)
            sql = self.revise_sql3(sql, dim)
            return sql

        if sub_anlys == '收入分析':
            sql = fetch_cust_dim_income()
        elif sub_anlys == '客户数分析':
            sql = fetch_cust_dim_num_cust()
        elif sub_anlys == '客单价分析':
            sql = fetch_cust_dim_avg_spend_per_cust()

        self.fetch_and_save(sql, date, group, metric, dim, sub_anlys)

    
class FetchIncomeTrend(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)

    def fetch_and_save(self, sql: str, date: datetime.date, group: str, metric: str, dim: str, dim_val: str, k: int) -> None:
        '''
        fetch data and save relevant information
        '''
        # 根据sql获取数据
        df = self.fetch(self.project, sql)
        # display需要的params
        display_params = [date, dim, dim_val, k]
        # 设定坐标，保存到session state里面
        coordinate = (self.index, group, metric)
        st.session_state['records_data'][coordinate] = [display_params, df]

    def revise_sql1(self, org_sql: str, dim: str, dim_val: str) -> str:
            '''
            (case1) revise original sql and return it
            '''
            dim_col = self.dim_dict[dim]
            sql = re.sub('where', f"where {dim_col} = '{dim_val}' and", org_sql)
            return sql
    
    def revise_sql2(self, org_sql: str, dim: str, dim_val: str) -> str:
        '''
        (case2) revise original sql and return it
        '''
        cust_type_dim, anot_dim = dim.split('-')  # 中文的维度名
        cust_type_dim_col, anot_dim_col = self.dim_dict[cust_type_dim], self.dim_dict[anot_dim]  # 转化为数据表中的列名
        cust_type_dim_val, anot_dim_val = dim_val.split('-')  # 维度值
        sql = re.sub('where', f"where {cust_type_dim_col} = '{cust_type_dim_val}' and {anot_dim_col} = '{anot_dim_val}' and", org_sql)
        return sql

    def fetch_income_trend(self, group: str, date: datetime.date, dim: Optional[str], dim_val: Optional[str], k: Optional[int], metric: str, return_sql: bool = False):
        '''
        fetch data for income trend analysis from kylin
        :param group: 分析类型-'收入趋势分析'
        :param date: 日期
        :param dim: 维度中文名，如'省份'、'客户类型'
        :param dim_val: 维度值，如'北京'、'企业'
        :param k: 过去K个月
        :param metric: 指标，如'（按月）收入'、'（同比）收入增长额'
        :param return_sql: 是否返回sql
        '''
        # 日期变量
        td = datetime.date.today()
        # 本月第一天和最后一天
        _, this_month_end_ty = self.parse_date(td)
        # 去年同期本月第一天和最后一天
        _, this_month_end_ly = self.parse_date(td - relativedelta(years=1))
        # 今年第一天
        year_start_ty, _ = self.parse_date(td.replace(month=1))
        
        if k:
            date_k_month_ago = date - relativedelta(months=k)
            # k个月前的第一天
            k_month_ago_start_ty, _ = self.parse_date(date_k_month_ago)
            # 去年同期k个月前的第一天
            k_month_ago_start_ly, _ = self.parse_date(date_k_month_ago - relativedelta(years=1))

        def fetch_income_km():
            '''
            过去K个月每月收入
            '''
            sql = f"""select (cast(year({self.date_dim}) as varchar) 
                   || '-' 
                   ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias}, 
                   sum({self.income_dim}) as \"{metric}\"
                   from {self.table}
                   where {self.date_dim} >= '{k_month_ago_start_ty}' and {self.date_dim} <= '{this_month_end_ty}'
                   group by {self.month_date_alias}"""
            return sql

        def fetch_income_growth_rate_yoy_km():
            '''
            过去K个月每月收入同比增长率
            '''
            sql = f"""select t1.{self.month_date_alias} as {self.month_date_alias}, 今年, 去年
                   from
                   (select (cast(year({self.date_dim}) as varchar)
                   || '-' 
                   ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias}, 
                   sum({self.income_dim}) as 今年
                   from {self.table}
                   where {self.date_dim} >= '{k_month_ago_start_ty}' and {self.date_dim} <= '{this_month_end_ty}'
                   group by {self.month_date_alias}) t1
                   join
                   (select (cast(year(timestampadd(year, 1, {self.date_dim})) as varchar) 
                   || '-' 
                   ||  substring('0' + cast(month(timestampadd(year, 1, {self.date_dim})) as varchar), -2, 2)) as {self.month_date_alias}, 
                   sum({self.income_dim}) as 去年
                   from {self.table}
                   where {self.date_dim} >= '{k_month_ago_start_ly}' and {self.date_dim} <= '{this_month_end_ly}'
                   group by {self.month_date_alias}) t2
                   on t1.{self.month_date_alias} = t2.{self.month_date_alias}
                   """
            return sql

        def fetch_income_ytd_pm():
            '''
            （今年）每月累计收入
            '''
            sql = f"""select (cast(year({self.date_dim}) as varchar) 
                   || '-' 
                   ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias}, 
                   sum({self.income_dim}) as \"{metric}\"
                   from {self.table}
                   where {self.date_dim} >= '{year_start_ty}' and {self.date_dim} <= '{this_month_end_ty}'
                   group by {self.month_date_alias}"""
            return sql

        def fetch_income_growth_rate_yoy_cont_sign(max_k: int):
            '''
            最近收入同比增长连续为正（负）的月份数
            :param max_k: 预设的最大连续为正（负）月数
            '''
            date_k_month_ago = td - relativedelta(months=max_k)
            k_month_ago_start_ty, _ = self.parse_date(date_k_month_ago)
            k_month_ago_start_ly, _ = self.parse_date(date_k_month_ago - relativedelta(years=1))

            sql = f"""select t1.{self.month_date_alias} as {self.month_date_alias}, 今年, 去年
                   from
                   (select (cast(year({self.date_dim}) as varchar) 
                   || '-'
                   ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias},
                   sum({self.income_dim}) as 今年
                   from {self.table}
                   where {self.date_dim} >= '{k_month_ago_start_ty}' and {self.date_dim} <= '{this_month_end_ty}'
                   group by {self.month_date_alias}) t1
                   join
                   (select (cast(year(timestampadd(year, 1, {self.date_dim})) as varchar) 
                   || '-'
                   ||  substring('0' + cast(month(timestampadd(year, 1, {self.date_dim})) as varchar), -2, 2)) as {self.month_date_alias}, 
                   sum({self.income_dim}) as 去年
                   from {self.table}
                   where {self.date_dim} >= '{k_month_ago_start_ly}' and {self.date_dim} <= '{this_month_end_ly}'
                   group by {self.month_date_alias}) t2
                   on t1.{self.month_date_alias} = t2.{self.month_date_alias}
                   """
            return sql
        
        def fetch_avg_spend_per_cust_km():
            '''
            过去K个月每月客单价
            '''
            sql = f"""select {self.month_date_alias}, avg(总收入) as \"{metric}\"
                  from (
                  select (cast(year({self.date_dim}) as varchar) 
                  || '-' 
                  ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias},
                  {self.cust_id_dim}, sum({self.income_dim}) as 总收入
                  from {self.table}
                  where {self.date_dim} >= '{k_month_ago_start_ty}' and {self.date_dim} <= '{this_month_end_ty}'
                  group by {self.month_date_alias}, {self.cust_id_dim}
                  )
                  group by {self.month_date_alias}"""
            return sql

        if metric == '过去K个月每月收入':
            sql = fetch_income_km()
        elif metric == '过去K个月每月收入同比增长率':
            sql = fetch_income_growth_rate_yoy_km()
        elif metric == '（今年）每月累计收入':
            sql = fetch_income_ytd_pm()
        elif metric == '最近收入同比增长连续为正（负）的月份数':
            k = self.max_k  # 预设的最大连续为正（负）月数
            sql = fetch_income_growth_rate_yoy_cont_sign(k)
        elif metric == '过去K个月每月客单价':
            sql = fetch_avg_spend_per_cust_km()

        # 无下钻
        if dim == '全部':
            pass
        # 一维下钻
        elif '-' not in dim:
            sql = self.revise_sql1(sql, dim, dim_val)
        # 二维下钻
        elif '-' in dim:
            sql = self.revise_sql2(sql, dim, dim_val)

        if return_sql == False:
            self.fetch_and_save(sql, date, group, metric, dim, dim_val, k)
        else:
            return sql


class FetchCustDev(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)

    def fetch_and_save(self, sql: str, date: datetime.date, group: str, metric: str, dim: str, dim_val: str, k: int) -> None:
        '''
        fetch data and save relevant information
        '''
        # 根据sql获取数据
        df = self.fetch(self.project, sql)
        # display需要的params
        display_params = [date, dim, dim_val, k]
        # 设定坐标，保存到session state里面
        coordinate = (self.index, group, metric)
        st.session_state['records_data'][coordinate] = [display_params, df]

    def revise_sql1(self, org_sql: str) -> str:
            '''
            (case1) revise original sql and return it
            '''
            # 替换所有的in为not in
            sql = re.sub(' in ', ' not in ', org_sql)
            return sql
        
    def revise_sql2(self, org_sql: str, dim: str, dim_val: str) -> str:
            '''
            (case2) revise original sql and return it
            '''
            dim_col = self.dim_dict[dim]
            sql = re.sub('where', f"where {dim_col} = '{dim_val}' and", org_sql)
            return sql
    
    def revise_sql3(self, org_sql: str, dim: str, dim_val: str) -> str:
        '''
        (case3) revise original sql and return it
        '''
        cust_type_dim, anot_dim = dim.split('-')  # 中文的维度名
        cust_type_dim_col, anot_dim_col = self.dim_dict[cust_type_dim], self.dim_dict[anot_dim]  # 转化为数据表中的列名
        cust_type_dim_val, anot_dim_val = dim_val.split('-')  # 维度值
        sql = re.sub('where', f"where {cust_type_dim_col} = '{cust_type_dim_val}' and {anot_dim_col} = '{anot_dim_val}' and", org_sql)
        return sql

    def fetch_cust_dev(self, group: str, date: datetime.date, dim: Optional[str], dim_val: Optional[str], k: int, metric: str, return_sql: bool = False) -> Optional[str]:
        '''
        fetch data for customer development analysis from kylin
        :param group: 分析类型-'客户发展分析'
        :param date: 日期
        :param dim: 维度中文名，如'省份'、'客户类型'
        :param dim_val: 维度值，如'北京'、'企业'
        :param k: 过去K个月
        :param metric: 指标，如'（按月）收入'、'（同比）收入增长额'
        :param return_sql: 是否返回sql语句
        :return: None or sql
        '''        
        td = datetime.date.today()
        # 本月第一天和最后一天
        this_month_start_ty, this_month_end_ty = self.parse_date(td)
        # 去年同期本月第一天和最后一天
        this_month_start_ly, this_month_end_ly = self.parse_date(td - relativedelta(years=1))
        # 上个月第一天和最后一天
        last_month_start_ty, last_month_end_ty = self.parse_date(td - relativedelta(months=1))
        # 去年同期上个月第一天和最后一天
        last_month_start_ly, last_month_end_ly = self.parse_date(td - relativedelta(years=1, months=1))

        if k:
            date_k_month_ago = td - relativedelta(months=k)
            # k个月前的第一天
            k_month_ago_start_ty, _ = self.parse_date(date_k_month_ago)
            # 去年同期k个月前的第一天
            k_month_ago_start_ly, _ = self.parse_date(date_k_month_ago - relativedelta(years=1))

        def fetch_num_existing_cust_km(metric: str, k: int):
            '''
            过去K个月每月存量客户数
            '''
            sql_lst = []
            for i in range(k + 1):
                date_i_month_ago = td - relativedelta(months=i)
                date_i_plus_1_month_ago = td - relativedelta(months=i + 1)
                date_i_month_ago_start, date_i_month_ago_end = self.parse_date(date_i_month_ago)
                date_i_plus_1_month_ago_start, date_i_plus_1_month_ago_end = self.parse_date(date_i_plus_1_month_ago)
                sql = f"""select (cast(year({self.date_dim}) as varchar) 
                      || '-'
                      ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias}, 
                      count(distinct {self.cust_id_dim}) as \"{metric}\"
                      from {self.table}
                      where {self.date_dim} >= '{date_i_month_ago_start}' and {self.date_dim} <= '{date_i_month_ago_end}' and {self.cust_id_dim} in (
                        select {self.cust_id_dim}
                        from {self.table}
                        where {self.date_dim} >= '{date_i_plus_1_month_ago_start}' and {self.date_dim} <= '{date_i_plus_1_month_ago_end}'
                      )
                      group by {self.month_date_alias}"""
                sql_lst.append(sql)
            
            sql = '\nunion\n'.join(sql_lst)
            return sql
        
        def fetch_num_new_cust_km(metric: str, k: int):
            '''
            过去K个月每月新增客户数
            '''
            sql = fetch_num_existing_cust_km(metric, k)
            sql = self.revise_sql1(sql)
            return sql
        
        def fetch_num_lost_cust_km(metric: str, k: int):
            '''
            过去K个月每月流失客户数
            '''
            sql_lst = []
            for i in range(k + 1):
                date_i_month_ago = td - relativedelta(months=i)
                date_i_plus_1_month_ago = td - relativedelta(months=i + 1)
                date_i_month_ago_start, date_i_month_ago_end = self.parse_date(date_i_month_ago)
                date_i_plus_1_month_ago_start, date_i_plus_1_month_ago_end = self.parse_date(date_i_plus_1_month_ago)
                sql = f"""select (cast(year(timestampadd(month, 1, {self.date_dim})) as varchar) 
                      || '-' 
                      || substring('0' + cast(month(timestampadd(month, 1, {self.date_dim})) as varchar), -2, 2)) as {self.month_date_alias}, 
                      count(distinct {self.cust_id_dim}) as \"{metric}\"
                      from {self.table}
                      where {self.date_dim} >= '{date_i_plus_1_month_ago_start}' and {self.date_dim} <= '{date_i_plus_1_month_ago_end}' and {self.cust_id_dim} not in (
                        select {self.cust_id_dim}
                        from {self.table}
                        where {self.date_dim} >= '{date_i_month_ago_start}' and {self.date_dim} <= '{date_i_month_ago_end}'
                      )
                      group by {self.month_date_alias}"""
                sql_lst.append(sql)
            
            sql = '\nunion\n'.join(sql_lst)
            return sql
        
        def fetch_tot_num_cust_km():
            '''
            过去K个月每月总客户数
            '''
            sql = f"""select (cast(year({self.date_dim}) as varchar) 
                  || '-' 
                  ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias}, 
                  count(distinct {self.cust_id_dim}) as \"{metric}\"
                  from {self.table}
                  where {self.date_dim} >= '{k_month_ago_start_ty}' and {self.date_dim} <= '{this_month_end_ty}'
                  group by {self.month_date_alias}"""
            return sql
        
        def fetch_num_cust_growth_yoy_km(k_month_ago_start_ty: str, k_month_ago_start_ly: str):
            '''
            过去K个月每月客户数（同比）增长额
            '''
            sql = f"""select t1.{self.month_date_alias} as {self.month_date_alias}, 今年, 去年
                   from
                   (select (cast(year({self.date_dim}) as varchar) 
                   || '-' 
                   ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias},
                   count(distinct {self.cust_id_dim}) as 今年
                   from {self.table}
                   where {self.date_dim} >= '{k_month_ago_start_ty}' and {self.date_dim} <= '{this_month_end_ty}'
                   group by {self.month_date_alias}) t1
                   join
                   (select (cast(year(timestampadd(year, 1, {self.date_dim})) as varchar) 
                   || '-' 
                   ||  substring('0' + cast(month(timestampadd(year, 1, {self.date_dim})) as varchar), -2, 2)) as {self.month_date_alias},
                   count(distinct {self.cust_id_dim}) as 去年
                   from {self.table}
                   where {self.date_dim} >= '{k_month_ago_start_ly}' and {self.date_dim} <= '{this_month_end_ly}'
                   group by {self.month_date_alias}) t2
                   on t1.{self.month_date_alias} = t2.{self.month_date_alias}
                   """
            return sql
        
        # 过去K个月每月客户数（同比）增长率
        fetch_num_cust_growth_rate_yoy_km = fetch_num_cust_growth_yoy_km

        def fetch_num_new_cust_ytd():
            '''
            （今年）累计新增客户数
            PS：用函数是防止metric不匹配导致变量赋值出错
            '''
            sql = FetchNumCust(self.index).fetch_num_cust(group, date, metric, return_sql=True)
            return sql

        # （今年）累计流失客户数
        fetch_num_lost_cust_ytd = fetch_num_new_cust_ytd

        def fetch_tot_num_cust_growth_rate_yoy_cont_sign(max_k: int):
            '''
            最近总客户数同比增长连续为正（负）的月份数
            :param max_k: 预设的最大连续为正（负）月数
            '''
            # 用max_k复写时间
            date_k_month_ago = td - relativedelta(months=max_k)
            k_month_ago_start_ty, _ = self.parse_date(date_k_month_ago)
            k_month_ago_start_ly, _ = self.parse_date(date_k_month_ago - relativedelta(years=1))

            sql = fetch_num_cust_growth_yoy_km(k_month_ago_start_ty, k_month_ago_start_ly)
            return sql

        def fetch_num_net_growth_cust_cont_sign(max_k: int):
            '''
            最近净增客户数连续为正（负）的月份数
            :param max_k: 预设的最大连续为正（负）月数
            '''
            
            metric_new_cust = '过去K个月每月新增客户数'
            metric_lost_cust = '过去K个月每月流失客户数'
            sql_new_cust = fetch_num_new_cust_km(metric_new_cust, max_k)
            sql_lost_cust = fetch_num_lost_cust_km(metric_lost_cust, max_k)
            sql = f"""select t1.{self.month_date_alias} as {self.month_date_alias}, {metric_new_cust}, {metric_lost_cust}
                  from 
                  ({sql_new_cust}) t1
                  join
                  ({sql_lost_cust}) t2
                  on t1.{self.month_date_alias} = t2.{self.month_date_alias}
                  order by {self.month_date_alias}"""
            return sql
        
        def fetch_existing_new_lost_cust_prop_tm():
            '''
            本月存量、新增、流失客户占比
            '''
            sql = f"""select 存量, 新增, 流失
                    from
                    (select '1' as id, count(distinct {self.cust_id_dim}) as 存量
                    from {self.table}
                    where ({self.date_dim} >= '{this_month_start_ty}' and {self.date_dim} <= '{this_month_end_ty}') and {self.cust_id_dim} in  (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{last_month_start_ty}' and {self.date_dim} <= '{last_month_end_ty}')) t1
                    join
                    (select '1' as id, count(distinct {self.cust_id_dim}) as 新增
                    from {self.table}
                    where ({self.date_dim} >= '{this_month_start_ty}' and {self.date_dim} <= '{this_month_end_ty}') and {self.cust_id_dim} not in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{last_month_start_ty}' and {self.date_dim} <= '{last_month_end_ty}')) t2
                    on t1.id = t2.id
                    join
                    (select '1' as id, count(distinct {self.cust_id_dim}) as 流失
                    from {self.table}
                    where ({self.date_dim} >= '{last_month_start_ty}' and {self.date_dim} <= '{last_month_end_ty}') and {self.cust_id_dim} not in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{this_month_start_ty}' and {self.date_dim} <= '{this_month_end_ty}')) t3
                    on t2.id = t3.id"""
            return sql
        
        def fetch_income_existing_cust_tm():
            '''
            本月存量客户收入
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\"
                    from {self.table}
                    where ({self.date_dim} >= '{this_month_start_ty}' and {self.date_dim} <= '{this_month_end_ty}') and {self.cust_id_dim} in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{last_month_start_ty}' and {self.date_dim} <= '{last_month_end_ty}')"""
            return sql
        
        def fetch_income_growth_existing_cust_yoy_tm():
            '''
            本月存量客户收入（同比）增长额
            '''
            sql = f"""select '本月' as 月份, sum({self.income_dim}) as \"{metric}\"
                    from {self.table}
                    where ({self.date_dim} >= '{this_month_start_ty}' and {self.date_dim} <= '{this_month_end_ty}') and {self.cust_id_dim} in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{last_month_start_ty}' and {self.date_dim} <= '{last_month_end_ty}')
                    union
                    select '去年本月' as 月份, sum({self.income_dim}) as \"{metric}\"
                    from {self.table}
                    where ({self.date_dim} >= '{this_month_start_ly}' and {self.date_dim} <= '{this_month_end_ly}') and {self.cust_id_dim} in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{last_month_start_ly}' and {self.date_dim} <= '{last_month_end_ly}')"""
            return sql
        
        # 本月存量客户收入（同比）增长率
        fetch_income_growth_rate_existing_cust_yoy_tm = fetch_income_growth_existing_cust_yoy_tm
        
        def fetch_income_new_cust_tm():
            '''
            本月新增客户收入
            '''
            sql = fetch_income_existing_cust_tm()
            sql = self.revise_sql1(sql)
            return sql
        
        def fetch_income_growth_new_cust_yoy_tm():
            '''
            本月新增客户收入（同比）增长额
            '''
            sql = fetch_income_growth_existing_cust_yoy_tm()
            sql = self.revise_sql1(sql)
            return sql
        
        # 本月新增客户收入（同比）增长率
        fetch_income_growth_rate_new_cust_yoy_tm = fetch_income_growth_new_cust_yoy_tm
        
        def fetch_income_lost_cust_tm():
            '''
            本月流失客户收入
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\"
                    from {self.table}
                    where ({self.date_dim} >= '{last_month_start_ty}' and {self.date_dim} <= '{last_month_end_ty}') and {self.cust_id_dim} not in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{this_month_start_ty}' and {self.date_dim} <= '{this_month_end_ty}')"""
            return sql
        
        def fetch_income_growth_lost_cust_yoy_tm():
            '''
            本月流失客户收入（同比）增长额
            '''
            sql = f"""select '本月' as 月份, sum({self.income_dim}) as \"{metric}\"
                    from {self.table}
                    where ({self.date_dim} >= '{last_month_start_ty}' and {self.date_dim} <= '{last_month_end_ty}') and {self.cust_id_dim} not in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{this_month_start_ty}' and {self.date_dim} <= '{this_month_end_ty}')
                    union
                    select '去年本月' as 月份, sum({self.income_dim}) as \"{metric}\"
                    from {self.table}
                    where ({self.date_dim} >= '{last_month_start_ly}' and {self.date_dim} <= '{last_month_end_ly}') and {self.cust_id_dim} not in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{this_month_start_ly}' and {self.date_dim} <= '{this_month_end_ly}')"""
            return sql 
        
        # 本月流失客户收入（同比）增长率
        fetch_income_growth_rate_lost_cust_yoy_tm = fetch_income_growth_lost_cust_yoy_tm
        
        if metric == '过去K个月每月存量客户数':
            sql = fetch_num_existing_cust_km(metric, k)
        elif metric == '过去K个月每月新增客户数':
            sql = fetch_num_new_cust_km(metric, k)
        elif metric == '过去K个月每月流失客户数':
            sql = fetch_num_lost_cust_km(metric, k)
        elif metric == '过去K个月每月总客户数':
            sql = fetch_tot_num_cust_km()
        elif metric == '过去K个月每月客户数（同比）增长额':
            sql = fetch_num_cust_growth_yoy_km(k_month_ago_start_ty, k_month_ago_start_ly)
        elif metric == '过去K个月每月客户数（同比）增长率':
            sql = fetch_num_cust_growth_rate_yoy_km(k_month_ago_start_ty, k_month_ago_start_ly)
        elif metric == '（今年）累计新增客户数':
            sql = fetch_num_new_cust_ytd()
        elif metric == '（今年）累计流失客户数':
            sql = fetch_num_lost_cust_ytd()
        elif metric == '最近总客户数同比增长连续为正（负）的月份数':
            k = self.max_k  # 预设的最大连续为正（负）月数
            sql = fetch_tot_num_cust_growth_rate_yoy_cont_sign(k)
        elif metric == '最近净增客户数连续为正（负）的月份数':
            if return_sql == False:
                k = self.max_k  # 预设的最大连续为正（负）月数
            sql = fetch_num_net_growth_cust_cont_sign(k)
        elif metric == '本月存量、新增、流失客户占比':
            sql = fetch_existing_new_lost_cust_prop_tm()
        elif metric == '本月存量客户收入':
            sql = fetch_income_existing_cust_tm()
        elif metric == '本月存量客户收入（同比）增长额':
            sql = fetch_income_growth_existing_cust_yoy_tm()
        elif metric == '本月存量客户收入（同比）增长率':
            sql = fetch_income_growth_rate_existing_cust_yoy_tm()
        elif metric == '本月新增客户收入':
            sql = fetch_income_new_cust_tm()
        elif metric == '本月新增客户收入（同比）增长额':
            sql = fetch_income_growth_new_cust_yoy_tm()
        elif metric == '本月新增客户收入（同比）增长率':
            sql = fetch_income_growth_rate_new_cust_yoy_tm()
        elif metric == '本月流失客户收入':
            sql = fetch_income_lost_cust_tm()
        elif metric == '本月流失客户收入（同比）增长额':
            sql = fetch_income_growth_lost_cust_yoy_tm()
        elif metric == '本月流失客户收入（同比）增长率':
            sql = fetch_income_growth_rate_lost_cust_yoy_tm()
            
        # 无下钻
        if dim == '全部':
            pass
        # 一维下钻
        elif '-' not in dim:
            sql = self.revise_sql2(sql, dim, dim_val)
        # 二维下钻
        elif '-' in dim:
            sql = self.revise_sql3(sql, dim, dim_val)

        if return_sql == False:
            self.fetch_and_save(sql, date, group, metric, dim, dim_val, k)
        else:
            return sql

class FetchPlanAchvmt(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)
        
    def fetch_and_save(self, sql: str, date: datetime.date, group: str, metric: str, k: int) -> None:
        '''
        fetch data and save relevant information
        '''
        # 根据sql获取数据
        df = self.fetch(self.project, sql)
        # display需要的params
        display_params = [date, k]
        # 设定坐标，保存到session state里面
        coordinate = (self.index, group, metric)
        st.session_state['records_data'][coordinate] = [display_params, df]
        
    def fetch_plan_achvmt(self, group: str, date: datetime.date, k: int, metric: str, return_sql: bool = False) -> Optional[str]:
        '''
        fetch data for plan achievement analysis from kylin
        :param group: 分析类型-'计划达成分析'
        :param date: 日期
        :param k: 过去K个月
        :param metric: 指标
        :param return_sql: 是否返回sql语句
        '''
        # 其他类中的方法含有dim和dim_val两个变量，用于维度下钻
        # 但这里没有维度分析，故将dim、dim_val设为None
        dim = None
        dim_val = None
        
        def fetch_income_ytd():
            '''
            （今年）累计收入
            '''
            sql = FetchIncome(self.index).fetch_income(group, date, metric, return_sql=True)
            return sql
        
        def fetch_income_ytd_pm():
            '''
            （今年）每月累计收入
            '''
            sql = FetchIncomeTrend(self.index).fetch_income_trend(group, date, dim, dim_val, k, metric, return_sql=True)
            return sql
        
        def fetch_income_km():
            '''
            过去K个月每月收入
            '''
            sql = FetchIncomeTrend(self.index).fetch_income_trend(group, date, dim, dim_val, k, metric, return_sql=True)
            return sql
        
        def fetch_tot_num_cust_tm():
            '''
            本月总客户数
            '''
            # 相当于获取'过去0个月每月总客户数'
            k = 0
            metric = '过去K个月每月总客户数'
            sql = FetchCustDev(self.index).fetch_cust_dev(group, date, dim, dim_val, k, metric, return_sql=True)
            return sql
        
        def fetch_tot_num_cust_km():
            '''
            过去K个月每月总客户数
            '''
            sql = FetchCustDev(self.index).fetch_cust_dev(group, date, dim, dim_val, k, metric, return_sql=True)
            return sql
        
        def fetch_num_net_growth_cust_km():
            '''
            过去K个月每月净增客户数
            '''
            metric = '最近净增客户数连续为正（负）的月份数'
            sql = FetchCustDev(self.index).fetch_cust_dev(group, date, dim, dim_val, k, metric, return_sql=True)
            return sql
        
        if metric == '（今年）累计收入':
            sql = fetch_income_ytd()
        elif metric == '（今年）每月累计收入':
            sql = fetch_income_ytd_pm()
        elif metric == '过去K个月每月收入':
            sql = fetch_income_km()
        elif metric == '本月总客户数':
            sql = fetch_tot_num_cust_tm()
        elif metric == '过去K个月每月总客户数':
            sql = fetch_tot_num_cust_km()
        elif metric == '过去K个月每月净增客户数':
            sql = fetch_num_net_growth_cust_km()
        
        if return_sql == False:
            self.fetch_and_save(sql, date, group, metric, k)
        else:
            return sql
            

class FetchRanking(FetchCustDim):
    def __init__(self, index: int) -> None:
        super().__init__(index)
        
    def fetch_ranking(self, group: str, date: datetime.date, dim: str, sub_anlys: str, metric: str, return_sql: bool = False) -> Optional[str]:
        '''
        fetch data for ranking analysis from kylin
        :param group: 分析类型-'排名分析'
        :param date: 日期
        :param dim: 维度中文名，如'省份'、'客户类型'
        :param sub_anlys: 子分析类型，如'收入分析'、'客户数分析'
        :param metric: 指标，如'（按月）收入'、'（同比）收入增长额'
        :param return_sql: 是否返回sql语句
        '''
        def fetch_ranking_income():
            # 时间变量
            td = datetime.date.today()
            year_start_ty, _ = self.parse_date(td.replace(month=1))
            year_start_ly, _ = self.parse_date((td - relativedelta(years=1)).replace(month=1))
            _, this_month_end_ty = self.parse_date(td)
            _, this_month_end_ly = self.parse_date(td - relativedelta(years=1))
            date_month_start_tm, date_month_end_tm = self.parse_date(date)  # 某月
            date_month_start_lm, date_month_end_lm= self.parse_date(date - relativedelta(months=1))  # 某月的上一个月
            # 维度变量
            dim_col = dim_val_dict[dim]  # 维度列名
            
            # 利用FetchCustDim中的fetch_cust_dim方法
            if metric in ['（按月）收入', '（同比）收入增长额', '（同比）收入增长率', '（今年）累计收入']:
                sql = FetchCustDim(self.index).fetch_cust_dim(group, date, dim, sub_anlys, metric, return_sql=True)
            # 需要写新sql的指标
            elif metric == '（今年）累计收入增长率':
                sql = f"""select {dim_col} as {dim}, sum({self.income_dim}) as \"{metric}\",
                    case
                    when {self.date_dim} >= '{year_start_ty}' and {self.date_dim} <= '{this_month_end_ty}' then '{this_month_end_ty[: -3]}'
                    when {self.date_dim} >= '{year_start_ly}' and {self.date_dim} <= '{this_month_end_ly}' then '{this_month_end_ly[: -3]}'
                    end as {self.month_date_alias}
                    from {self.table}
                    group by {dim}, {self.month_date_alias}"""
            elif metric == '（按月）新增客户收入':
                sql = f"""select {dim_col} as {dim}, sum({self.income_dim}) as \"{metric}\"
                    from {self.table}
                    where ({self.date_dim} >= '{date_month_start_tm}' and {self.date_dim} <= '{date_month_end_tm}') and {self.cust_id_dim} not in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{date_month_start_lm}' and {self.date_dim} <= '{date_month_end_lm}')
                    group by {dim}"""
            elif metric == '（按月）流失客户收入':
                sql = f"""select {dim_col} as {dim}, sum({self.income_dim}) as \"{metric}\"
                    from {self.table}
                    where ({self.date_dim} >= '{date_month_start_lm}' and {self.date_dim} <= '{date_month_end_lm}') and {self.cust_id_dim} not in (
                    select {self.cust_id_dim}
                    from {self.table}
                    where {self.date_dim} >= '{date_month_start_tm}' and {self.date_dim} <= '{date_month_end_tm}')
                    group by {dim}"""
            return sql
        
        def fetch_ranking_num_cust():
            # 利用FetchCustDim中的fetch_cust_dim方法
            sql = FetchCustDim(self.index).fetch_cust_dim(group, date, dim, sub_anlys, metric, return_sql=True)
            return sql
        
        if sub_anlys == '收入分析':
            sql = fetch_ranking_income()
        elif sub_anlys == '客户数分析':
            sql = fetch_ranking_num_cust()
            
        if return_sql == False:
            self.fetch_and_save(sql, date, group, metric, dim, sub_anlys)
        else:
            return sql

class FetchKeyCustIncome(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)
    
    def fetch_key_cust_income(self, group: str, date: datetime.date, metric: str):
        '''
        fetch data for key customer income analysis from kylin
        :param group: 分析类型-'关键客群收入分析'
        :param date: 日期
        :param metric: 指标
        '''
        # 日期变量
        date_month_start_ty, date_month_end_ty = self.parse_date(date)  # 某月月初和月末
        date_month_start_ly, date_month_end_ly = self.parse_date(date - relativedelta(years=1))  # 上一年同月月初和月末
        year_start_ty, _ = self.parse_date(date.replace(month=1))  # 今年年初
        
        # 查询同期数据时，定义今年和去年时间维度的名称
        this_year_name = '今年'
        last_year_name = '去年'
        
        # 查询不同客群时，定义的不同客户等级名称
        key_cust_name = '关键客群'
        level1_cust_name = '一级客群'
        level2_cust_name = '二级客群'
        level3_cust_name = '三级客群'
        other_cust_name = '其他客群'
        
        # 不同客群等级维度值
        key_cust_val = 0
        level1_cust_val = 1
        level2_cust_val = 2
        level3_cust_val = 3
                
        def fetch_key_cust_income_prop_m():
            '''
            关键客群（按月）收入占比
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\",
                    case {self.cust_level_dim}
                    when {key_cust_val} then '{key_cust_name}'
                    else '{other_cust_name}'
                    end as {self.cust_level_alias}
                    from {self.table}
                    where {self.date_dim} >= '{date_month_start_ty}' and {self.date_dim} <= '{date_month_end_ty}'
                    group by {self.cust_level_alias}"""
            return sql
            
        def fetch_key_cust_income_ytd_prop():
            '''
            关键客群（今年）累计收入占比
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\",
                    case {self.cust_level_dim}
                    when {key_cust_val} then '{key_cust_name}'
                    else '{other_cust_name}'
                    end as {self.cust_level_alias}
                    from {self.table}
                    where {self.date_dim} >= '{year_start_ty}' and {self.date_dim} <= '{date_month_end_ty}'
                    group by {self.cust_level_alias}"""
            return sql
            
        def fetch_key_cust_vs_comp_cust_income_m():
            '''
            关键客群vs非关键客群：（按月）收入
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\",
                    case {self.cust_level_dim}
                    when {key_cust_val} then '{key_cust_name}'
                    when {level1_cust_val} then '{level1_cust_name}'
                    when {level2_cust_val} then '{level2_cust_name}'
                    when {level3_cust_val} then '{level3_cust_name}'
                    end as {self.cust_level_alias}
                    from {self.table}
                    where {self.date_dim} >= '{date_month_start_ty}' and {self.date_dim} <= '{date_month_end_ty}'
                    group by {self.cust_level_alias}
                    having {self.cust_level_alias} is not null"""
            return sql
        
        def fetch_key_cust_vs_comp_cust_income_growth_yoy():
            '''
            关键客群vs非关键客群：（按月）收入（同比）增长额
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\",
                    case {self.cust_level_dim}
                    when {key_cust_val} then '{key_cust_name}'
                    when {level1_cust_val} then '{level1_cust_name}'
                    when {level2_cust_val} then '{level2_cust_name}'
                    when {level3_cust_val} then '{level3_cust_name}'
                    end as {self.cust_level_alias},
                    case 
                    when {self.date_dim} >= '{date_month_start_ty}' and {self.date_dim} <= '{date_month_end_ty}' then '{this_year_name}'
                    when {self.date_dim} >= '{date_month_start_ly}' and {self.date_dim} <= '{date_month_end_ly}' then '{last_year_name}'
                    end as {self.month_date_alias}
                    from {self.table}
                    group by {self.cust_level_alias}, {self.month_date_alias}
                    having {self.cust_level_alias} is not null and {self.month_date_alias} is not null"""
            return sql
        
        # 关键客群vs非关键客群：收入（同比）增长率
        fetch_key_cust_vs_comp_cust_income_growth_rate_yoy = fetch_key_cust_vs_comp_cust_income_growth_yoy
            
        def fetch_key_cust_vs_comp_cust_income_ytd():
            '''
            关键客群vs非关键客群：（按月）（今年）累计收入
            '''
            sql = f"""select sum({self.income_dim}) as \"{metric}\",
                    case {self.cust_level_dim}
                    when {key_cust_val} then '{key_cust_name}'
                    when {level1_cust_val} then '{level1_cust_name}'
                    when {level2_cust_val} then '{level2_cust_name}'
                    when {level3_cust_val} then '{level3_cust_name}'
                    end as {self.cust_level_alias}
                    from {self.table}
                    where {self.date_dim} >= '{year_start_ty}' and {self.date_dim} <= '{date_month_end_ty}'
                    group by {self.cust_level_alias}"""
            return sql
        
        def fetch_key_cust_vs_comp_cust_avg_spend_per_cust_m():
            '''
            关键客群vs非关键客群：（按月）客单价
            '''
            sql = f"""select avg(总收入) as \"{metric}\",
                    case {self.cust_level_dim}
                    when {key_cust_val} then '{key_cust_name}'
                    when {level1_cust_val} then '{level1_cust_name}'
                    when {level2_cust_val} then '{level2_cust_name}'
                    when {level3_cust_val} then '{level3_cust_name}'
                    end as {self.cust_level_alias}
                    from (
                        select {self.cust_id_dim}, {self.cust_level_dim}, sum({self.income_dim}) as 总收入
                        from {self.table}
                        where {self.date_dim} >= '{date_month_start_ty}' and {self.date_dim} <= '{date_month_end_ty}'
                        group by {self.cust_id_dim}, {self.cust_level_dim}
                    )
                    group by {self.cust_level_alias}
                    having {self.cust_level_alias} is not null"""
            return sql
        
        if metric == '关键客群（按月）收入占比':
            sql = fetch_key_cust_income_prop_m()
        elif metric == '关键客群（今年）累计收入占比':
            sql = fetch_key_cust_income_ytd_prop()
        elif metric == '关键客群vs非关键客群：（按月）收入':
            sql = fetch_key_cust_vs_comp_cust_income_m()
        elif metric == '关键客群vs非关键客群：（按月）收入（同比）增长额':
            sql = fetch_key_cust_vs_comp_cust_income_growth_yoy()
        elif metric == '关键客群vs非关键客群：（按月）收入（同比）增长率':
            sql = fetch_key_cust_vs_comp_cust_income_growth_rate_yoy()
        elif metric == '关键客群vs非关键客群：（今年）累计收入':
            sql = fetch_key_cust_vs_comp_cust_income_ytd()
        elif metric == '关键客群vs非关键客群：（按月）客单价':
            sql = fetch_key_cust_vs_comp_cust_avg_spend_per_cust_m()
            
        self.fetch_and_save(sql, date, group, metric)
        

class FetchKeyCustTrend(FetchData):
    def __init__(self, index: int) -> None:
        super().__init__(index)
        
    def fetch_and_save(self, sql: str, date: datetime.date, group: str, metric: str, k: int) -> None:
        '''
        fetch data and save relevant information
        '''
        # 根据sql获取数据
        df = self.fetch(self.project, sql)
        # display需要的params
        display_params = [date, k]
        # 设定坐标，保存到session state里面
        coordinate = (self.index, group, metric)
        st.session_state['records_data'][coordinate] = [display_params, df]
        
    def fetch_key_cust_trend(self, group: str, date: datetime.date, k: int, metric: str):
        '''
        fetch data for key customer trend from kylin
        :param group: 分析类型-'关键客群趋势分析'
        :param date: 日期
        :param k: 过去K个月
        :param metric: 指标
        '''
        # 日期变量
        td = datetime.date.today()
        _, this_month_end_ty = self.parse_date(date)  # 本月月初和月末
        _, this_month_end_ly = self.parse_date(date - relativedelta(years=1))  # 去年同月月初和月末
        
        if k:
            date_k_month_ago = td - relativedelta(months=k)
            # k个月前的第一天
            k_month_ago_start_ty, _ = self.parse_date(date_k_month_ago)
            # 去年同期k个月前的第一天
            k_month_ago_start_ly, _ = self.parse_date(date_k_month_ago - relativedelta(years=1))
            
        # 查询不同客群时，定义的不同客户等级名称
        key_cust_name = '关键客群'
        level1_cust_name = '一级客群'
        level2_cust_name = '二级客群'
        level3_cust_name = '三级客群'
        other_cust_name = '其他客群'
        
        # 不同客群等级维度值
        key_cust_val = 0
        level1_cust_val = 1
        level2_cust_val = 2
        level3_cust_val = 3
            
        def fetch_key_cust_income_prop_km(date_lower_bound: str, date_upper_bound: str, metric: str):
            '''
            关键客群过去K个月收入占比
            :param date_lower_bound: 日期下界
            :param date_upper_bound: 日期上界
            :param metric: 指标
            '''
            sql = f"""select (cast(year({self.date_dim}) as varchar)
                    || '-'
                    ||  substring('0' + cast(month({self.date_dim}) as varchar), -2, 2)) as {self.month_date_alias},
                    sum({self.income_dim}) as \"{metric}\",
                    case {self.cust_level_dim}
                    when {key_cust_val} then '{key_cust_name}'
                    else '{other_cust_name}'
                    end as {self.cust_level_alias}
                    from {self.table}
                    where {self.date_dim} >= '{date_lower_bound}' and {self.date_dim} <= '{date_upper_bound}'
                    group by {self.cust_level_alias}, {self.month_date_alias}
                    having {self.cust_level_alias} is not null"""
            return sql
        
        def fetch_key_cust_growth_income_prop_cont_sign():
            '''
            关键客群收入占比连续提升（下降）的月份数
            '''
            pass
        
        def fetch_key_cust_vs_whole_cust_income_yoy_km():
            '''
            关键客群vs整体客群：过去K个月收入（同比）增长率
            '''
            sql_ty = fetch_key_cust_income_prop_km(k_month_ago_start_ty, this_month_end_ty, '今年')
            
            sql_ly = fetch_key_cust_income_prop_km(k_month_ago_start_ly, this_month_end_ly, '去年')
            sql_ly = re.sub('year(', 'year(timestampadd(year, 1, ', sql_ly)
            sql_ly = re.sub('month(', 'month(timestampadd(year, 1, ', sql_ly)
            sql_ly = re.sub(') as varchar', ')) as varchar', sql_ly)
            
            sql = f"""select t1.{self.month_date_alias} as {self.month_date_alias}, t1.{self.cust_level_alias}s as {self.cust_level_alias}s, 今年, 去年
                    from
                    ({sql_ty}) t1
                    join
                    ({sql_ly}) t2
                    on concat(t1.{self.month_date_alias}, t1.{self.cust_level_alias}s) = concat(t2.{self.month_date_alias}, t2.{self.cust_level_alias}s)"""
            return sql
        
        def fetch_key_cust_vs_comp_cust_income_yoy_km():
            '''
            关键客群vs非关键客群：过去K个月收入（同比）增长率
            '''
            sql = fetch_key_cust_vs_whole_cust_income_yoy_km()
            org_sent = f"""case {self.cust_level_dim}
                        when {key_cust_val} then '{key_cust_name}'
                        else '{other_cust_name}'"""
            revised_sent = f"""case {self.cust_level_dim}
                            when {key_cust_val} then '{key_cust_name}'
                            when {level1_cust_val} then '{level1_cust_name}'
                            when {level2_cust_val} then '{level2_cust_name}'
                            when {level3_cust_val} then '{level3_cust_name}'"""
            sql = re.sub(org_sent, revised_sent, sql)
            return sql
        
        if metric == '关键客群过去K个月收入占比':
            sql = fetch_key_cust_income_prop_km(k_month_ago_start_ty, this_month_end_ty, metric)
        elif metric == '关键客群收入占比连续提升（下降）的月份数':
            sql = fetch_key_cust_growth_income_prop_cont_sign()
        elif metric == '关键客群vs整体客群：过去K个月收入（同比）增长率':
            sql = fetch_key_cust_vs_whole_cust_income_yoy_km()
        elif metric == '关键客群vs非关键客群：过去K个月收入（同比）增长率':
            sql = fetch_key_cust_vs_comp_cust_income_yoy_km()
            
        self.fetch_and_save(sql, date, group, metric, k)
        

class FetchKeyCustDev(FetchCustDev):
    def __init__(self, index: int) -> None:
        super().__init__(index)
        
    def revise_sql1(self, org_sql: str, metric: str, col_name: str) -> str:
        sql = re.sub(f'as \"{metric}\"', f'as {col_name}', org_sql)
        return sql
        
    def fetch_key_cust_dev(self, group: str, date: datetime.date, k: int, metric: str) -> Optional[str]:
        '''
        fetch data for customer development analysis from kylin
        :param group: 分析类型-'客户发展分析'
        :param date: 日期
        :param k: 过去K个月
        :param metric: 指标，如'（按月）收入'、'（同比）收入增长额'
        :return: None or sql
        '''  
        # 这里没有下钻分析，传入参数中应为'全部'，传入参数中应为None
        dim = '全部'
        dim_val = None
        
        if metric != '关键客群过去K个月存量、新增、流失客户占比':
            org_metric = metric[4: ]  # 修改指标名，剪切掉'关键课群'，以复用FetchCustDim中的fetch_cust_dim方法
            org_sql = FetchCustDev(self.index).fetch_cust_dev(group, date, dim, dim_val, k, org_metric, return_sql=True)  # 获取原sql
            key_cust_val = 0  # 关键客群值
            sql = re.sub('where', f'where {self.cust_level_dim} = {key_cust_val} and', org_sql)  # 添加关键客群条件
        else:
            fetch_cust_dev_inst = FetchCustDev(self.index)
            # '客户发展分析'-'过去K个月每月存量客户数'
            org_metric_existing = '过去K个月每月存量客户数'
            org_sql_existing_km = fetch_cust_dev_inst.fetch_cust_dev(group, date, dim, dim_val, k, org_metric_existing, return_sql=True)
            sql_existing_km = self.revise_sql1(org_sql_existing_km, org_metric_existing, '存量')  # 修改alias
            # '客户发展分析'-'过去K个月每月新增客户数'
            org_metric_new = '过去K个月每月新增客户数'
            org_sql_new_km = fetch_cust_dev_inst.fetch_cust_dev(group, date, dim, dim_val, k, org_metric_new, return_sql=True)
            sql_new_km = self.revise_sql1(org_sql_new_km, org_metric_new, '新增')  # 修改alias
            # '客户发展分析'-'过去K个月每月流失客户数'
            org_metric_lost = '过去K个月每月流失客户数'
            org_sql_lost_km = fetch_cust_dev_inst.fetch_cust_dev(group, date, dim, dim_val, k, org_metric_lost, return_sql=True)
            sql_lost_km = self.revise_sql1(org_sql_lost_km, org_metric_lost, '流失')  # 修改alias
            st.write('here')
            sql = f"""select t1.{self.month_date_alias}, 存量, 新增, 流失
                    from
                    ({sql_existing_km}) t1
                    join
                    ({sql_new_km}) t2
                    on t1.{self.month_date_alias} = t2.{self.month_date_alias}
                    join
                    ({sql_lost_km}) t3
                    on t2.{self.month_date_alias} = t3.{self.month_date_alias}"""
        
            # 测试
            st.warning('测试sql')
            st.write(sql)
        
        # self.fetch_and_save(sql, date, group, metric, dim, dim_val, k)


class FetchKeyCustPlanAchvmt(FetchPlanAchvmt):
    def __init__(self, index: int) -> None:
        super().__init__(index)
        
    def fetch_key_cust_plan_achvmt(self, group: str, date: datetime.date, k: int, metric: str):
        '''
        fetch data for plan achievement analysis from kylin
        :param group: 分析类型-'计划达成分析'
        :param date: 日期
        :param k: 过去K个月
        :param metric: 指标
        '''
        org_metric = metric[4: ]  # 修改指标名，剪切掉'关键课群'，以复用FetchCustDim中的fetch_cust_dim方法
        org_sql = FetchPlanAchvmt(self.index).fetch_plan_achvmt(group, date, k, org_metric, return_sql=True)  # 获取原sql
        key_cust_val = 0  # 关键客群值
        sql = re.sub('where', f'where {self.cust_level_dim} = {key_cust_val} and', org_sql)  # 添加关键客群条件
        
        self.fetch_and_save(sql, date, group, metric, k)
    

class FetchKeyCustRanking(FetchRanking):
    def __init__(self, index: int) -> None:
        super().__init__(index)
        
    def fetch_and_save(self, sql: str, date: datetime.date, group: str, metric: str, desig_cust: str, dim: str, sub_anlys: str) -> None:
        '''
        fetch data and save relevant information
        '''
        # 根据sql获取数据
        df = self.fetch(self.project, sql)
        # display需要的params
        display_params = [date, desig_cust, dim, sub_anlys]
        # 设定坐标，保存到session state里面
        coordinate = (self.index, group, metric)
        st.session_state['records_data'][coordinate] = [display_params, df]
        
    def fetch_key_cust_ranking(self, group: str, date: datetime.date, desig_cust: str, dim: str, sub_anlys: str, metric: str):
        '''
        fetch data for ranking analysis from kylin
        :param group: 分析类型-'排名分析'
        :param date: 日期
        :param desig_cust: designated cust group 指定客群
        :param dim: 维度中文名，如'省份'、'客户类型'
        :param sub_anlys: 子分析类型，如'收入分析'、'客户数分析'
        :param metric: 指标，如'（按月）收入'、'（同比）收入增长额'
        '''
        org_metric = metric[4: ]  # 修改指标名，剪切掉'关键课群'，以复用FetchCustDim中的fetch_cust_dim方法
        org_sql = FetchRanking(self.index).fetch_ranking(group, date, dim, sub_anlys, org_metric, return_sql=True)  # 获取原sql
        
        # 客群名和客群值
        cust_name_val = {'关键客群': 0, '一级客群': 1, '二级客群': 2, '三级客群': 3}
        sql = re.sub('where', f'where {self.cust_level_dim} = {cust_name_val[desig_cust]} and', org_sql)  # 添加关键客群条件
        
        self.fetch_and_save(sql, date, group, metric, desig_cust, dim, sub_anlys)
    
    
# def display_expander(index: int):
#     expander = st.expander('新建段落')
#     group = expander.selectbox('选择段落类型', ['收入分析', '客户数分析', '客单价分析'])
#     if group == '收入分析':
#         expander.write('选择了收入分析')
#         # 还有可以加一个时间范围类型，单时间点、双时间点、时间区间（这个涉及对比问题，暂时先不考虑）
#         name = expander.text_input('请输入段落名称')
#         date = expander.date_input('请选择时间范围类型', [datetime.date(2021, 1, 1), datetime.date(2021, 1, 31)])
#         metric = expander.selectbox('请选择需要计算的指标', ['总收入','（同比）收入增长额','收入同比增长率','（今年）累计收入'])
#         desc = expander.text_input('请输入段落描述')
#     # build button
#     build_btn = expander.button('创建', key=f'build{index}', on_click=build_btn_click, args=(index, name, group, desc))
#     if build_btn:
#         st.write('创建成功！')

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

def fetch(index, cp):
    '''
    fetch data
    :param index: index of the record
    :param cp: coordinate and params of the record
    '''
    group, params = cp
    if group == '收入分析':
        fetch = FetchIncome(index)
        fetch.fetch_income(group, *params)
    elif group == '客户数分析':
        fetch = FetchNumCust(index)
        fetch.fetch_num_cust(group, *params)
    elif group == '客单价分析':
        fetch = FetchAvgSpendPerCust(index)
        fetch.fetch_avg_spend_per_cust(group, *params)
    elif group == '客群分维度分析':
        fetch = FetchCustDim(index)
        fetch.fetch_cust_dim(group, *params)
    elif group == '收入趋势分析':
        fetch = FetchIncomeTrend(index)
        fetch.fetch_income_trend(group, *params)
    elif group == '客户发展分析':
        fetch = FetchCustDev(index)
        fetch.fetch_cust_dev(group, *params)
    elif group == '计划达成分析':
        fetch = FetchPlanAchvmt(index)
        fetch.fetch_plan_achvmt(group, *params)
    elif group == '排名分析':
        fetch = FetchRanking(index)
        fetch.fetch_ranking(group, *params)
    elif group == '关键客群收入分析':
        fetch = FetchKeyCustIncome(index)
        fetch.fetch_key_cust_income(group, *params)
    elif group == '关键客群趋势分析':
        fetch = FetchKeyCustTrend(index)
        fetch.fetch_key_cust_trend(group, *params)
    elif group == '关键客群发展分析':
        fetch = FetchKeyCustDev(index)
        fetch.fetch_key_cust_dev(group, *params)
    elif group == '关键客群计划达成分析':
        fetch = FetchKeyCustPlanAchvmt(index)
        fetch.fetch_key_cust_plan_achvmt(group, *params)
    elif group == '关键客群排名分析':
        fetch = FetchKeyCustRanking(index)
        fetch.fetch_key_cust_ranking(group, *params)
        
if st.button('提交'):
    # 从kylin获取数据，并保存到session_state里面
    for index, cp in st.session_state['records_params'].items():
        fetch(index, cp)
        

    # date, customer_level, customer_type, metric = temp_data
    # fetch = Fetch_data(st.session_state['rows'])
    # fetch.income_analysis(date, customer_level, customer_type, metric)
