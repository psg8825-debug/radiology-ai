import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import datetime

# [보안 설정] Streamlit Secrets에서 상자(이름표)를 가져옵니다.
# 실제 키 값은 GitHub 코드가 아니라 Streamlit 웹사이트 설정창에 넣으셔야 합니다.
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    ADMIN_PWD = st.secrets["ADMIN_PASSWORD"]
except KeyError as e:
    st.error(f"Secrets 설정이 누락되었습니다: {e}")
    st.stop()

# AI 모델 및 데이터베이스 초기화
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 사이드바 메뉴 구성
st.sidebar.title("🩺 Chest Logic AI")
menu = st.sidebar.radio("메뉴 선택", ["Case Analysis (User)", "Admin Review (교수님 전용)"])

# --- [1] 사용자 페이지: 케이스 분석 ---
if menu == "Case Analysis (User)":
    st.title("🫁 Radiology AI Thought Partner")
    st.write("환자 정보와 영상 소견을 입력하면 'Chest Logic'에 따라 분석합니다.")

    # 통합 입력창 (Info + Findings)
    user_input = st.text_area(
        "Patient History & Radiology Findings", 
        placeholder="예: 52/M, Non-smoker, Chronic cough.\nFindings: Patchy GGOs in peripheral distribution...",
        height=350
    )

    if st.button("Run Analysis"):
        if user_input:
            with st.spinner("교수님의 로직으로 심층 분석 중..."):
                # AI에게 전달할 프롬프트 설정
                instruction = "너는 대학병원 영상의학과 교수다. 다음 입력을 바탕으로 전문적인 판독문, 진단 근거(Reasoning), 추천 사항을 작성하라."
                full_prompt = f"{instruction}\n\n[Input Data]\n{user_input}"
                
                # AI 호출
                response = model.generate_content(full_prompt)
                ai_result = response.text
                
                # 결과 출력
                st.markdown("---")
                st.markdown("### 📋 Analysis Result")
                st.write(ai_result)
                
                # 데이터베이스(Supabase) 저장
                try:
                    supabase.table("analysis_logs").insert({
                        "user_input": user_input,
                        "ai_output": ai_result
                    }).execute()
                    st.success("로그가 성공적으로 기록되었습니다.")
                except Exception as e:
                    st.error(f"데이터 저장 중 오류 발생: {e}")
        else:
            st.warning("분석할 내용을 입력해 주세요.")

# --- [2] 관리자 페이지: 교수님 전용 검토 ---
elif menu == "Admin Review (교수님 전용)":
    st.title("👨‍🏫 Review Dashboard")
    
    # 관리자 암호 확인
    input_pwd = st.text_input("관리자 암호를 입력하세요", type="password")
    
    if input_pwd == ADMIN_PWD:
        st.success("인증 성공. 사용자 로그를 불러옵니다.")
        
        # DB에서 데이터 가져오기 (최신순)
        res = supabase.table("analysis_logs").select("*").order("created_at", desc=True).execute()
        
        if res.data:
            for log in res.data:
                # 각 케이스를 접이식(Expander) 메뉴로 표시
                with st.expander(f"Case Log: {log['created_at'][:16]}"):
                    st.markdown("**[User Input]**")
                    st.info(log['user_input'])
                    
                    st.markdown("**[AI Output]**")
                    st.write(log['ai_output'])
                    
                    # 교수님 피드백 입력 및 저장
                    feedback = st.text_input("교수님 검토 의견", value=log.get('admin_feedback', '') or '', key=f"f_{log['id']}")
                    if st.button("의견 저장", key=f"b_{log['id']}"):
                        supabase.table("analysis_logs").update({"admin_feedback": feedback}).eq("id", log['id']).execute()
                        st.toast("검토 의견이 반영되었습니다!")
        else:
            st.write("아직 기록된 데이터가 없습니다.")
            
    elif input_pwd != "":
        st.error("암호가 틀렸습니다.")
