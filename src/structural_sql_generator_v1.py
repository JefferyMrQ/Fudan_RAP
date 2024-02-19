import re
import datetime
import calendar
from dateutil.relativedelta import relativedelta
from typing import Optional
import yaml
from yaml import Loader
from functools import wraps

from abc import ABC, abstractmethod

# # 业务对象类型A
# obj_A = {}
# A_types = ['省份', '行业', '客户等级', '客户类型']

# prov_lst = ['上海', '云南', '内蒙古',
#             '北京', '吉林', '四川', '天津', '宁夏',
#             '安徽', '山东', '山西', '广东', '广西',
#             '新疆', '本部', '江苏', '江西', '河北',
#             '河南', '浙江', '海南', '湖北', '湖南',
#             '甘肃', '福建', '西藏', '贵州', '辽宁',
#             '重庆', '陕西', '青海', '黑龙江']
# hy_lst = ['交通物流行业', '企业客户一部', '证券保险客户拓展部', '文化旅游拓展部', '教育行业拓展部',
#           '重要客户服务部', '工业互联网BU', '银行客户拓展部', '医疗健康BU', '智慧城市BU', '生态环境拓展部',
#           '政务行业拓展部', '企业客户二部', '传媒与互联网客户拓展部', '农业行业拓展部']
# cust_level_lst = ['0', '1', '2', '3']
# cust_type_lst = ['政府', '企业']

# obj_A.update(
#     dict(zip(A_types, [prov_lst, hy_lst, cust_level_lst, cust_type_lst])))
# obj_A.update({'全部': 'all'})
# print(obj_A)

# # 业务对象类型B
# obj_B = {}

# B_types = ['产品']
# prod_lst = ['固网基础业务_数据网元',
#             '固网基础业务_互联网专线',
#             '固网基础业务_固话',
#             '固网基础业务_宽带',
#             '固网基础业务_其他',
#             '移网基础业务_工作手机',
#             '移网基础业务_行业短信',
#             '创新业务_IDC',
#             '创新业务_物联网',
#             '创新业务_云计算',
#             '创新业务_IT服务',
#             '创新业务_大数据',
#             '信息安全']

# obj_B.update(dict(zip(B_types, [prod_lst])))

# # 事件类型
# obj_event = {}

# event_types = ['购买']
# event_prop_lst = ['金额', '数量']

# obj_event.update(dict(zip(event_types, [event_prop_lst])))


def judge_return_or_append(func):
    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        sql_segment, return_or_append = func(instance, *args, **kwargs)
        if return_or_append == 'a':
            if 'select' in func.__name__:
                instance.select_fields.append(sql_segment)
            elif 'where' in func.__name__:
                instance.where_conds.append(sql_segment)
            elif 'other' in func.__name__:
                instance.other_syntax.append(sql_segment)
        if return_or_append == 'r':
            return sql_segment
    return wrapper

class GeneratorTools:
    global field_dict
    global analysis_dict
    
    # alias
    month_field_alias = '月份'  # case when字段别名，为了方便起见字段值统一设为月份值，因此以'月份'作为其别名
    
    # 在所有时间的分析中，本期和上一期时间类型的对应关系
    tp_lp_type_corr_dict = {'某月': '某月的上月', '今年': '去年12月'}  # tp: this_period, lp: last_period, corr: correspondence
    
    # 一个测试的开关
    toggle = "Off"
    
    def __init__(self, 
                 table_name: str,
                 group: str,
                 metric: str,
                 date: datetime.date, 
                 sub_anlys: Optional[str] = None,
                 dim: Optional[str] = None,
                 dim_val: Optional[str] = None, 
                 k: Optional[int] =None):
        '''
        :param table_name: 表名
        :param group: 组别  例如: '收入分析'、'客户数分析'
        :param metric: 指标  例如: '（按月）收入'、'（按月）存量客户数'
        :param date: 日期 例如: datetime.date(2021, 7, 1)
        :param sub_anlys: 子分析 对于部分analysis group起作用，例如“客群分维度分析”中的“收入分析”就是一个sub_anlys
        :param dim: 维度 包含单一维度和双维度情况，其中双维度中两个维度之间用“-”连接，例如“省份-行业”
        :param dim_val: 维度值，在双维度情况下，两个维度值之间用“-”连接，例如“上海-交通物流行业”; 如果dim有值，dim_val为None，说明是groupby的情况
        :param k: 过去K个月
        '''
        self.table_name = table_name
        self.group = group
        self.metric = metric
        
        self.time_field = field_dict['时间']  # 时间字段
        
        self.date = date
        self.sub_anlys = sub_anlys
        self.dim = dim
        self.dim_val = dim_val
        self.k = k
        
        self.select_fields = []
        self.where_conds = []
        self.other_syntax = []  # 包含最后的group by和having
    
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
    
    def gen_cond_time_range(self, time_cond_type: str, date: Optional[datetime.date] = None) -> str:
        '''
        有娱时间条件比较特殊, 一半只有一个固定的时间字段, 并且查询的时间种类变化繁多
        因此将其单独拿出来处理, 简化并节省了下面select、where、other的代码, 此外还便于维护
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年', '过去K个月'等
        :param date: 日期 例如: datetime.date(2021, 7, 1)
        :return: 时间条件文本
        '''
        time_field = self.time_field  # 时间字段
        
        if time_cond_type == '某月':
            date_this_month_ty = date
            lower_bound, upper_bound = self.parse_date(date_this_month_ty)  # date_this_month_start_ty, date_this_month_end_ty
        elif time_cond_type == '某月的上月':
            date_last_month_ty = date - relativedelta(months=1)
            lower_bound, upper_bound = self.parse_date(date_last_month_ty)  # date_last_month_start_ty, date_last_month_end_ty
        elif time_cond_type == '本月':
            this_month_today = datetime.date.today()
            lower_bound, upper_bound = self.parse_date(this_month_today)  # this_month_start_ty, this_month_end_ty
        elif time_cond_type == '上月':
            last_month_today = datetime.date.today() - relativedelta(months=1)
            lower_bound, upper_bound = self.parse_date(last_month_today)  # last_month_start_ty, last_month_end_ty
        elif time_cond_type == '今年':
            lower_bound = datetime.date(datetime.date.today().year, 1, 1).strftime('%Y-%m-%d')  # 今年年初日期
            this_month_today = datetime.date.today()
            _, upper_bound = self.parse_date(this_month_today)  # 本月月末日期
        elif time_cond_type == '去年12月':
            dec_ly = datetime.date(datetime.date.today().year - 1, 12, 1)  # 去年12月任意一天即可，这里随意选择了1号
            lower_bound, upper_bound = self.parse_date(dec_ly)
            
        
        time_cond = f"{time_field} >= '{lower_bound}' and {time_field} <= '{upper_bound}'"
        return time_cond
       

class SQLSelectWidgetGenerator(GeneratorTools):
    '''
    生成SQL语句中的select部分
    '''
    def __init__(self, *args):
        GeneratorTools.__init__(self, *args)
        
    @judge_return_or_append
    def gen_select_field(self, field: str, return_or_append: str = 'a'):
        '''
        生成sum(select_field)语句
        :param field: 字段名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        select_item = f"{field}"
        return select_item, return_or_append
        
    @judge_return_or_append
    def gen_select_field_sum(self, field: str, return_or_append: str = 'a') -> Optional[str]:
        '''
        生成sum(select_field)语句
        :param field: 字段名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        select_sum_item = f"sum({field}) as \"{self.metric}\""
        return select_sum_item, return_or_append
    
    @judge_return_or_append
    def gen_select_field_count_distinct(self, field: str, return_or_append: str = 'a') -> Optional[str]:
        '''
        生曾count(distinct select_field)语句
        :param field: 字段名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        select_count_distinct_item = f"count(distinct {field}) as \"{self.metric}\""
        return select_count_distinct_item, return_or_append
    
    @judge_return_or_append
    def gen_select_field_avg(self, field: str, return_or_append: str = 'a'):
        '''
        生曾count(distinct select_field)语句
        :param field: 字段名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        select_avg_item = f"avg({field}) as \"{self.metric}\""
        return select_avg_item, return_or_append
    
    @judge_return_or_append
    def gen_select_field_sum_avg(self, field: str, groupby_field: str, return_or_append: str = 'a') -> Optional[str]:
        '''
        生曾sum+avg语句
        :param field: 字段名
        :param groupby_field: 客单价类似的分析要求算每个个体的值之和, 因此要先设置一个group by字段
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        sql_generator = SQLGenerator(self.table_name,
                                     self.group,
                                     self.metric,
                                     self.date)
        # revise the expression of sub sql
        sub_alias = '总收入'  # 这个alias是根据具体业务写的
        sql_generator.metric = sub_alias
        # sql_generator.measurement = self.measurement  #  实例化的不会导致度量的变化，可不修改 
        sql_generator.expression = 'sum'
        # group by field setting
        sql_generator.gen_select_field(groupby_field)
        sql_generator.gen_other_syntax_group_by(groupby_field)
        
        sub_sql = sql_generator.integrating_sql()
        self.table = f"({sub_sql})"
        
        self.metric = '客单价'  # 本实例的alias
        self.gen_select_field_avg(sub_alias)
        
        # 这里的处理还没想好如何优化
        # 要处理的是如何不产生后续解析产生的where等一系列条件
        self.toggle = 'On'
    
    @judge_return_or_append
    def gen_select_field_time_yoy(self, time_cond_type: str, date: Optional[datetime.date] = None, return_or_append: str = 'a') -> Optional[str]:
        '''
        只有一个时间段的'同比', 例如'某月', '今年'
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年', '过去K个月'等
        :param date: 日期 例如: datetime.date(2021, 7, 1)
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        if time_cond_type in ['某月']:
            date = self.date
        
        # ly_type_request_dict = {'某月': '某月的上月'}  # yoy计算时, 本期的时间区间类型:上期的时间区间类型（Note：换成tp_lp_type_corr_dict了）
        if time_cond_type == '某月':
            # 获取本期和上期的时间区间类型
            type_tp = time_cond_type  # tp: this period
            type_lp = self.tp_lp_type_corr_dict[type_tp]  # tp_lp_type_corr_dict是描述本期和上期对应关系的字典类变量
            # 分别获取两者的时间区间条件语句
            time_cond_tp = self.gen_cond_time_range(time_cond_type=type_tp, date=date)
            time_cond_lp = self.gen_cond_time_range(time_cond_type=type_lp, date=date)
            mapped_val = {'本期': f"{date.strftime('%Y-%m')}", '上期': f"{(date - relativedelta(months=1)).strftime('%Y-%m')}"}  # case when映射后的值
            
            
        select_time_yoy_item = \
            f"""
            case
            when {time_cond_tp} then '{mapped_val['本期']}'
            when {time_cond_lp} then '{mapped_val['上期']}'
            end as {self.month_field_alias}
            """
        
        # date_this_month_ty = date  
        # date_this_month_start_ty, date_this_month_end_ty = self.parse_date(date_this_month_ty)
        # date_last_month_ty = date_this_month_ty - relativedelta(months=1)
        # date_last_month_start_ty, date_last_month_end_ty = self.parse_date(date_last_month_ty)
        # select_time_yoy_field = \
        #     f"""
        #     case
        #     when {field} >= '{date_this_month_start_ty}' and {field} <= '{date_this_month_end_ty}' then 'date_this_month_start_ty'
        #     when {field} >= '{date_last_month_start_ty}' and {field} <= '{date_last_month_end_ty}' then 'date_last_month_start_ty'
        #     """
        
        return select_time_yoy_item, return_or_append
    
    
class SQLWhereWidgetGenerator(GeneratorTools):
    '''
    生成SQL语句中的where部分
    '''
    def __init__(self, *args):
        GeneratorTools.__init__(self, *args)
        
    @judge_return_or_append
    def gen_where_cond_time_range(self, time_cond_type: str, return_or_append: str = 'a') -> Optional[str]:
        '''
        生成时间范围where条件, 返回语句或添加在where_conds列表中
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年', '过去K个月'等
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        :return: 时间范围where条件文本
        '''
        if time_cond_type in ['某月', '某月的上月']:
            date = self.date
        else:
            date = None
        time_cond = self.gen_cond_time_range(time_cond_type=time_cond_type, date=date)
        return time_cond, return_or_append
        
    # @judge_return_or_append
    # def gen_where_time_cond_date_this_month(self, date: datetime.date, return_or_append: str) -> Optional[str]:
    #     '''
    #     生成'所选date的本月时间'where条件
    #     :param date: 日期 例如: datetime.date(2021, 7, 1)
    #     :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
    #     '''
    #     # 获取所选date本月始末日期
    #     date_this_month_ty = date
    #     date_this_month_start_ty, date_this_month_end_ty = self.parse_date(date_this_month_ty)
    #     time_where_cond_date_this_month = f"{self.date_dim} >= {date_this_month_start_ty} and {self.date_dim} <= {date_this_month_end_ty}"
    #     return time_where_cond_date_this_month, return_or_append
    
    # @judge_return_or_append
    # def gen_where_time_cond_date_last_month(self, date: datetime.date, return_or_append: str) -> Optional[str]:
    #     '''
    #     生成'所选date的上个月时间'where条件
    #     :param date: 日期 例如: datetime.date(2021, 7, 1)
    #     :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
    #     '''
    #     # 获取所选date上月始末日期
    #     date_last_month_ty = date - relativedelta(months=1)
    #     date_last_month_start_ty, date_last_month_end_ty = self.parse_date(date_last_month_ty)
    #     time_where_cond_date_last_month = f"{self.date_dim} >= {date_last_month_start_ty} and {self.date_dim} <= {date_last_month_end_ty}"
    #     return time_where_cond_date_last_month, return_or_append
    
    @judge_return_or_append      
    def gen_where_cond_existing(self, field: str, return_or_append: str = 'a'):
        '''
        生成'存量'where条件
        :param field: 字段
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        time_where_cond_last_month = self.gen_cond_time_range('某月的上月', self.date)
        # 生成where条件
        existing_where_cond = \
            f"""{field} in (
                select {field}
                from {self.table_name}
                where {time_where_cond_last_month})"""
        return existing_where_cond, return_or_append
    
    @judge_return_or_append  
    def gen_where_cond_new(self, field: str, time_cond_type: str, return_or_append: str = 'a'):
        '''
        生成'新增'where条件
        :param field: 字段
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年', '过去K个月'等
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        if time_cond_type == '某月':
            time_cond_type_lp = self.tp_lp_type_corr_dict[time_cond_type]  # 获得'某月的上月'
            time_where_cond = self.gen_where_cond_existing(time_cond_type_lp)
        elif time_cond_type == '今年':
            time_cond_type_lp = self.tp_lp_type_corr_dict[time_cond_type]  # 获得'去年12月'
            time_where_cond = self.gen_where_cond_existing(time_cond_type_lp)
            
        # 生成where条件
        new_where_cond = \
            f"""{field} not in (
                select {field}
                from {self.table_name}
                where {time_where_cond})"""
        return new_where_cond, return_or_append
    
    @judge_return_or_append 
    def gen_where_cond_lost(self, field: str, time_cond_type: str, return_or_append: str = 'a'):
        '''
        生成'流失'where条件
        :param field: 字段
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年', '过去K个月'等
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        if time_cond_type == '某月':
            time_where_cond = self.gen_where_cond_existing('某月')
        elif time_cond_type == '今年':
            time_where_cond = self.gen_where_cond_existing('今年')
        # 生成where条件
        lost_where_cond = \
            f"""{field} not in (
                select {field}
                from {self.table_name}
                where {time_where_cond})"""
        return lost_where_cond, return_or_append
        
    def gen_where_time_cond_k_month(self, field: str, k: int, return_or_append: str = 'a'):
        pass

    def gen_sql_k_month_with_special_val():
        '''
        生成'过去K个月'且含有存量、新增这些特殊取值的sql
        '''
        pass


class SQLOtherWidgetGenerator(GeneratorTools):
    '''
    生成SQL语句中的各个部分
    '''
    def __init__(self, *args):
        GeneratorTools.__init__(self, *args)
        
    @judge_return_or_append
    def gen_other_syntax_group_by(self, field: str, return_or_append: str = 'a'):
        '''
        生成指定field的group by
        :param field: 指定的字段
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        other_syntax = f"group by {field}"
        return other_syntax, return_or_append
        
    @judge_return_or_append
    def gen_other_syntax_for_case_when(self, return_or_append: str = 'a'):
        '''
        生成case when语句对应的group by和having
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        '''
        other_syntax = \
            f"""
            group by {self.month_field_alias}
            having {self.month_field_alias} is not null
            """
        return other_syntax, return_or_append
        

class SQLGenerator(SQLSelectWidgetGenerator, SQLWhereWidgetGenerator, SQLOtherWidgetGenerator):
    '''
    解析metric得到"以事件为导向的框架", EOF(Event-Oriented Framework)
    EOF: [业务对象A的属性, 业务对象B的属性, 事件, 时间范围, 统计方法]
    '''
    def __init__(self, 
                 table_name: str,
                 group: str,
                 metric: str,
                 date: datetime.date, 
                 sub_anlys: Optional[str] = None,
                 dim: Optional[str] = None,
                 dim_val: Optional[str] = None, 
                 k: Optional[int] =None):
        SQLSelectWidgetGenerator.__init__(self, table_name, group, metric, date, sub_anlys, dim, dim_val, k)
        SQLWhereWidgetGenerator.__init__(self, table_name, group, metric, date, sub_anlys, dim, dim_val, k)
        SQLOtherWidgetGenerator.__init__(self, table_name, group, metric, date, sub_anlys, dim, dim_val, k)
        
        self.parse_framework()
        
    def parse_metric(self):
        '''
        解析metric得到EOF
        '''
        global analysis_dict
        framework = analysis_dict[self.group][self.metric]
        return framework
    
    def parse_framework(self):
        '''
        解析EOF，生成sql参数
        '''
        # 获取EOF
        framework = self.parse_metric()
        
        # 获取EOF中的各个参数
        self.bo_A = framework['业务对象A']  # Business Object A  业务对象A
        self.bo_A_prop = framework['业务对象A属性']
        self.bo_A_prop_value = framework['业务对象A属性值']
        self.bo_B = framework['业务对象B']
        self.bo_B_prop = framework['业务对象B属性']
        self.bo_B_prop_value = framework['业务对象B属性值']
        self.event = framework['事件']
        self.event_prop = framework['事件属性']
        self.measurement = framework['度量']
        self.time_category = framework['时间']
        self.expression = framework['统计方法']
        
        # 解析参数
        # 解析业务对象A
        # 解析业务对象B
        # 解析事件
        # 解析时间
        # 解析统计方法
        
    def parse_event(self):
        '''
        解析事件
        '''
        pass
    
    def parse_time(self):
        '''
        解析时间
        '''
        if self.time_category == '某月':
            self.gen_where_cond_time_range('某月')
        elif self.time_category == '某月的上月':  # 这个是原数据里没有的值，但是要跟业务对象属性'流失'配合
            self.gen_where_cond_time_range('某月的上月')
        elif self.time_category == '某月+同比':
            # 添加select 和 other
            self.gen_select_field_time_yoy('某月')
            self.gen_other_syntax_for_case_when()
        elif self.time_category == '今年':
            self.gen_where_cond_time_range('今年')
        elif self.time_category == '去年12月':
            self.gen_where_cond_time_range('去年12月')
        elif self.time_category == '今年+同比':
            pass
        elif self.time_category == '今年+每月':
            pass
        elif self.time_category == '最近连续月份+每月+同比':
            pass
        elif self.time_category == '本月':
            pass
        elif self.time_category == '本月+同比':
            pass
        elif self.time_category == '过去K个月+每月':
            pass
        elif self.time_category == '过去K个月+每月+同比':
            pass
            
    def parse_expression(self):
        '''
        解析统计方法
        '''
        # 根据event判断        
        if self.expression == 'sum':
            self.gen_select_field_sum(field=field_dict[self.measurement])
        elif self.expression == 'count distinct':
            self.gen_select_field_count_distinct(field=field_dict[self.measurement])
        elif self.expression == 'sum+avg':
            self.gen_select_field_sum_avg(field=field_dict[self.measurement])
        
    def parse_bo_A(self):
        '''
        解析业务对象A
        '''
        bo_A = self.bo_A
        bo_A_prop = self.bo_A_prop
        bo_A_prop_value = self.bo_A_prop_value
        
        # 工具函数
        drop_empty_elem = lambda lst: list(filter(None, lst))  # 去除列表中的空元素
        
        # 去除数据中的无用信息
        if '(TBD)' in bo_A_prop_value:
            bo_A_prop_value = bo_A_prop_value.replace('(TBD)', '')
            
        # 解析业务对象A属性
        if '+' not in bo_A_prop and '+/' not in bo_A_prop:
            # 当只有一个固定的业务对象A属性时
            field = [field_dict[bo_A_prop], ]
        elif '+' in bo_A_prop and '+/' in bo_A_prop:
            # 当既有多个固定的业务对象A属性，又有可选的业务对象A属性时
            pass
        elif '+/' in bo_A_prop:
            # 当允许有多个可选的业务对象A属性时
            field = []
        elif '+' in bo_A_prop:
            # 当有多个固定的业务对象A属性时
            prop_lst = re.split('\+', bo_A_prop)
            prop_lst = drop_empty_elem(prop_lst)
            
            count_lst = re.findall('\+', bo_A_prop)
            count = len(count_lst)
            
            if count == 1:
                # 当有两个固定的业务对象A属性时
                field = [field_dict[prop] for prop in prop_lst]
        
        # 解析业务对象A属性值
        if '+' not in bo_A_prop_value and '+/' not in bo_A_prop_value:
            # 当只有一个固定的业务对象A属性值时
            val = [bo_A_prop_value, ]
        elif '+' in bo_A_prop_value and '+/' in bo_A_prop_value:
            # 当既有多个固定的业务对象A属性值，又有可选的业务对象A属性值时
            pass
        elif '+/' in bo_A_prop_value:
            # 当允许有多个可选的业务对象A属性值时
            val = re.split('\+/', bo_A_prop_value)
            val = drop_empty_elem(val)
        elif '+' in bo_A_prop_value:
            # 当有多个固定的业务对象A属性值时
            val = re.split('\+', bo_A_prop_value)
            val = drop_empty_elem(val)
        
        # 解析val
        if val[0] == 'all':
            pass
        elif val[0] == '存量':
            self.gen_where_cond_existing(field[0])
        elif val[0] == '新增':
            if self.time_category == '某月':
                self.gen_where_cond_new(field[0], '某月')
            elif self.time_category == '今年':
                self.gen_where_cond_new(field[0], '今年')
        elif val[0] == '流失':
            if self.time_category == '某月':
                self.gen_where_cond_lost(field[0], '某月')
                self.time_category = self.tp_lp_type_corr_dict[self.time_category]  # where的时间要修改（后续看看这个点需不需要在原数据里修改）
            elif self.time_category == '今年':
                self.gen_where_cond_lost(field[0], '今年')
                self.time_category = self.tp_lp_type_corr_dict[self.time_category]
            
        # # 解析val
        # if isinstance(val, str):
        #     if val == 'all':
        #         pass  # 目前只有 客户-客户id-all 这一种情况满足此条件，因此无需解析处理
        # elif isinstance(val, list):
        #     if val[0] == 'all':
        #         pass
        #     elif val[0] == '存量':
        #         self.gen_where_cond_existing()
            
        #     elif val[0] == '新增':
        #         pass
        #     elif val[0] == '流失':
        #         pass
        
        # if val1 in locals() and val2 in locals():
        #     # 判断val1
        #     if val1 == 'all':
        #         pass
        #     elif val1 == '存量':
        #         pass
        #     elif val1 == '新增':
        #         pass
        #     elif val1 == '流失':
        #         pass
        #     # 判断val2
        #     if val2 == 'groupby':
        #         pass
        #     elif val2 == '待定值':
        #         pass
    
    def parse_bo_B(self, bo_B, bo_B_prop, bo_B_prop_value):
        '''
        解析业务对象B
        '''
        if '+' not in bo_B_prop and '+/' not in bo_B_prop:
            # 当只有一个固定的业务对象A属性时
            bo_A_field = field_dict[bo_B_prop]
        elif '+' in bo_B_prop or '+/' in bo_B_prop:
            pass
    
    def parse(self):
        self.parse_expression()  # P1 例如sum+avg就要先生成子sql再修改select
        if self.toggle == "On":
            pass
        elif self.toggle == "Off":
            self.parse_bo_A()  # P2 例如有些业务对象的分析会修改时间分析的参数
            self.parse_time()
        
        
    def integrating_sql(self):
        '''
        整合sql
        '''
        self.parse()
        
        select_segment = 'select' + ' ' + ', '.join(self.select_fields)
        from_segment = 'from' + ' ' + self.table_name
        where_segment = 'where' + ' ' + ' and '.join(self.where_conds) if len(self.where_conds) != 0 else ''
        other_segment = '\n'.join(self.other_syntax)
        sql = f"{select_segment}\n{from_segment}\n{where_segment}\n{other_segment}"
        return sql

def load_matching_data():
    '''
    从数据文件中加载metric-EOF的匹配数据
    '''
    field_data_file = open('./data/field_data.yaml', 'r', encoding='utf-8')
    analysis_data_file = open('./data/analysis_data.yaml', 'r', encoding='utf-8')
    field_dict = yaml.load(field_data_file, Loader=Loader)  # field_dict 属性:属性名
    analysis_dict = yaml.load(analysis_data_file, Loader=Loader)  # analysis_dict 组别:指标:EOF
    globals()["field_dict"] = field_dict
    globals()["analysis_dict"] = analysis_dict

def get_sql():
    '''
    Step1: 根据ParseMetrics类解析metric得到EOF(Event-Oriented Framework)
    Step2: 根据EOF变量和SQLGenerator类生成SQL语句
    '''
    pass

__all__ = list(filter(lambda var: not var.startswith('_'), dir()))

if __name__ == "__main__":
    # load matching data
    load_matching_data()
    
    # parse metric
    selected_group = ""
    selected_metric = ""
    # parse_metrics = ParseMetrics(selected_group, selected_metric)
    # framework = parse_metrics.parse_metric()
    
    # set test params
    table_name = 'data'
    group = '客单价分析'
    metric = '（按月）新增客户单价'
    date = datetime.date(2022, 7, 1)
    
    # generate sql
    sql_generator = SQLGenerator(table_name=table_name,
                                 group=group,
                                 metric=metric,
                                 date=date)
    
    sql = sql_generator.integrating_sql()
    print(sql)

