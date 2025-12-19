import streamlit as st
import hashlib
import io
import shutil
from datetime import datetime

# --- 尝试加载库 ---
try:
    import treepoem
    from PIL import Image
except ImportError:
    st.error("❌ 错误：找不到必要的库。请检查 requirements.txt 是否包含 'treepoem' 和 'Pillow'。")
    st.stop()

# --- 检查 Ghostscript 环境 ---
if not shutil.which("gs"):
    st.warning("⚠️ 警告：未检测到 Ghostscript (gs)。在本地请安装 Ghostscript；在 Streamlit Cloud 请添加 packages.txt。")

# --- 页面配置 ---
st.set_page_config(page_title="AAMVA Generator (Industrial Engine)", layout="wide", page_icon="🏭")

st.title("🏭 AAMVA 生成器 (Treepoem/BWIPP 工业引擎版)")
st.markdown("""
> **引擎升级：** 本版本使用 **Treepoem (BWIPP)** 替代了旧的 Python 库。
> **优势：** 它是工业级标准，原生支持 **Numeric Compaction**。只要数据里有长串数字（如填充的0），它会**自动**生成完美的平行黑点纹理，无需修改头部或破坏数据结构。
""")
st.divider()

# ==========================================
# 1. 侧边栏：数据录入 (完全保持原始逻辑)
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
    st.header("🎨 工业级纹理控制")
    
    # 工业引擎不需要"头部欺骗"，只需要填充 0，它自己就会变聪明
    enable_padding = st.checkbox("启用填充 (Ghost Padding)", value=True, help="在有效数据后追加 0。Treepoem 会自动将其压缩为平行纹理。")
    padding_amount = st.slider("纹理区域大小 (0的数量)", 50, 500, 200, help="调整 0 的数量以匹配真实驾照的宽度。")

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
    st.subheader("🖼️ Treepoem 渲染预览")
    generate_btn = st.button("🚀 启动工业引擎生成", type="primary", use_container_width=True)

if generate_btn:
    # --- A. 数据构建 (严格保持您校验过的逻辑) ---
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

    # 4. Offsets
    header_base_len = 21
    designators_total_len = 20
    offset_dl = header_base_len + designators_total_len
    len_dl = len(subfile_dl_final.encode('latin-1'))
    offset_zw = offset_dl + len_dl
    len_zw = len(subfile_zw.encode('latin-1'))
    
    des_dl = f"DL{offset_dl:04d}{len_dl:04d}"
    des_zw = f"ZW{offset_zw:04d}{len_zw:04d}" 

    # --- 关键：Treepoem 不需要"头部欺骗" ---
    # 我们可以使用标准的 AAMVA 头部，因为它足够聪明，能正确处理
    header = f"@\x0a\x1e\x0dANSI 636031080102"
    
    # 组合有效数据
    valid_payload = header + des_dl + des_zw + subfile_dl_final + subfile_zw
    
    # 幽灵填充 (Ghost Padding)
    # 即使是 Treepoem，我们也需要提供"内容"来填充空间
    # 但 Treepoem 看到这堆 0 会自动且必然地使用 Numeric Compaction
    final_data_to_encode = valid_payload
    if enable_padding:
        final_data_to_encode += ("0" * padding_amount)

    try:
        with st.spinner("启动 BWIPP 引擎渲染中 (Ghostscript)..."):
            # --- 使用 Treepoem 生成 ---
            # options 参数对应 BWIPP 的参数
            image = treepoem.generate_barcode(
                barcode_type='pdf417',
                data=final_data_to_encode,
                options={
                    'columns': 20,       # 强制20列
                    'eclevel': 5,        # 纠错等级 (AAMVA推荐3-5)
                    # Treepoem 默认就很聪明，不需要额外设置 macro 参数
                    # 只要数据是长串数字，它就会生成平行纹理
                }
            )

            # 转换为 Streamlit 可显示的格式
            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()

        with col_preview:
            st.success("✅ **工业引擎生成成功**")
            st.image(img_bytes, caption="Treepoem/BWIPP 生成结果 (注意观察完美的平行纹理)", use_column_width=True)
            
            st.download_button(
                label="⬇️ 下载 PNG (Treepoem版)",
                data=img_bytes,
                file_name=f"WI_DL_BWIPP_{padding_amount}.png",
                mime="image/png",
                type="primary",
                use_container_width=True
            )

        with col_data:
            st.info("⚙️ 引擎状态报告")
            st.write("Treepoem (BWIPP) 已自动优化编码结构。")
            st.write(f"数据总长: {len(final_data_to_encode)} 字节")
            st.markdown("""
            **为什么这个版本更好？**
            1. **无需Hack头部：** 我们使用了标准的 `\\x1e` 分隔符，数据结构更规范。
            2. **自动模式切换：** BWIPP 引擎极其智能，看到末尾的 `0` 会自动使用数字压缩，生成最纯正的平行纹理。
            """)

    except Exception as e:
        st.error(f"Treepoem 生成失败: {e}")
        st.error("请确认服务器已安装 Ghostscript。")
        with st.expander("错误详情"):
            st.exception(e)
