import streamlit as st
import hashlib
import io
from datetime import datetime

# --- 尝试加载库 ---
try:
    from pdf417 import encode, render_image
    from PIL import Image
except ImportError:
    st.error("请安装库: pip install pdf417 Pillow")
    st.stop()

st.set_page_config(page_title="WI Texture Lab", layout="wide")
st.title("🔬 WI 驾照纹理实验室：寻找填充材质")
st.markdown("""
**核心发现：** 真实 ID 未使用 Numeric Mode (902)。
**推测：** 它使用的是 Byte/Text Mode，但填充了特定的**重复字符**导致了平行纹理。
**任务：** 请尝试下方的不同填充材质，对比哪一种的纹理与真驾照最像。
""")

# ==========================================
# 1. 简化的数据录入 (保持核心结构)
# ==========================================
with st.sidebar:
    st.header("1. 基础设置")
    # 这里使用硬编码的默认值以节省时间，专注于纹理测试
    last_name = st.text_input("姓 (Last Name)", "ALBERT")
    padding_count = st.slider("填充长度", 50, 400, 200, help="调整填充区域的大小")
    
    st.divider()
    st.header("🧪 2. 填充材质选择 (关键)")
    
    pad_type = st.radio(
        "选择用于填充剩余空间的字符：",
        ("Null Byte (\\x00)", "Space (空格)", "Zero ('0' - Byte Mode)"),
        index=0
    )
    
    st.info("说明：真驾照的平行纹理很可能来自于 Null Byte 的重复排列。")

# ==========================================
# 2. 生成逻辑
# ==========================================

def get_padding_char(p_type):
    if "Null" in p_type: return "\x00"
    if "Space" in p_type: return " "
    if "Zero" in p_type: return "0"
    return "\x00"

def generate_barcode():
    # --- A. 构建标准数据 (不做特洛伊欺骗，模拟原生 Byte Mode) ---
    # 使用标准的 \x1e 头部，看看 Python 库在纯 Byte Mode 下的表现
    header = "@\x0a\x1e\x0dANSI 636031080102"
    
    # 模拟一段数据
    payload = (
        "DLDCAD\x0aDCBNONE\x0aDCDNONE\x0aDBA08082030\x0aDCSALBERT\x0aDACANTHONY\x0a"
        "DADNONE\x0aDBD06062022\x0aDBB08081998\x0aDBC1\x0aDAYBRN\x0aDAU070 IN\x0a"
        "DAGW169N10741 REDWOOD LN\x0aDAIGERMANTOWN\x0aDAJWI\x0aDAK5302239710000  \x0a"
        "DAQA4160009828800\x0aDCFOTAJI2022060615751296\x0aDCGUSA\x0ADDEN\x0ADDFN\x0a"
        "DDGN\x0aDCK0130100287726422\x0aDDAN\x0aDDB09012015\x0d"
        "ZWZWA99000000000\x0d"
    )
    
    # 简单的偏移量模拟
    full_data_structure = header + "DL00410276ZW03170017" + payload
    
    # --- B. 注入填充材质 ---
    char = get_padding_char(pad_type)
    padding_str = char * padding_count
    
    final_data = full_data_structure + padding_str
    
    return final_data, char

# ==========================================
# 3. 渲染与分析
# ==========================================

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🚀 生成并分析", type="primary"):
        data, char_used = generate_barcode()
        
        try:
            # 编码
            codes = encode(data, columns=20, security_level=5)
            
            # 渲染
            img = render_image(codes, scale=3, ratio=3, padding=0)
            
            # 转换
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()
            
            st.image(img_bytes, caption=f"填充材质: {pad_type}", use_column_width=True)
            
            # 下载
            st.download_button("⬇️ 下载此版本", img_bytes, "test_texture.png", "image/png")
            
        except Exception as e:
            st.error(f"生成失败: {e}")

with col2:
    st.subheader("📊 基因诊断")
    if 'codes' in locals():
        # 检查是否包含 Numeric Mode (902)
        has_902 = 902 in codes
        # 检查是否包含 Text Mode (900)
        has_900 = 900 in codes
        # 检查是否包含 Byte Mode Shift (901/924)
        has_byte = 901 in codes or 924 in codes
        
        st.write(f"**填充字符 Hex:** `{char_used.encode('latin-1').hex()}`")
        
        st.divider()
        st.markdown("**编码器模式检测:**")
        if has_902:
            st.error("⚠️ 检测到 Numeric Mode (902) - 这与真驾照不符")
        else:
            st.success("✅ 未检测到 Numeric Mode (902) - 符合真驾照特征")
            
        if has_byte:
            st.info("ℹ️ 检测到 Byte Mode (901/924) - 这是预期的")
            
        st.markdown("""
        **如何判断哪个是对的？**
        请观察生成的图片右下角：
        1. **Null (\\x00):** 通常生成垂直方向的、断断续续的块状纹理。
        2. **Space ( ):** 通常生成非常空的、或者细碎的纹理。
        3. **Zero (0):** 如果在 Byte Mode 下，会生成杂乱的噪点。
        """)
