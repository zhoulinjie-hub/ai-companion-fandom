"""
streamlit:开源的python库，构建交互式web网站(数据科学、机器学习)
    1. 安装 streamlit：pip install streamlit
    2. 在 Python 文件中引入 streamlit 模块
    3. 基于 streamlit 中提供的 API 来构建 Web 应用
    4. 运行程序：streamlit run xxxx.py（http://localhost:8501/）
"""

import streamlit as st

# 设置页面的配置项
st.set_page_config(
    page_title="streamlit入门",
    page_icon="🧊",
    layout="wide", #布局
    initial_sidebar_state="expanded", #侧边栏
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

#标题
st.title("Streamlit 入门演示")
st.header("Streamlit 一级标题")
st.subheader("Streamlit 二级标题")

#段落文字
st.write("布偶猫，被誉为“猫中仙女”，以其优雅的外表和温顺的性格成为最受欢迎的宠物猫之一。")
st.write("它们体型较大，成年后可达10-20斤，拥有深邃的蓝色眼眸和柔顺的中长毛，毛色多为双色、手套色或重点色，宛如戴着一副可爱的面具。最迷人的是其松弛柔软的体态……")
st.write("性格是布偶猫最大的魅力。它们极度温顺、安静且粘人，被称为“小狗猫”，喜欢跟随主人走动，享受陪伴。它们通常脾气很好，忍耐力强，能与儿童和其他宠物友好相处……")
st.write("养护方面，需要定期梳理其丰厚毛发以防止打结，并提供足够的关注与互动。拥有一只布偶猫，就如同拥有了一位温柔优雅、终生依恋的毛茸茸家人。")

#图片
st.image("AI应用/resource/img.png")

#logo
st.logo("AI应用/resource/img.png")

#表格
student_data = {
    "姓名": ["王林", "李慕婉", "贝罗", "莫厉海", "石萧"],
    "学号": ["20260001", "20260002", "20260003", "20260004", "20260005"],
    "语文": [98, 90, 59, 29, 80],
    "数学": [88, 78, 65, 70, 39],
    "英语": [99, 89, 87, 59, 62],
    "总分": [285, 257, 211, 158, 181]
}
st.table(student_data)

#输入框
name = st.text_input("请输入姓名")
st.write(f"您输入的姓名为：{name}")

password = st.text_input("请输入密码", type = "password")
st.write(f"您输入的密码为：{password}")

gender = st.radio("请输入您的性别", ["男", "女", "未知"],index = 1)
st.write(f"您的性别为: {gender}")

