import cv2
from PIL import Image
import gradio as gr
import os
import tempfile
import zipfile
import io
from rembg import remove, new_session

MAX_DURATION = 10.0
MAX_IMAGES = 20

# 建立一個全域字典來儲存已載入的模型 (快取 session)
sessions = {}

def get_session(model_name):
    """取得模型 session，如果沒載入過就載入，有就直接拿來用"""
    if model_name not in sessions:
        print(f"正在載入模型: {model_name} ... (首次載入需要下載，請稍候)")
        sessions[model_name] = new_session(model_name)
    return sessions[model_name]

def toggle_rembg_sections(do_remove_bg: bool):
    """勾選 / 取消 去背時，控制『模型選擇』與『Alpha Matting』區塊顯示"""
    return (
        gr.update(visible=do_remove_bg),  # model_group
        gr.update(visible=do_remove_bg),  # alpha_group
    )

def resize_for_line_sticker(img, max_width=320, max_height=270):
    """將圖片縮放至 LINE 動態貼圖規格 (保持比例)"""
    width, height = img.size
    width_ratio = max_width / width
    height_ratio = max_height / height
    ratio = min(width_ratio, height_ratio)
    
    if ratio >= 1:
        return img, width, height
    
    new_width = int(width * ratio)
    new_height = int(height * ratio)
    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return resized_img, new_width, new_height

# 修改：加入 dpi_value 參數
def extract_frames(video_path, mode, interval_sec, num_frames, do_remove_bg, 
                   model_name, dpi_value, fg_threshold, bg_threshold, erode_size, resize_option):

    if video_path is None or video_path == "":
        return [], "請先上傳影片 😆", None

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return [], "無法讀取影片,請確認格式是否正確。", None

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

    if fps <= 0 or frame_count <= 0:
        cap.release()
        return [], "無法取得影片資訊(可能是不支援的格式)。", None

    duration = frame_count / fps

    if duration > MAX_DURATION:
        cap.release()
        return [], f"影片長度 {duration:.2f} 秒,已超過 {MAX_DURATION} 秒上限。", None

    # 計算取樣點
    timestamps = []
    if mode == "每隔幾秒截圖":
        if interval_sec is None or interval_sec <= 0:
            interval_sec = 1.0
        t = 0.0
        while t < duration and len(timestamps) < MAX_IMAGES:
            timestamps.append(t)
            t += interval_sec
    elif mode == "指定總張數":
        if num_frames is None or num_frames <= 0:
            num_frames = 1
        n = min(int(num_frames), MAX_IMAGES)
        step = duration / (n + 1)
        timestamps = [step * (i + 1) for i in range(n)]

    images = []
    for t in timestamps:
        frame_idx = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        
        # 修改：使用使用者設定的 DPI
        pil_img.info['dpi'] = (int(dpi_value), int(dpi_value))
        
        images.append(pil_img)
        if len(images) >= MAX_IMAGES:
            break

    cap.release()

    if len(images) == 0:
        return [], "沒有擷取到任何圖片。", None

    if len(images) > 0:
        original_width, original_height = images[0].size
        resolution_info = f"{original_width} x {original_height} 像素"
    else:
        resolution_info = ""

    # 去背邏輯
    mode_text = ""
    if do_remove_bg:
        current_session = get_session(model_name)
        processed = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            input_bytes = buf.getvalue()

            output_bytes = remove(
                input_bytes,
                session=current_session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=int(fg_threshold),
                alpha_matting_background_threshold=int(bg_threshold),
                alpha_matting_erode_size=int(erode_size),
                post_process_mask=True
            )

            out_img = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
            # 修改：去背後重新設定 DPI
            out_img.info['dpi'] = (int(dpi_value), int(dpi_value))
            processed.append(out_img)
        images = processed
        mode_text = f"(已去背 - 模型:{model_name})"
    else:
        processed_images = []
        for img in images:
            rgba_img = img.convert("RGBA")
            # 修改：保留 DPI 資訊
            rgba_img.info['dpi'] = (int(dpi_value), int(dpi_value))
            processed_images.append(rgba_img)
        images = processed_images

    # 調整尺寸
    if resize_option == "LINE 動態貼圖 (最寬320px × 最高270px)":
        resized_images = []
        for img in images:
            resized_img, new_w, new_h = resize_for_line_sticker(img)
            # 修改：縮放後保留 DPI
            resized_img.info['dpi'] = (int(dpi_value), int(dpi_value))
            resized_images.append(resized_img)
        images = resized_images
        final_width, final_height = images[0].size
        size_text = f"\n📐 原始尺寸: {resolution_info}\n📏 輸出尺寸: {final_width} x {final_height} 像素 (LINE 貼圖規格)\n🖨️ 設定 DPI: {dpi_value}"
    else:
        final_width, final_height = images[0].size
        size_text = f"\n📐 輸出尺寸: {resolution_info}\n🖨️ 設定 DPI: {dpi_value}"

    info = f"成功擷取 {len(images)} 張圖片 {mode_text}{size_text}"

    # ZIP 打包
    temp_dir = tempfile.mkdtemp()
    img_paths = []
    for i, img in enumerate(images, start=1):
        path = os.path.join(temp_dir, f"frame_{i:03d}.png")
        # 修改：儲存時寫入 DPI 元數據
        img.save(path, dpi=(int(dpi_value), int(dpi_value)))
        img_paths.append(path)

    zip_path = os.path.join(temp_dir, "frames.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in img_paths:
            z.write(p, arcname=os.path.basename(p))

    return images, info, zip_path


def switch_mode(mode):
    if mode == "每隔幾秒截圖":
        return gr.update(visible=True), gr.update(visible=False)
    else:
        return gr.update(visible=False), gr.update(visible=True)


with gr.Blocks(theme=gr.themes.Default()) as demo:
    gr.Markdown("# 🎬 影片擷取 + AI 智能去背工具")
    gr.Markdown("支援多種去背模型切換，專為 LINE 貼圖製作優化")
    gr.Markdown("喜歡這個工具嗎？請 [點此贊助](https://portaly.cc/xiaohu/support)，鼓勵小胡持續創作")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📹 影片上傳")
            video_input = gr.Video(
                label="上傳影片(最多 10 秒)",
                sources=["upload"],
                format="mp4"
            )

            gr.Markdown("### ⚙️ 擷取設定")
            mode_radio = gr.Radio(
                ["每隔幾秒截圖", "指定總張數"],
                value="每隔幾秒截圖",
                label="擷取模式",
            )
            interval_sec_input = gr.Number(
                value=1.0, label="每隔幾秒截一張(秒)", visible=True
            )
            num_frames_input = gr.Slider(
                minimum=1, maximum=20, value=5, step=1,
                label="指定要擷取的張數(最多 20)", visible=False
            )

        with gr.Column(scale=1):
            gr.Markdown("### 🎨 輸出與去背設定")
            
            # 新增：DPI 設定滑桿
            gr.Markdown("#### 🖨️ DPI 解析度設定")
            dpi_slider = gr.Slider(
                minimum=72,
                maximum=300,
                value=300,
                step=1,
                label="設定圖片 DPI",
                info="🔹 72 DPI：適合純螢幕觀看、網頁使用 (檔案最小)\n🔹 300 DPI：適合後續匯入 Procreate 繪圖、印刷使用 (LINE 貼圖建議選此項以利後製)"
            )
            

            gr.Markdown("#### 📏 輸出尺寸設定")
            resize_radio = gr.Radio(
                choices=["原始影片尺寸", "LINE 動態貼圖 (最寬320px × 最高270px)"],
                value="原始影片尺寸",
                label="選擇輸出尺寸",
                info="LINE 貼圖會自動等比例縮放至規格內"
            )
            
            gr.Markdown("---") # 分隔線
            remove_bg_checkbox = gr.Checkbox(
                value=False,
                label="啟用 AI 去背功能",
            )

            with gr.Accordion("🤖 AI 模型選擇", open=True, visible=False) as model_group:
                model_dropdown = gr.Dropdown(
                    choices=[
                        ("u2net | 通用標準 (最穩定，適合大多數情況)", "u2net"),
                        ("isnet-anime | 動漫二次元 (製作卡通貼圖首選，線條乾淨)", "isnet-anime"),
                        ("isnet-general-use | 新版通用 (細節處理比 u2net 更好)", "isnet-general-use"),
                        ("u2net_human_seg | 真人專用 (針對人體輪廓優化)", "u2net_human_seg"),
                        ("silueta | 快速人像 (體積小速度快，適合全身照)", "silueta"),
                        ("u2net_cloth_seg | 衣物識別 (只保留衣服，去除人物)", "u2net_cloth_seg"),
                        ("u2netp | 輕量版 (速度最快，但在低解析度下邊緣較粗糙)", "u2netp"),
                    ],
                    value="u2net",
                    label="選擇去背模型",
                    info="💡 提示：製作「大胡/小胡」貼圖時，強烈建議選擇 isnet-anime 模型！"
                )

            with gr.Accordion("🔧 進階參數 (邊緣修飾)", open=True, visible=False) as alpha_group:
                fg_threshold_slider = gr.Slider(
                    minimum=180, maximum=255, value=240, step=5,
                    label="前景閾值", info="越高越嚴格 (180-255)"
                )
                bg_threshold_slider = gr.Slider(
                    minimum=0, maximum=30, value=10, step=1,
                    label="背景閾值", info="越低越嚴格 (0-30)"
                )
                erode_size_slider = gr.Slider(
                    minimum=0, maximum=20, value=10, step=1,
                    label="侵蝕大小", info="去除邊緣殘留 (0-20px)"
                )

    run_btn = gr.Button("🎉 開始擷取", variant="primary", size="lg")

    gr.Markdown("### 📊 擷取結果")
    info_text = gr.Markdown("")
    gallery = gr.Gallery(columns=4, label="圖片預覽", height="auto")
    zip_output = gr.File(label="📦 下載所有圖片 (ZIP)")

    gr.Markdown("""
        ---
        ### 💡 參數說明
        
        #### 🎨 去背參數
        | 參數 | 作用 | 調整建議 |
        |------|------|----------|
        | **前景閾值** | 判斷哪些像素確定是前景 | 有細節(頭髮)→降低 / 要銳利→提高 |
        | **背景閾值** | 判斷哪些像素確定是背景 | 背景不乾淨→提高 / 主體被切→降低 |
        | **侵蝕大小** | 邊緣向內收縮的程度 | 有色邊→提高 / 主體變小→降低 |
        
        #### 📏 LINE 動態貼圖規範
        - **尺寸限制**: 最寬 320px × 最高 270px
        - **縮放方式**: 等比例縮放,保持原始比例不變形
        - **範例**: 
            - 1920x1080 → 縮放為 320x180
            - 1080x1920 (直式) → 縮放為 151x270
            - 640x480 → 320x240 (已符合規格)
        
        **常見問題**:
        - 邊緣有白邊/綠邊 → 增加侵蝕大小
        - 主體被切掉 → 減少侵蝕大小
        - 頭髮細節丟失 → 降低前景閾值
        - 背景不乾淨 → 提高背景閾值
        """)

    # 事件綁定
    remove_bg_checkbox.change(
        fn=toggle_rembg_sections,
        inputs=remove_bg_checkbox,
        outputs=[model_group, alpha_group],
    )

    mode_radio.change(
        fn=switch_mode,
        inputs=mode_radio,
        outputs=[interval_sec_input, num_frames_input],
    )

    run_btn.click(
        fn=extract_frames,
        inputs=[
            video_input,
            mode_radio,
            interval_sec_input,
            num_frames_input,
            remove_bg_checkbox,
            model_dropdown,
            dpi_slider,  # 加入 DPI 參數
            fg_threshold_slider,
            bg_threshold_slider,
            erode_size_slider,
            resize_radio,
        ],
        outputs=[gallery, info_text, zip_output]
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)