import streamlit as st
from streamlit_modal import Modal
import numpy as np


# define modal to set a popup
my_modal = Modal(title='', key='my_modal', max_width=1000)

# initialize the session state of the button
if 'confirm_add' not in st.session_state:
    st.session_state['confirm_add'] = False

# callback function
def add_btn_click():
    st.session_state['confirm_add'] = True



with st.container():
    filter_group, filter_name, add_record = st.columns([0.4, 0.4, 0.2])
    with filter_group:
        st.selectbox('Select a number', [1,2,3,4,5], key='1')
    with filter_name:
        st.selectbox('Select a number', [1,2,3,4,5], key='2')
    with add_record:
        if st.button('Add segment'):
            with my_modal.container():
                st.markdown("""
                            你好
                            
                            我是个弹窗
                            """)
                select_group = st.selectbox('请选择段落类型：', ['收入分析', '客户数分析', '客单价分析'])
                
                if select_group == '收入分析':
                    st.markdown("""你好，我是个弹窗""")
                st.button('确定', key='confirm_add', on_click=add_btn_click)

if 'records' not in globals():
    records = []

# operation after add_segment
if st.session_state['confirm_add']:
    record = []
    if records:
        record.append(records[0])
    else:
        records.append(1)
    record
    st.session_state['confirm_add'] = False
    # st.experimental_rerun()

st.write(records)

order_col, name_col, group_col, desc_col, oper_col = st.columns(5, gap='small')
with order_col:
    st.subheader('全选')
    if records:
        st.write(records[0])
with name_col:
    st.subheader('名称')
    if records:
        st.write(records[1])
with group_col:
    st.subheader('分组')
    if records:
        st.write(records[2])
with desc_col:
    st.subheader('描述')
    if records:
        st.write(records[3])
with oper_col:
    st.subheader('操作')
    if records:
        st.write(records[4])

