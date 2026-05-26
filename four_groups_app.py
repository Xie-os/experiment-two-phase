import streamlit as st
import os
import json
import re
from datetime import datetime
from openai import OpenAI

# ==================== 页面设置 ====================
st.set_page_config(page_title="设计实验", layout="wide")

# ==================== 用户编号输入与分组 ====================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "group" not in st.session_state:
    st.session_state.group = None

if st.session_state.user_id is None:
    st.markdown("### 欢迎参与设计实验")
    st.markdown("""
    本实验包含**两个设计阶段**，请按页面提示完成任务。

**任务背景**：  
    每个人的手机几乎都有手机壳。请在不添加任何芯片或电子元件，单纯依靠物理结构、材质或造型创意，为手机壳增加一个实用的“非电子”附加功能（例如解决：刷剧手酸、躺着砸脸、卡片易丢、无聊想解压等生活小烦恼）。
    
系统将根据你的编号自动分配流程，部分阶段可能需要独立完成，部分阶段可借助AI助手。
    """)
    uid_input = st.text_input("请输入你的用户编号（例如 G1-01）：")
    if st.button("开始实验"):
        if uid_input.strip() == "":
            st.warning("编号不能为空")
        else:
            # 从编号中提取组号，例如 "G1-01" -> 1, "G2-05" -> 2
            match = re.search(r'G(\d)', uid_input.strip())
            if match:
                st.session_state.group = int(match.group(1))
            else:
                st.error("编号格式错误，请输入类似 G1-01 的格式")
                st.stop()

            st.session_state.user_id = uid_input.strip()
            st.session_state.phase = 1
            st.session_state.phase1_text = ""
            st.session_state.phase2_text = ""
            st.session_state.messages = []
            st.session_state.greeted = False
            st.rerun()
    st.stop()

# ==================== 根据组别设置AI开关 ====================
group = st.session_state.group
# 组1: 纯AI (两个阶段都有AI)
# 组2: 纯人工 (两个阶段都无AI)
# 组3: 阶段一AI, 阶段二人工
# 组4: 阶段一人工, 阶段二AI
ai_phase1 = (group == 1 or group == 3)
ai_phase2 = (group == 1 or group == 4)

# ==================== 连接 DeepSeek API ====================
@st.cache_resource
def get_client():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = st.secrets.get("DEEPSEEK_API_KEY")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
client = get_client()

# ==================== AI问候工具函数 ====================
def activate_ai_greeting():
    if not st.session_state.greeted:
        with st.spinner("AI正在准备..."):
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "你好，请用一句话打招呼，开启一段协作对话。"}],
                temperature=0.2,
                max_tokens=200
            )
        st.session_state.messages.append({"role": "assistant", "content": resp.choices[0].message.content})
        st.session_state.greeted = True

# ==================== 阶段一界面 ====================
if st.session_state.phase == 1:
    title = "阶段一"
    if ai_phase1:
        title += "（有AI助手）"
    else:
        title += "（独立完成）"
    st.title(title)

    st.markdown("### 📋 任务说明")
    st.markdown("""
    **阶段一：问题发现与初步构思**  
    请你围绕“设计手机壳非电子的附加功能”这一主题，完成以下内容：  
    请看着你现在的手机，发挥想象力：在不添加任何芯片或电子元件的前提下，单纯靠物理结构、材质或造型创意，手机壳还能揉合什么好玩、有用的功能？请尽可能快地列出多个手机壳创意改造点子（一句话一个，越多越好）。
    - 若当前阶段提供AI助手，你可以自由与AI讨论并整合建议到编辑区。
    - 若当前阶段独立完成，请依靠自己的知识和搜集相关资料作答。
    """)

    if ai_phase1:
        activate_ai_greeting()
        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.subheader("💬 与AI讨论区")
            for msg in st.session_state.messages:
                if msg["role"] in ["user", "assistant"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
            user_input = st.chat_input("输入你的想法...")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
                with st.spinner("AI思考中..."):
                    resp = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=st.session_state.messages,
                        temperature=0.2,
                        max_tokens=2000
                    )
                ai_msg = resp.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                with st.chat_message("assistant"):
                    st.markdown(ai_msg)
        with col_right:
            st.subheader("📝 阶段一作答区")
            st.caption("在此整理你的思路（可结合AI建议）。用【】括起**你自己的原创想法**，最终提交时会显示为红色。")
            p1 = st.text_area("答案", value=st.session_state.phase1_text, height=400, key="p1")
            st.session_state.phase1_text = p1
    else:
        st.subheader("📝 阶段一作答区（请独立完成，不要使用任何AI工具）")
        p1 = st.text_area("答案", value=st.session_state.phase1_text, height=400, key="p1")
        st.session_state.phase1_text = p1

    st.divider()
    if st.button("保存并进入阶段二"):
        if st.session_state.phase1_text.strip() == "":
            st.warning("请至少写一些内容再继续")
        else:
            if ai_phase1:
                st.session_state.messages = []
                st.session_state.greeted = False
            st.session_state.phase = 2
            st.rerun()
    st.stop()

# ==================== 阶段二界面 ====================
if st.session_state.phase == 2:
    title = "阶段二"
    if ai_phase2:
        title += "（有AI助手）"
    else:
        title += "（独立完成）"
    st.title(title)

    st.markdown("### 📋 任务说明")
    st.markdown("""
    **阶段二：方案细化与完整呈现**  
    基于阶段一的构思，请进一步深化你的设计方案，包含以下要点：  
   请从刚才阶段一的点子中选出一个。分点罗列，详细明这个手机壳的附加功能具体是如何使用或应用的。例如：功能详述、结构/材质说明、使用场景和优势等等。
    - 若当前阶段提供AI助手，你可以自由与AI讨论并整合建议。
    - 若独立完成，请依靠自己的思考作答。
    - 阶段一的内容已自动带入，你可以在此基础上修改完善。
    """)

    initial_text = st.session_state.phase1_text
    if st.session_state.phase2_text:
        initial_text += "\n\n" + st.session_state.phase2_text

    if ai_phase2:
        activate_ai_greeting()
        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.subheader("💬 与AI讨论区")
            for msg in st.session_state.messages:
                if msg["role"] in ["user", "assistant"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
            user_input = st.chat_input("输入你的想法...")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
                with st.spinner("AI思考中..."):
                    resp = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=st.session_state.messages,
                        temperature=0.2,
                        max_tokens=2000
                    )
                ai_msg = resp.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                with st.chat_message("assistant"):
                    st.markdown(ai_msg)
        with col_right:
            st.subheader("📝 阶段二作答区")
            st.caption("可整合阶段一内容和AI建议。请用【】括起**你自己的原创想法**，提交后将显示为红色，以区别于AI的建议。")
            p2 = st.text_area("答案", value=initial_text, height=400, key="p2")
            st.session_state.phase2_text = p2
    else:
        st.subheader("📝 阶段二作答区（请独立完成，不要使用任何外部工具）")
        st.caption("阶段一的内容已显示，你可以继续编辑。")
        p2 = st.text_area("答案", value=initial_text, height=400, key="p2")
        st.session_state.phase2_text = p2

    if st.button("✅ 提交最终方案"):
        final_text = st.session_state.phase2_text
        if ai_phase2:
            display = re.sub(r'【(.*?)】', r'<span style="color:red">【\1】</span>', final_text)
            st.markdown("###方案预览（红色部分为你自己的想法）")
            st.markdown(display, unsafe_allow_html=True)
        else:
            st.markdown("### 你提交的内容")
            st.markdown(final_text)

        data = {
            "user_id": st.session_state.user_id,
            "group": st.session_state.group,
            "phase1_text": st.session_state.phase1_text,
            "phase2_text": st.session_state.phase2_text,
            "messages": st.session_state.messages if (ai_phase1 or ai_phase2) else [],
            "timestamp": datetime.now().isoformat()
        }
        import tempfile
        filename = os.path.join(tempfile.gettempdir(), f"experiment_{st.session_state.user_id}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.success("方案已提交，感谢你的参与！")
        st.info("你现在可以关闭本页面。")
        st.stop()