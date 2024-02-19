import streamlit as st
import datetime
import calendar
from pyecharts import options as opts
from pyecharts.charts import Bar, Pie, Line
from streamlit_echarts import st_pyecharts
from typing import Union
import pandas as pd
import numpy as np
import re
from dateutil.relativedelta import relativedelta
from typing import Optional

    
class Display:
    month_date_alias = '月份'
    def __init__(self, coordinate: tuple, data: list) -> None:
        self.index, self.group, self.metric = coordinate
        self.display_params, self.df = data

    def format_metric(self, 
                      obj: Union[int, float, list], 
                    #   col: str = None, 
                      unit: str = '亿元') -> Union[int, float, list]:
        '''
        部分指标的格式化，目前转化单位为亿元（默认原数据单位为万元），保留两位小数
        '''
        round_num = 2

        if unit == '亿元':
            base_num = 1e8
        elif unit == '万元':
            base_num = 1e4
        elif unit == '元' or unit == '%' or unit == '个':
            base_num = 1

        if isinstance(obj, int) or isinstance(obj, float):
            return (obj / base_num).round(round_num)
        # elif isinstance(obj, pd.DataFrame):
        #     df = obj.copy()
        #     df[col] = (df[col] / base_num).round(round_num)
        #     return df
        elif isinstance(obj, list):
            lst = np.array(obj)
            lst = (lst / base_num).round(round_num).tolist()
            return lst
        
    def parse_date(self, date: datetime.date, k: Optional[int] = None) -> list:
        '''
        parse date to lists of formatted string
        if k is None, return month of last year and this year for yoy calculation
        else return k months ago and this month for trend calculation
        '''
        # 获取指定日期的今年月份和去年同期月份，例如：2022-01, 2021-01
        month_ty = '{}-{}'.format(date.year, str(date.month).rjust(2, '0'))
        month_ly = '{}-{}'.format(date.year - 1, str(date.month).rjust(2, '0'))
        if k:
            # 获取k个月前的月份和前一年同期月份，str，例如：2022-01, 2021-01
            date_k_month_ago = date - relativedelta(months=k)
            k_month_ago_ty = '{}-{}'.format(date_k_month_ago.year, str(date_k_month_ago.month).rjust(2, '0'))
            k_month_ago_ly = '{}-{}'.format(date_k_month_ago.year - 1, str(date_k_month_ago.month).rjust(2, '0'))
           
            # 生成时间轴数据列表
            date_range_ty= pd.date_range(date_k_month_ago, date, freq='M')
            y_ty, m_ty = date_range_ty.year, date_range_ty.month
            month_lst_ty = list(map(lambda y, m: str(y) + '-' + str(m).zfill(2)), y_ty, m_ty)
            
            return [k_month_ago_ty, month_ty, k_month_ago_ly, month_ly, month_lst_ty]
        
        else:
            return [month_ly, month_ty]
        
    def judge_cont_num(lst: list) -> tuple:
        '''
        判断连续为正（负）的月份数
        :param lst: 确保是按照日期升序排列的数值list
        :return: 连续为正（负）的月份数，正负标识
        '''
        count = 0

        curr_num = lst[-1]
        if curr_num > 0:
            sign = '正'
            for i in reversed(lst):
                if i > 0:
                    count += 1
        else:
            sign = '负'
            for i in reversed(lst):
                if i < 0:
                    count += 1
        
        return count, sign
    
    def show_cont_sign_metric(self, cont_num: int, sign: str, dim: str, dim_val: str, metric: str):
        '''
        显示连续为正（负）的月份数的指标
        :param cont_num: 连续为正（负）的月份数
        :param sign: 正、负
        :param dim: 维度中文名，如'省份'、'客户类型'
        :param dim_val: 维度值，如'北京'、'企业'
        :param metric: 指标名
        '''
        sent = metric
        # 无下钻
        if dim == '全部':
            sent = re.sub('最近', f'最近整体客群', sent)
        # 一维下钻
        elif '-' not in dim:
            if dim == '产品':
                sent = re.sub('最近', f'最近{dim_val}产品', sent)
            else:
                sent = re.sub('最近', f'最近{dim_val}客群', sent)
        # 二维下钻
        elif '-' in dim:
            cust_type_dim_val, anot_dim_val = dim_val.split('-')
            if '产品' in dim:
                sent = re.sub('最近', f'最近{cust_type_dim_val}客群-{anot_dim_val}产品', sent)
            else:
                sent = re.sub('最近', f'最近{cust_type_dim_val}-{anot_dim_val}客群', sent)
        # 统一修改两处
        sent = re.sub('正（负）', sign, sent)
        sent = re.sub('$', f'为{cont_num}个月')
        # display
        st.write(sent)


        # def parse_date(self, date: datetime.date) -> list:
        #     '''
        #     parse date to string (单值)
        #     '''
        #     _, last_day = calendar.monthrange(date.year, date.month)
        #     date_start = '{}-{}-{}'.format(date.year, str(date.month).rjust(2, '0'), '01')
        #     date_end = '{}-{}-{}'.format(date.year, str(date.month).rjust(2, '0'), str(last_day).rjust(2, '0'))
        #     return [date_start, date_end]

## 可以自定义多个维度时的代码
# class IncomeAnalysis(Display):
#         def __init__(self) -> None:
#             super().__init__()

#         def show_tot_income_m(self, date, customer_level, customer_type, monthly_income):
#             st.write(f'{date.year}年{date.month}月{customer_level}等级{customer_type}类型客户收入{monthly_income}亿元')

#         def show_income_growth_yoy(self, date, customer_level, customer_type, income_growth_yoy):
#             st.write(f"{date.year}年{date.month}月{customer_level}等级{customer_type}类型客户同比收入增长额为{income_growth_yoy}亿元")

#         def show_income_growth_rate_yoy(self, date, customer_level, customer_type, income_growth_yoy):
#             st.write(f"{date.year}年{date.month}月{customer_level}等级{customer_type}类型客户同比收入增长率为{income_growth_yoy}%")

#         def show_income_ytd(self, date, customer_level, customer_type, income_ytd):
#             st.write(f"{date.year}年{customer_level}等级{customer_type}类型客户今年累计收入为{income_ytd}亿元")

## 可以自定义多个维度时的代码
# def parse_coordinate(coordinate: tuple, data: list):
#     '''
#     parse coordinate to index, group, metric
#     :param coordinate: the coordinate of the paragraph
#     :return: index, group, metric
#     '''
#     index, group, metric = coordinate
#     display_params, df = data
#     if group == '收入分析':
#         date, customer_level, customer_type = display_params

#         display = IncomeAnalysis()

#         if metric == '（按月）收入':
#             monthly_income = format_metric(df[metric].iloc[0])
#             display.show_tot_income_m(date, customer_level, customer_type, monthly_income)

#         elif metric == '（同比）收入增长额':
#             income_ty = df[df[f'{self.month_date_alias}'] == '{}-{}'.format(date.year, str(date.month).rjust(2, '0'))][metric].iloc[0]
#             income_ly = df[df[f'{self.month_date_alias}'] == '{}-{}'.format(date.year - 1, str(date.month).rjust(2, '0'))][metric].iloc[0]
#             income_growth_yoy    = format_metric(income_ty - income_ly)
#             display.show_income_growth_yoy(date, customer_level, customer_type, income_growth_yoy)  # 方法名和变量名不能一样

#         elif metric == '（同比）收入增长率':
#             income_ty = df[df[f'{self.month_date_alias}'] == '{}-{}'.format(date.year, str(date.month).rjust(2, '0'))][metric].iloc[0]
#             income_ly = df[df[f'{self.month_date_alias}'] == '{}-{}'.format(date.year - 1, str(date.month).rjust(2, '0'))][metric].iloc[0]
#             income_growth_rate_yoy = ((income_ty - income_ly) / income_ly * 100).round(round_num)
#             display.show_income_growth_rate_yoy(date, customer_level, customer_type, income_growth_rate_yoy)

#         elif metric == '（今年）累计收入':
#             income_ytd = format_metric(df[metric].iloc[0])
#             display.show_income_ytd(date, customer_level, customer_type, income_ytd)

class DisplayIncome(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        self.date, = self.display_params

    def show(self):
        if self.metric == '（按月）收入':
            monthly_income = self.format_metric(self.df[self.metric].iloc[0])
            self.show_tot_income_m(monthly_income)

        elif self.metric == '（同比）收入增长额':
            month_ty, month_ly = self.parse_date(self.date)
            income_ty = self.df[self.df[f'{self.month_date_alias}'] == month_ty][self.metric].iloc[0]
            income_ly = self.df[self.df[f'{self.month_date_alias}'] == month_ly][self.metric].iloc[0]
            income_growth_yoy = self.format_metric(income_ty - income_ly)
            self.show_income_growth_yoy(income_growth_yoy)  # 方法名和变量名不能一样

        elif self.metric == '（同比）收入增长率':
            month_ty, month_ly = self.parse_date(self.date)
            income_ty = self.df[self.df[f'{self.month_date_alias}'] == month_ty][self.metric].iloc[0]
            income_ly = self.df[self.df[f'{self.month_date_alias}'] == month_ly][self.metric].iloc[0]
            income_growth_rate_yoy = ((income_ty - income_ly) / income_ly * 100)
            income_growth_rate_yoy = self.format_metric(income_growth_rate_yoy, unit='元')
            self.show_income_growth_rate_yoy(income_growth_rate_yoy)

        elif self.metric == '（今年）累计收入':
            income_ytd = self.format_metric(self.df[self.metric].iloc[0])
            self.show_income_ytd(income_ytd)

    def show_tot_income_m(self, monthly_income):
        st.write(f'{self.date.year}年{self.date.month}月客户收入{monthly_income}亿元')

    def show_income_growth_yoy(self, income_growth_yoy):
        st.write(f"{self.date.year}年{self.date.month}月同比收入增长额为{income_growth_yoy}亿元")

    def show_income_growth_rate_yoy(self, income_growth_rate_yoy):
        st.write(f"{self.date.year}年{self.date.month}月同比收入增长率为{income_growth_rate_yoy}%")

    def show_income_ytd(self, income_ytd):
        st.write(f"今年累计收入为{income_ytd}亿元")


class DisplayNumCust(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        self.date, = self.display_params

    def show(self):
        val = self.df[self.metric].iloc[0]
        if self.metric == '（按月）存量客户数':
            self.show_num_existing_cust_m(val)
        elif self.metric == '（按月）新增客户数':
            self.show_num_new_cust_m(val)
        elif self.metric == '（按月）流失客户数':
            self.show_num_lost_cust_m(val)
        elif self.metric == '（今年）累计新增客户数':
            self.show_num_new_cust_ytd(val)
        elif self.metric == '（今年）累计流失客户数':
            self.show_num_lost_cust_ytd(val)
        elif self.metric == '（按月）总客户数':
            self.show_tot_num_cust_m(val)
        elif self.metric in ['（同比）客户数增长值', '（同比）客户数增长率']:
            month_ty, month_ly = self.parse_date(self.date)
            num_cust_ty = self.df[self.df[f'{self.month_date_alias}'] == month_ty][self.metric].iloc[0]
            num_cust_ly = self.df[self.df[f'{self.month_date_alias}'] == month_ly][self.metric].iloc[0]
            if self.metric == '（同比）客户数增长值':
                num_cust_growth_yoy = num_cust_ty - num_cust_ly
                self.show_num_cust_growth_yoy(num_cust_growth_yoy)
            elif self.metric == '（同比）客户数增长率':
                num_cust_growth_rate_yoy = ((num_cust_ty - num_cust_ly) / num_cust_ly * 100)
                num_cust_growth_rate_yoy = self.format_metric(num_cust_growth_rate_yoy, unit='元')
                self.show_num_cust_growth_rate_yoy(num_cust_growth_rate_yoy)

    def show_num_existing_cust_m(self, monthly_num_existing_cust):
        st.write(f'{self.date.year}年{self.date.month}月存量客户数为{monthly_num_existing_cust}户')

    def show_num_new_cust_m(self, monthly_num_new_cust):
        st.write(f'{self.date.year}年{self.date.month}月新增客户数为{monthly_num_new_cust}户')

    def show_num_lost_cust_m(self, monthly_num_lost_cust):
        st.write(f'{self.date.year}年{self.date.month}月流失客户数为{monthly_num_lost_cust}户')

    def show_num_new_cust_ytd(self, num_new_cust_ytd):
        st.write(f'{datetime.date.today().year}年累计新增客户数为{num_new_cust_ytd}户')

    def show_num_lost_cust_ytd(self, num_lost_cust_ytd):
        st.write(f'{datetime.date.today().year}年累计流失客户数为{num_lost_cust_ytd}户')

    def show_tot_num_cust_m(self, monthly_tot_num_cust):
        st.write(f'{self.date.year}年{self.date.month}月总客户数为{monthly_tot_num_cust}户')

    def show_num_cust_growth_yoy(self, num_cust_growth_yoy):
        st.write(f"{self.date.year}年{self.date.month}月同比客户数增长值为{num_cust_growth_yoy}户")

    def show_num_cust_growth_rate_yoy(self, num_cust_growth_rate_yoy):
        st.write(f"{self.date.year}年{self.date.month}月同比客户数增长率为{num_cust_growth_rate_yoy}%")


class DisplayAvgSpendPerCust(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        self.date, = self.display_params

    def show(self):
        val = self.df[self.metric].iloc[0]
        val = self.format_metric(val, unit='元')
        if self.metric == '（按月）客单价':
            self.show_avg_spend_per_cust_m(val)
        elif self.metric == '（按月）新增客户单价':
            self.show_avg_spend_per_new_cust_m(val)
        elif self.metric == '（按月）流失客户单价':
            self.show_avg_spend_per_lost_cust_m(val)
        elif self.metric == '（按月）存量客户单价':
            self.show_avg_spend_per_existing_cust_m(val)

    def show_avg_spend_per_cust_m(self, monthly_avg_spend_per_cust):
        st.write(f'{self.date.year}年{self.date.month}月客单价为{monthly_avg_spend_per_cust}元')

    def show_avg_spend_per_new_cust_m(self, monthly_avg_spend_per_new_cust):
        st.write(f'{self.date.year}年{self.date.month}月新增客户客单价为{monthly_avg_spend_per_new_cust}元')
    
    def show_avg_spend_per_lost_cust_m(self, monthly_avg_spend_per_lost_cust):
        st.write(f'{self.date.year}年{self.date.month}月流失客户客单价为{monthly_avg_spend_per_lost_cust}元')

    def show_avg_spend_per_existing_cust_m(self, monthly_avg_spend_per_existing_cust):
        st.write(f'{self.date.year}年{self.date.month}月存量客户客单价为{monthly_avg_spend_per_existing_cust}元')


class DisplayCustDim(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        self.date, self.dim, self.sub_anlys = self.display_params

    def show(self):
        if self.sub_anlys == '收入分析':
            if self.metric == '（按月）收入' or self.metric == '（今年）累计收入':
                unit = '亿元'
                x_arr = self.df[self.dim].tolist()
                y_arr = self.df[self.metric].tolist()
                y_arr = self.format_metric(y_arr, unit=unit)  # 保留两位小数，以亿元为单位
                self.show_one_dim_chart(x_arr, y_arr, self.dim, self.group, self.metric, unit)
            elif self.metric == '（同比）收入增长额' or self.metric == '（同比）收入增长率':
                x_arr = self.df[self.dim].tolist()
                month_ty, month_ly = self.parse_date(self.date)
                df_ty = self.df[self.df[f'{self.month_date_alias}'] == month_ty]
                df_ly = self.df[self.df[f'{self.month_date_alias}'] == month_ly]
                if df_ly.empty:
                    st.error('同比指标计算中，去年数据为空！')
                else:
                    self.df = pd.merge(df_ty, df_ly, on=self.dim, suffixes=('_ty', '_ly'))
                    if self.metric == '（同比）收入增长额':
                        unit = '亿元'
                        self.df[self.metric] = self.df[self.metric + '_ty'] - self.df[self.metric + '_ly']
                        y_arr = self.df[self.metric].tolist()
                        y_arr = self.format_metric(y_arr, unit=unit)  # 保留两位小数，以亿元为单位
                        self.show_one_dim_chart(x_arr, y_arr, self.dim, self.group, self.metric, unit)
                    elif self.metric == '（同比）收入增长率':
                        y_arr = ((self.df[self.metric + '_ty'] - self.df[self.metric + '_ly']) / self.df[self.metric + '_ly'] * 100).round(2).tolist()
                        self.show_one_dim_chart(x_arr, y_arr, self.dim, self.group, self.metric, '%')
        elif self.sub_anlys == '客户数分析':
            if self.metric not in ['（同比）客户增长值', '（同比）客户增长率']:
                x_arr = self.df[self.dim].tolist()
                y_arr = self.df[self.metric].tolist()
                self.show_one_dim_chart(x_arr, y_arr, self.dim, self.group, self.metric, '亿元')
            elif self.metric == '（同比）客户增长值' or self.metric == '（同比）客户增长率':
                x_arr = self.df[self.dim].tolist()
                month_ty, month_ly = self.parse_date(self.date)
                df_ty = self.df[self.df[f'{self.month_date_alias}'] == month_ty]
                df_ly = self.df[self.df[f'{self.month_date_alias}'] == month_ly]
                if df_ly.empty:
                    st.error('同比指标计算中，去年数据为空！')
                else:
                    self.df = pd.merge(df_ty, df_ly, on=self.dim, suffixes=('_ty', '_ly'))
                    if self.metric == '（同比）客户增长值':
                        self.df[self.metric] = self.df[self.metric + '_ty'] - self.df[self.metric + '_ly']
                        y_arr = self.df[self.metric].tolist()
                        self.show_one_dim_chart(x_arr, y_arr, self.dim, self.group, self.metric, '亿元')
                    elif self.metric == '（同比）客户增长率':
                        y_arr = ((self.df[self.metric + '_ty'] - self.df[self.metric + '_ly']) / self.df[self.metric + '_ly'] * 100).round(2).tolist()
                        self.show_one_dim_chart(x_arr, y_arr, self.dim, self.group, self.metric, '%')
        elif self.sub_anlys == '客单价分析':
            x_arr = self.df[self.dim].tolist()
            y_arr = self.df[self.metric].tolist()
            y_arr = self.format_metric(y_arr, unit='万元')
            self.show_one_dim_chart(x_arr, y_arr, self.dim, self.group, self.metric, '万元')

    def show_one_dim_chart(self, x_arr: list, y_arr: list, dim: str, sub_anlys: str, metric: str, unit: str = None):
        self.x_arr, self.y_arr = x_arr, y_arr
        self.dim, self.sub_anlys, self.metric, self.unit = dim, sub_anlys, metric, unit
        if '同比' in self.metric:  # 同比数据存在负值，不适合用饼图展示
            self.show_one_dim_bar()
        elif dim == '省份':  # 维度值数大于8
            self.show_one_dim_bar()
        elif dim == '行业':  # 维度值数大于8
            self.show_one_dim_bar()
        elif dim == '客户等级':  # 维度值数小于8
            self.show_one_dim_pie()
        elif dim == '客户类型':  # 维度值数小于8
            self.show_one_dim_pie()
        elif dim == '产品':  # 维度值数大于8
            self.show_one_dim_bar() 

    def show_one_dim_bar(self):
        bar = (
            Bar()
            .add_xaxis(self.x_arr)
            .add_yaxis(f'{self.metric}', self.y_arr, category_gap='50%')
            .set_global_opts(
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-15, interval=0)),
                title_opts=opts.TitleOpts(title=f'{self.date.year}年{self.date.month}月{self.sub_anlys}-{self.metric}-{self.dim}',
                                          subtitle=f'单位：{self.unit}'),
            )
        )
        st_pyecharts(bar)

    def show_one_dim_pie(self):
        pie = (
            Pie()
            .add("", [list(z) for z in zip(self.x_arr, self.y_arr)])
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f'{self.date.year}年{self.date.month}月{self.sub_anlys}-{self.metric}-{self.dim}', 
                                          subtitle=f'单位：{self.unit}')
            )
        )
        st_pyecharts(pie)


class DisplayIncomeTrend(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        self.date, self.dim, self.dim_val, self.k = self.display_params

    def show(self):
        self.df.sort_values(by=f'{self.month_date_alias}', inplace=True)  # 确保日期升序排列
        if self.metric == '最近收入同比增长连续为正（负）的月份数':  # 这个指标display跟其他的不一样，它是文字，其他都是折线图
            ser_ty = self.df['今年']  # series
            ser_ly = self.df['去年']
            y_arr = ((ser_ty - ser_ly) / ser_ly * 100).tolist()
            # 判断连续为正（负）的月份数
            cont_num, sign = self.judge_cont_num(y_arr)
            # display
            self.show_cont_sign_metric(cont_num, sign, self.dim, self.dim_val)
        else:
            if self.metric == '过去K个月每月收入' or self.metric == '过去K个月每月客单价':
                x_arr = self.df[f'{self.month_date_alias}'].tolist()
                y_arr = self.df[self.metric].tolist()
                if self.metric == '过去K个月每月收入':
                    unit='亿元'
                    y_arr = self.format_metric(y_arr, unit)  # 保留两位小数，以亿元为单位
                elif self.metric == '过去K个月每月客单价':
                    unit='元'
                    y_arr = self.format_metric(y_arr, unit)
            elif self.metric == '过去K个月每月收入同比增长率':
                unit = '%'
                x_arr = self.df[f'{self.month_date_alias}'].tolist()
                ser_ty = self.df['今年']  # series
                ser_ly = self.df['去年']
                y_arr = ((ser_ty - ser_ly) / ser_ly * 100).tolist()
                y_arr = self.format_metric(y_arr, unit)
            elif self.metric == '（今年）每月累计收入':
                unit = '亿元'
                x_arr = self.df[f'{self.month_date_alias}'].tolist()
                # 累加(要确保日期升序排列)
                self.df[self.metric] = self.df[self.metric].cumsum()
                y_arr = self.df[self.metric].tolist()
                y_arr = self.format_metric(y_arr, unit)  # 保留两位小数，以亿元为单位

            self.show_line(x_arr, y_arr, self.date, self.k, self.metric, self.dim, self.dim_val, unit)
            
    # def show_income_growth_rate_yoy_cont_sign(self, cont_num: int, sign: str, dim: str, dim_val: str):
    #     # 无下钻
    #     if dim == '全部':
    #         st.write(f"近期整体客群收入同比增长连续为{sign}的月份数为{cont_num}个月")
    #     # 一维下钻
    #     elif '-' not in dim:
    #         if dim == '产品':
    #             st.write(f"近期{dim_val}产品收入同比增长连续为{sign}的月份数为{cont_num}个月")
    #         else:
    #             st.write(f"近期{dim_val}客群收入同比增长连续为{sign}的月份数为{cont_num}个月")
    #     # 二维下钻
    #     elif '-' in dim:
    #         if dim == '产品':
    #             st.write(f"近期{dim_val}产品收入同比增长连续为{sign}的月份数为{cont_num}个月")
    #         else:
    #             st.write(f"近期{dim_val}客群收入同比增长连续为{sign}的月份数为{cont_num}个月")
        
    def show_line(self, x_arr: list, y_arr: list, date: datetime.date, k: int, metric: str, dim: str, dim_val: str, unit: str = None):
        # ylabel
        if dim == '全部':
            ylabel = '整体客群'
        elif '-' not in dim:
            ylabel = f"{dim}:{dim_val}"
        else:
            ylabel = '&'.join(map(lambda d, dv: d + ':' + dv, dim.split('-'), dim_val.split('-')))
        # title
        if 'K' in metric:
            metric = metric.replace('K', str(k))
        title = f'{date.year}年{date.month}月{metric}'
        # subtitle
        if unit == None:
            subtitle = None
        else:
            subtitle = f'单位：{unit}'
        line = (
            Line()
            .add_xaxis(xaxis_data=x_arr)
            .add_yaxis(series_name=ylabel, y_axis=y_arr)
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, subtitle=subtitle)
            )
        )

        st_pyecharts(line)


class DisplayCustDev(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        self.date, self.dim, self.dim_val, self.k = self.display_params

    def show(self):
        self.df.sort_values(by=f'{self.month_date_alias}', inplace=True)  # 确保日期升序排列
        if 'K个月' in self.metric:  # 折线图（需要check）
            unit = '个'
            x_arr = self.df[self.month_date_alias].tolist()
            y_arr = self.df[self.metric].tolist()
            y_arr = self.format_metric(y_arr, unit)
            self.show_line(x_arr, y_arr, self.date, self.k, self.metric, self.dim, self.dim_val, unit)
        elif self.metric in ['（今年）累计新增客户数', '（今年）累计流失客户数']:  # 文字1
            val = self.df[self.metric].iloc[0]
            if self.metric == '（今年）累计新增客户数':
                st.write(f'{datetime.date.today().year}年累计新增客户数为{val}户')
            elif self.metric == '（今年）累计流失客户数':
                st.write(f'{datetime.date.today().year}年累计流失客户数为{val}户')
        elif self.metric in ['最近总客户数同比增长连续为正（负）的月份数', '最近净增客户数连续为正（负）的月份数']:  # 文字2
            ser_ty = self.df['今年']  # series
            ser_ly = self.df['去年']
            y_arr = (ser_ty - ser_ly) / ser_ly * 100
            y_arr = y_arr.tolist()
            # 判断连续为正（负）的月份数
            cont_num, sign = self.judge_cont_num(y_arr)
            # display
            self.show_cont_sign_metric(cont_num, sign, self.dim, self.dim_val, self.metric)
        elif self.metric == '本月存量、新增、流失客户占比':  # 饼图
            pass
        elif '本月' in self.metric:  # 文字3
            pass
        
    def show_line(self, x_arr: list, y_arr: list, date: datetime.date, k: int, metric: str, dim: str, dim_val: str, unit: str = None):
        # ylabel
        if dim == '全部':
            ylabel = '整体客群'
        elif '-' not in dim:
            ylabel = f"{dim}:{dim_val}"
        else:
            ylabel = list(map(lambda d, dv: d + ':' + dv, dim.split('-'), dim_val.split('-')))
        # title
        if 'K' in metric:
            metric = metric.replace('K', str(k))
        title = f'{date.year}年{date.month}月{metric}'
        # subtitle
        if unit == None:
            subtitle = None
        else:
            subtitle = f'单位：{unit}'
        line = (
            Line()
            .add_xaxis(xaxis_data=x_arr)
            .add_yaxis(series_name=ylabel, y_axis=y_arr)
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, subtitle=subtitle)
            )
        )

        st_pyecharts(line)
        
    def show_pie(self):
        pass
                

class DisplayPlanAchvmt(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        
    def show(self):
        pass
    
    
class DisplayRanking(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        
    def show(self):
        pass
    

class DisplayKeyCustIncome(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        
    def show(self):
        pass
    
    
class DisplayKeyCustTrend(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        
    def show(self):
        pass


class DisplayKeyCustDev(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        
    def show(self):
        pass


class DisplayKeyCustPlanAchvmt(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        
    def show(self):
        pass
    
    
class DisplayKeyCustRanking(Display):
    def __init__(self, coordinate: tuple, data: list) -> None:
        super().__init__(coordinate, data)
        
    def show(self):
        pass

    
def parse_coordinate(coordinate: tuple, data: list):
    '''
    parse coordinate to index, group, metric
    :param coordinate: the coordinate of the paragraph
    :return: index, group, metric
    '''
    _, group, _ = coordinate
    if group == '收入分析':
        display = DisplayIncome(coordinate, data)
    elif group == '客户数分析':
        display = DisplayNumCust(coordinate, data)
    elif group == '客单价分析':
        display = DisplayAvgSpendPerCust(coordinate, data)
    elif group == '客群分维度分析':
        display = DisplayCustDim(coordinate, data)
    elif group == '收入趋势分析':
        display = DisplayIncomeTrend(coordinate, data)
    elif group == '客户发展分析':
        display = DisplayCustDev(coordinate, data)
    elif group =='计划达成分析':
        display = DisplayPlanAchvmt(coordinate, data)
    elif group == '排名分析':
        display = DisplayRanking(coordinate, data)
    elif group == '关键客群收入分析':
        display = DisplayKeyCustIncome(coordinate, data)
    elif group == '关键客群趋势分析':
        display = DisplayKeyCustTrend(coordinate, data)
    elif group == '关键客群发展分析':
        display = DisplayKeyCustDev(coordinate, data)
    elif group == '关键客群计划达成分析':
        display = DisplayKeyCustPlanAchvmt(coordinate, data)
    elif group == '关键客群排名分析':
        display = DisplayKeyCustRanking(coordinate, data)
    
    display.show()

for coordinate, data in st.session_state['records_data'].items():
    parse_coordinate(coordinate, data)
        