import streamlit as st
import hashlib
import io
import os
from datetime import datetime
from PIL import Image

# --- 尝试加载 pdf417 库 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("找不到 pdf417 库！请在环境运行: `pip install pdf417`")
    st.stop()

# --- 页面配置 ---
st.set_page_config(page_title="AAMVA WI DL Generator", layout="wide")
st.title("🆔 AAMVA PDF417 生成器 (WI DL Version)")
st.markdown("基于校验过的核心算法，无逻辑修改版。")
st.markdown("---")

# ==========================================
# 1. 辅助函数 (完全保留原始逻辑)
# ==========================================

def convert_height_to_inches(height_str):
    # [逻辑保持原样]
    height_str = height_str.strip()
    if len(height_str) < 3:
        return f"{int(height_str):03d}"
    try:
        inches_part = int(height_str[-2:])
        feet_part = int(height_str[:-2])
        total_inches = (feet_part * 12) + inches_part
        return f"{total_inches:03d}"
    except ValueError:
        return height_str

# ==========================================
# 2. Streamlit 侧边栏：对应原脚本的 get_input
# ==========================================
with st.sidebar:
    st.header("📝 数据输入")
    
    # 使用原脚本的默认值作为控件的 value
    
    with st.expander("1. 身份信息", expanded=True):
        ui_fname = st.text_input("名 (First Name)", "ANTHONY")
        ui_mname = st.text_input("中间名 (Middle Name)", "NONE")
        ui_lname = st.text_input("姓 (Last Name)", "ALBERT")

    with st.expander("2. 地址信息", expanded=True):
        ui_addr = st.text_input("街道地址", "W169N10741 REDWOOD LN")
        ui_city = st.text_input("城市", "GERMANTOWN")
        ui_zip = st.text_input("邮编 (输入5位自动补0000)", "530223971")

    with st.expander("3. 日期 (支持 / 格式)", expanded=True):
        ui_dob = st.text_input("出生日期 (DOB)", "08/08/1998")
        ui_exp = st.text_input("过期日期 (EXP)", "08/08/2030")
        ui_iss = st.text_input("签发日期 (ISS)", "06/06/2022")

    with st.expander("4. 证件详情", expanded=True):
        ui_dln = st.text_input("驾照号码 (DL Number)", "A4160009828800")
        ui_class = st.text_input("类型 (CLASS)", "D")
        ui_rest = st.text_input("限制 (REST)", "NONE")
        ui_end = st.text_input("背书 (END)", "NONE")
        # 原脚本指明 DD/DCF 若包含斜杠将被保留
        ui_dd = st.text_input("鉴别码 (DD/DCF)", "OTAJI2022060615751296")
        ui_icn = st.text_input("库存控制号 (ICN/DCK)", "0130100287726422")

    with st.expander("5. 选项与特征", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            ui_realid = st.selectbox("REAL ID?", ["Y", "N"], index=0)
            ui_vet = st.selectbox("退伍军人?", ["Y", "N"], index=1) # 默认 N
        with col2:
            ui_donor = st.selectbox("器官捐献?", ["Y", "N"], index=1) # 默认 N
            ui_sex = st.selectbox("性别 (1=男, 2=女)", ["1", "2"], index=0)
            
        ui_height_raw = st.text_input("身高 (如 510)", "510")
        ui_eyes = st.text_input("眼睛 (如 BRN)", "BRN")

# ==========================================
# 3. 核心生成逻辑
# ==========================================

# 创建两列布局
col_preview, col_debug = st.columns([1, 1])

with col_preview:
    st.subheader("生成结果")
    run_btn = st.button("🚀 生成条码", type="primary", use_container_width=True)

if run_btn:
    # --- A. 模拟原脚本的数据清洗逻辑 ---
    def clean_input(val, default, protect_slashes=False):
        val = val.strip().upper()
        if not val: val = default
        if not protect_slashes and "/" in val:
            val = val.replace("/", "")
        return val

    # 应用清洗逻辑
    first_name = clean_input(ui_fname, "ANTHONY")
    middle_name = clean_input(ui_mname, "NONE")
    last_name = clean_input(ui_lname, "ALBERT")
    
    address = clean_input(ui_addr, "W169N10741 REDWOOD LN")
    city = clean_input(ui_city, "GERMANTOWN")
    
    zip_temp = clean_input(ui_zip, "530223971")
    zip_code = zip_temp.replace("-", "").strip()
    if len(zip_code) == 5: zip_code += "0000"
    
    dob = clean_input(ui_dob, "08/08/1998")
    exp_date = clean_input(ui_exp, "08/08/2030")
    iss_date = clean_input(ui_iss, "06/06/2022")
    
    dl_number = clean_input(ui_dln, "A4160009828800")
    class_code = clean_input(ui_class, "D")
    rest_code = clean_input(ui_rest, "NONE")
    end_code = clean_input(ui_end, "NONE")
    # 原脚本 protect_slashes=True
    dd_code = clean_input(ui_dd, "OTAJI2022060615751296", protect_slashes=True)
    icn_code = clean_input(ui_icn, "0130100287726422")
    
    real_id_option = clean_input(ui_realid, "Y")
    dda_code = "F" if real_id_option == "Y" else "N"
    
    vet_option = clean_input(ui_vet, "N")
    donor_option = clean_input(ui_donor, "N")
    
    sex = clean_input(ui_sex, "1")
    height_input = clean_input(ui_height_raw, "510")
    height = convert_height_to_inches(height_input)
    eyes = clean_input(ui_eyes, "BRN")

    # --- B. 数据构建 (严格保留原始结构) ---
    
    iin = "636031"
    aamva_version = "08"
    jurisdiction_version = "01" 
    num_entries = "02" 
    
    # 1. DL Subfile
    subfile_dl_base = (
        f"DL"                        
        f"DCA{class_code}\x0a"       
        f"DCB{rest_code}\x0a"        
        f"DCD{end_code}\x0a"   
        f"DBA{exp_date}\x0a"
        f"DCS{last_name}\x0a"        
        f"DAC{first_name}\x0a"  
        f"DAD{middle_name}\x0a"      
        f"DBD{iss_date}\x0a"        
        f"DBB{dob}\x0a"
        f"DBC{sex}\x0a"
        f"DAY{eyes}\x0a"      
        f"DAU{height} IN\x0a"      
        f"DAG{address}\x0a"          
        f"DAI{city}\x0a"             
        f"DAJWI\x0a"                
        f"DAK{zip_code}  \x0a"        
        f"DAQ{dl_number}\x0a"        
        f"DCF{dd_code}\x0a"        
        f"DCGUSA\x0a"             
        f"DDEN\x0a"                  
        f"DDFN\x0a"                  
        f"DDGN\x0a"                  
        f"DCK{icn_code}\x0a"
        f"DDA{dda_code}\x0a"
    )

    # 2. ZW Calculation
    zwa_payload = f"{dl_number}{dob}{icn_code}".encode('utf-8')
    zwa_hash = hashlib.sha256(zwa_payload).hexdigest()
    zwa_prefix = "99" if int(zwa_hash[0], 16) % 2 == 0 else "58"
    zwa_suffix = str(int(zwa_hash[-8:], 16)).zfill(9)[:9]
    zwa_final_val = f"{zwa_prefix}{zwa_suffix}"
    
    # 3. Tail Items
    tail_items = [f"DDB09012015"] 
    if vet_option == "Y":
        tail_items.append("DDL1")
    if donor_option == "Y":
        tail_items.append("DDK1")
    
    subfile_dl_tail = "\x0a".join(tail_items)
    
    # Final DL Subfile
    subfile_dl_final = subfile_dl_base + subfile_dl_tail + "\x0d" 

    # 4. ZW Subfile
    subfile_zw = (
        f"ZW"             
        f"ZWA{zwa_final_val}"  
    ) + "\x0d"

    # 5. Header & Offsets
    header_base_len = 21
    designators_total_len = int(num_entries) * 10 
    
    offset_dl = header_base_len + designators_total_len
    len_dl = len(subfile_dl_final.encode('latin-1'))
    
    offset_zw = offset_dl + len_dl
    len_zw = len(subfile_zw.encode('latin-1'))
    
    des_dl = f"DL{offset_dl:04d}{len_dl:04d}"
    des_zw = f"ZW{offset_zw:04d}{len_zw:04d}" 

    header = f"@\x0a\x1e\x0dANSI {iin}{aamva_version}{jurisdiction_version}{num_entries}"
    
    # Final Data String
    final_data = header + des_dl + des_zw + subfile_dl_final + subfile_zw

    # --- C. 编码与渲染 (严格参数: col=20, sec=6, pad=0) ---
    try:
        with st.spinner("正在生成 PDF417..."):
            codes = encode(final_data, columns=20, security_level=6)
            image = render_image(codes, scale=3, ratio=3, padding=0)
            
            # 转为字节流供前端显示
            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()

        # --- D. 显示结果 ---
        with col_preview:
            st.success("条码生成成功！")
            st.image(img_bytes, caption="Generated PDF417", use_column_width=True)
            
            # 下载按钮
            file_name = f"WI_DL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            st.download_button(
                label="⬇️ 下载 PNG 图片",
                data=img_bytes,
                file_name=file_name,
                mime="image/png",
                use_container_width=True
            )

        with col_debug:
            st.info("📊 数据校验信息 (Hex Dump)")
            st.text_area("生成的数据内容", value=final_data, height=150)
            st.caption(f"数据总长度: {len(final_data.encode('latin-1'))} 字节")
            
            # 简单的 Hex 查看器
            hex_data = final_data.encode('latin-1').hex()
            st.code(hex_data, language="text")

    except Exception as e:
        st.error(f"生成出错: {e}")
