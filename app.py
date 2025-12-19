import streamlit as st
import hashlib
import io
from datetime import datetime

# --- 库加载 ---
try:
    from pdf417 import encode, render_image
    from PIL import Image
except ImportError:
    st.error("❌ 错误：请安装 pdf417 和 Pillow 库。")
    st.stop()

# --- 页面配置 ---
st.set_page_config(page_title="AAMVA Generator (Data Focus)", layout="wide", page_icon="🛡️")

st.title("🛡️ AAMVA PDF417 生成器 (数据一致性版)")
st.markdown("""
> **当前策略：** 优先保证数据纯净度。
> **填充方案：** 使用 **Null Byte (\\x00)** 填充剩余空间。
> **结果：** 扫描数据干净无杂质（无尾部空格或0），物理尺寸通过填充量调整，视觉纹理为垂直块状（Byte Mode）。
""")
st.divider()

# ==========================================
# 1. 侧边栏：数据录入
# ==========================================
with st.sidebar:
    st.header("📝 1. 身份信息")
    ui_fname = st.text_input("名 (First Name)", "ANTHONY")
    ui_mname = st.text_input("中间名 (Middle Name)", "NONE")
    ui_lname = st.text_input("姓 (Last Name)", "ALBERT")

    st.header("📍 2. 地址信息")
    ui_addr = st.text_input("街道地址", "W169N10741 REDWOOD LN")
    ui_city = st.text_input("城市", "GERMANTOWN")
    ui_zip = st.text_input("邮编 (输入5位自动补0000)", "530223971")

    st.header("📅 3. 日期 (MMDDYYYY)")
    ui_dob = st.text_input("出生日期", "08081998")
    ui_exp = st.text_input("过期日期", "08082030")
    ui_iss = st.text_input("签发日期", "06062022")

    st.header("🚘 4. 证件详情")
    ui_dln = st.text_input("驾照号码", "A4160009828800")
    ui_class = st.text_input("类型 (CLASS)", "D")
    ui_rest = st.text_input("限制 (REST)", "NONE")
    ui_end = st.text_input("背书 (END)", "NONE")
    ui_dd = st.text_input("鉴别码 (DD/DCF)", "OTAJI2022060615751296")
    ui_icn = st.text_input("库存控制号 (ICN)", "0130100287726422")

    st.header("📏 5. 物理特征")
    ui_sex = st.selectbox("性别", ["1", "2"], index=0)
    ui_height = st.text_input("身高 (如 510)", "510")
    ui_eyes = st.text_input("眼睛", "BRN")

    st.markdown("---")
    st.header("📐 尺寸微调")
    # 这里不需要选择材质了，强制使用 Null Byte
    padding_amount = st.slider("填充长度 (调整条码大小)", 50, 400, 200, 
                               help="增加此数值可以撑大条码的物理面积。")

# ==========================================
# 2. 逻辑处理
# ==========================================

def convert_height(h):
    h = h.strip()
    try:
        if len(h) < 3: return f"{int(h):03d}"
        return f"{(int(h[:-2])*12)+int(h[-2:]):03d}"
    except: return h

def clean_input(val, default):
    val = val.strip().upper()
    return val if val else default

# ==========================================
# 3. 生成逻辑
# ==========================================

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🖼️ 条码预览")
    generate_btn = st.button("🚀 生成纯净数据条码", type="primary", use_container_width=True)

if generate_btn:
    # --- A. 数据清洗 ---
    fname = clean_input(ui_fname, "ANTHONY")
    lname = clean_input(ui_lname, "ALBERT")
    mname = clean_input(ui_mname, "NONE")
    
    addr = clean_input(ui_addr, "ADDRESS")
    city = clean_input(ui_city, "CITY")
    zipc = clean_input(ui_zip, "00000").replace("-","").strip()
    if len(zipc) == 5: zipc += "0000"
    
    # 日期处理：移除斜杠
    dob = clean_input(ui_dob, "01011990").replace("/","")
    exp = clean_input(ui_exp, "01012030").replace("/","")
    iss = clean_input(ui_iss, "01012022").replace("/","")
    
    dln = clean_input(ui_dln, "A000000000")
    dd = clean_input(ui_dd, "REF123") # 保留斜杠如果原本就有
    icn = clean_input(ui_icn, "ICN123")
    sex = ui_sex
    eyes = clean_input(ui_eyes, "BRN")
    h_in = convert_height(clean_input(ui_height, "510"))
    
    cls = clean_input(ui_class, "D")
    rest = clean_input(ui_rest, "NONE")
    end = clean_input(ui_end, "NONE")

    # --- B. 构建 Subfiles ---
    # 1. DL Data
    subfile_dl = (
        f"DLDCAD\x0aDCB{rest}\x0aDCD{end}\x0aDBA{exp}\x0aDCS{lname}\x0aDAC{fname}\x0a"
        f"DAD{mname}\x0aDBD{iss}\x0aDBB{dob}\x0aDBC{sex}\x0aDAY{eyes}\x0aDAU{h_in} IN\x0a"
        f"DAG{addr}\x0aDAI{city}\x0aDAJWI\x0aDAK{zipc}  \x0aDAQ{dln}\x0a"
        f"DCF{dd}\x0aDCGUSA\x0ADDEN\x0ADDFN\x0ADDGN\x0ADCK{icn}\x0ADDAN\x0a"
        f"DDB09012015\x0d"
    )
    
    # 2. ZW Data (Hash)
    try:
        zhash = hashlib.sha256(f"{dln}{dob}{icn}".encode()).hexdigest()
        zval = ("99" if int(zhash[0],16)%2==0 else "58") + str(int(zhash[-8:],16)).zfill(9)[:9]
    except:
        zval = "99000000000"
    subfile_zw = f"ZWZWA{zval}\x0d"
    
    # --- C. 计算 Offset (严格基于有效数据) ---
    h_len = 21 # Header length
    des_len = 20 # 2 entries * 10
    
    off_dl = h_len + des_len
    len_dl = len(subfile_dl.encode('latin-1'))
    
    off_zw = off_dl + len_dl
    len_zw = len(subfile_zw.encode('latin-1'))
    
    des_dl = f"DL{off_dl:04d}{len_dl:04d}"
    des_zw = f"ZW{off_zw:04d}{len_zw:04d}"
    
    # --- D. 组合最终数据 ---
    # 1. 头部：使用完全标准的 AAMVA 头部 (带 \x1e)
    # 这会告诉扫描器这是一个合法的二进制数据包
    header = f"@\x0a\x1e\x0dANSI 636031080102"
    
    valid_payload = header + des_dl + des_zw + subfile_dl + subfile_zw
    
    # 2. 填充：使用 Null Byte (\x00)
    # 这不会在扫描结果中显示可见字符
    padding = "\x00" * padding_amount
    
    final_data = valid_payload + padding
    
    # --- E. 编码与渲染 ---
    try:
        # 使用 PDF417 编码
        # 库会自动检测到 \x00 和 \x1e，全程使用 Byte Compaction Mode
        codes = encode(final_data, columns=20, security_level=5)
        image = render_image(codes, scale=3, ratio=3, padding=0)
        
        # 显示
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        with col1:
            st.success("✅ 生成成功 (数据一致性优先)")
            st.image(img_bytes, caption="最终条码 (Byte Mode 填充)", use_column_width=True)
            
            # 下载
            file_name = f"WI_DL_CLEAN_{datetime.now().strftime('%H%M%S')}.png"
            st.download_button("⬇️ 下载 PNG", img_bytes, file_name, "image/png", type="primary")

        with col2:
            st.info("📊 数据结构报告")
            st.write(f"**有效载荷长度:** {len(valid_payload)} 字节")
            st.write(f"**填充材质:** Null Byte (\\x00)")
            st.write(f"**填充数量:** {padding_amount}")
            st.markdown("""
            **扫描预期:**
            * 使用记事本扫描时，数据将在 `...DDB09012015` 处完美结束。
            * 光标不会移动到下一行，后面没有任何可见的乱码。
            * 条码右下角纹理将呈现为垂直堆叠的块状（这是 Null 在 Byte Mode 下的正常物理表现）。
            """)

    except Exception as e:
        st.error(f"生成失败: {e}")
