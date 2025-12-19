import streamlit as st
import hashlib
import io
from datetime import datetime
from PIL import Image

# --- 尝试加载 pdf417 库 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("❌ 错误：找不到 pdf417 库。请在 requirements.txt 中添加 'pdf417'。")
    st.stop()

# --- 页面配置 ---
st.set_page_config(page_title="AAMVA Generator Pro", layout="wide", page_icon="🆔")

st.title("🆔 AAMVA PDF417 生成器 (纹理增强版)")
st.markdown("""
> **核心功能：** 本工具包含 **“平行黑点纹理 (Numeric Compaction)”** 生成算法。  
> 通过在数据末尾注入“幽灵数据”，强制 PDF417 编码器切换模式，生成真实证件特有的密集平行纹理。
""")
st.divider()

# ==========================================
# 1. 侧边栏：数据录入 (完全保留原始逻辑)
# ==========================================
with st.sidebar:
    st.header("📝 数据录入")

    with st.expander("1. 身份信息", expanded=True):
        ui_fname = st.text_input("名 (First Name)", "ANTHONY")
        ui_mname = st.text_input("中间名 (Middle Name)", "NONE")
        ui_lname = st.text_input("姓 (Last Name)", "ALBERT")

    with st.expander("2. 地址信息", expanded=True):
        ui_addr = st.text_input("街道地址", "W169N10741 REDWOOD LN")
        ui_city = st.text_input("城市", "GERMANTOWN")
        ui_zip = st.text_input("邮编 (输入5位自动补0000)", "530223971")

    with st.expander("3. 日期 (支持斜杠)", expanded=True):
        ui_dob = st.text_input("出生日期 (DOB)", "08/08/1998")
        ui_exp = st.text_input("过期日期 (EXP)", "08/08/2030")
        ui_iss = st.text_input("签发日期 (ISS)", "06/06/2022")

    with st.expander("4. 证件详情", expanded=True):
        ui_dln = st.text_input("驾照号码 (DL Number)", "A4160009828800")
        ui_class = st.text_input("类型 (CLASS)", "D")
        ui_rest = st.text_input("限制 (REST)", "NONE")
        ui_end = st.text_input("背书 (END)", "NONE")
        ui_dd = st.text_input("鉴别码 (DD/DCF)", "OTAJI2022060615751296")
        ui_icn = st.text_input("库存控制号 (ICN/DCK)", "0130100287726422")

    with st.expander("5. 选项与特征", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            ui_realid = st.selectbox("REAL ID?", ["Y", "N"], index=0)
            ui_vet = st.selectbox("退伍军人?", ["Y", "N"], index=1)
        with col2:
            ui_donor = st.selectbox("器官捐献?", ["Y", "N"], index=1)
            ui_sex = st.selectbox("性别", ["1", "2"], index=0)
            
        ui_height_raw = st.text_input("身高 (如 510)", "510")
        ui_eyes = st.text_input("眼睛", "BRN")

    st.markdown("---")
    st.header("🎨 纹理控制 (关键)")
    enable_texture = st.checkbox("启用平行黑点纹理 (Numeric Mode)", value=True, help="在末尾注入大量 0 以触发视觉纹理。")
    padding_amount = st.slider("注入密度 (Ghost Zeros)", 50, 400, 180, help="调整 0 的数量。数量越多，右下角的平行纹理区域越大。")
    force_header_fix = st.checkbox("强制头部兼容 (Header Fix)", value=True, help="将头部不可见字符替换为空格。这是解决 Python 库乱码问题的关键。")

# ==========================================
# 2. 逻辑处理函数
# ==========================================

def convert_height_to_inches(height_str):
    height_str = height_str.strip()
    if len(height_str) < 3: return f"{int(height_str):03d}"
    try:
        return f"{(int(height_str[:-2])*12)+int(height_str[-2:]):03d}"
    except ValueError:
        return height_str

def process_input(val, default, protect_slashes=False):
    val = val.strip().upper()
    if not val: val = default
    if not protect_slashes and "/" in val: val = val.replace("/", "")
    return val

# ==========================================
# 3. 主生成逻辑
# ==========================================

col_preview, col_data = st.columns([1, 1])

with col_preview:
    st.subheader("🖼️ 条码预览")
    generate_btn = st.button("🚀 生成最终条码", type="primary", use_container_width=True)

if generate_btn:
    # --- A. 数据准备 (保持原逻辑) ---
    first_name = process_input(ui_fname, "ANTHONY")
    middle_name = process_input(ui_mname, "NONE")
    last_name = process_input(ui_lname, "ALBERT")
    address = process_input(ui_addr, "W169N10741 REDWOOD LN")
    city = process_input(ui_city, "GERMANTOWN")
    
    zip_temp = process_input(ui_zip, "530223971")
    zip_code = zip_temp.replace("-", "").strip()
    if len(zip_code) == 5: zip_code += "0000"
    
    dob = process_input(ui_dob, "08/08/1998")
    exp_date = process_input(ui_exp, "08/08/2030")
    iss_date = process_input(ui_iss, "06/06/2022")
    
    dl_number = process_input(ui_dln, "A4160009828800")
    class_code = process_input(ui_class, "D")
    rest_code = process_input(ui_rest, "NONE")
    end_code = process_input(ui_end, "NONE")
    dd_code = process_input(ui_dd, "OTAJI2022060615751296", protect_slashes=True)
    icn_code = process_input(ui_icn, "0130100287726422")
    
    real_id_option = process_input(ui_realid, "Y")
    dda_code = "F" if real_id_option == "Y" else "N"
    
    vet_option = process_input(ui_vet, "N")
    donor_option = process_input(ui_donor, "N")
    sex = process_input(ui_sex, "1")
    height = convert_height_to_inches(process_input(ui_height_raw, "510"))
    eyes = process_input(ui_eyes, "BRN")

    # --- B. 构建标准 AAMVA 数据包 ---
    
    # 1. DL Subfile
    subfile_dl_base = (
        f"DL" f"DCA{class_code}\x0a" f"DCB{rest_code}\x0a" f"DCD{end_code}\x0a"
        f"DBA{exp_date}\x0a" f"DCS{last_name}\x0a" f"DAC{first_name}\x0a"
        f"DAD{middle_name}\x0a" f"DBD{iss_date}\x0a" f"DBB{dob}\x0a"
        f"DBC{sex}\x0a" f"DAY{eyes}\x0a" f"DAU{height} IN\x0a"
        f"DAG{address}\x0a" f"DAI{city}\x0a" f"DAJWI\x0a"
        f"DAK{zip_code}  \x0a" f"DAQ{dl_number}\x0a" f"DCF{dd_code}\x0a"
        f"DCGUSA\x0a" f"DDEN\x0a" f"DDFN\x0a" f"DDGN\x0a"
        f"DCK{icn_code}\x0a" f"DDA{dda_code}\x0a"
    )

    # 2. ZW Hash
    zwa_payload = f"{dl_number}{dob}{icn_code}".encode('utf-8')
    zwa_hash = hashlib.sha256(zwa_payload).hexdigest()
    zwa_prefix = "99" if int(zwa_hash[0], 16) % 2 == 0 else "58"
    zwa_suffix = str(int(zwa_hash[-8:], 16)).zfill(9)[:9]
    zwa_final_val = f"{zwa_prefix}{zwa_suffix}"
    
    tail_items = [f"DDB09012015"] 
    if vet_option == "Y": tail_items.append("DDL1")
    if donor_option == "Y": tail_items.append("DDK1")
    subfile_dl_final = subfile_dl_base + "\x0a".join(tail_items) + "\x0d" 

    # 3. ZW Subfile
    subfile_zw = (f"ZW" f"ZWA{zwa_final_val}") + "\x0d"

    # 4. Offsets (Critical: Must be clean length)
    header_base_len = 21
    designators_total_len = 20 # 2 entries * 10
    
    offset_dl = header_base_len + designators_total_len
    len_dl = len(subfile_dl_final.encode('latin-1'))
    
    offset_zw = offset_dl + len_dl
    len_zw = len(subfile_zw.encode('latin-1')) # Clean length
    
    des_dl = f"DL{offset_dl:04d}{len_dl:04d}"
    des_zw = f"ZW{offset_zw:04d}{len_zw:04d}" 

    # --- C. 纹理注入与编码 (The Magic Part) ---
    
    # 1. 头部处理 (Trojan Header)
    # 如果开启 header fix，我们将 \x1e 替换为空格，欺骗库进入 Text Mode
    sep = " " if force_header_fix else "\x1e"
    header = f"@{sep}\x0dANSI 636031080102"
    
    # 2. 组合数据
    # 这是标准的、合法的数据包
    valid_payload = header + des_dl + des_zw + subfile_dl_final + subfile_zw
    
    # 3. 幽灵填充 (Ghost Padding)
    # 如果开启纹理，我们在合法数据之后追加 0
    final_data_to_encode = valid_payload
    if enable_texture:
        final_data_to_encode += ("0" * padding_amount)
        
    try:
        # 编码 (High Security Level for density)
        # security_level=7 是产生密集 Macro 纹理的最佳选择
        codes = encode(final_data_to_encode, columns=20, security_level=7)
        
        # 检查是否触发了 902 (Numeric Latch)
        has_numeric_latch = 902 in codes
        
        # 渲染
        image = render_image(codes, scale=3, ratio=3, padding=0)
        
        # --- D. 结果展示 ---
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        with col_preview:
            st.image(img_bytes, caption="生成的 PDF417 (右下角应有平行黑点)", use_column_width=True)
            
            # 状态指示
            if enable_texture:
                if has_numeric_latch:
                    st.success("✅ **成功触发数字模式 (Parallel Dots)!**\n\n检测到 Code 902，纹理已生成。")
                else:
                    st.error("❌ **未触发数字模式 (Still Random Noise)**\n\n请尝试勾选 '强制头部兼容' 或增加注入密度。")

            st.download_button(
                label="⬇️ 下载 PNG",
                data=img_bytes,
                file_name=f"WI_DL_{last_name}_{datetime.now().strftime('%H%M%S')}.png",
                mime="image/png",
                type="primary",
                use_container_width=True
            )

        with col_data:
            st.info("📊 数据结构校验")
            st.text(f"Offset DL: {offset_dl} (Length: {len_dl})")
            st.text(f"Offset ZW: {offset_zw} (Length: {len_zw})")
            st.text(f"Inject Padding: {padding_amount if enable_texture else 0} zeros")
            
            st.markdown("**生成数据 (Hex 预览):**")
            st.code(final_data_to_encode.encode('latin-1').hex()[:200] + "...", language="text")

    except Exception as e:
        st.error(f"生成出错: {e}")
