#### 说明
- sql中{}表示替换字符，[]表示可选条件

#### 1. 收入分析
> 要求
> 
> - 本月收入各指标计算，包括月度总体指标：收入、（同比）收入增长额、收入同比增长率、（今年）累计收入
> - 以上都是单值，可以用语句展现

设计：

- 指标名：
    - （按月）收入  -- [客户id（=all）-产品（=all）-购买（=总金额）-time（=某月）-expr（=sum）]
    - （同比）收入增长额  -- [客户id（=all）-产品（=all）-购买（=总金额）-time（=某月+同比）-expr（=sum）]
    - （同比）收入增长率 -- [客户id（=all）-产品（=all）-购买（=总金额）-time（=某月+同比）-expr（=sum）]
    - （今年）累计收入 -- [客户id（=all）-产品（=all）-购买（=总金额）-time（=今年）-expr（=sum）]

- 所需数据查询:
    - （按月）收入
    ```sql
    select sum({income_dim}) as 总收入  -- just an alias
    from {table}
    where {date_dim} >= '{start date of selected month}' and {date_dim} <= '{end date of selected month}' and [{province_dim} = '{province}'] and [{customer_level_dim} = '{customer_level}'] and [{customer_type_dim} = '{customer_type}']
    ```
    - （同比）收入增长额、（同比）收入增长率
    ```sql
    --type1
    select sum({income_dim}) as 总收入,  -- don't miss the comma
    case
    when ({date_dim} >= '{start date of a month}') and ({date_dim} <= '{end date of a month}') then '{personalized month of this year}'
    when ({date_dim} >= '{start date of the same month last year}') and ({date_dim} <= '{end date of the same month last year}') then '{personalized month of last year}'
    end as 月份  -- just an alias
    from {table}
    where 1=1 and [{province_dim} = '{province}'] and [{customer_level_dim} = '{customer_level}'] and [{customer_type_dim} = '{customer_type}']
    group by 月份
    having 月份 is not null  -- drop the 'other' solution caused by CASE expression
    ```
    ```sql
    --type2（感觉不用这个type，因为后面还有更复杂的情况是基于type1的）
    select t1.月份 as 月份, 今年, 去年
    from
    (select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, sum({income_dim}) as 今年
    from {table}
    where {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}'
    group by 月份) t1
    join
    (select (cast(year(timestampadd(year, 1, {date_dim})) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(year, 1, {date_dim})) as varchar), -2, 2)) as 月份, sum({income_dim}) as 去年
    from {table}
    where {date_dim} >= '{去年某月初}' and {date_dim} <= '{去年某月末}'
    group by 月份) t2
    on t1.月份 = t2.月份 
    ```
    - （今年）累计收入
    ```sql
    select sum({income_dim}) as 总收入
    from {table}
    where {date_dim} >= '{start date of this year}' and {date_dim} <= '{end date of this month}' and [{province_dim} = '{province}'] and [{customer_level_dim} = '{customer_level}'] and [{customer_type_dim} = '{customer_type}']
    ```

- 输出（语句）：
    - （按月）收入：{}年{}月{}地区{}等级{}类型客户收入{}亿元
    - （同比）收入增长额：{}年{}月{}地区{}等级{}类型客户同比收入增长额为{}亿元
    - （同比）收入增长率：{}年{}月{}地区{}等级{}类型客户同比收入增长率为{}%
    - （今年）累计收入：{}年{}地区{}等级{}类型客户累计收入为{}亿元

#### 2. 客户数分析
> 要求
> 
> - 本月客户数各指标计算
> - 以上都是单值，可以用语句展现

- 指标名
    - （按月）存量客户数 -- [客户id（=存量）-None-计数（=数量）-time（=某月）-expr（=count_distinct）]
    - （按月）新增客户数 -- [客户id（=新增）-None-计数（=数量）-time（=某月）-expr（=count_distinct）]
    - （按月）流失客户数 -- [客户id（=新增）-None-计数（=数量）-time（=某月）-expr（=count_distinct）]
    - （今年）累计新增客户数 -- [客户id（=新增）-None-计数（=数量）-time（=今年）-expr（=count_distinct）]
    - （今年）累计流失客户数 -- [客户id（=流失）-None-计数（=数量）-time（=今年）-expr（=count_distinct）]
    - （按月）总客户数 -- [客户id（=all）-None-计数（=数量）-time（=某月）-expr（=count_distinct）]
    - （同比）客户增长值 -- [客户id（=all）-None-计数（=数量）-time（=某月+同比）-expr（=count_distinct）]
    - （同比）客户增长率 -- [客户id（=all）-None-计数（=数量）-time（=某月+同比）-expr（=count_distinct）]

- 需要的查询
    - （按月）存量客户数
    ```sql
    select count(distinct {customer_id_dim})  -- 要用distinct去重
    from {table}
    where ({date_dim} >= '{某月初}' and {date_dim} <= '{某月末}') and {customer_id_dim} in  (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')
    ```
    <!-- 下面这个方法也行 -->
    <!-- ```sql
      select count(distinct customer_id)
      from (select customer_id
      from merged_data
      where account_period >= '2021-01-01' and account_period <= '2021-01-31'
      intersect  # intersect默认去重
      select customer_id
      from merged_data
      where account_period >= '2022-01-01' and account_period <= '2022-01-31')
      ``` -->

    - （按月）新增客户数
    ```sql
    select count(distinct {customer_id_dim})
    from {table}
    where ({date_dim} >= '{某月初}' and {date_dim} <= '{某月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')
    ```
    - （按月）流失客户数
    ```sql
    select count(distinct {customer_id_dim})
    from {table}
    where ({date_dim} >= '{上月初}' and {date_dim} <= '{上月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}')
    ```
    - （今年）累计新增客户数<font color=ferrari>【今年一月至今所有新增客户，和去年12月份比】</font>
    ```sql
    select count(distinct {customer_id_dim})
    from {table}
    where ({date_dim} >= '{今年年初}' and {date_dim} <= '{本月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{去年12月初}' and {date_dim} <= '{去年12月末}')
    ```
    - （今年）累计流失客户数
    ```sql
    select count(distinct {customer_id_dim})
    from {table}
    where ({date_dim} >= '{去年12月初}' and {date_dim} <= '{去年12月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{今年年初}' and {date_dim} <= '{本月末}')
    ```
    - （按月）总客户数
    ```sql
    select count(distinct {customer_id_dim})
    from {table}
    where ({date_dim} >= '{某月初}' and {date_dim} <= '{某月末}')
    ```
    - （同比）客户增长值<font color=ferrari>【我的理解是总客户数的同比增长值】</font>
    ```sql
    select count(distinct {customer_id_dim}),
    case
    when {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}' then '{某月份}'
    when {date_dim} >= '{去年某月初}' and {date_dim} <= '{去年某月末}' then '{去年某月份}'
    end as 月份  -- alias
    from {table}
    group by 月份
    having 月份 is not null
    ```
    - （同比）客户增长率
      > 【同"（同比）客户增长值"】


#### 3. 客单价分析
> 要求
> 
> - （月）所有客户平均客单价（简称客单价）、新增客户单价、流失客户单价、存量客户单价计算

- 指标名
    - （按月）客单价 -- [客户id（=all）-产品（=all）-购买（=客单价）-time（=某月）-expr（=sum+avg）]
    - （按月）新增客户单价 -- [客户id（=新增）-产品（=all）-购买（=客单价）-time（=某月）-expr（=sum+avg）]
    - （按月）流失客户单价 -- [客户id（=流失）-产品（=all）-购买（=客单价）-time（=某月）-expr（=sum+avg）]
    - （按月）存量客户单价 -- [客户id（=存量）-产品（=all）-购买（=客单价）-time（=某月）-expr（=sum+avg）]

- 需要的查询
    - （按月）客单价<font color=ferrari>【平均从每个客户上获得的收入】</font>
    ```sql
    select avg(总收入) as 客单价
    from (
    select {customer_id_dim}, sum({income_dim}) as 总收入
    from {table}
    where {date_dim} >= '{某月份初}' and {date_dim} <= '{某月份末}'
    group by {customer_id_dim})
    ```
    - （按月）新增客户单价
    ```sql
    select avg(总收入) as 客单价
    from (
    select {customer_id_dim}, sum({income_dim}) as 总收入
    from {table}
    where ({date_dim} >= '{某月初}' and {date_dim} <= '{某月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where ({date_dim} >= '{上个月初}' and {date_dim} <= '{上个月末}'))
    group by {customer_id_dim})
    ```
    - （按月）流失客户单价
    ```sql
    select avg(总收入) as 客单价
    from (
    select {customer_id_dim}, {total_income} as 总收入
    from {table}
    where ({date_dim} >= '上个月初' and {date_dim} <= '上个月末') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where ({date_dim} >= '某月初' and {date_dim} <= '某月末'))
    group by {customer_id_dim})
    ```
    - （按月）存量客户单价
    ```sql
    select avg(总收入) as 客单价
    from (
    select {customer_id_dim}, {total_income} as 总收入
    from {table}
    where ({date_dim} >= '某月初' and {date_dim} <= '某月末') and  {customer_id_dim} in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '上个月初' and {date_dim} <= '上个月末')
    group by {customer_id_dim})
    ```

#### 4. 客群分维度分析
> 要求
> 
> - 按维度（省份、产品、行业、等级、政/企）的各收入指标计算
> - 按维度（省份、产品、行业、等级、政/企）的各客户数指标计算
> - 按维度（省份、产品、行业、等级、政/企）的客单价计算
> - 以上都是一维向量，可以用柱状图（当N>8时）或饼图（当N<=8时）展现

- 指标名
    - （按月）各收入指标计算 -- [某维度（=groupby)-产品（=all/groupby）-购买（=总金额）-time（=某月/某月+同比/今年）-expr（=sum）]
    - （按月）各客户数指标计算 -- [【客户id（=all/存量/新增/流失）+某维度（=groupby）】-产品（=all/groupby）-计数（=数量）-time（=某月/某月+同比/今年）-expr（=count_distinct）]
    - （按月）客单价计算 -- [【客户id（=all/存量/新增/流失）+某维度（=groupby)】-产品（=all/groupby）-购买（=客单价）-time（=某月）-expr（=sum+avg）]

- 需要的查询
    - （按月）各收入指标计算
    ```sql
    select {dim}, {metric}  -- 就是之前收入分析加上某一维度的group by
    from {table}
    where {date_dim} >= '某月初' and {date_dim} <= '某月末'
    group by {dim}
    ```

    - （按月）各客户数指标计算
        - 存量
        ```sql
        select {dim}, count(distinct {customer_id_dim}) as 数量
        from {table}
        where ({date_dim} >= '某月初' and {date_dim} <= '某月末') and {customer_id_dim} in (select {customer_id_dim}
        from {table}
        where {date_dim} >= '上个月初' and {date_dim} <= '上个月末')
        group by dim
        ```

        - 新增
        ```sql
        select dim, count(distinct {customer_id_dim}) as 数量
        from {table}
        where ({date_dim} >= '{某月初}' and {date_dim} <= '某月末') and {customer_id_dim} not in (
        select {customer_id_dim}
        from {table}
        where {date_dim} >= '上个月初' and {date_dim} <= '上个月末')
        group by dim
        ```

        - 流失
        ```sql
        select dim, count(distinct {customer_id_dim}) as 数量
        from {table}
        where ({date_dim} >= '上个月初' and {date_dim} <= '上个月末') and {customer_id_dim} not in (
        select {customer_id_dim}
        from {table}
        where {date_dim} >= '{某月初}' and {date_dim} <= '某月末')
        group by dim
        ```

    - （按月）客单价计算
        - （按月）客单价
        ```sql
        select province_name, avg(sum_sale)
        from (
        select province_name, customer_id, sum({income_dim}) as sum_sale
        from merged_data
        where account_period >= '2022-01-01' and account_period <= '2022-01-31'
        group by province_name, customer_id)
        group by province_name
        ```

        - （按月）新增客户单价
        ```sql
        select dim, avg(sum_sale)
        from (
        select dim, customer_id, sum({income_dim}) as sum_sale
        from merged_data
        where (account_period >= '2022-01-01' and account_period <= '2022-01-31') and customer_id not in (
        select customer_id
        from merged_data
        where (account_period >= '2021-01-01' and account_period <= '2021-01-31'))
        group by dim, customer_id)
        group by dim
        ```

        - （按月）流失客户单价
        ```sql
        select dim, avg(sum_sale)
        from (
        select dim, customer_id, sum({income_dim}) as sum_sale
        from merged_data
        where (account_period >= '2021-01-01' and account_period <= '2021-01-31') and customer_id not in (
        select customer_id
        from merged_data
        where (account_period >= '2022-01-01' and account_period <= '2022-01-31'))
        group by dim, customer_id)
        group by dim
        ```

        - （按月）存量客户单价计算
        ```sql
        select dim, avg(sum_sale)
        from (
        select dim, customer_id, sum({income_dim}) as sum_sale
        from merged_data
        where (account_period >= '2022-01-01' and account_period <= '2022-01-31') and  customer_id in (
        select customer_id
        from merged_data
        where account_period >= '2021-01-01' and account_period <= '2021-01-31')
        group by dim, customer_id)
        group by dim
        ```

#### 5. 收入趋势分析
> 要求
>
> - 整个客群过去K个月的收入、同比增长率 （折线图）（K是一个全局变量，比如过去12个月）
> - 整个客群今年1月起的累计收入（折线图，下同）
> - 整个客群最近收入同比增长连续为正（负）的月份数
> - 整个客群过去K个月的客单价 （折线图）
> - 以上趋势子客群（省份、产品、行业、等级、政/企）的单一维度分析<font color=ferrari>以及政企和其他维度的交叉下钻</font>

- 指标名：
    - 过去K个月每月收入 -- [客户id（=all）/某维度（=维度值）-产品（=all/产品值）-购买（=总金额）-time（=过去K个月+每月）-expr（=sum）]
    - 过去K个月每月收入同比增长率 -- [客户id（=all）/某维度（=维度值）-产品（=all/产品值）-购买（=总金额）-time（=过去K个月+每月+同比）-expr（=sum）]
    - （今年）累计收入 -- [客户id（=all）/某维度（=维度值）-产品（=all/产品值）-购买（=总金额）-time（=今年）-expr（=sum）]
    - 最近收入同比增长连续为正（负）的月份数 -- [客户id（=all）/某维度（=维度值）-产品（=all/产品值）-购买（=总金额）-time（=过去K个月+每月）-expr（=sum）]
    - 过去K个月每月客单价 -- [客户id（=all）/某维度（=维度值）-产品（=all/产品值）-购买（=客单价）-time（=过去K个月+每月）-expr（=sum）]

- 需要的查询
    - 过去K个月每月收入
    ```sql
    select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, sum({income_dim})
    from {table}
    where {date_dim} >= '{前K个月}' and {date_dim} <= '{本月}'
    group by 月份
    ```
    <!-- ```sql
      select [{total_income} as 总收入] 或者是 [{某产品income} as {某产品}收入],  -- don't miss the comma
      case
      when ({date_dim} >= '{start date of a month}') and ({date_dim} <= '{end date of a month}') then '{personalized month of this year}'  -- 循环获得这个case when结构
      end as 月份  -- just an alias
      from {table}
      where 1=1 and [{province_dim} = '{province}'] and [{customer_level_dim} = '{customer_level}'] and [{customer_type_dim} = '{customer_type}']
      group by 月份
      having 月份 is not null
      ``` -->
    - 过去K个月每月收入同比增长率
    ```sql
    select t1.月份 as 月份, 今年, 去年
    from
    (select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, sum({income_dim}) as 今年
    from {table}
    where {date_dim} >= '{前K个月}' and {date_dim} <= '{本月}'
    group by 月份) t1
    join
    (select (cast(year(timestampadd(year, 1, {date_dim})) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(year, 1, {date_dim})) as varchar), -2, 2)) as 月份, sum({income_dim}) as 去年
    from {table}
    where {date_dim} >= '{去年前K个月}' and {date_dim} <= '{去年本月}'
    group by 月份) t2
    on t1.月份 = t2.月份
    ```
    <!-- ```sql
      select [{total_income} as 总收入] 或者是 [{某产品income} as {某产品}收入],  -- don't miss the comma
      case
      when ({date_dim} >= '{start date of a month}') and ({date_dim} <= '{end date of a month}') then '{personalized month of this year}'
      when ({date_dim} >= '{start date of the same month last year}') and ({date_dim} <= '{end date of the same month last year}') then '{personalized month of last year}'  -- 循环获得这个case when结构
      end as 月份  -- just an alias
      from {table}
      where 1=1 and [{province_dim} = '{province}'] and [{customer_level_dim} = '{customer_level}'] and [{customer_type_dim} = '{customer_type}']
      group by 月份
      having 月份 is not null
      ``` -->
    - （今年）<font color=ferrari>每月</font>累计收入
      > 【类同"过去K个月收入"】
    - 最近收入同比增长连续为正（负）的月份数 (<font color=ferrari>需要设置一个最大月的限制，目前将其默认值设为36;是同比增长额还是增长率</font>)
      > 【同"过去K个月收入同比增长率"】
    - 过去K个月每月客单价
    ```sql
      select 月份, avg(总收入) as {metric}
      from (
        select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, {cust_id_dim}, sum({income_dim}) as 总收入
        from {table}
        where {date_dim} >= '{前K个月}' and {date_dim} <= '{本月}'
        group by 月份, {cust_id_dim}
      )
      group by 月份
    ```
    <!-- ```sql
      select 月份, avg({}收入) as 客单价
      from (
      select {customer_id_dim}, [{total_income} as 总收入] 或者是 [{某产品income} as {某产品}收入],
      case
      when ({date_dim} >= '{start date of a month}') and ({date_dim} <= '{end date of a month}') then '{personalized month of this year}'  -- 循环获得这个case when结构
      end as 月份
      from {table}
      where {date_dim} >= '{某月份初}' and {date_dim} <= '{某月份末}'
      group by 月份, {customer_id_dim})
      group by 月份
      ``` -->

- 图名：
    - {}产品{}客群过去K个月收入折线图
    - {}产品{}客群过去K个月收入同比增长率折线图
    - {}产品{}客群今年累计收入折线图
    - {}产品{}客群最近收入同比增长连续为正/负的月份数
    - {}产品{}客群过去K个月客单价折线图


#### 6. 客户发展分析
> 要求
>
> - 整体客群过去K个月的（存量客户数、新增客户数、流失客户数、总客户数、（同比）客户增长数、（同比）客户增长率）
> - 整个客群今年1月起的累计新增客户数、累计流失客户数
> - 整个客群最近总客户数同比增长连续为正（负）的月份数
> - 整个客群最近净增（新增-流失）客户数连续为正（负）的月份数
> - 整个客群本月存量、新增、流失客群各自的收入、收入同比增长率、占比、收入增幅
> - 以上趋势在子客群（省份、产品、行业、等级、政/企）的分析

- 指标名
    - 过去K个月每月存量客户数 -- [客户id（=存量）+/某维度（=维度值）-None-计数（=数量）-time（=过去K个月+每月）-expr（=count_distinct）]
    - 过去K个月每月新增客户数 -- [客户id（=新增）+/某维度（=维度值）-None-计数（=数量）-time（=过去K个月+每月）-expr（=count_distinct）]
    - 过去K个月每月流失客户数 -- [客户id（=流失）+/某维度（=维度值）-None-计数（=数量）-time（=过去K个月+每月）-expr（=count_distinct）]
    - 过去K个月每月总客户数 -- [客户id（=all）+/某维度（=维度值）-None-计数（=数量）-time（=过去K个月+每月）-expr（=count_distinct）]
    - 过去K个月每月客户数（同比）增长额
    - 过去K个月每月客户数（同比）增长率
    - （今年）累计新增客户数
    - （今年）累计流失客户数
    - 最近总客户数同比增长连续为正（负）的月份数
    - 最近净增客户数连续为正（负）的月份数
    - 本月存量、新增、流失客户占比
    - 本月存量客户收入
    - 本月存量客户收入（同比）增长额
    - 本月存量客户收入（同比）增长率
    - 本月新增客户收入
    - 本月新增客户收入（同比）增长额
    - 本月新增客户收入（同比）增长率
    - 本月流失客户收入
    - 本月流失客户收入（同比）增长额
    - 本月流失客户收入（同比）增长率

- 需要的查询
    - 过去K个月<font color=ferrari>每月</font>存量客户数
    注：这里日期加减可以用TIMESTAMPADD函数，例如`TIMESTAMPADD(MONTH, -1, date '2021-01-01') `
    ```sql
    select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, count(distinct {customer_id_dim})
    from {table}
    where ({date_dim} >= '{某月初}' and {date_dim} <= '{某月末}') and {customer_id_dim} in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上个月初}' and {date_dim} <= '{上个月末}')
    group by 月份
    union
    {前i个月查询结果} -- 循环union i=1,2,...,K
    ```
    - 过去K个月每月新增客户数
    ```sql
    select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, count(distinct {customer_id_dim})
    from {table}
    where {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}'and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上个月初}' and {date_dim} <= '{上个月末}')
    group by 月份
    union
    {前i个月查询结果} -- 循环union i=1,2,...,K
    ```
    - 过去K个月每月流失客户数<font color=ferrari>【注意月份列是都是上个月的日期】</font>
    ```sql
    select (cast(year(timestampadd(month, 1, {date_dim})) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(month, 1, {date_dim})) as varchar), -2, 2)) as 月份, count(distinct {customer_id_dim}) [sum(metric)]
    from {table}
    where ({date_dim} >= '{上个月初}' and {date_dim} <= '{上个月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}')
    group by 月份
    union
    {前i个月查询结果} -- 循环union i=1,2,...,K
    ```
    - 过去K个月每月总客户数
    ```sql
    select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, count(distinct {customer_id_dim})
    from {table}
    where {date_dim} >= '{前K个月}' and {date_dim} <= '{本月}'
    group by 月份
    ```
    - 过去K个月每月客户数（同比）增长额
    ```sql
    select t1.月份 as 月份, 今年, 去年
    (select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, count(distinct {customer_id_dim}) as 今年
    from {table}
    where {date_dim} >= '{前K个月}' and {date_dim} <= '{本月}'
    group by 月份) t1
    join
    (select (cast(year(timestampadd(year, 1, {date_dim})) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(year, 1, {date_dim})) as varchar), -2, 2)) as 月份, count({customer_id_dim}) as 去年
    from {table}
    where {date_dim} >= '{去年前K个月}' and {date_dim} <= '{去年本月}'
    group by 月份) t2
    on t1.月份 = t2.月份
    ```
    - 过去K个月每月客户数（同比）增长率
    【同"过去K个月每月客户数（同比）增长额"】
    - （今年）累计新增客户数<font color=blue>【omit】</font>
    【同"客户数分析"-"（今年）累计新增客户数"】
    - （今年）累计流失客户数<font color=blue>【omit】</font>
    【同"客户数分析"-"（今年）累计新增客户数"】
    -  最近总客户数同比增长连续为正（负）的月份数
    【同"过去K个月每月客户数（同比）增长额"】
    -  最近净增客户数连续为正（负）的月份数
    ```sql
    select t1.月份 as 月份, 新增, 流失
    from 
    ({过去K个月每月新增客户数sql}) t1
    join
    ({过去K个月每月流失客户数sql}) t2
    on t1.月份 = t2.月份
    order by 月份
    ```
    <!-- 测试sql
    select t1.月份 as 月份, 新增, 流失
    from
    (select (cast(year(account_period) as varchar) || '-' ||  substring('0' + cast(month(account_period) as varchar), -2, 2)) as 月份, count(distinct customer_id) as 新增
    from data
    where account_period >= '2022-01-01' and account_period <= '2022-01-31'and customer_id not in (
    select customer_id
    from data
    where account_period >= timestampadd(month, -1, date '2022-01-01') and account_period <= timestampadd(month, -1, date '2022-01-31'))
    group by 月份
    union 
    select (cast(year(account_period) as varchar) || '-' ||  substring('0' + cast(month(account_period) as varchar), -2, 2)) as 月份, count(distinct customer_id) as 新增
    from data
    where account_period >= '2022-02-01' and account_period <= '2022-02-30'and customer_id not in (
    select customer_id
    from data
    where account_period >= timestampadd(month, -1, date '2022-02-01') and account_period <= timestampadd(month, -1, date '2022-02-28'))
    group by 月份) t1
    join
    (select (cast(year(timestampadd(month, 1, account_period)) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(month, 1, account_period)) as varchar), -2, 2)) as 月份, count(distinct customer_id) as 流失
    from data
    where account_period >= timestampadd(month, -1, date '2022-01-01') and account_period <= timestampadd(month, -1, date '2022-01-31')and customer_id not in (
    select customer_id
    from data
    where account_period >= '2022-01-01' and account_period <= '2022-01-31')
    group by 月份
    union 
    select (cast(year(timestampadd(month, 1, account_period)) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(month, 1, account_period)) as varchar), -2, 2)) as 月份, count(distinct customer_id) as 流失
    from data
    where account_period >= timestampadd(month, -1, date '2022-02-01') and account_period <= timestampadd(month, -1, date '2022-02-28')and customer_id not in (
    select customer_id
    from data
    where account_period >= '2022-02-01' and account_period <= '2022-02-28')
    group by 月份) t2
    on t1.月份 = t2.月份
    order by 月份
     -->
    -  本月存量、新增、流失客户占比
    ```sql
    -- 存量
    select 存量, 新增, 流失
    from
    (select '1' as id, count(distinct {customer_id_dim}) as 存量  -- 要用distinct去重
    from {table}
    where ({date_dim} >= '{本月初}' and {date_dim} <= '{本月末}') and {customer_id_dim} in  (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')) t1
    join
    -- 新增
    (select '1' as id, count(distinct {customer_id_dim}) as 新增
    from {table}
    where ({date_dim} >= '{本月初}' and {date_dim} <= '{本月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')) t2
    on t1.id = t2.id
    join
    -- 流失
    (select '1' as id, count(distinct {customer_id_dim}) as 流失
    from {table}
    where ({date_dim} >= '{上月初}' and {date_dim} <= '{上月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{本月初}' and {date_dim} <= '{本月末}')) t3
    on t2.id = t3.id
    ```
    <!-- 测试sql
    select 存量, 新增, 流失
    from
    (select '1' as id, count(distinct customer_id) as 存量
    from data
    where (account_period >= '2022-02-01' and account_period <= '2022-02-28') and customer_id in  (
    select customer_id
    from data
    where account_period >= '2022-01-01' and account_period <= '2022-01-31')) t1
    join
    -- 新增
    (select '1' as id, count(distinct customer_id) as 新增
    from data
    where (account_period >= '2022-02-01' and account_period <= '2022-02-28') and customer_id not in (
    select customer_id
    from data
    where account_period >= '2022-01-01' and account_period <= '2022-01-31')) t2
    on t1.id = t2.id
    join
    -- 流失
    (select '1' as id, count(distinct customer_id) as 流失
    from data
    where (account_period >= '2022-01-01' and account_period <= '2022-01-31') and customer_id not in (
    select customer_id
    from data
    where account_period >= '2022-02-01' and account_period <= '2022-02-28')) t3
    on t2.id = t3.id
     -->
    -  本月存量客户收入
    ```sql
    select sum({income_dim})
    from {table}
    where ({date_dim} >= '{本月初}' and {date_dim} <= '{本月末}') and {customer_id_dim} in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')
    ```
    -  本月存量客户收入（同比）增长额
    <font color=ferrari>[这里可以用join写，类似过去K个月每月客户数（同比）增长额]</font>
    ```sql
    select '{本月}' as 月份, sum({income_dim})
    from {table}
    where ({date_dim} >= '{本月初}' and {date_dim} <= '{本月末}') and {customer_id_dim} in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')
    union
    select '{去年本月}' as 月份, sum({income_dim})
    from {table}
    where ({date_dim} >= '{去年本月初}' and {date_dim} <= '{去年本月末}') and {customer_id_dim} in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{去年上月初}' and {date_dim} <= '{去年上月末}')
    ```
    <!-- 测试sql
    select '2022-02' as 月份, sum(income)
    from data
    where (account_period >= '2022-02-01' and account_period <= '2022-02-28') and customer_id in  (
    select customer_id
    from data
    where account_period >= '2022-01-01' and account_period <= '2022-01-31')
    union
    select '2021-02' as 月份, sum(income)
    from data
    where (account_period >= '2021-02-01' and account_period <= '2021-02-28') and customer_id in  (
    select customer_id
    from data
    where account_period >= '2021-01-01' and account_period <= '2021-01-31')
     -->
    -  本月存量客户收入（同比）增长率
    【同"本月存量客户收入（同比）增长额"】
    -  本月新增客户收入
    ```sql
    select sum({income_dim})
    from {table}
    where ({date_dim} >= '{本月初}' and {date_dim} <= '{本月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')
    ```
    -  本月新增客户收入（同比）增长额
    ```sql
    select '{本月}' as 月份, sum({income_dim})
    from {table}
    where ({date_dim} >= '{本月初}' and {date_dim} <= '{本月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')
    union
    select '{去年本月}' as 月份, sum({income_dim})
    from {table}
    where ({date_dim} >= '{去年本月初}' and {date_dim} <= '{去年本月末}') and {customer_id_dim} not in  (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{去年上月初}' and {date_dim} <= '{去年上月末}')
    ```
    -  本月新增客户收入（同比）增长率
    【同"本月新增客户收入（同比）增长额"】
    -  本月流失客户收入
    ```sql
    select sum({income_dim})
    from {table}
    where ({date_dim} >= '{上月初}' and {date_dim} <= '{上月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{本月初}' and {date_dim} <= '{本月末}')
    ```
    -  本月流失客户收入（同比）增长额
    ```sql
    select '{本月}' as 月份, sum({income_dim})
    from {table}
    where ({date_dim} >= '{上月初}' and {date_dim} <= '{上月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{本月初}' and {date_dim} <= '{本月末}')
    union
    select '{去年本月}' as 月份, sum({income_dim})
    from {table}
    where ({date_dim} >= '{去年上月初}' and {date_dim} <= '{去年上月末}') and {customer_id_dim} not in  (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{去年本月初}' and {date_dim} <= '{去年本月末}')
    ```
    -  本月流失客户收入（同比）增长率
    【同"本月流失客户收入（同比）增长额"】

- 展示形式
    - 过去K个月每月存量客户数 -- 折线图
    - 过去K个月每月新增客户数 -- 折线图
    - 过去K个月每月流失客户数 -- 折线图
    - 过去K个月每月总客户数 -- 折线图
    - 过去K个月每月客户数（同比）增长额 -- 折线图
    - 过去K个月每月客户数（同比）增长率 -- 折线图
    - （今年）累计新增客户数 -- 文字1
    - （今年）累计流失客户数 -- 文字1
    - 最近总客户数同比增长连续为正（负）的月份数 -- 文字2
    - 最近净增客户数连续为正（负）的月份数 -- 文字2
    - 本月存量、新增、流失客户占比 -- 饼图
    - 本月存量客户收入 -- 文字3（可以用re.sub('$', , )来写，这之下的取值都用val来代替，df.[self.metric].iloc[0]）
    - 本月存量客户收入（同比）增长额 -- 文字3
    - 本月存量客户收入（同比）增长率 -- 文字3
    - 本月新增客户收入 -- 文字3
    - 本月新增客户收入（同比）增长额 -- 文字3
    - 本月新增客户收入（同比）增长率 -- 文字3
    - 本月流失客户收入 -- 文字3
    - 本月流失客户收入（同比）增长额 -- 文字3
    - 本月流失客户收入（同比）增长率 -- 文字3


#### 7. 计划达成分析
> 要求
>
> - 整个客群（关键客群）今年累计收入，及其与计划目标的对比【计划目标是在数据库中，还是由用户自定义？答：demo数据中并未包含月度目标，我们可以另外构建一个202101到202303的月度目标值作为演示】
> - （关键客群）累计收入与同类客群的累计收入对比【关键客群是指具体一个客户吗？同类客群是说所有维度都一样的客群吗？答：可以不管此处的关键客群。在后面的关键客群分析中，我们再单独分析关键客群】
> - 整个客群（关键客群）今年1月起的累计收入（折线图，重复上面）
> - 整个客群（关键客群）过去K个月起的收入与计划目标的对比
> - 整个客群（关键客群）本月客户总数，及其与计划目标的对比
> - 整个客群（关键客群）过去K个月起的客户数与计划目标的对比
> - 整个客群（关键客群）过去K个月起的净新增客户数与计划目标的对比
> - 对其它客群的以上分析【其他客群指的是？答：对整体客群，此项不适用。可以忽略。此项只适用于关键客群和其它客群的对比。】

- 目标值模拟
  ```python
  import numpy as np
  import pandas as pd
  import datetime

  # 日期
  dates = pd.date_range(start='2021-01-01', end=datetime.date.today().strftime("%Y-%m-%d"), freq='MS')
  months = list(map(lambda date: date.strftime("%Y-%m-%d")[: -3], dates))
  # 收入
  obj_income = np.random.randint(15, 50, size=len(months))
  obj_income_per_date = dict(zip(months, obj_income))
  # 客户数
  obj_num_cust = np.random.randint(5500, 6500, size=len(months))
  obj_num_cust_per_date = dict(zip(months, obj_num_cust))
  # 净增客户数
  obj_net_growth_num_cust = np.random.randint(10, 100, size=len(months))
  obj_net_growth_num_cust_per_date = dict(zip(months, obj_net_growth_num_cust))

  # 具体数据匹配处理
  df['目标'] = df[metric].map({obj_per_date})
  ```

- 指标名
    - （今年）累计收入
    - （今年）每月累计收入
    - 过去K个月每月收入
    - 本月总客户数
    - 过去K个月每月总客户数
    - 过去K个月每月净增客户数

- 需要的查询
    - （今年）累计收入
    【同'收入分析'-'（今年）累计收入'】
    - （今年）每月累计收入
    【同"收入趋势分析"-"（今年）每月累计收入"】
    - 过去K个月每月收入
    【同"收入趋势分析"-"过去K个月每月收入"】
    - 本月总客户数
    【可以复写'客户发展分析'-'过去K个月每月总客户数'，设置K为0】
    ```sql
    select count(distinct {customer_id})
    from {table}
    where {date_dim} >= '{本月初}' and {date_dim} <= '{本月末}'
    ```
    - 过去K个月每月总客户数
    【同"客户发展分析"-"过去K个月每月总客户数"】
    - 过去K个月每月净增客户数
    【同"客户发展分析"-"最近净增客户数连续为正（负）的月份数"】

#### 8. 排名分析
> 要求
>
> -	按收入、收入绝对值增长、同比增长率、累计收入、累计收入增长率、<font color=ferrari>任务完成率【这个不清楚是什么】</font>、新增客户数、<font color=ferrari>新增客户金额【金额理解为收入】</font>、流失客户数、流失客户金额 从高到低对省分或等级或产品或行业排序，输出表格、top K和bottom K、和排序图

- 指标名
    - （按月）收入
    - （同比）收入增长额
    - （同比）收入增长率
    - （今年）累计收入
    - （今年）累计收入增长率
    - （按月）新增客户数
    - （按月）新增客户收入
    - （按月）流失客户数
    - （按月）流失客户收入

- 所需查询
    - （按月）收入
    【同"客群分维度分析"-"（按月）各收入指标计算"】
    - （同比）收入增长额
    【同"客群分维度分析"-"（按月）各收入指标计算"】
    - （同比）收入增长率
    【同"客群分维度分析"-"（按月）各收入指标计算"】
    - （今年）累计收入
    【同"客群分维度分析"-"（按月）各收入指标计算"】
    - （今年）累计收入增长率
    ```sql
    select {dim}, sum({income_dim}),
    case
    when {date_dim} >= '{今年初}' and {date_dim} <= '{本月末}' then '{本月}'
    when {date_dim} >= '{去年初}' and {date_dim} <= '{去年本月末}' then '{去年本月}'
    end as 月份
    from {table}
    group by {dim}, 月份
    ```
    - （按月）新增客户数
    【同"客群分维度分析"-"（按月）各客户数指标计算"】
    - （按月）新增客户收入
    【类同"客户发展分析"-"本月新增客户收入"】
    ```sql
    select {dim}, sum({income_dim})
    from {table}
    where ({date_dim} >= '{某月初}' and {date_dim} <= '{某月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{上月初}' and {date_dim} <= '{上月末}')
    group by {dim}
    ```
    - （按月）流失客户数
    【同"客群分维度分析"-"（按月）各客户数指标计算"】
    - （按月）流失客户收入
    【类同"客户发展分析"-"本月流失客户收入"】
    ```sql
    select {dim}, sum({income_dim})
    from {table}
    where ({date_dim} >= '{上月初}' and {date_dim} <= '{上月末}') and {customer_id_dim} not in (
    select {customer_id_dim}
    from {table}
    where {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}')
    group by {dim}
    ```


#### 9. 关键客群收入分析
> 要求
>
> - 集团要客在全体要客的收入（累计收入）占比（单值）
> - 集团要客与其它三个等级要客的收入（增长额、同比增长率、累计收入、客单价）的对比（柱状图）

- 指标名
    - 关键客群（按月）收入占比
    - 关键客群（今年）累计收入占比
    - 关键客群vs非关键客群：（按月）收入 <font color=ferrari>这里非关键客群包含1、2、3三个客群</font>
    - 关键客群vs非关键客群：（按月）收入（同比）增长额
    - 关键客群vs非关键客群：（按月）收入（同比）增长率
    - 关键客群vs非关键客群：（今年）累计收入
    - 关键客群vs非关键客群：（按月）客单价

- 所需查询
    - 关键客群（按月）收入占比
    ```sql
    select sum({income_dim}),
    case {customer_level_dim} 
    when 0 then '关键客群'
    else '其他客群'
    end as 客户等级
    from {table}
    where {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}'
    group by 客户等级
    ```
    - 关键客群（今年）累计收入占比
    ```sql
    select sum({income_dim}),  -- 可复用上面的sql（以时间为input）
    case {customer_level_dim}
    when 0 then '关键客群'
    else '其他客群'
    end as 客户等级
    from {table}
    where {date_dim} >= '{今年初}' and {date_dim} <= '{本月末}'
    group by 客户等级
    ```
    - 关键客群vs非关键客群：（按月）收入
    ```sql
    select sum({income_dim}),
    case {customer_level_dim}
    when 0 then '关键客群'
    when 1 then '一级客群'
    when 2 then '二级客群'
    when 3 then '三级客群'
    -- [when {customer_level_dim} = {选择的非关键客群} then '非关键客群'/ else '其他客群']  -- 可以尝试复用上面的sql（加上客群level的input）
    end as 客户等级
    from {table}
    where {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}'
    group by 客户等级
    having 客户等级 is not null
    ```
    - 关键客群vs非关键客群：（按月）收入（同比）增长额
    ```sql
    --type1
    select sum({income_dim}),
    case {customer_level_dim}
    when 0 then '关键客群'
    when 1 then '一级客群'
    when 2 then '二级客群'
    when 3 then '三级客群'
    -- [when {customer_level_dim} = {选择的非关键客群} then '非关键客群'/ else '其他客群']
    end as 客户等级,
    case 
    when {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}' then '今年'
    when {date_dim} >= '{去年某月初}' and {date_dim} <= '{去年某月末}' then '去年'
    end as 月份
    from {table}
    group by 客户等级, 月份
    having 客户等级 is not null and 月份 is not null
    ```
    <!-- 测试sql
    select t1.月份, t1.收入, t2.收入
    from 
    (select sum(income) as 收入,
    case 
    when account_period >= '2022-01-01' and account_period <= '2022-01-31' then '今年'
    when account_period >= '2021-01-01' and account_period <= '2021-01-31' then '去年'
    end as 月份
    from data
    where customer_level = 0 -- 关键客群
    group by 月份) t1
    join
    (select sum(income) as 收入,
    case 
    when account_period >= '2022-01-01' and account_period <= '2022-01-31' then '今年'
    when account_period >= '2021-01-01' and account_period <= '2021-01-31' then '去年'
    end as 月份
    from data
    where 1=1 and customer_level = 1
    group by 月份) t2
    on t1.月份 = t2.月份
     -->
    <!-- 另一个版本的sql
    ```sql
    select t1.月份, t1.收入 as 关键客群, t2.收入 as {整体/level:1/2/3}客群
    from
    (select sum({income_dim}) as 收入,
    case 
    when {date_dim} >= {某月初} and {date_dim} <= {某月末} then '今年'
    when {date_dim} >= {去年某月初} and {date_dim} <= {去年某月末} then '去年'
    end as 月份
    from {table}
    where {customer_level_dim} = 0 -- 关键客群
    group by 月份) t1
    join
    (select sum({income_dim}) as 收入,
    case 
    when {date_dim} >= {某月初} and {date_dim} <= {某月末} then '今年'
    when {date_dim} >= {去年某月初} and {date_dim} <= {去年某月末} then '去年'
    end as 月份
    from {table}
    where 1=1 [and {customer_level_dim} = {选择的非关键客群}]  -- 如果有的话
    group by 月份) t2
    on t1.月份 = t2.月份
    ``` -->
    - 关键客群vs非关键客群：（按月）收入（同比）增长率
    【同上】
    - 关键客群vs非关键客群：（今年）累计收入
    ```sql
    select sum({income_dim}),
    case {customer_level_dim}
    when 0 then '关键客群'
    when 1 then '一级客群'
    when 2 then '二级客群'
    when 3 then '三级客群'
    end as 客户等级
    from {table}
    where {date_dim} >= '{今年初}' and {date_dim} <= '{本月末}'
    group by 客户等级
    ```
    - 关键客群vs非关键客群：（按月）客单价
    ```sql
    select avg(总收入),
    case {customer_level_dim}
    when 0 then '关键客群'
    when 1 then '一级客群'
    when 2 then '二级客群'
    when 3 then '三级客群'
    -- [when {customer_level_dim} = {选择的非关键客群} then '非关键客群'/ else '其他客群']
    end as 客户等级
    from (
      select {cusomter_id_dim}, {customer_level_dim}, sum({income_dim}) as 总收入
      from {table}
      where {date_dim} >= '{某月初}' and {date_dim} <= '{某月末}'
      group by {cusomter_id_dim}, {customer_level_dim}
    )
    group by 客户等级
    having 客户等级 is not null
    ```


#### 10. 关键客群客户数分析（略）


#### 11. 关键客群趋势分析
> 要求
>
> - 关键客群在整体客群过去K个月的收入占比
> - 关键客群与整体客群过去K个月的收入同比增长率的对比
> - 关键客群与其它非关键客群过去K个月的收入同比增长率的对比 （若类别<=5）
> - 关键客群的收入占比连续提升（下降）的月份数

- 指标名
    - 关键客群过去K个月收入占比
    - 关键客群收入占比连续提升（下降）的月份数
    - 关键客群vs整体客群：过去K个月收入（同比）增长率
    - 关键客群vs非关键客群：过去K个月收入（同比）增长率

- 所需查询
    - 关键客群过去K个月收入占比
    ```sql
    select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, sum({income_dim}),
    case {customer_level_dim}
    when 0 then '关键客群'
    else '其他客群'
    end as 客户等级
    from {table}
    where {date_dim} >= '{前K个月初}' and {date_dim} <= '{本月末}'
    group by 客户等级, 月份
    having 客户等级 is not null
    ```
    <!-- 另一种方法
    ```sql 
    select t1.月份, t1.收入 as 关键客群收入, t2.收入 as 整体收入
    (select row_number() over(order by 收入) as id, (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, sum({income_dim}) as 收入
    from {table}
    where {date_dim} >= '{前K个月}' and {date_dim} <= '{本月}' and {customer_level_dim} = 0
    group by 月份) t1
    join
    (select row_number() over(order by 收入) as id, (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, sum({income_dim}) as 收入
    from {table}
    where {date_dim} >= '{前K个月}' and {date_dim} <= '{本月}'
    group by 月份) t2
    on t1.id = t2.id
    ``` -->
    - 关键客群收入占比连续提升（下降）的月份数
    【复写上面sql，修改K值为默认最大K值】
    <!-- 【复写上面sql，修改K值为默认最大K值】 -->
    - 关键客群vs整体客群：过去K个月收入（同比）增长率
    ```sql
    -- 可以复写上面sql，以时间为input，获取两个sql，然后join
    select t1.月份 as 月份, t1.客户等级 as 客户等级, 今年, 去年
    from
    (select (cast(year({date_dim}) as varchar) || '-' ||  substring('0' + cast(month({date_dim}) as varchar), -2, 2)) as 月份, sum({income_dim}) as 今年,
    case {customer_level_dim}
    when 0 then '关键客群'
    else '其他客群'
    end as 客户等级
    from {table}
    where {date_dim} >= '{前K个月初}' and {date_dim} <= '{本月末}'
    group by 客户等级, 月份
    having 客户等级 is not null) t1
    join
    (select (cast(year(timestampadd(year, 1, {date_dim})) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(year, 1, {date_dim})) as varchar), -2, 2)) as 月份, sum({income_dim}) as 去年,
    case {customer_level_dim}
    when 0 then '关键客群'
    else '其他客群'
    end as 客户等级
    from {table}
    where {date_dim} >= '{去年前K个月初}' and {date_dim} <= '{去年本月末}'
    group by 客户等级, 月份
    having 客户等级 is not null) t2
    on concat(t1.月份, t1.客户等级) = concat(t2.月份, t2.客户等级)
    ```
    <!-- 测试sql
    select t1.月份 as 月份, t1.客户等级 as 客户等级, 今年, 去年
    from
    (select (cast(year(account_period) as varchar) || '-' ||  substring('0' + cast(month(account_period) as varchar), -2, 2)) as 月份, sum(income) as 今年,
    case customer_level
    when 0 then '关键客群'
    else '其他客群'
    end as 客户等级
    from data
    where account_period >= '2022-01-01' and account_period <= '2022-06-30'
    group by 客户等级, 月份
    having 客户等级 is not null) t1
    join
    (select (cast(year(timestampadd(year, 1, account_period)) as varchar) || '-' ||  substring('0' + cast(month(timestampadd(year, 1, account_period)) as varchar), -2, 2)) as 月份, sum(income) as 去年,
    case customer_level
    when 0 then '关键客群'
    else '其他客群'
    end as 客户等级
    from data
    where account_period >= '2021-01-01' and account_period <= '2021-06-30'
    group by 客户等级, 月份
    having 客户等级 is not null) t2
    on concat(t1.月份, t1.客户等级) = concat(t2.月份, t2.客户等级) -->
    <!-- 【复写上面sql，用re在第二个where处添加条件】 -->
    - 关键客群vs非关键客群：过去K个月收入（同比）增长率
    【复写上面sql，修改case when语句】


#### 12. 关键客群发展分析
> 要求
>
> - 关键客群过去K个月的（存量客户数、新增客户数、流失客户数、总客户数、（同比）客户增长数、（同比）客户增长率、<font color=ferrari>占比【理解为每月存量、新增、流失客户占比】</font>）
> - 关键客群今年1月起的累计新增客户数、累计流失客户数【这个分析是否跟上面的过去K个月的分析有重复？答：不一样，年度累计一定本年开始，如从1月开始，K则可能跨年度】
> - 关键客群最近总客户数同比增长连续为正（负）的月份数
> - 关键客群最近净增（新增-流失）客户数连续为正（负）的月份数
> - 关键客群本月存量、新增、流失客群各自的收入、收入同比增长率、占比、收入增幅

- 指标名【除了有一个之前没有的，其他都可以复写"客户发展分析"中的指标，用re在where处加条件】
    - 关键客群过去K个月每月存量客户数
    - 关键客群过去K个月每月新增客户数
    - 关键客群过去K个月每月流失客户数
    - 关键客群过去K个月每月总客户数
    - 关键客群过去K个月每月客户数（同比）增长额
    - 关键客群过去K个月每月客户数（同比）增长率
    - 关键客群过去K个月存量、新增、流失客户占比
    ```sql
    select t1.月份 as 月份, 存量, 新增, 流失
    from
    -- 存量
    (【'客户发展分析'-'过去K个月每月存量客户数'】) t1
    join
    -- 新增
    (【'客户发展分析'-'过去K个月每月新增客户数'】) t2
    on t1.id = t2.id
    join
    -- 流失
    (【'客户发展分析'-'过去K个月每月流失客户数'】) t3
    on t2.id = t3.id
    ```
    - 关键客群（今年）累计新增客户数
    - 关键客群（今年）累计流失客户数
    - 关键客群最近总客户数同比增长连续为正（负）的月份数
    - 关键客群最近净增客户数连续为正（负）的月份数
    - 关键客群本月存量、新增、流失客户占比
    - 关键客群本月存量客户收入
    - 关键客群本月存量客户收入（同比）增长额
    - 关键客群本月存量客户收入（同比）增长率
    - 关键客群本月新增客户收入
    - 关键客群本月新增客户收入（同比）增长额
    - 关键客群本月新增客户收入（同比）增长率
    - 关键客群本月流失客户收入
    - 关键客群本月流失客户收入（同比）增长额
    - 关键客群本月流失客户收入（同比）增长率


#### 13. 关键客群计划达成分析
> 要求
>
> - 关键客群今年累计收入，及其与计划目标的对比
> - 关键客群累计收入与同类客群的累计收入对比<font color=ferrari>【这里的目标是什么呢？是比例值吗？】</font>
> - 关键客群今年1月起的累计收入（折线图，重复上面）
> - 关键客群过去K个月起的收入与计划目标的对比
> - 关键客群本月客户总数【有点疑惑，要先弄清关键客群的定义和在数据表中的呈现形式。答：Level=0的是关键客户】，及其与计划目标的对比
> - 关键客群过去K个月起的客户数与计划目标的对比
> - 关键客群过去K个月起的净新增客户数与计划目标的对比

- 指标名【全部都可以复写"计划达成分析"中的指标，用re在where处加条件】
    - 关键客群（今年）累计收入
    - <font color=blue>{待定指标}</font>
    - 关键客群（今年）每月累计收入
    - 关键客群过去K个月每月收入
    - 关键客群本月总客户数
    - 关键客群过去K个月每月客户数
    - 关键客群过去K个月每月净增客户数


#### 14. 关键客群排名分析
> 要求
>
> - 分类维度后【这里的意思是对其他客群进行排序吗？答：我修改一下，把每个客群，就是Level=0-3的客群，分别做各指标的排名】，按收入、收入绝对值增长、同比增长率、累计收入、累计收入增长率、任务完成率、新增客户数、新增客户金额、流失客户数、流失客户金额 从高到低对省分或等级或产品或行业排序，输出表格、top K和bottom K、和排序图

- 指标名【全部都可以复写"排名分析"中的指标，用re在where处加条件】
    - 指定客群（按月）收入<font color=ferrari>【指定客群可任选：关键客群和其他客群的其一】</font>
    - 指定客群（同比）收入增长额
    - 指定客群（同比）收入增长率
    - 指定客群（今年）累计收入
    - 指定客群（今年）累计收入增长率
    - 指定客群（按月）新增客户数
    - 指定客群（按月）新增客户收入
    - 指定客群（按月）流失客户数
    - 指定客群（按月）流失客户收入
