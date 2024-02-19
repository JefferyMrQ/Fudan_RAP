import re
import datetime
import calendar
from dateutil.relativedelta import relativedelta
from typing import Optional
import yaml
from yaml import Loader
from functools import wraps


# 读取配置文件
FIELD_DATA_FILE = open('../data/field_data.yaml', 'r', encoding='utf-8')
ANALYSIS_DATA_FILE = open('../data/analysis_data.yaml', 'r', encoding='utf-8')

# 读取配置信息
FIELD_DICT = yaml.load(FIELD_DATA_FILE, Loader=Loader)  # FIELD_DICT 属性:属性名
EVENT_FIELD_DICT = FIELD_DICT['事件属性']
BO_A_FIELD_DICT = FIELD_DICT['业务对象A属性']
BO_B_FIELD_DICT = FIELD_DICT['业务对象B属性']
ANALYSIS_DICT = yaml.load(ANALYSIS_DATA_FILE, Loader=Loader)  # ANALYSIS_DICT 组别:指标:EOF


def judge_return_or_append(func):
    """
    decorator, 判断返回还是追加
    """
    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        sql_segment, return_or_append = func(instance, *args, **kwargs)
        if return_or_append == 'a':
            if 'select' in func.__name__:
                instance.select_fields.append(sql_segment)
            elif 'where' in func.__name__:
                instance.where_conds.append(sql_segment)
            # elif 'other' in func.__name__:
            #     instance.other_syntax.append(sql_segment)
            elif 'groupby' in func.__name__:
                instance.groupby_fields.append(sql_segment)
            elif 'having' in func.__name__:
                instance.having_conds.append(sql_segment)
        if return_or_append == 'r':
            return sql_segment
    return wrapper


class GeneratorTools:
    global EVENT_FIELD_DICT
    global BO_A_FIELD_DICT
    global BO_B_FIELD_DICT
    global ANALYSIS_DICT
    
    # alias
    month_field_alias = '月份'  # case when字段别名，为了方便起见字段值统一设为月份值，因此以'月份'作为其别名
    
    # max_k 用于判断最近连续正/负月份数（可以根据业务要求修改，做测试尽量选的少一些）
    max_k = 2
    
    # 在所有时间的分析中，本期和上一期时间类型的对应关系
    yoy_tp_lp_type_corr_dict = {'某月': '去年某月', '今年': '去年ytd', '本月': '去年本月'}  # (同比)tp: this_period, lp: last_period, corr: correspondence
    mom_tp_lp_type_corr_dict = {'某月': '某月的上月', '今年': '去年12月', '本月': '上月', '去年本月': '去年上月'}  # (环比)tp: this_period, lp: last_period, corr: correspondence
    
    drop_empty_elem = lambda self, lst: list(filter(None, lst))  # 去除列表中的空元素
    
    def __init__(self, 
                 table_name: str,
                 group: str,
                 metric: str,
                 date: datetime.date, 
                 sub_anlys: Optional[str] = None,
                 dim_A: Optional[str] = None,
                 dim_val_A: Optional[str] = None, 
                 dim_B: Optional[str] = None,
                 dim_val_B: Optional[str] = None, 
                 k: Optional[int] =None,
                 desig_cust: Optional[str] = None):
        """
        :param table_name: 表名
        :param group: 组别  例如: '收入分析'、'客户数分析'
        :param metric: 指标  例如: '（按月）收入'、'（按月）存量客户数'
        :param date: 日期 例如: datetime.date(2021, 7, 1)
        :param sub_anlys: 子分析 对于部分analysis group起作用，例如“客群分维度分析”中的“收入分析”就是一个sub_anlys
        :param dim_A: 业务对象A维度（替换待定属性） 包含单一维度和双维度情况，其中双维度中两个维度之间用“-”连接，例如“省份-行业”
        :param dim_val_A: 业务对象A维度值（替换待定值），在双维度情况下，两个维度值之间用“-”连接，例如“上海-交通物流行业”
        :param dim_B: 业务对象B维度（替换待定属性） 包含单一维度和双维度情况，其中双维度中两个维度之间用“-”连接，例如“客户等级-产品名”
        :param dim_val_B: 业务对象B维度值（替换待定值），在双维度情况下，两个维度值之间用“-”连接，例如“0-某产品”
        :param k: 过去K个月
        :param desig_cust: 指定客户，为了'关键客群排名分析'中'客户等级'属性需要指定其'待定值'
        """
        self.table_name = table_name
        self.group = group
        self.metric = metric
        
        self.time_field = EVENT_FIELD_DICT['时间']  # 时间字段
        
        self.date = date
        self.sub_anlys = sub_anlys
        self.dim_A = dim_A
        self.dim_val_A = dim_val_A
        self.dim_B = dim_B
        self.dim_val_B = dim_val_B
        self.k = k
        self.desig_cust = desig_cust
        
        self.select_fields = []
        self.where_conds = []
        # self.other_syntax = []  # 包含最后的group by和having
        self.groupby_fields = []
        self.having_conds = []
    
    def parse_date(self, date: datetime.date) -> list:
        """
        parse a date to a sequence of strings, containing the start date and the end date of the month 
        """
        _, last_day = calendar.monthrange(date.year, date.month)
        month_start = '{}-{}-{}'.format(date.year,
                                        str(date.month).rjust(2, '0'), '01')
        month_end = '{}-{}-{}'.format(date.year, str(date.month).rjust(2,
                                                                       '0'), str(last_day).rjust(2, '0'))
        return [month_start, month_end]
    
    def remove_blank_space(self, text):
        lines = text.split('\n')
        non_empty_lines = []
        for line in lines:
            line = line.strip()
            if line:
                non_empty_lines.append(line)
        return '\n'.join(non_empty_lines)
    
    def gen_sub_sql_generator(self, **kwargs):
        params_dict = {'table_name': self.table_name,
                       'group': self.group,
                       'metric': self.metric,
                       'date': self.date,
                       'sub_anlys': self.sub_anlys,
                       'dim_A': self.dim_A,
                       'dim_val_A': self.dim_val_A,
                       'dim_B': self.dim_B,
                       'dim_val_B': self.dim_val_B,
                       'k': self.k}
        if kwargs:
            params_dict.update(kwargs)
            
        sql_generator = SQLGenerator(**params_dict)
        return sql_generator
    
    def gen_cond_time_range(self, time_cond_type: str, date: Optional[datetime.date] = None) -> str:
        """
        有娱时间条件比较特殊, 一半只有一个固定的时间字段, 并且查询的时间种类变化繁多
        因此将其单独拿出来处理, 简化并节省了下面select、where、other的代码, 此外还便于维护
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年', '过去K个月'等
        :param date: 日期 例如: datetime.date(2021, 7, 1)
        :return: 时间条件文本
        """
        time_field = self.time_field  # 时间字段
        
        td = datetime.date.today()
        if time_cond_type == '某月':
            date_this_month_ty = date  # ty: this year
            lower_bound, upper_bound = self.parse_date(date_this_month_ty)  # date_this_month_start_ty, date_this_month_end_ty
        elif time_cond_type == '去年某月':
            date_this_month_ly = date - relativedelta(years=1)
            lower_bound, upper_bound = self.parse_date(date_this_month_ly)
        elif time_cond_type == '某月的上月':
            date_last_month_ty = date - relativedelta(months=1)
            lower_bound, upper_bound = self.parse_date(date_last_month_ty)  # date_last_month_start_ty, date_last_month_end_ty
        elif time_cond_type == '本月':
            this_month_today_ty = td
            lower_bound, upper_bound = self.parse_date(this_month_today_ty)  # this_month_start_ty, this_month_end_ty
        elif time_cond_type == '去年本月':
            this_month_today_ly = td - relativedelta(years=1)
            lower_bound, upper_bound = self.parse_date(this_month_today_ly)
        elif time_cond_type == '上月':
            last_month_today_ty = td - relativedelta(months=1)
            lower_bound, upper_bound = self.parse_date(last_month_today_ty)  # last_month_start_ty, last_month_end_ty
        elif time_cond_type == '去年上月':
            last_month_today_ly = td - relativedelta(years = 1, months=1)
            lower_bound, upper_bound = self.parse_date(last_month_today_ly)
        elif time_cond_type in ['今年', '今年+每月']:
            lower_bound = datetime.date(td.year, 1, 1).strftime('%Y-%m-%d')  # 今年年初日期
            this_month_today_ty = td
            _, upper_bound = self.parse_date(this_month_today_ty)  # 今年本月月末日期
        elif time_cond_type == '去年ytd':
            td_ly = td - relativedelta(years=1)
            lower_bound = datetime.date(td_ly.year, 1, 1).strftime('%Y-%m-%d')  # 去年年初日期
            this_month_today_ly = td_ly
            _, upper_bound = self.parse_date(this_month_today_ly)  # 去年本月月末日期
        elif time_cond_type == '去年12月':
            dec_ly = datetime.date(td.year - 1, 12, 1)  # 去年12月任意一天即可，这里随意选择了1号
            lower_bound, upper_bound = self.parse_date(dec_ly)
        elif time_cond_type == '过去K个月+每月':
            this_month_today = td
            k_month_ago_today = this_month_today - relativedelta(months=self.k)
            lower_bound, _ = self.parse_date(k_month_ago_today)
            _, upper_bound = self.parse_date(this_month_today)
        elif time_cond_type == '去年过去K个月+每月':
            this_month_today_ly = td - relativedelta(years=1)
            k_month_ago_today_ly = this_month_today_ly - relativedelta(months=self.k)
            lower_bound, _ = self.parse_date(k_month_ago_today_ly)
            _, upper_bound = self.parse_date(this_month_today_ly)
        elif time_cond_type == '最近连续月份+每月':
            this_month_today = td
            k_month_ago_today = this_month_today - relativedelta(months=self.max_k)
            lower_bound, _ = self.parse_date(k_month_ago_today)
            _, upper_bound = self.parse_date(this_month_today)
            
        time_cond = f"{time_field} >= '{lower_bound}' and {time_field} <= '{upper_bound}'"
        return time_cond
       

class SQLSelectWidgetGenerator(GeneratorTools):
    """
    生成SQL语句中的select部分
    """
    def __init__(self, *args):
        GeneratorTools.__init__(self, *args)
        
    @judge_return_or_append
    def gen_select_field(self, field: str, alias: Optional[str] = None, return_or_append: str = 'a'):
        """
        生成select field语句
        :param field: 字段名
        :param alias: 字段别名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        select_item = f"{field}"
        select_item += f" as {alias}" if alias is not None else ''
        return select_item, return_or_append
        
    @judge_return_or_append
    def gen_select_field_sum(self, field: str, return_or_append: str = 'a') -> Optional[str]:
        """
        生成sum(select_field)语句
        :param field: 字段名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        select_sum_item = f"sum({field}) as \"{self.metric}\""
        return select_sum_item, return_or_append
    
    @judge_return_or_append
    def gen_select_field_count_distinct(self, field: str, return_or_append: str = 'a') -> Optional[str]:
        """
        生成count(distinct select_field)语句
        :param field: 字段名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        select_count_distinct_item = f"count(distinct {field}) as \"{self.metric}\""
        return select_count_distinct_item, return_or_append
    
    @judge_return_or_append
    def gen_select_field_avg(self, field: str, return_or_append: str = 'a'):
        """
        生成avg(field)语句
        :param field: 字段名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        select_avg_item = f"avg({field}) as \"{self.metric}\""
        return select_avg_item, return_or_append
    
    def gen_select_field_sum_avg(self, groupby_main_field: str, groupby_dim_field: str = None, special_toggle: bool = False) -> Optional[str]:
        """
        生成sum+avg语句
        :param field: 字段名
        :param groupby_main_field: 主字段, 在内部group by
        :param groupby_dim_field: 维度字段, 在内外部都要group by
        :param special_toggle: 特殊开关，针对'关键客群收入分析'-'关键客群vs非关键客群：（按月）客单价'的情况
        """
        # 内层
        sub_sql_generator = self.gen_sub_sql_generator()
        # 设置内层alias
        sub_alias = '总收入'  # 内层
        # revise the expression of sub sql
        sub_sql_generator.expression = 'sum'
        # sub_sql_generator.measurement = field  #  实例化的不会导致度量的变化，可不修改 
        if special_toggle:
            # 生成内层sql时，需要消除传入的属性和属性值信息
            sub_sql_generator.bo_A_prop = re.sub('\+.*', '', sub_sql_generator.bo_A_prop)
            sub_sql_generator.bo_A_prop_value = re.sub('\+.*', '', sub_sql_generator.bo_A_prop_value)
        # group by dim field setting first if exists
        if groupby_dim_field is not None:
            sub_sql_generator.gen_select_field(groupby_dim_field)
            sub_sql_generator.gen_groupby_field(groupby_dim_field)
        # group by main field setting
        sub_sql_generator.gen_select_field(groupby_main_field)
        sub_sql_generator.gen_groupby_field(groupby_main_field)
        
        sub_sql = sub_sql_generator.integrating_sql()
        sub_sql = re.sub(f"\"{sub_sql_generator.metric}\"", f"{sub_alias}", sub_sql)
        
        # 外层
        self.table_name = f"({sub_sql})"
        self.metric = '客单价'  # 外层alias
        self.gen_select_field_avg(sub_alias)  # 外层select item, 以内层alias为输入字段
    
    @judge_return_or_append
    def gen_select_field_time_yoy(self, time_cond_type: str, date: Optional[datetime.date] = None, return_or_append: str = 'a') -> Optional[str]:
        """
        只有一个时间段的'同比', 例如'某月', '今年'
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年ytd', '过去K个月'等
        :param date: 日期 例如: datetime.date(2021, 7, 1)
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        if time_cond_type in ['某月']:
            date = self.date
        
        if time_cond_type == '某月':
            # 获取本期和上期的时间区间类型
            type_tp = time_cond_type  # tp: this period
            type_lp = self.yoy_tp_lp_type_corr_dict[type_tp]  # 去年某月
            # 分别获取两者的时间区间条件语句
            time_cond_tp = self.gen_cond_time_range(time_cond_type=type_tp, date=date)
            time_cond_lp = self.gen_cond_time_range(time_cond_type=type_lp, date=date)
            mapped_val = {'本期': f"{date.strftime('%Y-%m')}", '上期': f"{(date - relativedelta(years=1)).strftime('%Y-%m')}"}  # case when映射后的值
        elif time_cond_type == '今年':
            # 获取本期和上期的时间区间类型
            type_tp = time_cond_type
            type_lp = self.yoy_tp_lp_type_corr_dict[type_tp]  # 去年ytd
            # 分别获取两者的时间区间条件语句
            time_cond_tp = self.gen_cond_time_range(time_cond_type=type_tp)
            time_cond_lp = self.gen_cond_time_range(time_cond_type=type_lp)
            td = datetime.datetime.today()
            td_ly = td - relativedelta(years=1)
            mapped_val = {'本期': f"{td.strftime('%Y-%m')}", '上期': f"{td_ly.strftime('%Y-%m')}"}  # case when映射后的值
            
        select_time_yoy_item = \
            f"""
            case
            when {time_cond_tp} then '{mapped_val['本期']}'
            when {time_cond_lp} then '{mapped_val['上期']}'
            end as {self.month_field_alias}
            """
        return select_time_yoy_item, return_or_append
        
    @judge_return_or_append
    def gen_select_field_month_format(self, return_or_append: str = 'a') -> Optional[str]:
        """
        生成月份日期字段
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        month_format_item = f"(cast(year({self.time_field}) as varchar) || '-' ||  substring('0' + cast(month({self.time_field}) as varchar), -2, 2)) as {self.month_field_alias}"
        return month_format_item, return_or_append
    
    @judge_return_or_append
    def gen_select_field_month_format_lm(self, return_or_append: str = 'a') -> Optional[str]:
        """
        生成月份日期字段+1个月
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        month_format_item = f"(cast(year(timestampadd(month, 1, {self.month_field_alias})) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(month, 1, {self.month_field_alias})) as varchar), -2, 2)) as {self.month_field_alias}"
        return month_format_item, return_or_append
    
    @judge_return_or_append
    def gen_select_field_month_format_ly(self, return_or_append: str = 'a') -> Optional[str]:
        """
        生成月份日期字段+1年
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        month_format_item = f"(cast(year(timestampadd(year, 1, {self.month_field_alias})) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(year, 1, {self.month_field_alias})) as varchar), -2, 2)) as {self.month_field_alias}"
        return month_format_item, return_or_append
    
    @judge_return_or_append
    def gen_select_field_month_format_lm_ly(self, return_or_append: str = 'a') -> Optional[str]:
        """
        生成月份日期字段+1个月+1年
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        month_format_item = f"(cast(year(timestampadd(month, 13, {self.month_field_alias})) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(month, 13, {self.month_field_alias})) as varchar), -2, 2)) as {self.month_field_alias}"
        return month_format_item, return_or_append
        
    @judge_return_or_append
    def gen_select_field_case_when(self, val_lst: list, case_when_field: str, case_when_alias: str = None, return_or_append: str = 'a') -> Optional[str]:
        """
        生成case when语句（这里只设计了某一字段等于某一值的when语句，如果需要>=，<=，可以做对应的修改）
        :param val_lst: case when的值列表
        :param case_when_field: case when，并且要group by的字段
        :param case_when_alias: case when字段别名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        if case_when_alias is None:
            case_when_alias = case_when_field + '_对比'
            
        val_alias_suffix = '_客群'
            
        case_when_item = f"\ncase {case_when_field}"
        for val in val_lst:
            if val == 'other':
                pass
            else:
                case_when_item += f"\nwhen {val} then '{val}{val_alias_suffix}'"
        if 'other' in val_lst:
            case_when_item += f"\nelse '其他_客群'"
        case_when_item += f"\nend as {case_when_alias}"
        return case_when_item, return_or_append
    
class SQLWhereWidgetGenerator(GeneratorTools):
    """
    生成SQL语句中的where部分
    """
    def __init__(self, *args):
        GeneratorTools.__init__(self, *args)
        
    @judge_return_or_append
    def gen_where_cond_time_range(self, time_cond_type: str, return_or_append: str = 'a') -> Optional[str]:
        """
        生成时间范围where条件, 返回语句或添加在where_conds列表中
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年ytd', '过去K个月'等
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        :return: 时间范围where条件文本
        """
        if time_cond_type in ['某月', '某月的上月']:
            date = self.date
        else:
            date = None
        time_cond = self.gen_cond_time_range(time_cond_type=time_cond_type, date=date)
        return time_cond, return_or_append
    
    @judge_return_or_append      
    def gen_where_cond_existing(self, field: str, time_cond_type: str, return_or_append: str = 'a'):
        """
        生成'存量'where条件
        :param field: 字段
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年ytd', '过去K个月'等
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        time_cond_type_lp = self.mom_tp_lp_type_corr_dict[time_cond_type]
        time_where_cond = self.gen_where_cond_time_range(time_cond_type_lp, 'r')
        # 生成where条件
        existing_where_cond = \
            f"""{field} in (
                select {field}
                from {self.table_name}
                where {time_where_cond})"""
        return existing_where_cond, return_or_append
    
    @judge_return_or_append  
    def gen_where_cond_new(self, field: str, time_cond_type: str, return_or_append: str = 'a'):
        """
        生成'新增'where条件
        :param field: 字段
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年ytd', '过去K个月'等
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        time_cond_type_lp = self.mom_tp_lp_type_corr_dict[time_cond_type]
        time_where_cond = self.gen_where_cond_time_range(time_cond_type_lp, 'r')
        # 生成where条件
        new_where_cond = \
            f"""{field} not in (
                select {field}
                from {self.table_name}
                where {time_where_cond})"""
        return new_where_cond, return_or_append
    
    @judge_return_or_append 
    def gen_where_cond_lost(self, field: str, time_cond_type: str, return_or_append: str = 'a'):
        """
        生成'流失'where条件
        :param field: 字段
        :param time_cond_type: 时间条件的类型, 例如'某月', '某月的上月', '本月', '上月', '今年', '去年ytd', '过去K个月'等
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        time_where_cond = self.gen_where_cond_time_range(time_cond_type, 'r')
        # 生成where条件
        lost_where_cond = \
            f"""{field} not in (
                select {field}
                from {self.table_name}
                where {time_where_cond})"""
        return lost_where_cond, return_or_append
    
    @judge_return_or_append 
    def gen_where_dim_field_val(self, dim_field: str, dim_val: str, return_or_append: str = 'a'):
        """
        生成'{dim_field} = {dim_val}'where条件
        :param dim_field: 属性字段（维度字段）
        :param dim_val: 属性值（维度值）
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        where_cond_dim_equals_dim_val = f"{dim_field} = '{dim_val}'"
        return where_cond_dim_equals_dim_val, return_or_append

class SQLGroupByWidgetGenerator(GeneratorTools):
    """
    生成SQL语句中的groupby部分
    """
    def __init__(self, *args):
        GeneratorTools.__init__(self, *args)
    
    @judge_return_or_append
    def gen_groupby_field(self, field: str, return_or_append: str = 'a'):
        """
        生成group by语句
        :param field: 字段名
        :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
        """
        groupby_field = f"{field}"
        return groupby_field, return_or_append

class SQLHavingWidgetGenerator(GeneratorTools):
    """
    生成SQL语句中的having部分
    """
    def __init__(self, *args):
        GeneratorTools.__init__(self, *args)
        
    @judge_return_or_append
    def gen_having_is_not_none(self, field: str, return_or_append: str = 'a'):
        """
        生成group by语句
        """
        having_is_not_none = f"{field} is not null"
        return having_is_not_none, return_or_append


# class SQLOtherWidgetGenerator(GeneratorTools):
#     """
#     生成SQL语句中的各个部分
#     """
#     def __init__(self, *args):
#         GeneratorTools.__init__(self, *args)
        
#     @judge_return_or_append
#     def gen_other_syntax_group_by(self, field: str, return_or_append: str = 'a'):
#         """
#         生成指定field的group by
#         :param field: 指定的字段
#         :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
#         """
#         added_toggle = False
#         for syntax in self.other_syntax:
#             if 'group by' in syntax:
#                 self.other_syntax.remove(syntax)
#                 other_syntax = f"{syntax}, {field}"
#                 added_toggle = True
#         if added_toggle == False:
#             other_syntax = f"group by {field}"
#         return  other_syntax, return_or_append
        
#     @judge_return_or_append
#     def gen_other_syntax_for_case_when(self, return_or_append: str = 'a'):
#         """
#         生成case when语句对应的group by和having
#         :param return_or_append: 值为'r'，则返回； 值为'a'，则追加
#         """
#         groupby_syntax = self.gen_other_syntax_group_by(self.month_field_alias, 'r')
#         other_syntax = \
#             f"""
#             {groupby_syntax}
#             having {self.month_field_alias} is not null
#             """
#         return other_syntax, return_or_append
        

class SQLGenerator(SQLSelectWidgetGenerator, 
                   SQLWhereWidgetGenerator, 
                   SQLGroupByWidgetGenerator, 
                   SQLHavingWidgetGenerator):
    """
    解析metric得到"以事件为导向的框架", EOF(Event-Oriented Framework)
    EOF: [业务对象A的属性, 业务对象B的属性, 事件, 时间范围, 统计方法]
    """
    def __init__(self, 
                 table_name: str,
                 group: str,
                 metric: str,
                 date: datetime.date, 
                 sub_anlys: Optional[str] = None,
                 dim_A: Optional[str] = None,
                 dim_val_A: Optional[str] = None, 
                 dim_B: Optional[str] = None,
                 dim_val_B: Optional[str] = None, 
                 k: Optional[int] =None,
                 desig_cust: Optional[str] = None):
        """
        :param table_name: 表名
        :param group: 组别  例如: '收入分析'、'客户数分析'
        :param metric: 指标  例如: '（按月）收入'、'（按月）存量客户数'
        :param date: 日期 例如: datetime.date(2021, 7, 1)
        :param sub_anlys: 子分析 对于部分analysis group起作用，例如“客群分维度分析”中的“收入分析”就是一个sub_anlys
        :param dim_A: 业务对象A维度（替换待定属性） 包含单一维度和双维度情况，其中双维度中两个维度之间用“-”连接，例如“省份-行业”
        :param dim_val_A: 业务对象A维度值（替换待定值），在双维度情况下，两个维度值之间用“-”连接，例如“上海-交通物流行业”
        :param dim_B: 业务对象B维度（替换待定属性） 包含单一维度和双维度情况，其中双维度中两个维度之间用“-”连接，例如“客户等级-产品名”
        :param dim_val_B: 业务对象B维度值（替换待定值），在双维度情况下，两个维度值之间用“-”连接，例如“0-某产品”
        :param k: 过去K个月
        :param desig_cust: 指定客户，为了'关键客群排名分析'中'客户等级'属性需要指定其'待定值'
        """
        SQLSelectWidgetGenerator.__init__(self, table_name, group, metric, date, sub_anlys, dim_A, dim_val_A, dim_B, dim_val_B, k, desig_cust)
        SQLWhereWidgetGenerator.__init__(self, table_name, group, metric, date, sub_anlys, dim_A, dim_val_A, dim_B, dim_val_B, k, desig_cust)
        SQLGroupByWidgetGenerator.__init__(self, table_name, group, metric, date, sub_anlys, dim_A, dim_val_A, dim_B, dim_val_B, k, desig_cust)
        SQLHavingWidgetGenerator.__init__(self, table_name, group, metric, date, sub_anlys, dim_A, dim_val_A, dim_B, dim_val_B, k, desig_cust)
        
        self.parse_framework()
        
    def parse_metric(self):
        """
        解析metric得到EOF
        """
        if self.group == '客群分维度分析':
            framework = ANALYSIS_DICT[self.group][self.sub_anlys][self.metric]
        else:
            framework = ANALYSIS_DICT[self.group][self.metric]
            
        if isinstance(framework, str) and '-' in framework:
            links = re.split('-', framework)
            if len(links) == 2:
                linked_group, linked_metric = links
                framework = ANALYSIS_DICT[linked_group][linked_metric]
            elif len(links) == 3:
                linked_group, linked_sub_anlys, linked_metric = links
                framework = ANALYSIS_DICT[linked_group][linked_sub_anlys][linked_metric]
            
        return framework
    
    def parse_framework(self):
        """
        解析EOF，生成sql参数
        """
        # 获取EOF
        framework = self.parse_metric()
        self.framework = framework
        
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
        
        # 去除数据中的无用信息
        remove_tbd_info = lambda x: x.replace('(TBD)', '') if '(TBD)' in x else x
        self.bo_A_prop = remove_tbd_info(self.bo_A_prop)
        self.bo_A_prop_value = remove_tbd_info(self.bo_A_prop_value)
        self.bo_B_prop_value = remove_tbd_info(self.bo_B_prop_value)
        
    def parse_event(self):
        """
        解析事件（弃用）
        """
        pass
    
    def parse_time(self):
        """
        解析时间
        """
        if self.time_category in ['某月', 
                                  '去年某月',
                                  '某月的上月', 
                                  '今年', 
                                  '去年ytd',
                                  '去年12月', 
                                  '本月',
                                  '去年本月',
                                  '上月',
                                  '去年上月']:
            self.gen_where_cond_time_range(self.time_category)
        elif self.time_category == '某月+同比':
            # 添加select 和 other
            self.gen_select_field_time_yoy('某月')
            self.gen_groupby_field(self.month_field_alias)
            self.gen_having_is_not_none(self.month_field_alias)
            # self.gen_other_syntax_for_case_when()
        elif self.time_category == '今年+同比':
            self.gen_select_field_time_yoy('今年')
            self.gen_groupby_field(self.month_field_alias)
            self.gen_having_is_not_none(self.month_field_alias)
        elif self.time_category in ['今年+每月', 
                                    '最近连续月份+每月', 
                                    '过去K个月+每月',
                                    '去年过去K个月+每月']:
            self.gen_where_cond_time_range(self.time_category)
            if self.time_category == '去年过去K个月+每月':
                self.gen_select_field_month_format_ly()
            else:
                self.gen_select_field_month_format()
            self.gen_groupby_field(self.month_field_alias)
        # elif self.time_category == '本月+同比':
        #     # 直接写一个self.sql
        #     # TODO: 应该可以跟下面的判断合并处理，可以优化(已经尝试优化)
        #     # 今年 子sql
        #     sql_generator_ty = self.gen_sub_sql_generator()
        #     sql_generator_ty.time_category = '本月'
        #     sub_sql_ty = sql_generator_ty.integrating_sql()
            
        #     # 去年 子sql
        #     sql_generator_ly = self.gen_sub_sql_generator()
        #     sql_generator_ly.time_category = '去年本月'
        #     sub_sql_ly = sql_generator_ly.integrating_sql()
            
        #     # 整合
        #     sql_lst = [sub_sql_ty, sub_sql_ly]
        #     self.sql = '\nunion\n'.join(sql_lst)
        elif self.time_category in ['过去K个月+每月+同比', '最近连续月份+每月+同比', '本月+同比']:
            # TODO: '过去K个月+每月+同比' 和 '最近连续月份+每月+同比'只能处理main_field为all时的情况
            # TODO: 不能处理main_field为存量/新增/流失等特殊情况
            # TODO: 可以尝试'本月+同比'的逻辑进行优化
            # 直接写一个self.sql
            # 今年 子sql
            sub_sql_alias_ty = '今年'
            sql_generator_ty = self.gen_sub_sql_generator()
            sql_generator_ty.metric = sub_sql_alias_ty
            if self.time_category == '本月+同比':
                sql_generator_ty.time_category = '本月'
                sql_generator_ty.gen_select_field_month_format_lm() if self.A_val[0] == '流失' else sql_generator_ty.gen_select_field_month_format()
                sql_generator_ty.gen_groupby_field(self.month_field_alias)
            else:
                sql_generator_ty.k = self.max_k if self.time_category == '最近连续月份+每月+同比' else self.k
                sql_generator_ty.time_category = '过去K个月+每月'
            sub_sql_ty = sql_generator_ty.integrating_sql()
  
            # 去年ytd 子sql
            sub_sql_alias_ly = '去年'
            sql_generator_ly = self.gen_sub_sql_generator()
            sql_generator_ly.metric = sub_sql_alias_ly
            if self.time_category == '本月+同比':
                sql_generator_ly.time_category = '去年本月'
                sql_generator_ly.gen_select_field_month_format_lm_ly() if self.A_val[0] == '流失' else sql_generator_ly.gen_select_field_month_format_ly()
                sql_generator_ly.gen_groupby_field(self.month_field_alias)
            else:
                sql_generator_ly.k = self.max_k if self.time_category == '最近连续月份+每月+同比' else self.k
                sql_generator_ly.time_category = '去年过去K个月+每月'
            sub_sql_ly = sql_generator_ly.integrating_sql()

            subsql_groupby_fields = sql_generator_ty.groupby_fields  # 子sql的group by fields，用sql_generator_ty和sql_generator_ly都可以
            # select部分
            select_fields = list(map(lambda field: f"t1.{field} as {field}", subsql_groupby_fields))
            select_fields.extend([sub_sql_alias_ty, sub_sql_alias_ly])
            select_segment = "select" + " " + ", ".join(select_fields)
            # join on的on部分
            if len(subsql_groupby_fields) == 1:
                on_segment = f"on t1.{subsql_groupby_fields[0]} = t2.{subsql_groupby_fields[0]}"
            else:
                on_items_t1 = list(map(lambda field: f"t1.{field}", subsql_groupby_fields))
                on_items_t2 = list(map(lambda field: f"t2.{field}", subsql_groupby_fields))
                on_segment = f"on concat({', '.join(on_items_t1)}) = concat({', '.join(on_items_t2)})"
            self.sql = \
                f"""
                {select_segment}
                from
                ({sub_sql_ty}) t1
                join
                ({sub_sql_ly}) t2
                {on_segment}
                """
        elif self.time_category in ['过去K个月+每月(存量)', 
                                    '过去K个月+每月(新增)',
                                    '过去K个月+每月(流失)']:
            # 直接写一个self.sql
            sql_lst = []
            td = datetime.date.today()
            for i in range(self.k + 1):
                # i月前
                date_i_month_ago = td - relativedelta(months=i)
                date_i_sql_generator = self.gen_sub_sql_generator()
                date_i_sql_generator.bo_A_prop_value = self.bo_A_prop_value  # * 这个处理是因为'关键客群发展分析'-'关键客群过去K个月存量、新增、流失客户占比'需要修改prop_value
                date_i_sql_generator.time_category = '某月'
                date_i_sql_generator.date = date_i_month_ago
                if self.time_category == '过去K个月+每月(流失)':
                    date_i_sql_generator.gen_select_field_month_format_lm()
                else:
                    date_i_sql_generator.gen_select_field_month_format()
                date_i_sql_generator.gen_groupby_field(self.month_field_alias)
                sub_sql = date_i_sql_generator.integrating_sql()
                sql_lst.append(sub_sql)
            self.sql = '\nunion\n'.join(sql_lst)
            
    def parse_expression(self):
        """
        解析统计方法
        """
        # 根据event判断        
        if self.expression == 'sum':
            self.gen_select_field_sum(field=EVENT_FIELD_DICT[self.measurement])
        elif self.expression == 'count distinct':
            self.gen_select_field_count_distinct(field=EVENT_FIELD_DICT[self.measurement])
        elif self.expression == 'sum+avg':
            # TODO: sum+avg和其他条件结合的各种情况应该还可以优化
            # 先配置main_field和dim_field
            self.parse_bo_A_prop()
            self.parse_bo_A_prop_val()
            self.parse_bo_B_prop()
            self.parse_bo_B_prop_val()
            
            if self.group == '客群分维度分析':
                # * sum+avg & '客群分维度分析'
                self.group = self.sub_anlys  # 为了gen_select_field_sum_avg可以正常运行，这里要修改group
                self.gen_select_field_sum_avg(groupby_main_field=self.main_field, groupby_dim_field=self.dim_field)
                
                self.gen_select_field(self.dim_field)
                self.gen_groupby_field(self.dim_field)
            elif (self.group == '关键客群收入分析') and (self.metric == '关键客群vs非关键客群：（按月）客单价'):
                # * sum+avg & '关键客群收入分析'-'关键客群vs非关键客群：（按月）客单价'
                # 类同parse_bo_A中的parse_vs函数
                case_when_field = self.dim_field  # case when的字段
                case_when_alias = case_when_field + '_对比'  # case when别名，例如customer_level_对比
                vs_prop_val = self.A_val[1]  # case when对应属性值
                vs_prop_val = re.search(r"\((.*)\)", vs_prop_val).group(1)  # 提取括号内的内容
                val_lst = re.split('\s+vs\s+', vs_prop_val)  # 分割
                # 生成外层case when
                self.gen_select_field_case_when(val_lst, case_when_field, case_when_alias)
                
                # avg+sum内层sql
                self.gen_select_field_sum_avg(groupby_main_field=self.main_field, groupby_dim_field=case_when_field, special_toggle=True)
                # 生成外层groupby
                self.gen_groupby_field(case_when_alias)
                # 生成外层having
                self.gen_having_is_not_none(case_when_alias)
            elif self.time_category == '过去K个月+每月':
                # * sum+avg & 过去K个月+每月
                # 生成外层月份alias
                self.gen_select_field(self.month_field_alias)
                # avg+sum内层sql
                self.gen_select_field_sum_avg(groupby_main_field=self.main_field)
                # 生成外层groupby
                self.gen_groupby_field(self.month_field_alias)
            else:
                self.gen_select_field_sum_avg(groupby_main_field=self.main_field)
                
            self.parse_bo_A = lambda: None
            self.parse_bo_B = lambda: None
            self.parse_time = lambda: None
        
    def parse_bo_A_prop(self) -> None:
        """
        解析业务对象A属性
        将bo_A_prop解析成A_field，结合输入参数dim_A从格式化文本解析成具体的属性列表
        e.g. 客户id+客户等级+/待定属性 -> [客户id, 客户等级, 待定属性] -> [客户id, 客户等级, 省份]
        """
        def sub_tbd_prop(prop_lst: list, dim_A: str) -> list:
            """
            substitute 'to be determined' property
            :param prop_lst: list of properties
            :param dim_A: dimension A
            """
            tbd_prop_desc = '待定属性'  # to be determined property description
            if tbd_prop_desc in prop_lst:
                # 存在待定属性
                if dim_A is None:
                    # dim_A为空时
                    prop_lst.remove(tbd_prop_desc)
                else:
                    # dim_A不为空
                    tbd_index = prop_lst.index(tbd_prop_desc)
                    if '-' not in dim_A:
                        # 一维下钻
                        prop_lst[tbd_index] = f'{dim_A}'
                    elif '-' in dim_A:
                        # 二维下钻
                        prop_lst[tbd_index: tbd_index + 1] = dim_A.split('-')
                return prop_lst
            else:
                return prop_lst
            
        bo_A_prop = self.bo_A_prop  # framework中'业务对象A属性'的值，例如'客户id+/待定属性'
        if '+' not in bo_A_prop and '+/' not in bo_A_prop:
            # 当只有一个固定的业务对象A属性时
            # 第一步：获得字段列表
            self.A_field = [BO_A_FIELD_DICT[bo_A_prop], ]  # 获得字段列表
        elif re.search(r"\+(?=[^/])", bo_A_prop) is not None and '+/' in bo_A_prop:
            # 当既有多个固定的业务对象A属性，又有可选的业务对象A属性时
            prop_lst = re.split('[\+|\+/]', bo_A_prop)
            prop_lst = self.drop_empty_elem(prop_lst)
            # 第一步：根据输入的dim_A将待定属性替换成具体字段
            prop_lst = sub_tbd_prop(prop_lst, self.dim_A)
            # 第二部：生成对应的字段列表
            self.A_field = [BO_A_FIELD_DICT[prop] for prop in prop_lst]
        elif '+/' in bo_A_prop:
            # 当允许有多个可选的业务对象A属性时    
            prop_lst = re.split('\+/', bo_A_prop)  # 分割原始属性描述
            prop_lst = self.drop_empty_elem(prop_lst)
            # 第一步：根据输入的dim_A将待定属性替换成具体字段
            prop_lst = sub_tbd_prop(prop_lst, self.dim_A)
            # 第二步：生成对应的字段列表
            self.A_field = [BO_A_FIELD_DICT[prop] for prop in prop_lst]  # 获得字段列表，如province_name等
        elif '+' in bo_A_prop:
            # 有多个固定的业务对象A属性时
            prop_lst = re.split('\+', bo_A_prop)
            prop_lst = self.drop_empty_elem(prop_lst)
            self.A_field = [BO_A_FIELD_DICT[prop] for prop in prop_lst]  # 获得字段列表，如province_name等
        
        # 特殊步骤：根据prop_lst长度，为sum+avg生成main field和dim field
        if self.expression == 'sum+avg':
            if len(self.A_field) == 1:
                # 特殊为sum+avg生成为main field
                self.main_field = self.A_field[0]
            elif len(self.A_field) == 2:
                # 特殊为sum+avg划分为main field和dim field
                self.main_field = self.A_field[0]
                self.dim_field = self.A_field[1]
    
    def parse_bo_A_prop_val(self) -> None:
        '''
        解析业务对象A属性值
        新增+0+/待定值 -> [新增, 0, 待定值]
        '''
        bo_A_prop_value = self.bo_A_prop_value
        # 解析业务对象A属性值
        if '+' not in bo_A_prop_value and '+/' not in bo_A_prop_value:
            # 当只有一个固定的业务对象A属性值时
            self.A_val = [bo_A_prop_value, ]
        elif re.search(r"\+(?=[^/])", bo_A_prop_value) is not None and '+/' in bo_A_prop_value:
            # 当既有多个固定的业务对象A属性值，又有可选的业务对象A属性值时
            self.A_val = re.split('[\+|\+/]', bo_A_prop_value)
            self.A_val = self.drop_empty_elem(self.A_val)
            if len(self.A_field) == 2:
                # 有两个A字段
                self.A_val = [self.A_val[0], self.A_val[1]]
            elif len(self.A_field) == 3:
                # 有三个A字段
                pass  # 目前业务来说，这种情况不用其余处理
        elif '+/' in bo_A_prop_value:
            # 当允许有多个可选的业务对象A属性值时
            self.A_val = re.split('\+/', bo_A_prop_value)
            self.A_val = self.drop_empty_elem(self.A_val)
            if len(self.A_field) == 1:
                # 只有一个A字段（也可以设计成更一般性的，判断A_field和A_val的长度是否相等）
                self.A_val = [self.A_val[0], ]  # 丢弃多余的字段值
            elif len(self.A_field) == 2:
                # 有两个A字段
                pass  # 目前业务来说，这种情况不用其余处理
                
                # if self.expression == 'sum+avg':
                #     # 特殊准备一个groupby field
                #     self.groupby_field_for_sum_avg = self.A_val[1]
        elif '+' in bo_A_prop_value:
            # 当有多个固定的业务对象A属性值时
            self.A_val = re.split('\+', bo_A_prop_value)
            self.A_val = self.drop_empty_elem(self.A_val)
            if len(self.A_field) == 2:
                # 有两个A字段
                pass  # 目前业务来说，这种情况不用其余处理
    
    # TODO 优化思路        
    # ? parse_bo_A_prop_val的设计有一个想法，就是效仿parse_bo_A_prop，在这个方法内部就替换掉待定值
    # ? 但是这样写会导致下钻维度数量和下钻属性值的顺序没法确定，还没想到如何进行处理
    # def parse_bo_A_prop_val(self) -> None:
    #     """
    #     解析业务对象A属性值
    #     将bo_A_prop_val解析成A_val，结合输入参数dim_A_val从格式化文本解析成具体的属性值列表
    #     e.g. 存量+0+/待定值 -> [存量, 0, 待定值] -> [存量, 0, 上海]
    #     """
    #     def sub_tbd_prop_val(prop_val_lst: list, dim_val_A: str) -> list:
    #         """
    #         substitute 'to be determined' property
    #         :param prop_val_lst: list of properties
    #         :param dim_val_A: dimension value A
    #         """
    #         tbd_prop_val_desc = '待定值'  # to be determined property value description
    #         if tbd_prop_val_desc in prop_val_lst:
    #             # 存在待定值
    #             if dim_val_A is None:
    #                 # dim_val_A为空时
    #                 prop_val_lst.remove(tbd_prop_val_desc)
    #             else:
    #                 # dim_val_A不为空
    #                 tbd_index = prop_val_lst.index(tbd_prop_val_desc)
    #                 if '-' not in dim_val_A:
    #                     # 一维下钻
    #                     prop_val_lst[tbd_index] = f'{dim_val_A}'
    #                 elif '-' in dim_val_A:
    #                     # 二维下钻
    #                     prop_val_lst[tbd_index: tbd_index + 1] = dim_val_A.split('-')
    #             return prop_val_lst
    #         else:
    #             return prop_val_lst
        
    #     bo_A_prop_val = self.bo_A_prop_value  # framework中'业务对象A属性值'的值，例如'存量+/groupby'
    #     if '+' not in bo_A_prop_val and '+/' not in bo_A_prop_val:
    #         # 当只有一个固定的业务对象A属性值时
    #         self.A_val = [bo_A_prop_val, ]
    #     elif re.search(r"\+(?=[^/])", bo_A_prop_val) is not None and '+/' in bo_A_prop_val:
    #         # 当既有多个固定的业务对象A属性值，又有可选的业务对象A属性值时
    #         pass
    #     elif '+/' in bo_A_prop_val:
    #         # 当允许有多个可选的业务对象A属性值时
    #         prop_val_lst = re.split('\+/', bo_A_prop_val)
    #         prop_val_lst = self.drop_empty_elem(prop_val_lst)
    #         # 第一步：根据输入的dim_A_val将待定属性值替换成具体字段值
    #         prop_val_lst = sub_tbd_prop_val(prop_val_lst, self.dim_A)
    #         # 第二步：定义字段值列表（不是属性值，属性值是指'待定值'这些，字段值是替换后了的值）
    #         self.A_val = prop_val_lst
            
    #         # if len(self.A_field) == 1:
    #         #     # 只有一个A字段/属性（也可以设计成更一般性的，判断A_field和A_val的长度是否相等）
    #         #     self.A_val = [self.A_val[0], ]  # 丢弃多余的字段值
    #         # elif len(self.A_field) == 2:
    #         #     # 有两个A字段/属性
    #         #     pass  # 目前业务来说，这种情况不用其余处理
    #     elif '+' in bo_A_prop_val:
    #         # 当有多个固定的业务对象A属性值时
    #         prop_val_lst = re.split('\+', bo_A_prop_val)
    #         prop_val_lst = self.drop_empty_elem(prop_val_lst)
    #         self.A_val = prop_val_lst
                
    def parse_bo_A(self) -> None:
        """
        解析业务对象A
        """
        self.parse_bo_A_prop()
        self.parse_bo_A_prop_val()
        
        def parse_groupby(groupby_field: str):
            """
            解析业务对象A属性值的特殊值:groupby, 生成对应的子句
            :param groupby_field: group by的字段
            """
            self.gen_select_field(groupby_field)
            self.gen_groupby_field(groupby_field)
        
        def parse_undetermined_val():
            """
            解析业务对象A属性值的特殊值:待定值, 生成对应的子句
            """
            if '-' not in self.dim_A:
                # 单一维度下钻
                dim_field_A = BO_A_FIELD_DICT[self.dim_A]
                self.gen_where_dim_field_val(dim_field_A, self.dim_val_A)
            elif '-' in self.dim_A:
                # 双维度下钻
                cust_type_dim, anot_dim = re.split('-', self.dim_A)  # 分别是 客户类型维度 和 另一个维度
                cust_type_dim_field, anot_dim_field = BO_A_FIELD_DICT[cust_type_dim], BO_A_FIELD_DICT[anot_dim]
                cust_type_dim_val, anot_dim_val = re.split('-', self.dim_val_A)  # 分别是 客户类型维度值 和 另一个维度值
                self.gen_where_dim_field_val(cust_type_dim_field, cust_type_dim_val)
                self.gen_where_dim_field_val(anot_dim_field, anot_dim_val)
       
        def parse_vs(vs_field: str, vs_prop_val: str):
            """
            解析业务对象A属性值的特殊值:(包含vs的值), 生成对应的子句
            :param vs_field: 对比的属性对应的字段, 例如customer_level
            :param vs_prop_val: 对比的属性值, 例如(0 vs other), (0 vs 1 vs 2 vs 3)
            """
            case_when_field = vs_field  # case when的字段
            case_when_alias = case_when_field + '_对比'  # case when别名，例如customer_level_对比
            vs_prop_val = re.search(r"\((.*)\)", vs_prop_val).group(1)  # 提取括号内的内容
            val_lst = re.split('\s+vs\s+', vs_prop_val)  # 分割
            self.gen_select_field_case_when(val_lst, case_when_field, case_when_alias)
            self.gen_groupby_field(case_when_alias)
            self.gen_having_is_not_none(case_when_alias)  # 如果case when中没有定义else，将默认返回null，所以要去掉null
                
        # 解析self.A_val
        main_field_val = self.A_val[0]  # main field的值, 在此业务中，main field为:客户id
        if main_field_val == 'all':
            # 如果main field值为特殊值: all
            # TODO: 可以优化对self.A_val的判断逻辑，目前来说这些判断还是太局限了，不够泛化
            if len(self.A_val) == 1:
                # 如果对象A属性值只有一个值
                pass
            elif len(self.A_val) == 2:
                # 如果对象A属性值有两个值
                if self.A_val[1] == 'groupby':
                    # 如果第二个值是特殊值: groupby
                    groupby_field = self.A_field[1]
                    parse_groupby(groupby_field)
                elif self.A_val[1] == '待定值':
                    # 如果第二个值是特殊值: 待定值
                    parse_undetermined_val()
                elif 'vs' in self.A_val[1]:
                    # 如果第二个值是特殊值: (包含vs的值)
                    vs_field = self.A_field[1]  # vs的属性对应的字段，例如customer_level
                    vs_prop_val = self.A_val[1]  # vs的属性值，例如(0 vs other), (0 vs 1 vs 2 vs 3)
                    parse_vs(vs_field, vs_prop_val)
                else:
                    # 如果第二个值是普通值
                    self.gen_where_dim_field_val(self.A_field[1], self.A_val[1])  # 生成where dim_field=dim_val的子句
            elif len(self.A_val) == 3:
                # 如果对象A属性值有三个值
                # 判断第二个值
                if self.A_val[1] == '待定值':
                    # 如果第二个值是特殊值：待定值（它对应的属性不应该为'待定属性'）
                    # 目前这种情况只出现在'关键客群排名分析'中，比较特殊
                    self.gen_where_dim_field_val(self.A_field[1], self.desig_cust)  # * desig_cust是特殊指定的客群等级值,只针对目前的业务
                else:
                    # 如果第二个值是普通值
                    self.gen_where_dim_field_val(self.A_field[1], self.A_val[1])  # TODO: 可以优化这里的逻辑
                # 判断第三个值
                if self.A_val[2] == '待定值':
                    parse_undetermined_val()
                elif self.A_val[2] == 'groupby':
                    groupby_field = self.A_field[2]
                    parse_groupby(groupby_field)
                else:
                    # 目前还没有vs等业务解析需求
                    pass
        elif main_field_val in ['存量', '新增', '流失']:
            # 如果main field值为特殊值: 存量/新增/流失
            # 定义函数调用字典
            val_func_dict = {'存量': self.gen_where_cond_existing,
                             '新增': self.gen_where_cond_new,
                             '流失': self.gen_where_cond_lost}
            # 生成特殊值对应的where子句
            if self.time_category in self.mom_tp_lp_type_corr_dict.keys():
                # 如果时间类型在tp_lp_type_corr_dict的键中
                # （这里时间类型是指framework中'时间'key的值，如'某月', '今年'）
                # 【为了确保下面where生成函数内部可运行，若key中没有，要需要的时间类型，可以自行添加】
                val_func_dict[main_field_val](self.A_field[0], self.time_category)  # 调用对应的where生成函数
            # 生成一般子句
            if len(self.A_val) == 1:
                pass
            elif len(self.A_val) == 2:
                if self.A_val[1] == 'groupby':
                    # 如果第二个值是特殊值: groupby
                    groupby_field = self.A_field[1]
                    parse_groupby(groupby_field)
                elif self.A_val[1] == '待定值':
                    # 如果第二个值是特殊值: 待定值
                    parse_undetermined_val()
                elif 'vs' in self.A_val[1]:
                    # 如果第二个值是特殊值: (包含vs的值)
                    vs_field = self.A_field[1]  # vs的属性对应的字段，例如customer_level
                    vs_prop_val = self.A_val[1]  # vs的属性值，例如(0 vs other), (0 vs 1 vs 2 vs 3)
                    parse_vs(vs_field, vs_prop_val)
                else:
                    # 如果第二个值是普通值
                    self.gen_where_dim_field_val(self.A_field[1], self.A_val[1])  # 生成where dim_field=dim_val的子句
            elif len(self.A_val) == 3:
                # 如果对象A属性值有三个值
                # 判断第二个值
                if self.A_val[1] == '待定值':
                    # 如果第二个值是特殊值：待定值（它对应的属性不应该为'待定属性'）
                    # 目前这种情况只出现在'关键客群排名分析'中，比较特殊
                    self.gen_where_dim_field_val(self.A_field[1], self.desig_cust)  # * desig_cust是特殊指定的客群等级值,只针对目前的业务
                else:
                    # 如果第二个值是普通值
                    self.gen_where_dim_field_val(self.A_field[1], self.A_val[1])  # TODO: 可以优化这里的逻辑
                # 判断第三个值
                if self.A_val[2] == '待定值':
                    parse_undetermined_val()
                elif self.A_val[2] == 'groupby':
                    groupby_field = self.A_field[2]
                    parse_groupby(groupby_field)
                else:
                    # 目前还没有vs等业务解析需求
                    pass
            if self.time_category in ['过去K个月+每月']:
                # 特殊值为存量/新增/流失情况下，遇到特殊时间类型，要进行特殊处理（优先级高）
                self.time_category = self.time_category + f'({self.A_val[0]})'  # 时间类型后添加标签: 存量/新增/流失
            elif self.time_category == '本月+同比':
                # 这种情况会在parse_time中处理，这里pass，且不需要对流失进行时间替换
                pass
            elif main_field_val == '流失':
                # 特殊值为流失情况下，要对时间类型进行修改（优先级低）
                self.time_category = self.mom_tp_lp_type_corr_dict[self.time_category]
        elif main_field_val == '净增':
            # 清空sql语句container
            self.select_fields = []
            self.where_conds = []
            self.groupby_fields = []
            self.having_conds = []
            
            # 直接写一个sql
            # 新增
            new_cust_sql_generator = self.gen_sub_sql_generator()
            new_cust_sql_generator.bo_A_prop_value = '新增' + re.search(r'净增(.*)', self.bo_A_prop_value).group(1)
            if self.time_category == '最近连续月份+每月':
                new_cust_sql_generator.k = self.max_k
                new_cust_sql_generator.time_category = '过去K个月+每月'
            elif self.time_category == '过去K个月+每月':
                new_cust_sql_generator.k = self.k
            new_cust_sql = new_cust_sql_generator.integrating_sql()
            new_cust_sql = re.sub(f"\"{self.metric}\"", "新增", new_cust_sql)
            # 流失
            lost_cust_sql_generator = self.gen_sub_sql_generator()
            lost_cust_sql_generator.bo_A_prop_value = '流失' + re.search(r'净增(.*)', self.bo_A_prop_value).group(1)
            if self.time_category == '最近连续月份+每月':
                lost_cust_sql_generator.k = self.max_k
                lost_cust_sql_generator.time_category = '过去K个月+每月'
            elif self.time_category == '过去K个月+每月':
                lost_cust_sql_generator.k = self.k
            lost_cust_sql = lost_cust_sql_generator.integrating_sql()
            lost_cust_sql = re.sub(f"\"{self.metric}\"", "流失", lost_cust_sql)
            
            # 整合sql
            self.sql = \
                f"""
                select t1.月份 as 月份, 新增, 流失
                from 
                ({new_cust_sql}) t1
                join
                ({lost_cust_sql}) t2
                on t1.月份 = t2.月份
                order by 月份
                """
            
            # 使本层剩下的解析失效
            self.parse_bo_B = lambda: None
            self.parse_time = lambda: None
        elif main_field_val == '[存量, 新增, 流失]':
            # 清空sql语句container
            self.select_fields = []
            self.where_conds = []
            self.groupby_fields = []
            self.having_conds = []
            
            # 直接写一个sql
            # 存量
            existing_cust_sql_generator = self.gen_sub_sql_generator()
            # existing_cust_sql_generator.bo_A_prop_value = '存量+/待定值'  # 不能带（TBD），因为实例化就已经解析过了
            existing_cust_sql_generator.bo_A_prop_value = '存量' + re.search(r'\](.*)', self.bo_A_prop_value).group(1)
            # existing_cust_sql_generator.gen_select_field(field = "'1'", alias='id')
            existing_cust_sql_generator.gen_select_field_month_format()
            existing_cust_sql = existing_cust_sql_generator.integrating_sql()
            existing_cust_sql = re.sub(f"\"{self.metric}\"", "存量", existing_cust_sql)
            # 新增
            new_cust_sql_generator = self.gen_sub_sql_generator()
            # new_cust_sql_generator.bo_A_prop_value = '新增+/待定值'
            new_cust_sql_generator.bo_A_prop_value = '新增' + re.search(r'\](.*)', self.bo_A_prop_value).group(1)
            # new_cust_sql_generator.gen_select_field(field = "'1'", alias='id')
            new_cust_sql_generator.gen_select_field_month_format()
            new_cust_sql = new_cust_sql_generator.integrating_sql()
            new_cust_sql = re.sub(f"\"{self.metric}\"", "新增", new_cust_sql)
            # 流失
            lost_cust_sql_generator = self.gen_sub_sql_generator()
            # lost_cust_sql_generator.bo_A_prop_value = '流失+/待定值'
            lost_cust_sql_generator.bo_A_prop_value = '流失' + re.search(r'\](.*)', self.bo_A_prop_value).group(1)
            # lost_cust_sql_generator.gen_select_field(field = "'1'", alias='id')
            lost_cust_sql_generator.gen_select_field_month_format_lm()
            lost_cust_sql = lost_cust_sql_generator.integrating_sql()
            lost_cust_sql = re.sub(f"\"{self.metric}\"", "流失", lost_cust_sql)
            
            # 整合sql
            self.sql = \
                f"""
                select t1.{self.month_field_alias} as {self.month_field_alias}, 存量, 新增, 流失
                from
                ({existing_cust_sql}) t1
                join
                ({new_cust_sql}) t2
                on t1.id = t2.id
                join
                ({lost_cust_sql}) t3
                on t2.id = t3.id
                """
                
            # 使本层剩下的解析失效
            self.parse_bo_B = lambda: None
            self.parse_time = lambda: None
    
    def parse_bo_B_prop(self) -> None:
        """
        解析业务对象B属性
        """
        # TODO: parsebo_B_prop, parse_bo_B_prop_val, parse_bo_B应该是A的一个子集，应该可以合并优化
        bo_B_prop = self.bo_B_prop
        if '+' not in bo_B_prop and '+/' not in bo_B_prop:  # 这个条件根据后面的业务情况可以修改，这里为了简便沿用了bo_A的逻辑
            # 当只有一个固定的业务对象B属性时
            self.B_field = [BO_B_FIELD_DICT[bo_B_prop], ]
            
            if (self.dim_B is not None) and (self.expression == 'sum+avg'):
                    # 特殊为sum+avg定义dim field
                    self.dim_field = self.B_field[0]
    
    def parse_bo_B_prop_val(self) -> None:
        """
        解析业务对象B属性值
        """
        bo_B_prop_value = self.bo_B_prop_value
        if '/' not in bo_B_prop_value:
            self.B_val = [bo_B_prop_value, ]
        elif '/' in bo_B_prop_value:
            self.B_val = re.split('/', bo_B_prop_value)
            self.B_val = self.drop_empty_elem(self.B_val)
                
    def parse_bo_B(self) -> None:
        """
        解析业务对象B
        """
        self.parse_bo_B_prop()
        self.parse_bo_B_prop_val()
        
        # 解析self.B_val
        if self.B_val[0] == 'all':
            if len(self.B_val) == 1:
                pass
            elif len(self.B_val) == 2:
                if (self.dim_B is not None) and (self.B_val[1] == 'groupby'):
                    groupby_field = self.B_field[0]
                    self.gen_select_field(groupby_field)
                    self.gen_groupby_field(groupby_field)
                elif (self.dim_B is not None) and (self.B_val[1] == '待定值'):
                    if '-' not in self.dim_B:
                        # 一维下钻
                        dim_field_B = BO_B_FIELD_DICT[self.dim_B]
                        self.gen_where_dim_field_val(dim_field_B, self.dim_val_B)
                    elif '-' in self.dim_B:
                        # 二维下钻（目前业务其中一维是固定维度）
                        cust_type_dim, anot_dim = re.split('-', self.dim_B)  # 分别是 客户类型维度 和 另一个维度
                        cust_type_dim_field, anot_dim_field = BO_A_FIELD_DICT[cust_type_dim], BO_B_FIELD_DICT[anot_dim]  # * 分别来自A和B，e.g.现在业务需求下的：客户类型-产品名
                        cust_type_dim_val, anot_dim_val = re.split('-', self.dim_val_B)  # 分别是 客户类型维度值 和 另一个维度值
                        self.gen_where_dim_field_val(cust_type_dim_field, cust_type_dim_val)
                        self.gen_where_dim_field_val(anot_dim_field, anot_dim_val)
        
    def parse(self):
        self.parse_expression()  # P1 例如sum+avg就要先生成子sql再修改select
        self.parse_bo_A()  # P2 例如有些业务对象的分析会修改时间分析的参数
        self.parse_bo_B()
        self.parse_time()
        
    def integrating_sql(self):
        """
        整合sql
        """
        self.parse()
        
        if hasattr(self, 'sql'):
            self.sql = self.remove_blank_space(self.sql)
            return self.sql
        else:
            space = ' '
            select_segment = 'select' + space + ', '.join(self.select_fields)
            from_segment = 'from' + space + self.table_name
            where_segment = 'where' + space + ' and '.join(self.where_conds) if len(self.where_conds) != 0 else ''
            groupby_segment = "group by" + space + ', '.join(self.groupby_fields) if len(self.groupby_fields) != 0 else ''
            having_segment = "having" + space + ' and '.join(self.having_conds) if len(self.having_conds) != 0 else ''
            # other_segment = '\n'.join(self.other_syntax)
            # sql = f"{select_segment}\n{from_segment}\n{where_segment}\n{other_segment}"
            self.sql = f"{select_segment}\n{from_segment}\n{where_segment}\n{groupby_segment}\n{having_segment}"
            self.sql = self.remove_blank_space(self.sql)
            return self.sql
        

# def load_matching_data():
#     """
#     从数据文件中加载metric-EOF的匹配数据
#     """
#     field_data_file = open('./data/field_data.yaml', 'r', encoding='utf-8')
#     analysis_data_file = open('./data/analysis_data.yaml', 'r', encoding='utf-8')
#     field_dict = yaml.load(field_data_file, Loader=Loader)  # field_dict 属性:属性名
#     event_field_dict = field_dict['事件属性']
#     bo_A_field_dict = field_dict['业务对象A属性']
#     bo_B_field_dict = field_dict['业务对象B属性']
#     analysis_dict = yaml.load(analysis_data_file, Loader=Loader)  # analysis_dict 组别:指标:EOF
#     globals()["event_field_dict"] = event_field_dict
#     globals()["bo_A_field_dict"] = bo_A_field_dict
#     globals()["bo_B_field_dict"] = bo_B_field_dict
#     globals()["analysis_dict"] = analysis_dict

# def get_sql():
#     """
#     （弃用）
#     Step1: 根据ParseMetrics类解析metric得到EOF(Event-Oriented Framework)
#     Step2: 根据EOF变量和SQLGenerator类生成SQL语句
#     """
#     pass

__all__ = list(filter(lambda var: not var.startswith('_'), dir()))

if __name__ == "__main__":
    # # load matching data（在file开头写了，弃用此函数）
    # load_matching_data()
    
    # set test params
    table_name = 'data'
    group = '排名分析'
    metric = '（按月）流失客户收入'
    date = datetime.date(2022, 7, 1)
    sub_anlys = None
    dim_A = None
    dim_val_A = None
    dim_B = '产品名'  # 客户类型-产品名
    dim_val_B = '某产品'  # 政府-某产品
    k = 1
    desig_cust = '3'
    
    
    # generate sql
    sql_generator = SQLGenerator(table_name=table_name,
                                 group=group,
                                 metric=metric,
                                 date=date,
                                 sub_anlys=sub_anlys,
                                 dim_A = dim_A,
                                 dim_val_A=dim_val_A,
                                 dim_B = dim_B,
                                 dim_val_B = dim_val_B,
                                 k=k,
                                 desig_cust=desig_cust)
    
    sql = sql_generator.integrating_sql()
    print(sql)